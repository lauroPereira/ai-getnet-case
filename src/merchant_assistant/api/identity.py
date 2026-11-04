"""Identity: credential -> principal -> scopes -> merchant (ADR 0017, spec v0.7.0 version 2).

The assistant issues RS256 access tokens (RFC 9068 profile) for the synthetic demo users (password grant) and service
clients (client credentials), publishes its public key as JWKS and verifies every bearer token in one place
(`Identity.verify`, the `resolve_credential` of the ADR). Pointing `JWT_JWKS_URL` and `JWT_ISSUER` at an external
OIDC provider replaces the issuer without touching the routes. Everything after verification works on a `Principal`:
scope and merchant checks on every tool call, the handoff case write, the rate limit and the read routes.

Secrets: passwords and client secrets are stored only as PBKDF2-SHA256 hashes; the signing key lives in the runtime
directory (or `JWT_PRIVATE_KEY_PATH`), never in the repository; tokens and secrets are never logged.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import math
import os
import secrets
import sqlite3
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from merchant_assistant.config import Settings

Role = Literal["merchant", "operator", "service", "demo", "admin"]

SUPPORT_READ = "support:read"
HANDOFF_CREATE = "handoff:create"
CONVERSATION_READ = "conversation:read"
HANDOFF_OPERATE = "handoff:operate"
HANDOFF_INTEGRATE = "handoff:integrate"
KB_ADMIN = "kb:admin"
PROFILES_ADMIN = "profiles:admin"

# Single role -> scopes table (spec v0.7.0, "Contrato entre os times / Identidade").
ROLE_SCOPES: dict[str, tuple[str, ...]] = {
    "merchant": (SUPPORT_READ, HANDOFF_CREATE, CONVERSATION_READ),
    "demo": (SUPPORT_READ, HANDOFF_CREATE, CONVERSATION_READ),
    "operator": (HANDOFF_OPERATE, SUPPORT_READ),
    "service": (HANDOFF_INTEGRATE,),
    "admin": (KB_ADMIN, PROFILES_ADMIN, SUPPORT_READ, HANDOFF_CREATE, CONVERSATION_READ),
}
ALL_SCOPES = tuple(sorted({scope for scopes in ROLE_SCOPES.values() for scope in scopes}))

AUDIENCE = "merchant-assistant"
TICKETING_AUDIENCE = "ticketing"
PERSON_TTL_SECONDS = 60 * 60
SERVICE_TTL_SECONDS = 10 * 60
LEEWAY_SECONDS = 30
TOKEN_TYPE = "at+jwt"
EXAMPLE_SUFFIX = "-fictitious"
WINDOW_SECONDS = 60

# Synthetic demo users (spec D1): username -> (role, merchant). Passwords come from DEMO_USER_PASSWORDS.
DEMO_USERS: dict[str, tuple[Role, str | None]] = {
    "cliente1988": ("merchant", "cliente1988"),
    "cliente_demo_002": ("merchant", "cliente_demo_002"),
    "op_ana": ("operator", None),
    "op_bruno": ("operator", None),
}
SERVICE_CLIENTS = {"ticketing-demo": "ticketing"}  # client_id -> service principal subject
PUBLIC_CLIENTS = ("merchant-assistant-web", "merchant-assistant-cli")  # password grant; no client secret
DEFAULT_PUBLIC_CLIENT = PUBLIC_CLIENTS[0]


class InvalidToken(Exception):
    """The bearer token is missing, malformed, tampered, expired, revoked or from another issuer/audience."""


class CredentialConfigError(ValueError):
    """Invalid credential configuration: the API refuses to start."""


@dataclass(frozen=True)
class Principal:
    """Who acts. `customer_id` is None for operators and services: they act only on the merchant of a case, read
    from the case by the server."""

    principal_id: str
    role: Role
    customer_id: str | None
    scopes: tuple[str, ...]

    @classmethod
    def of(cls, role: Role, subject: str, customer_id: str | None = None) -> Principal:
        """Principal ids: `merchant:<customer_id>`, `operator:<id>`, `service:<name>`, `demo:default`,
        `admin:default`."""
        return cls(f"{role}:{subject}", role, customer_id, ROLE_SCOPES[role])

    @classmethod
    def merchant(cls, customer_id: str) -> Principal:
        return cls.of("merchant", customer_id, customer_id)

    @classmethod
    def operator(cls, operator_id: str) -> Principal:
        return cls.of("operator", operator_id)

    @classmethod
    def from_session(cls, row: dict) -> Principal:
        """From the dict the route dependency hands to the routes."""
        return cls(row["principal_id"], row["role"], row.get("customer_id"), tuple(row.get("scopes") or ()))

    @property
    def audience(self) -> list[str]:
        return [AUDIENCE, TICKETING_AUDIENCE] if self.role == "operator" else [AUDIENCE]

    def has(self, scope: str) -> bool:
        return scope in self.scopes


# --- secrets ------------------------------------------------------------------------------------------------------


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def hash_secret(secret: str, iterations: int) -> str:
    """PBKDF2-SHA256 from the standard library: `pbkdf2_sha256$<iterations>$<salt>$<hash>`."""
    salt = secrets.token_bytes(16)
    derived = hashlib.pbkdf2_hmac("sha256", secret.encode("utf-8"), salt, iterations)
    return f"pbkdf2_sha256${iterations}${_b64(salt)}${_b64(derived)}"


def verify_secret(secret: str, stored: str) -> bool:
    try:
        scheme, iterations, salt, expected = stored.split("$")
        if scheme != "pbkdf2_sha256":
            return False
        derived = hashlib.pbkdf2_hmac("sha256", secret.encode("utf-8"), _unb64(salt), int(iterations))
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(_b64(derived), expected)


def _iterations(stored: str) -> int | None:
    try:
        return int(stored.split("$")[1])
    except (IndexError, ValueError):
        return None


@dataclass(frozen=True)
class Account:
    account_id: str  # `user:<username>` or `client:<client_id>`
    kind: Literal["user", "client"]
    principal: Principal
    secret: str


def _pairs(raw: str, variable: str) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for item in (part.strip() for part in raw.split(",")):
        if not item:
            continue
        name, sep, secret = item.partition(":")
        if not sep or not name.strip() or not secret.strip():
            raise CredentialConfigError(f"{variable}: each entry must be <username>:<password>")
        pairs.append((name.strip(), secret.strip()))
    return pairs


def _secret(value) -> str:
    return value.get_secret_value().strip() if value else ""


def configured_accounts(settings: Settings) -> list[Account]:
    """Users and clients from the configuration (spec D1). Raises CredentialConfigError when it is invalid."""
    accounts: list[Account] = []
    seen: set[str] = set()
    for username, password in _pairs(_secret(settings.demo_user_passwords), "DEMO_USER_PASSWORDS"):
        if username not in DEMO_USERS:
            raise CredentialConfigError(f"DEMO_USER_PASSWORDS: unknown demo user {username}")
        if username in seen:
            raise CredentialConfigError(f"DEMO_USER_PASSWORDS: user {username} is repeated")
        seen.add(username)
        role, customer_id = DEMO_USERS[username]
        accounts.append(Account(f"user:{username}", "user", Principal.of(role, username, customer_id), password))
    for role, value in (("demo", settings.api_demo_password), ("admin", settings.api_admin_password)):
        if password := _secret(value):
            customer_id = settings.api_demo_customer_id if role == "demo" else None  # D20: admin has none
            accounts.append(Account(f"user:{role}", "user", Principal.of(role, "default", customer_id), password))
    if client_secret := _secret(settings.ticketing_client_secret):
        accounts.append(
            Account(
                "client:ticketing-demo",
                "client",
                Principal.of("service", SERVICE_CLIENTS["ticketing-demo"]),
                client_secret,
            )
        )
    return accounts


def active_operator(settings: Settings, operator_id: str) -> bool:
    """An `operator_id` (without prefix, as in the webhooks) is active when its account is configured (spec D1)."""
    principal_id = f"operator:{operator_id}"
    accounts = configured_accounts(settings)
    return any(a.principal.role == "operator" and a.principal.principal_id == principal_id for a in accounts)


def check_configuration(settings: Settings) -> list[str]:
    """Validates the credential configuration at startup and returns warnings (fictitious example values)."""
    example = sorted(a.account_id for a in configured_accounts(settings) if a.secret.endswith(EXAMPLE_SUFFIX))
    if not example:
        return []
    return [
        "example credentials from .env.example are in use for "
        + ", ".join(example)
        + "; they are public and must be replaced before any exposure outside this host"
    ]


# --- signing key --------------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class SigningKey:
    private_key: rsa.RSAPrivateKey
    kid: str
    public_jwk: dict


def _thumbprint(jwk: dict) -> str:
    """RFC 7638 JWK thumbprint of an RSA public key."""
    canonical = json.dumps({"e": jwk["e"], "kty": jwk["kty"], "n": jwk["n"]}, separators=(",", ":"), sort_keys=True)
    return _b64(hashlib.sha256(canonical.encode("ascii")).digest())


def load_signing_key(path: Path) -> SigningKey:
    """Reads the RS256 private key, generating it on first use (mode 0600 where the platform supports it)."""
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        generated = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        pem = generated.private_bytes(
            serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
        )
        try:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:  # another process created it first: use that one
            pass
        else:
            with os.fdopen(fd, "wb") as handle:
                handle.write(pem)
    private_key = serialization.load_pem_private_key(path.read_bytes(), password=None)
    if not isinstance(private_key, rsa.RSAPrivateKey):
        raise CredentialConfigError("JWT signing key must be an RSA private key")
    jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(private_key.public_key()))
    kid = _thumbprint(jwk)
    return SigningKey(private_key, kid, jwk | {"kid": kid, "use": "sig", "alg": "RS256"})


# --- issuer and verifier ------------------------------------------------------------------------------------------


class Identity:
    """Issuer and the single verifier of bearer tokens. One instance per application."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._key: SigningKey | None = None
        self._lock = threading.Lock()
        self._synced: dict[str, str] = {}  # database path -> fingerprint of the configuration last synced
        self._dummy: str | None = None  # hash checked for unknown accounts, so they cost the same as known ones
        self._jwks_client = jwt.PyJWKClient(settings.jwt_jwks_url) if settings.jwt_jwks_url else None

    @property
    def issuer(self) -> str:
        return self.settings.jwt_issuer.rstrip("/")

    @property
    def key(self) -> SigningKey:
        with self._lock:
            if self._key is None:
                path = self.settings.jwt_private_key_path or (self.settings.runtime_path / "jwt" / "signing_key.pem")
                self._key = load_signing_key(Path(path))
            return self._key

    def jwks(self) -> dict:
        return {"keys": [self.key.public_jwk]}

    def openid_configuration(self) -> dict:
        return {
            "issuer": self.issuer,
            "jwks_uri": f"{self.issuer}/.well-known/jwks.json",
            "token_endpoint": f"{self.issuer}/v1/auth/token",
            "revocation_endpoint": f"{self.issuer}/v1/auth/revoke",
            "grant_types_supported": ["password", "client_credentials"],
            "token_endpoint_auth_methods_supported": ["client_secret_post", "client_secret_basic"],
            "scopes_supported": list(ALL_SCOPES),
            "access_token_signing_alg_values_supported": ["RS256"],
        }

    # --- accounts -------------------------------------------------------------------------------------------------

    def sync_accounts(self, conn: sqlite3.Connection) -> None:
        """Stores the configured users and clients as hashes; re-hashes only what changed. Accounts no longer
        configured are deactivated."""
        accounts = configured_accounts(self.settings)
        iterations = self.settings.password_hash_iterations
        fingerprint = hashlib.sha256(
            json.dumps([[a.account_id, a.principal.principal_id, a.secret] for a in accounts] + [iterations]).encode()
        ).hexdigest()
        key = str(self.settings.db_path)
        if self._synced.get(key) == fingerprint:
            return
        stamp = datetime.now(UTC).isoformat()
        rows = {r["account_id"]: r for r in conn.execute("SELECT * FROM auth_accounts")}
        for account in accounts:
            row = rows.get(account.account_id)
            if (
                row is not None
                and row["active"]
                and row["principal_id"] == account.principal.principal_id
                and _iterations(row["secret_hash"]) == iterations
                and verify_secret(account.secret, row["secret_hash"])
            ):
                continue
            conn.execute(
                "INSERT INTO auth_accounts"
                "(account_id,kind,principal_id,role,customer_id,secret_hash,active,updated_at) "
                "VALUES(?,?,?,?,?,?,1,?) ON CONFLICT(account_id) DO UPDATE SET kind=excluded.kind,"
                "principal_id=excluded.principal_id,role=excluded.role,customer_id=excluded.customer_id,"
                "secret_hash=excluded.secret_hash,active=1,updated_at=excluded.updated_at",
                (
                    account.account_id,
                    account.kind,
                    account.principal.principal_id,
                    account.principal.role,
                    account.principal.customer_id,
                    hash_secret(account.secret, iterations),
                    stamp,
                ),
            )
        configured = [a.account_id for a in accounts]
        marks = ",".join("?" * len(configured)) or "''"
        conn.execute(
            f"UPDATE auth_accounts SET active=0, updated_at=? WHERE account_id NOT IN ({marks})",  # noqa: S608
            (stamp, *configured),
        )
        self._synced[key] = fingerprint

    def authenticate(self, conn: sqlite3.Connection, account_id: str, secret: str) -> Principal | None:
        self.sync_accounts(conn)
        row = conn.execute("SELECT * FROM auth_accounts WHERE account_id=? AND active=1", (account_id,)).fetchone()
        if row is None and self._dummy is None:
            self._dummy = hash_secret(secrets.token_urlsafe(16), self.settings.password_hash_iterations)
        stored = row["secret_hash"] if row else self._dummy
        if not verify_secret(secret, stored) or row is None:  # same work whether the account exists or not
            return None
        role = row["role"]
        return Principal(row["principal_id"], role, row["customer_id"], ROLE_SCOPES[role])

    # --- tokens ---------------------------------------------------------------------------------------------------

    def issue(self, principal: Principal, client_id: str, *, now: float | None = None) -> dict:
        """Signs an access token for an authenticated principal and returns the token response (RFC 6749)."""
        now = int(time.time() if now is None else now)
        ttl = SERVICE_TTL_SECONDS if principal.role == "service" else PERSON_TTL_SECONDS
        claims = {
            "iss": self.issuer,
            "sub": principal.principal_id,
            "aud": principal.audience,
            "exp": now + ttl,
            "iat": now,
            "nbf": now,
            "jti": uuid.uuid4().hex,
            "client_id": client_id,
            "role": principal.role,
            "scope": " ".join(principal.scopes),
        }
        if principal.role == "merchant":
            claims["customer_id"] = principal.customer_id
        token = jwt.encode(
            claims, self.key.private_key, algorithm="RS256", headers={"typ": TOKEN_TYPE, "kid": self.key.kid}
        )
        return {"access_token": token, "token_type": "Bearer", "expires_in": ttl, "scope": claims["scope"]}

    def decode(self, token: str) -> dict:
        """Signature, `kid`, `typ`, `iss`, `aud` and time claims (30 s tolerance). Raises InvalidToken."""
        try:
            header = jwt.get_unverified_header(token)
            if header.get("alg") != "RS256" or str(header.get("typ", "")).lower() not in (
                TOKEN_TYPE,
                "application/at+jwt",
            ):
                raise InvalidToken("unexpected token type or algorithm")
            if self._jwks_client is not None:
                key = self._jwks_client.get_signing_key(header.get("kid") or "").key
            elif header.get("kid") == self.key.kid:
                key = self.key.private_key.public_key()
            else:
                raise InvalidToken("unknown signing key")
            return jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                audience=AUDIENCE,
                issuer=self.issuer,
                leeway=LEEWAY_SECONDS,
                options={"require": ["exp", "iat", "nbf", "iss", "aud", "sub", "jti"]},
            )
        except InvalidToken:
            raise
        except (jwt.PyJWTError, ValueError, TypeError) as exc:
            raise InvalidToken(type(exc).__name__) from exc

    def principal_from_claims(self, claims: dict) -> Principal:
        role = claims.get("role")
        if role not in ROLE_SCOPES or not str(claims.get("sub", "")).startswith(f"{role}:"):
            raise InvalidToken("unknown role")
        # The role table bounds what any issuer may grant: scopes outside the role are ignored.
        scopes = tuple(s for s in ROLE_SCOPES[role] if s in str(claims.get("scope", "")).split())
        if role == "merchant":
            customer_id = claims.get("customer_id")
            if not customer_id or claims["sub"] != f"merchant:{customer_id}":
                raise InvalidToken("merchant token without its merchant")
        elif role == "demo":
            customer_id = self.settings.api_demo_customer_id  # the demo merchant comes from the server configuration
        else:
            customer_id = None
        return Principal(claims["sub"], role, customer_id, scopes)

    def verify(self, token: str, conn: sqlite3.Connection) -> tuple[Principal, dict]:
        """The single verifier (`resolve_credential` in ADR 0017): returns the principal and the verified claims.
        Raises InvalidToken, including for a revoked `jti`."""
        claims = self.decode(token)
        if conn.execute("SELECT 1 FROM revoked_tokens WHERE jti=?", (claims["jti"],)).fetchone():
            raise InvalidToken("revoked")
        return self.principal_from_claims(claims), claims

    def revoke(self, conn: sqlite3.Connection, claims: dict) -> None:
        stamp = datetime.now(UTC)
        conn.execute(
            "INSERT OR IGNORE INTO revoked_tokens(jti,principal_id,expires_at,revoked_at) VALUES(?,?,?,?)",
            (claims["jti"], claims["sub"], datetime.fromtimestamp(claims["exp"], UTC).isoformat(), stamp.isoformat()),
        )
        conn.execute("DELETE FROM revoked_tokens WHERE expires_at<?", (stamp.isoformat(),))


