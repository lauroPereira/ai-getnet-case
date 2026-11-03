"""Operator JWTs validated by the assistant's JWKS, and the service's own client-credentials token."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass

import httpx
import jwt

from merchant_assistant.ticketing.config import TicketingSettings

ACCEPTED_TYP = {"at+jwt", "application/at+jwt"}


class AuthError(Exception):
    def __init__(self, status: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


class TransientError(Exception):
    """Network failure, timeout or 5xx from the assistant: worth another attempt."""


@dataclass(frozen=True)
class Operator:
    operator_id: str  # contract `operator_id`: the principal `operator:<id>` without its prefix
    principal: str
    scopes: frozenset[str]


class OperatorVerifier:
    """Checks signature (RS256, `kid` from the JWKS), `typ`, issuer, audience `ticketing`, validity with 30 s of
    clock skew, role and scope `handoff:operate`. An unknown `kid` reloads the JWKS (at most once per interval)."""

    def __init__(self, settings: TicketingSettings, client: httpx.Client, clock: Callable[[], float] = time.monotonic):
        self.settings, self.client, self.clock = settings, client, clock
        self._keys: dict[str, jwt.PyJWK] = {}
        self._fetched_at: float | None = None
        self._lock = threading.Lock()

    def _refresh(self) -> None:
        try:
            response = self.client.get(self.settings.assistant_jwks_url, timeout=self.settings.request_timeout_s)
            response.raise_for_status()
            keys = response.json().get("keys", [])
        except (httpx.HTTPError, ValueError) as exc:
            raise AuthError(503, "jwks_unavailable", "The assistant's signing keys could not be loaded.") from exc
        loaded = {}
        for item in keys:
            if item.get("kid") and item.get("kty") == "RSA":
                try:
                    loaded[item["kid"]] = jwt.PyJWK(item, algorithm="RS256")
                except jwt.PyJWTError:
                    continue
        self._keys, self._fetched_at = loaded, self.clock()

    def _key(self, kid: str) -> jwt.PyJWK:
        with self._lock:
            if kid not in self._keys:
                stale = self._fetched_at is None or self.clock() - self._fetched_at >= self.settings.jwks_min_refresh_s
                if stale:
                    self._refresh()
            key = self._keys.get(kid)
        if key is None:
            raise AuthError(401, "invalid_token", "Unknown signing key.")
        return key

    def verify(self, token: str) -> Operator:
        try:
            header = jwt.get_unverified_header(token)
        except jwt.PyJWTError as exc:
            raise AuthError(401, "invalid_token", "Malformed token.") from exc
        if header.get("alg") != "RS256" or header.get("typ") not in ACCEPTED_TYP or not header.get("kid"):
            raise AuthError(401, "invalid_token", "Unexpected token header.")
        key = self._key(header["kid"])
        try:
            claims = jwt.decode(
                token,
                key.key,
                algorithms=["RS256"],
                audience=self.settings.audience,
                issuer=self.settings.assistant_issuer,
                leeway=self.settings.clock_skew_s,
                options={"require": ["exp", "iat", "iss", "sub", "aud"]},
            )
        except jwt.PyJWTError as exc:
            raise AuthError(401, "invalid_token", "Token rejected.") from exc
        scopes = frozenset(str(claims.get("scope", "")).split())
        subject = str(claims["sub"])
        if claims.get("role") != "operator" or not subject.startswith("operator:") or subject == "operator:":
            raise AuthError(403, "insufficient_scope", "Only operators can use the ticketing service.")
        if self.settings.required_scope not in scopes:
            raise AuthError(403, "insufficient_scope", f"Scope {self.settings.required_scope} is required.")
        return Operator(operator_id=subject.removeprefix("operator:"), principal=subject, scopes=scopes)


class ServiceToken:
    """`client_credentials` token of `service:ticketing`, renewed before it expires or after a 401."""

    RENEW_MARGIN_S = 60

    def __init__(self, settings: TicketingSettings, client: httpx.Client, clock: Callable[[], float] = time.time):
        self.settings, self.client, self.clock = settings, client, clock
        self._token: str | None = None
        self._expires_at = 0.0
        self._lock = threading.Lock()

    def invalidate(self) -> None:
        with self._lock:
            self._token = None

    def get(self) -> str:
        with self._lock:
            if self._token and self.clock() < self._expires_at - self.RENEW_MARGIN_S:
                return self._token
            try:
                response = self.client.post(
                    f"{self.settings.assistant_url}/v1/auth/token",
                    data={
                        "grant_type": "client_credentials",
                        "client_id": self.settings.client_id,
                        "client_secret": self.settings.client_secret,
                    },
                    timeout=self.settings.request_timeout_s,
                )
            except httpx.HTTPError as exc:
                raise TransientError(f"token endpoint unreachable: {type(exc).__name__}") from exc
            if response.status_code >= 500 or response.status_code == 429:
                raise TransientError(f"token endpoint returned {response.status_code}")
            if response.status_code != 200:
                raise AuthError(502, "service_token_rejected", f"Token endpoint returned {response.status_code}.")
            body = response.json()
            self._token = body["access_token"]
            self._expires_at = self.clock() + float(body.get("expires_in", 0))
            return self._token
