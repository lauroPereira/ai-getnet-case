"""Identity: credential -> principal -> scopes -> merchant (ADR 0017, spec v0.7.0 version 2).

The assistant issues RS256 access tokens (RFC 9068 profile) for the synthetic demo users (password grant) and service
clients (client credentials), publishes its public key as JWKS and verifies every bearer token in one place
(`Identity.verify`, the `resolve_credential` of the ADR). Pointing `JWT_JWKS_URL` and `JWT_ISSUER` at an external
OIDC provider replaces the issuer without touching the routes. Everything after verification works on a `Principal`:
scope and merchant checks on every tool call, the handoff case write, the rate limit and the read routes.

Login by redirection (v0.13.0, spec D1, task 97): authorization code with PKCE S256 for the registered public
clients and their exact `redirect_uri` (`OAUTH_REDIRECT_URIS`), then rotating refresh tokens. A refresh token that was
already used and appears again revokes its whole family (every refresh token of that login and the access tokens
issued with them). Codes and refresh tokens are random 256-bit values stored only as SHA-256 digests.

External issuers (v0.13.0, spec D2, task 98): `OIDC_ISSUERS` lists OIDC providers (Dex in the compose) whose tokens
the API also accepts. Each issuer is compared exactly; its discovery document and JWKS are fetched on demand, cached
for a while and renewed once (at a limited rate) when a token names an unknown `kid`. Only the asymmetric algorithms
configured for that issuer are accepted. Its `groups` claim (or the claim named by `groups_claim`) maps to exactly one
role, and the scopes come from the role. With `groups_claim` `email` (Dex static users emit no `groups`, task 102a) the
map lists exact addresses, and only a single `email` with `email_verified` exactly true gets a role. A token from any
other issuer is refused (`invalid_issuer`); an unreachable issuer refuses only its own tokens.

Secrets: passwords and client secrets are stored only as PBKDF2-SHA256 hashes; the signing key lives in the runtime
directory (or `JWT_PRIVATE_KEY_PATH`), never in the repository; tokens and secrets are never logged.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import math
import os
import re
import secrets
import sqlite3
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal
from urllib.parse import quote, urlsplit

import httpx
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from merchant_assistant.config import Settings

Role = Literal["merchant", "operator", "service", "demo", "admin"]

SUPPORT_READ = "support:read"
SUPPORT_WRITE = "support:write"  # v0.12.0 (task 94): ask for a sale cancellation, executed only after an explicit yes
HANDOFF_CREATE = "handoff:create"
CONVERSATION_READ = "conversation:read"
HANDOFF_OPERATE = "handoff:operate"
HANDOFF_INTEGRATE = "handoff:integrate"
KB_ADMIN = "kb:admin"
PROFILES_ADMIN = "profiles:admin"

# Single role -> scopes table (spec v0.7.0, "Contrato entre os times / Identidade"). Only the merchant itself may write
# to its account (`support:write`, spec v0.12.0 D5); the shared demo session, operators and services may not.
ROLE_SCOPES: dict[str, tuple[str, ...]] = {
    "merchant": (SUPPORT_READ, HANDOFF_CREATE, CONVERSATION_READ, SUPPORT_WRITE),
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
SERVICE_CLIENTS = {"ticketing-demo": "ticketing", "telegram-operator": "telegram"}  # client_id -> subject
PUBLIC_CLIENTS = ("merchant-assistant-web", "merchant-assistant-cli")  # password grant; no client secret
DEFAULT_PUBLIC_CLIENT = PUBLIC_CLIENTS[0]

# v0.13.0 (task 97): authorization code and refresh token lifetimes.
AUTH_CODE_TTL_SECONDS = 60
REFRESH_TTL_SECONDS = 8 * 60 * 60  # a refresh token not used for this long expires
REFRESH_FAMILY_TTL_SECONDS = 24 * 60 * 60  # no rotation extends a login beyond this
LOOPBACK_HOSTS = ("localhost", "127.0.0.1", "::1")
PKCE_METHOD = "S256"
_CODE_CHALLENGE = re.compile(r"[A-Za-z0-9_-]{43}")  # base64url of a SHA-256 digest, without padding
_CODE_VERIFIER = re.compile(r"[A-Za-z0-9._~-]{43,128}")  # RFC 7636, section 4.1

# v0.13.0 (task 98): external OIDC issuers. Never `none` and never HS* (a public key is not an HMAC secret).
EXTERNAL_ALGORITHMS = ("RS256", "RS384", "RS512", "PS256", "PS384", "PS512", "ES256", "ES384", "ES512")
EXTERNAL_ROLES = ("merchant", "operator", "admin")  # `demo` is a shared session and `service` a local client
EXTERNAL_TOKEN_TYPES = ("", "jwt", TOKEN_TYPE, "application/at+jwt")
EXTERNAL_LEEWAY_SECONDS = 30  # clock tolerance for `exp`, `nbf` and `iat`
EXTERNAL_MAX_LIFETIME_SECONDS = 24 * 60 * 60  # `exp - iat` above this is refused
JWKS_TTL_SECONDS = 5 * 60  # discovery and JWKS are fetched again after this
JWKS_FORCED_RENEWAL_SECONDS = 30  # an unknown `kid` renews the JWKS at most once per issuer in this interval
ISSUER_RETRY_SECONDS = 30  # after a failed fetch the issuer refuses its tokens without fetching for this long
JWKS_MAX_STALE_SECONDS = EXTERNAL_MAX_LIFETIME_SECONDS  # cached keys keep serving while renewals fail, up to this
FETCH_TIMEOUT_SECONDS = 2.0  # connect and each read
FETCH_DEADLINE_SECONDS = 4.0  # whole response: connection, status line, headers and body
FETCH_MAX_BYTES = 256 * 1024
_DNS_LABEL = re.compile(r"[a-z][a-z0-9-]*")
_HEX = re.compile(r"[0-9a-f]+")
_EXACT_EMAIL = re.compile(r"[^@\s*]+@[^@\s*]+")  # an exact address of the role map: no wildcard, no bare domain
_ISSUER_KEYS = {"issuer", "audience", "groups", "algorithms", "groups_claim", "customer_id_claim"}

log = logging.getLogger("merchant_assistant.identity")


class InvalidToken(Exception):
    """The bearer token is missing, malformed, tampered, expired, revoked or from another issuer/audience."""


class UnknownIssuer(InvalidToken):
    """The token's `iss` is neither this API nor one of `OIDC_ISSUERS` (`401 invalid_issuer`)."""