def remember_principal(conn: sqlite3.Connection, principal: Principal) -> None:
    """Keeps `api_principals` current for the records that reference a principal (runs, comparisons)."""
    conn.execute(
        "INSERT INTO api_principals(principal_id,role,customer_id,access_key_digest,active,scopes) "
        "VALUES(?,?,?,NULL,1,?) ON CONFLICT(principal_id) DO UPDATE SET role=excluded.role,"
        "customer_id=excluded.customer_id,active=1,scopes=excluded.scopes "
        "WHERE role IS NOT excluded.role OR customer_id IS NOT excluded.customer_id OR scopes IS NOT excluded.scopes "
        "OR active<>1",
        (principal.principal_id, principal.role, principal.customer_id, json.dumps(list(principal.scopes))),
    )


# --- rate limit ---------------------------------------------------------------------------------------------------


def utc_seconds() -> float:
    return time.time()


def hit_rate_limit(conn: sqlite3.Connection, principal_id: str, limit: int, now: float | None = None) -> int | None:
    """Fixed 60 s window per principal (spec v0.7.0, D5). Counts this request and returns the seconds to wait when
    it is over the limit, else None. Called before any model call."""
    now = utc_seconds() if now is None else now
    window = int(now // WINDOW_SECONDS) * WINDOW_SECONDS
    row = conn.execute(
        "INSERT INTO rate_limit_hits(principal_id,window_start,count) VALUES(?,?,1) "
        "ON CONFLICT(principal_id,window_start) DO UPDATE SET count=count+1 RETURNING count",
        (principal_id, window),
    ).fetchone()
    conn.execute("DELETE FROM rate_limit_hits WHERE principal_id=? AND window_start<?", (principal_id, window))
    if row[0] <= limit:
        return None
    return max(1, math.ceil(window + WINDOW_SECONDS - now))