class NoRole(InvalidToken):
    """A valid token of an external issuer whose groups map to no role, or to more than one (`403`)."""


class IssuerUnavailable(Exception):
    """Discovery or JWKS of an external issuer could not be fetched or is not acceptable."""


class CredentialConfigError(ValueError):
    """Invalid credential configuration: the API refuses to start."""


class GrantRefused(Exception):
    """The authorization code or refresh token is unknown, used, expired, revoked or bound to something else
    (`invalid_grant`). The message is for tests only: the response never says which check failed."""


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
    if client_secret := _secret(settings.telegram_client_secret):  # the Telegram adapter acts as an operator (task 100)
        accounts.append(
            Account(
                "client:telegram-operator",
                "client",
                Principal.of("operator", SERVICE_CLIENTS["telegram-operator"]),
                client_secret,
            )
        )
    return accounts


def active_operator(settings: Settings, operator_id: str) -> bool:
    """An `operator_id` (without prefix, as in the webhooks) is active when its account is configured (spec D1)."""
    principal_id = f"operator:{operator_id}"
    accounts = configured_accounts(settings)
    return any(a.principal.role == "operator" and a.principal.principal_id == principal_id for a in accounts)


def registered_redirects(settings: Settings) -> dict[str, tuple[str, ...]]:
    """`OAUTH_REDIRECT_URIS`: `<client_id>=<redirect_uri>` entries separated by commas, one per URI (spec D1). Only
    public clients may have them; a URI is absolute, without fragment or credentials, and `https` unless its host is
    the loopback. Raises CredentialConfigError when the configuration is invalid."""
    registered: dict[str, list[str]] = {}
    for item in (part.strip() for part in settings.oauth_redirect_uris.split(",")):
        if not item:
            continue
        client_id, sep, uri = (piece.strip() for piece in item.partition("="))
        if not sep or client_id not in PUBLIC_CLIENTS or not uri:
            raise CredentialConfigError("OAUTH_REDIRECT_URIS: each entry must be <public client id>=<redirect uri>")
        try:
            parts = urlsplit(uri)
            host = parts.hostname
        except ValueError as exc:
            raise CredentialConfigError(f"OAUTH_REDIRECT_URIS: invalid redirect URI for {client_id}") from exc
        secure = parts.scheme == "https" or (parts.scheme == "http" and host in LOOPBACK_HOSTS)
        if not secure or not host or parts.fragment or parts.username is not None or parts.password is not None:
            raise CredentialConfigError(
                f"OAUTH_REDIRECT_URIS: the redirect URI of {client_id} must be absolute, https (http only on the "
                "loopback), without fragment or credentials"
            )
        registered.setdefault(client_id, []).append(uri)
    return {client_id: tuple(uris) for client_id, uris in registered.items()}


def redirect_allowed(settings: Settings, client_id: str, redirect_uri: str) -> bool:
    """Exact match against the registered URIs of the client, in constant time per URI (no normalisation)."""
    target = redirect_uri.encode("utf-8")
    found = False
    for uri in registered_redirects(settings).get(client_id, ()):
        found |= hmac.compare_digest(uri.encode("utf-8"), target)
    return found


def valid_code_challenge(challenge: str) -> bool:
    return bool(_CODE_CHALLENGE.fullmatch(challenge))


def pkce_challenge(verifier: str) -> str:
    """S256: base64url(SHA-256(code_verifier)) without padding (RFC 7636, section 4.2)."""
    return _b64(hashlib.sha256(verifier.encode("ascii")).digest())


def pkce_matches(verifier: str, challenge: str) -> bool:
    if not _CODE_VERIFIER.fullmatch(verifier):
        return False
    return hmac.compare_digest(pkce_challenge(verifier).encode("ascii"), challenge.encode("ascii"))


def secret_digest(value: str) -> str:
    """Digest under which codes and refresh tokens are stored (256-bit random values: no salt or stretching)."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _same(stored: str, presented: str) -> bool:
    return hmac.compare_digest(stored.encode("utf-8"), presented.encode("utf-8"))


def _external_principal_id(role: str, subject: str, issuer: str) -> str:
    """Encode each external identity component separately so delimiters cannot collide."""
    return f"{role}:{quote(subject, safe='')}@{quote(issuer, safe='')}"


@dataclass(frozen=True)
class ExternalIssuer:
    """One entry of `OIDC_ISSUERS` (spec D2)."""

    issuer: str  # compared exactly with the token's `iss` and the discovery document's `issuer`
    audience: str  # required in the token's `aud`
    groups: dict[str, str]  # group (or exact e-mail when groups_claim is `email`) -> role
    algorithms: tuple[str, ...] = ("RS256",)
    groups_claim: str = "groups"
    customer_id_claim: str | None = None  # required when a group maps to `merchant`

    @property
    def label(self) -> str:
        """Group issuer URLs with the same host and path when checking configuration duplicates."""
        parts = urlsplit(self.issuer)
        return f"{parts.netloc}{parts.path}".rstrip("/")


def _origin(url: str) -> tuple[str, str]:
    parts = urlsplit(url)
    return parts.scheme, parts.netloc.lower()


def _fetchable(url: str) -> bool:
    """`https`, or `http` on the loopback or on a single DNS label of a private network (the compose service `dex`):
    letters, digits and hyphens starting with a letter, not only hex digits, so never an IP literal in disguise."""
    try:
        parts = urlsplit(url)
        host = parts.hostname or ""
        parts.port  # noqa: B018 - an invalid port raises here
    except ValueError:
        return False
    label = bool(_DNS_LABEL.fullmatch(host)) and not _HEX.fullmatch(host)
    plain = parts.scheme == "http" and (host in LOOPBACK_HOSTS or label)
    return (
        (parts.scheme == "https" or plain)
        and bool(host)
        and not parts.query
        and not parts.fragment
        and parts.username is None
        and parts.password is None
    )


def configured_issuers(settings: Settings) -> tuple[ExternalIssuer, ...]:
    """`OIDC_ISSUERS`: a JSON list of `{"issuer", "audience", "groups", "algorithms"?, "groups_claim"?,
    "customer_id_claim"?}`; empty means only the assistant's own issuer. Raises CredentialConfigError."""
    raw = settings.oidc_issuers.strip()
    if not raw:
        return ()
    try:
        entries = json.loads(raw)
    except ValueError as exc:
        raise CredentialConfigError("OIDC_ISSUERS must be a JSON list of issuers") from exc
    if not isinstance(entries, list):
        raise CredentialConfigError("OIDC_ISSUERS must be a JSON list of issuers")
    issuers: list[ExternalIssuer] = []
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) - _ISSUER_KEYS:
            raise CredentialConfigError(f"OIDC_ISSUERS: each issuer is an object with the keys {sorted(_ISSUER_KEYS)}")
        issuer = entry.get("issuer")
        if not isinstance(issuer, str) or not _fetchable(issuer):
            raise CredentialConfigError(
                "OIDC_ISSUERS: issuer must be an https URL (http only on the loopback or a single-label host), "
                "without query, fragment or credentials"
            )
        label = ExternalIssuer(issuer, "", {}).label
        if issuer.rstrip("/") == settings.jwt_issuer.rstrip("/") or any(i.label == label for i in issuers):
            raise CredentialConfigError(f"OIDC_ISSUERS: {issuer} is repeated or is the assistant's own issuer")
        audience = entry.get("audience")
        if not isinstance(audience, str) or not audience.strip():
            raise CredentialConfigError(f"OIDC_ISSUERS: {issuer} needs an audience")
        algorithms = entry.get("algorithms", ["RS256"])
        if not isinstance(algorithms, list) or not algorithms or any(a not in EXTERNAL_ALGORITHMS for a in algorithms):
            raise CredentialConfigError(
                f"OIDC_ISSUERS: algorithms of {issuer} must be among {', '.join(EXTERNAL_ALGORITHMS)} "
                "(never none or HS*)"
            )
        groups = entry.get("groups")
        if (
            not isinstance(groups, dict)
            or not groups
            or any(not isinstance(g, str) or not g or r not in EXTERNAL_ROLES for g, r in groups.items())
        ):
            raise CredentialConfigError(
                f"OIDC_ISSUERS: groups of {issuer} must map group names to {', '.join(EXTERNAL_ROLES)}"
            )
        groups_claim = entry.get("groups_claim", "groups")
        customer_id_claim = entry.get("customer_id_claim")
        if not isinstance(groups_claim, str) or not groups_claim:
            raise CredentialConfigError(f"OIDC_ISSUERS: groups_claim of {issuer} must be a claim name")
        if groups_claim == "email" and any(not _EXACT_EMAIL.fullmatch(address) for address in groups):
            raise CredentialConfigError(
                f"OIDC_ISSUERS: with groups_claim email, groups of {issuer} must list exact addresses (no wildcard)"
            )
        if customer_id_claim is not None and (not isinstance(customer_id_claim, str) or not customer_id_claim):
            raise CredentialConfigError(f"OIDC_ISSUERS: customer_id_claim of {issuer} must be a claim name")
        if "merchant" in groups.values() and customer_id_claim is None:
            raise CredentialConfigError(
                f"OIDC_ISSUERS: {issuer} maps a group to merchant, so it needs customer_id_claim"
            )
        issuers.append(
            ExternalIssuer(issuer, audience, dict(groups), tuple(algorithms), groups_claim, customer_id_claim)
        )
    return tuple(issuers)


def fetch_json(url: str) -> dict:
    """GET a JSON object from an external issuer: no redirects, bounded size, short connect and read timeouts, and
    FETCH_DEADLINE_SECONDS for the whole response (connection, status line, headers and body). The request runs in a
    helper thread: when the deadline passes, the caller gets IssuerUnavailable at once and the client is closed, so the
    helper fails at its next read and ends. Raises IssuerUnavailable."""
    client = httpx.Client(timeout=FETCH_TIMEOUT_SECONDS, follow_redirects=False)
    outcome: dict = {}

    def fetch() -> None:
        try:
            outcome["data"] = _read_json(client, url)
        except Exception as exc:  # handed to the caller, or dropped once the deadline has passed
            outcome["error"] = exc
        finally:
            client.close()

    helper = threading.Thread(target=fetch, name="issuer-fetch", daemon=True)
    helper.start()
    helper.join(FETCH_DEADLINE_SECONDS)
    if helper.is_alive():
        client.close()  # closes the open connection; the helper's next read fails
        raise IssuerUnavailable("response too slow")
    if "error" in outcome:
        raise outcome["error"]
    return outcome["data"]


def _read_json(client: httpx.Client, url: str) -> dict:
    try:
        with client.stream("GET", url, headers={"Accept": "application/json"}) as response:
            if response.status_code != 200:
                raise IssuerUnavailable(f"HTTP {response.status_code}")
            body = bytearray()
            for chunk in response.iter_bytes():
                body += chunk
                if len(body) > FETCH_MAX_BYTES:
                    raise IssuerUnavailable("response too large")
        data = json.loads(bytes(body))
    except httpx.HTTPError as exc:
        raise IssuerUnavailable(type(exc).__name__) from exc
    except ValueError as exc:
        raise IssuerUnavailable("not JSON") from exc
    if not isinstance(data, dict):
        raise IssuerUnavailable("not a JSON object")
    return data


def monotonic_seconds() -> float:
    return time.monotonic()


class ExternalKeys:
    """Discovery document and JWKS of one external issuer, cached for JWKS_TTL_SECONDS. An unknown `kid` renews them
    at most once per JWKS_FORCED_RENEWAL_SECONDS (a key rotation is picked up without letting forged `kid`s drive
    fetches). One request fetches at a time and nobody waits for it: the others use the cached keys, or are refused
    at once when there are none. A failed fetch keeps the cached keys serving (up to JWKS_MAX_STALE_SECONDS) and
    stops fetches for ISSUER_RETRY_SECONDS."""

    def __init__(self, config: ExternalIssuer) -> None:
        self.config = config
        self._lock = threading.Lock()  # held only by the request that fetches
        self._keys: dict[str, dict] = {}  # replaced whole, read without the lock
        self._fetched_at: float | None = None
        self._forced_at: float | None = None
        self._retry_at = float("-inf")

    def _expired(self, now: float) -> bool:
        return self._fetched_at is None or now - self._fetched_at >= JWKS_TTL_SECONDS

    def _may_force(self, now: float) -> bool:
        return self._forced_at is None or now - self._forced_at >= JWKS_FORCED_RENEWAL_SECONDS

    def key(self, kid: str, algorithm: str):
        now = monotonic_seconds()
        wanted = self._expired(now) or (kid not in self._keys and self._may_force(now))
        if wanted and now >= self._retry_at and self._lock.acquire(blocking=False):
            try:
                if self._expired(now):
                    self._renew(now)
                elif kid not in self._keys and self._may_force(now):
                    self._forced_at = now
                    self._renew(now)
            finally:
                self._lock.release()
        fetched_at = self._fetched_at
        if fetched_at is None or now - fetched_at >= JWKS_MAX_STALE_SECONDS:
            raise InvalidToken("issuer unavailable")
        jwk = self._keys.get(kid)
        if jwk is None:
            raise InvalidToken("unknown signing key")
        if jwk.get("alg") not in (None, algorithm) or jwk.get("use") not in (None, "sig"):
            raise InvalidToken("signing key not meant for this algorithm")
        try:
            return jwt.PyJWK(jwk, algorithm=algorithm).key
        except (jwt.PyJWTError, ValueError, TypeError, KeyError) as exc:
            raise InvalidToken("unusable signing key") from exc

    def _renew(self, now: float) -> None:
        """Fetches discovery and JWKS. On failure the cached keys stay and fetches stop for a while."""
        if now < self._retry_at:
            return
        try:
            discovery = fetch_json(f"{self.config.issuer.rstrip('/')}/.well-known/openid-configuration")
            jwks_uri = discovery.get("jwks_uri")
            if discovery.get("issuer") != self.config.issuer:
                raise IssuerUnavailable("the discovery document names another issuer")
            if not isinstance(jwks_uri, str) or not _fetchable(jwks_uri):
                raise IssuerUnavailable("unacceptable jwks_uri")
            if urlsplit(jwks_uri).scheme == "http" and _origin(jwks_uri) != _origin(self.config.issuer):
                raise IssuerUnavailable("a plain http jwks_uri must be on the issuer's origin")
            listed = fetch_json(jwks_uri).get("keys")
            if not isinstance(listed, list):
                raise IssuerUnavailable("JWKS without keys")
        except IssuerUnavailable as exc:
            self._retry_at = now + ISSUER_RETRY_SECONDS
            log.warning("external issuer %s unavailable: %s", self.config.issuer, exc)
            return
        self._keys = {k["kid"]: k for k in listed if isinstance(k, dict) and isinstance(k.get("kid"), str)}
        self._fetched_at = now


def check_configuration(settings: Settings) -> list[str]:
    """Validates the credential configuration at startup and returns warnings (fictitious example values)."""
    registered_redirects(settings)  # an invalid redirect URI stops the startup
    configured_issuers(settings)  # and so does an invalid external issuer
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
        self._external = {i.issuer: ExternalKeys(i) for i in configured_issuers(settings)}

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
            "authorization_endpoint": f"{self.issuer}/v1/auth/authorize",
            "token_endpoint": f"{self.issuer}/v1/auth/token",
            "revocation_endpoint": f"{self.issuer}/v1/auth/revoke",
            "grant_types_supported": ["authorization_code", "refresh_token", "password", "client_credentials"],
            "response_types_supported": ["code"],
            "code_challenge_methods_supported": [PKCE_METHOD],
            "authorization_response_iss_parameter_supported": True,
            "token_endpoint_auth_methods_supported": ["none", "client_secret_post", "client_secret_basic"],
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
        return self._sign(principal, client_id, now)[0]

    def _sign(self, principal: Principal, client_id: str, now: float | None) -> tuple[dict, dict]:
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
        return {"access_token": token, "token_type": "Bearer", "expires_in": ttl, "scope": claims["scope"]}, claims

    def decode(self, token: str) -> dict:
        """Signature, `kid`, `typ`, `iss`, `aud` and time claims (30 s tolerance). The unverified `iss` only chooses
        how to verify: this API's key, an external issuer of `OIDC_ISSUERS` or `UnknownIssuer`. Raises InvalidToken."""
        try:
            header = jwt.get_unverified_header(token)
            issuer = jwt.decode(token, options={"verify_signature": False}).get("iss")
        except (jwt.PyJWTError, ValueError, TypeError, AttributeError) as exc:
            raise InvalidToken(type(exc).__name__) from exc
        if issuer == self.issuer:
            return self._decode_local(token, header)
        if isinstance(issuer, str) and issuer in self._external:
            return self._decode_external(token, header, self._external[issuer])
        raise UnknownIssuer("unknown issuer")

    def _decode_local(self, token: str, header: dict) -> dict:
        try:
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

    def _decode_external(self, token: str, header: dict, keys: ExternalKeys) -> dict:
        """An external issuer's token: one of its configured algorithms, a `kid` of its JWKS, its exact `iss`, its
        audience, `exp` and `iat` required, `nbf` checked when present, a lifetime of at most 24 h. A token without
        `jti` gets one derived from the digest of its signed part (per-token counters and revocation)."""
        config = keys.config
        algorithm, kid = header.get("alg"), header.get("kid")
        if algorithm not in config.algorithms or str(header.get("typ", "")).lower() not in EXTERNAL_TOKEN_TYPES:
            raise InvalidToken("unexpected token type or algorithm")
        if not isinstance(kid, str) or not kid:
            raise InvalidToken("token without kid")
        key = keys.key(kid, algorithm)
        try:
            claims = jwt.decode(
                token,
                key,
                algorithms=[algorithm],
                audience=config.audience,
                issuer=config.issuer,
                leeway=EXTERNAL_LEEWAY_SECONDS,
                options={"require": ["exp", "iat", "iss", "aud", "sub"]},
            )
        except (jwt.PyJWTError, ValueError, TypeError) as exc:
            raise InvalidToken(type(exc).__name__) from exc
        subject, jti = claims.get("sub"), claims.get("jti")
        if not isinstance(subject, str) or not subject or len(subject) > 255 or not subject.isprintable():
            raise InvalidToken("unusable subject")
        if any(not isinstance(claims[c], int | float) or isinstance(claims[c], bool) for c in ("exp", "iat")):
            raise InvalidToken("time claims must be numbers")
        if claims["exp"] - claims["iat"] > EXTERNAL_MAX_LIFETIME_SECONDS:
            raise InvalidToken("token lifetime too long")
        if jti is not None and (not isinstance(jti, str) or not jti):
            raise InvalidToken("unusable jti")
        if jti is None:  # from the signed part only: the signature has equivalent encodings (padding, ECDSA twin)
            claims["jti"] = "sha256:" + secret_digest(token.rsplit(".", 1)[0])[:32]
        return claims

    def _external_principal(self, claims: dict, config: ExternalIssuer) -> Principal:
        """`groups` -> exactly one role (none or several recognised groups refuse with NoRole); the scopes are the
        role's; a merchant takes its merchant from `customer_id_claim`. Mapped by `email` (fail closed): one address as
        text, compared exactly, and `email_verified` exactly true; anything else gets no role."""
        value = claims.get(config.groups_claim)
        if config.groups_claim == "email":
            if claims.get("email_verified") is not True or not isinstance(value, str):
                raise NoRole("no verified e-mail")
            groups = [value]
        else:
            groups = [value] if isinstance(value, str) else value if isinstance(value, list) else []
        roles = {config.groups[g] for g in groups if isinstance(g, str) and g in config.groups}
        if len(roles) != 1:
            raise NoRole("no recognised group" if not roles else "groups map to more than one role")
        role = roles.pop()
        customer_id = None
        if role == "merchant":
            customer_id = claims.get(config.customer_id_claim or "")
            if not isinstance(customer_id, str) or not re.fullmatch(self.settings.user_id_pattern, customer_id):
                raise InvalidToken("merchant token without its merchant")
        return Principal(
            _external_principal_id(role, claims["sub"], config.issuer), role, customer_id, ROLE_SCOPES[role]
        )

    def principal_from_claims(self, claims: dict) -> Principal:
        if claims.get("iss") != self.issuer and claims.get("iss") in self._external:
            return self._external_principal(claims, self._external[claims["iss"]].config)
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
        if conn.execute("SELECT 1 FROM revoked_tokens WHERE jti=?", (self.token_id(claims),)).fetchone():
            raise InvalidToken("revoked")
        return self.principal_from_claims(claims), claims

    def token_id(self, claims: dict) -> str:
        """What revocation and the per-token counters key on: the `jti`, prefixed with the issuer for an external
        issuer's token, so it never meets a local `jti` nor another issuer's."""
        issuer = claims.get("iss")
        return claims["jti"] if issuer == self.issuer else f"{issuer}#{claims['jti']}"

    def revoke(self, conn: sqlite3.Connection, claims: dict) -> None:
        stamp = datetime.now(UTC)
        conn.execute(
            "INSERT OR IGNORE INTO revoked_tokens(jti,principal_id,expires_at,revoked_at) VALUES(?,?,?,?)",
            (
                self.token_id(claims),
                self.principal_from_claims(claims).principal_id,
                datetime.fromtimestamp(claims["exp"], UTC).isoformat(),
                stamp.isoformat(),
            ),
        )
        conn.execute("DELETE FROM revoked_tokens WHERE expires_at<?", (stamp.isoformat(),))

    # --- authorization code and refresh tokens (task 97) -----------------------------------------------------------

    def create_code(
        self,
        conn: sqlite3.Connection,
        principal: Principal,
        account_id: str,
        client_id: str,
        redirect_uri: str,
        code_challenge: str,
    ) -> str:
        """One-use authorization code for an authenticated user, bound to the client, the exact `redirect_uri` and
        the S256 challenge. Only its digest is stored; the caller already checked client, URI and challenge."""
        now = int(utc_seconds())
        code = secrets.token_urlsafe(32)
        conn.execute("DELETE FROM auth_codes WHERE expires_at<?", (now - REFRESH_FAMILY_TTL_SECONDS,))
        conn.execute(
            "INSERT INTO auth_codes(code_hash,client_id,redirect_uri,code_challenge,account_id,principal_id,scope,"
            "created_at,expires_at) VALUES(?,?,?,?,?,?,?,?,?)",
            (
                secret_digest(code),
                client_id,
                redirect_uri,
                code_challenge,
                account_id,
                principal.principal_id,
                " ".join(principal.scopes),
                now,
                now + AUTH_CODE_TTL_SECONDS,
            ),
        )
        return code

    def redeem_code(
        self, conn: sqlite3.Connection, code: str, client_id: str, redirect_uri: str, code_verifier: str
    ) -> tuple[Principal, dict]:
        """`grant_type=authorization_code`: the code is consumed on its first presentation, whatever the outcome; a
        code presented again revokes the family it started (RFC 6749, section 4.1.2). Returns the principal and the
        token response with a refresh token. Raises GrantRefused."""
        self.sync_accounts(conn)
        now = int(utc_seconds())
        digest = secret_digest(code)
        conn.execute("BEGIN IMMEDIATE")
        try:
            row = conn.execute("SELECT * FROM auth_codes WHERE code_hash=?", (digest,)).fetchone()
            if row is None or not _same(row["code_hash"], digest):
                raise GrantRefused("unknown code")
            if row["used_at"] is not None:
                if row["family_id"]:
                    self._revoke_family(conn, row["family_id"], now)
                raise GrantRefused("code already used")
            conn.execute("UPDATE auth_codes SET used_at=? WHERE code_hash=?", (now, digest))
            checks = (
                row["expires_at"] > now,
                _same(row["client_id"], client_id),
                _same(row["redirect_uri"], redirect_uri),
                pkce_matches(code_verifier, row["code_challenge"]),
            )
            if not all(checks):
                raise GrantRefused("expired code or client, redirect_uri or code_verifier mismatch")
            principal = self._account_principal(conn, row)
            family_id = uuid.uuid4().hex
            conn.execute("UPDATE auth_codes SET family_id=? WHERE code_hash=?", (family_id, digest))
            response = self._issue_with_refresh(
                conn, principal, row["account_id"], client_id, family_id, now + REFRESH_FAMILY_TTL_SECONDS, now
            )
        except GrantRefused:
            conn.execute("COMMIT")  # the consumed code and a revoked family stay recorded
            raise
        except BaseException:
            conn.execute("ROLLBACK")
            raise
        conn.execute("COMMIT")
        return principal, response

    def refresh(self, conn: sqlite3.Connection, refresh_token: str, client_id: str) -> tuple[Principal, dict]:
        """`grant_type=refresh_token`: rotation. The presented token is spent and a new one of the same family is
        returned with a new access token and the same scopes. A token already spent, or presented by another client,
        revokes the family. Raises GrantRefused."""
        self.sync_accounts(conn)
        now = int(utc_seconds())
        digest = secret_digest(refresh_token)
        conn.execute("BEGIN IMMEDIATE")
        try:
            row = conn.execute("SELECT * FROM refresh_tokens WHERE token_hash=?", (digest,)).fetchone()
            if row is None or not _same(row["token_hash"], digest):
                raise GrantRefused("unknown refresh token")
            if row["revoked_at"] is not None:
                raise GrantRefused("revoked refresh token")
            if row["used_at"] is not None or not _same(row["client_id"], client_id):
                self._revoke_family(conn, row["family_id"], now)
                raise GrantRefused("refresh token reused or presented by another client: family revoked")
            if row["expires_at"] <= now:
                raise GrantRefused("expired refresh token")
            conn.execute("UPDATE refresh_tokens SET used_at=? WHERE token_hash=?", (now, digest))
            try:
                principal = self._account_principal(conn, row)
            except GrantRefused:
                self._revoke_family(conn, row["family_id"], now)
                raise
            response = self._issue_with_refresh(
                conn, principal, row["account_id"], client_id, row["family_id"], row["family_expires_at"], now
            )
        except GrantRefused:
            conn.execute("COMMIT")
            raise
        except BaseException:
            conn.execute("ROLLBACK")
            raise
        conn.execute("COMMIT")
        return principal, response

    def revoke_refresh(self, conn: sqlite3.Connection, refresh_token: str, principal_id: str) -> bool:
        """Logout: revokes the family of a refresh token of this principal. Someone else's token is left alone."""
        digest = secret_digest(refresh_token)
        conn.execute("BEGIN IMMEDIATE")
        try:
            row = conn.execute("SELECT * FROM refresh_tokens WHERE token_hash=?", (digest,)).fetchone()
            owned = row is not None and _same(row["principal_id"], principal_id)
            if owned:
                self._revoke_family(conn, row["family_id"], int(utc_seconds()))
        except BaseException:
            conn.execute("ROLLBACK")
            raise
        conn.execute("COMMIT")
        return owned

    def _account_principal(self, conn: sqlite3.Connection, row: sqlite3.Row) -> Principal:
        """The principal of a code or refresh token, from its account as configured now: a deactivated account or a
        changed principal refuses the grant. Scopes are those granted at login, bounded by the role."""
        account = conn.execute(
            "SELECT * FROM auth_accounts WHERE account_id=? AND active=1", (row["account_id"],)
        ).fetchone()
        if account is None or account["principal_id"] != row["principal_id"] or account["role"] not in ROLE_SCOPES:
            raise GrantRefused("account no longer active")
        role = account["role"]
        granted = set(row["scope"].split())
        scopes = tuple(s for s in ROLE_SCOPES[role] if s in granted)
        return Principal(row["principal_id"], role, account["customer_id"], scopes)

    def _issue_with_refresh(
        self,
        conn: sqlite3.Connection,
        principal: Principal,
        account_id: str,
        client_id: str,
        family_id: str,
        family_expires_at: int,
        now: int,
    ) -> dict:
        response, claims = self._sign(principal, client_id, None)
        refresh_token = secrets.token_urlsafe(32)
        conn.execute("DELETE FROM refresh_tokens WHERE family_expires_at<?", (now,))
        conn.execute(
            "INSERT INTO refresh_tokens(token_hash,family_id,client_id,account_id,principal_id,scope,created_at,"
            "expires_at,family_expires_at,access_jti,access_expires_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (
                secret_digest(refresh_token),
                family_id,
                client_id,
                account_id,
                principal.principal_id,
                " ".join(principal.scopes),
                now,
                min(now + REFRESH_TTL_SECONDS, family_expires_at),
                family_expires_at,
                claims["jti"],
                claims["exp"],
            ),
        )
        return response | {"refresh_token": refresh_token}

    def _revoke_family(self, conn: sqlite3.Connection, family_id: str, now: int) -> None:
        """Every refresh token of the family stops working, and so do the access tokens issued with them."""
        rows = conn.execute(
            "SELECT access_jti, access_expires_at, principal_id FROM refresh_tokens WHERE family_id=?", (family_id,)
        ).fetchall()
        conn.execute(
            "UPDATE refresh_tokens SET revoked_at=? WHERE family_id=? AND revoked_at IS NULL", (now, family_id)
        )
        stamp = datetime.now(UTC).isoformat()
        for row in rows:
            expires = datetime.fromtimestamp(row["access_expires_at"] + LEEWAY_SECONDS, UTC).isoformat()
            conn.execute(
                "INSERT OR IGNORE INTO revoked_tokens(jti,principal_id,expires_at,revoked_at) VALUES(?,?,?,?)",
                (row["access_jti"], row["principal_id"], expires, stamp),
            )


def remember_principal(conn: sqlite3.Connection, principal: Principal, issuer: str | None = None) -> None:
    """Keeps `api_principals` current for the records that reference a principal (runs, comparisons), with the
    issuer of the token that authenticated it (v0.13.0)."""
    conn.execute(
        "INSERT INTO api_principals(principal_id,role,customer_id,access_key_digest,active,scopes,issuer) "
        "VALUES(?,?,?,NULL,1,?,?) ON CONFLICT(principal_id) DO UPDATE SET role=excluded.role,"
        "customer_id=excluded.customer_id,active=1,scopes=excluded.scopes,issuer=excluded.issuer "
        "WHERE role IS NOT excluded.role OR customer_id IS NOT excluded.customer_id OR scopes IS NOT excluded.scopes "
        "OR issuer IS NOT excluded.issuer OR active<>1",
        (principal.principal_id, principal.role, principal.customer_id, json.dumps(list(principal.scopes)), issuer),
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
