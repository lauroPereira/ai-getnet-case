"""v0.13.0 task 98 (spec D2, CA-68, external issuer part): tokens of an external OIDC issuer (`OIDC_ISSUERS`) are
accepted with their groups mapped to a role and the role's scopes; an unknown issuer is refused with `invalid_issuer`;
signature, algorithm, `aud`, `exp`, `nbf` and lifetime are checked; discovery and JWKS are cached, renewed on a key
rotation at a limited rate, and an unreachable issuer refuses only its own tokens. Fake issuers in process, keys
generated in the tests, no network beyond a loopback server for the fetch helper, no cost."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import re
import socket
import sqlite3
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import jwt
import pytest
import yaml
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa

from merchant_assistant.api import identity
from merchant_assistant.api.identity import (
    CredentialConfigError,
    Identity,
    InvalidToken,
    IssuerUnavailable,
    NoRole,
    UnknownIssuer,
    configured_issuers,
)
from merchant_assistant.config import PROJECT_ROOT, Settings
from merchant_assistant.data.db import connect
from merchant_assistant.testing import TEST_USER_PASSWORDS, merchant_headers

IDP = "https://idp.example/dex"
OTHER_IDP = "https://other-idp.example"
GROUPS = {
    "assistant-merchants": "merchant",
    "assistant-operators": "operator",
    "assistant-admins": "admin",
}
OPERATOR_SCOPES = {"handoff:operate", "support:read"}
MERCHANT_SCOPES = {"support:read", "handoff:create", "conversation:read", "support:write"}


def issuer_entry(issuer=IDP, **override) -> dict:
    return {
        "issuer": issuer,
        "audience": "merchant-assistant",
        "groups": GROUPS,
        "customer_id_claim": "name",
    } | override


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


class FakeIssuer:
    """An OIDC issuer in process: discovery, JWKS and signed tokens with keys generated here."""

    def __init__(self, issuer: str = IDP) -> None:
        self.issuer = issuer
        self.private: dict[str, object] = {}
        self.published: list[str] = []
        self.down = False
        self.discovery_issuer = issuer
        self.jwk_extra: dict[str, dict] = {}

    def add_key(self, kid: str, kind: str = "rsa", publish: bool = True) -> None:
        if kind == "ec":
            self.private[kid] = ec.generate_private_key(ec.SECP256R1())
        else:
            self.private[kid] = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        if publish:
            self.published.append(kid)

    def jwk(self, kid: str) -> dict:
        key = self.private[kid]
        algorithm = jwt.algorithms.ECAlgorithm if isinstance(key, ec.EllipticCurvePrivateKey) else None
        algorithm = algorithm or jwt.algorithms.RSAAlgorithm
        public = json.loads(algorithm.to_jwk(key.public_key()))
        return public | {"kid": kid, "use": "sig"} | self.jwk_extra.get(kid, {})

    def serve(self, url: str) -> dict:
        if self.down:
            raise IssuerUnavailable("connection refused")
        base = self.issuer.rstrip("/")
        if url == f"{base}/.well-known/openid-configuration":
            return {"issuer": self.discovery_issuer, "jwks_uri": f"{base}/keys"}
        if url == f"{base}/keys":
            return {"keys": [self.jwk(kid) for kid in self.published]}
        raise IssuerUnavailable("HTTP 404")

    def token(self, kid: str = "k1", algorithm: str = "RS256", headers: dict | None = None, **claims) -> str:
        now = int(time.time())
        payload = {
            "iss": self.issuer,
            "sub": "CgdvcF9hbmESBWxvY2Fs",
            "aud": "merchant-assistant",
            "exp": now + 600,
            "iat": now,
            "groups": ["assistant-operators"],
            "name": "op_ana",
        } | claims
        payload = {k: v for k, v in payload.items() if v is not None}
        return jwt.encode(payload, self.private[kid], algorithm=algorithm, headers={"kid": kid} | (headers or {}))


class Network:
    """Replaces `identity.fetch_json`: routes each URL to its fake issuer and records every fetch."""

    def __init__(self, *issuers: FakeIssuer) -> None:
        self.issuers = issuers
        self.fetches: list[str] = []

    def __call__(self, url: str) -> dict:
        self.fetches.append(url)
        for issuer in self.issuers:
            if url.startswith(issuer.issuer.rstrip("/") + "/"):
                return issuer.serve(url)
        raise IssuerUnavailable("unknown host")


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


@pytest.fixture
def idp(monkeypatch):
    issuer = FakeIssuer()
    issuer.add_key("k1")
    network = Network(issuer)
    clock = Clock()
    monkeypatch.setattr(identity, "fetch_json", network)
    monkeypatch.setattr(identity, "monotonic_seconds", clock)
    return issuer, network, clock


@pytest.fixture
def external(offline, settings, idp):
    """The API with the fake issuer configured: returns (client, issuer, network, clock)."""
    settings.oidc_issuers = json.dumps([issuer_entry()])
    client, _, _ = offline()
    return (client, *idp)


def get(client, path: str, token: str):
    return client.get(path, headers={"Authorization": f"Bearer {token}"})


def assert_invalid(response, code: str = "invalid_token"):
    assert response.status_code == 401, response.text
    assert response.json()["error"]["code"] == code
    assert 'error="invalid_token"' in response.headers["www-authenticate"]


def open_db(settings):
    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row
    return conn


def verify(client, token):
    conn = connect(client.app.state.settings.db_path)
    try:
        return client.app.state.identity.verify(token, conn)
    finally:
        conn.close()


# --- accepted tokens ------------------------------------------------------------------------------------------------


def test_operator_token_of_the_external_issuer_is_accepted_with_the_role_scopes(external, settings):
    client, issuer, _, _ = external
    response = get(client, "/v1/handoffs", issuer.token())
    assert response.status_code == 200, response.text
    conn = open_db(settings)
    row = conn.execute("SELECT * FROM api_principals WHERE issuer=?", (IDP,)).fetchone()
    conn.close()
    assert row["principal_id"] == "operator:CgdvcF9hbmESBWxvY2Fs@https%3A%2F%2Fidp.example%2Fdex"
    assert row["role"] == "operator" and row["customer_id"] is None
    assert set(json.loads(row["scopes"])) == OPERATOR_SCOPES


def test_external_principal_components_cannot_collide(offline, settings, monkeypatch):
    issuer_a = FakeIssuer("https://issuer.example/x@issuer.example")
    issuer_b = FakeIssuer("https://issuer.example")
    issuer_a.add_key("a1")
    issuer_b.add_key("b1")
    monkeypatch.setattr(identity, "fetch_json", Network(issuer_a, issuer_b))
    settings.oidc_issuers = json.dumps([issuer_entry(issuer_a.issuer), issuer_entry(issuer_b.issuer)])
    client, _, _ = offline()

    for token in (issuer_a.token("a1", sub="alice"), issuer_b.token("b1", sub="alice@issuer.example/x")):
        assert get(client, "/v1/handoffs", token).status_code == 200

    conn = open_db(settings)
    try:
        principals = {
            row["issuer"]: row["principal_id"]
            for row in conn.execute("SELECT issuer, principal_id FROM api_principals WHERE issuer IS NOT NULL")
        }
    finally:
        conn.close()
    assert principals == {
        issuer_a.issuer: "operator:alice@https%3A%2F%2Fissuer.example%2Fx%40issuer.example",
        issuer_b.issuer: "operator:alice%40issuer.example%2Fx@https%3A%2F%2Fissuer.example",
    }


@pytest.mark.parametrize(
    ("changed_issuer", "expected_id"),
    [
        ("http://dex/dex", "operator:same-sub@http%3A%2F%2Fdex%2Fdex"),
        ("https://dex/dex/", "operator:same-sub@https%3A%2F%2Fdex%2Fdex%2F"),
    ],
)
def test_external_principal_ownership_survives_an_issuer_configuration_change(
    offline, settings, monkeypatch, changed_issuer, expected_id
):
    original = FakeIssuer("https://dex/dex")
    changed = FakeIssuer(changed_issuer)
    original.add_key("original")
    changed.add_key("changed")
    monkeypatch.setattr(identity, "fetch_json", Network(original))
    settings.oidc_issuers = json.dumps([issuer_entry(original.issuer)])
    first, _, _ = offline()
    opened = first.post("/messages", json={"message": "Quero falar com um atendente"}, headers=merchant_headers(first))
    assert opened.status_code == 200 and opened.json()["status"] == "handoff"
    first_token = original.token("original", sub="same-sub")
    cases = get(first, "/v1/handoffs", first_token).json()["cases"]
    case = next(case for case in cases if case["protocol"] == opened.json()["handoff"]["protocol"])
    claim_path = f"/v1/handoffs/{case['case_id']}/claim"
    claim = first.post(claim_path, headers={"Authorization": f"Bearer {first_token}"})
    assert claim.status_code == 200
    assert claim.json()["claimed_by"] == "same-sub@https%3A%2F%2Fdex%2Fdex"

    monkeypatch.setattr(identity, "fetch_json", Network(changed))
    settings.oidc_issuers = json.dumps([issuer_entry(changed.issuer)])
    second, _, _ = offline()
    assert_invalid(get(second, "/v1/handoffs", first_token), "invalid_issuer")
    second_token = changed.token("changed", sub="same-sub")
    claim = second.post(claim_path, headers={"Authorization": f"Bearer {second_token}"})
    assert claim.status_code == 409
    assert claim.json()["error"]["code"] == "claimed_by_other"

    conn = open_db(settings)
    try:
        principals = {
            row["issuer"]: row["principal_id"]
            for row in conn.execute(
                "SELECT issuer, principal_id FROM api_principals WHERE issuer IN (?, ?)",
                (original.issuer, changed.issuer),
            )
        }
    finally:
        conn.close()
    assert principals == {
        original.issuer: "operator:same-sub@https%3A%2F%2Fdex%2Fdex",
        changed.issuer: expected_id,
    }


def test_merchant_token_takes_its_merchant_from_the_configured_claim(external, settings):
    client, issuer, _, _ = external
    token = issuer.token(sub="merchant-sub-1", groups=["assistant-merchants"], name="cliente1988")
    assert get(client, "/v1/profiles", token).status_code == 200
    conn = open_db(settings)
    row = conn.execute("SELECT * FROM api_principals WHERE issuer=?", (IDP,)).fetchone()
    conn.close()
    assert row["principal_id"] == "merchant:merchant-sub-1@https%3A%2F%2Fidp.example%2Fdex"
    assert row["customer_id"] == "cliente1988"
    assert set(json.loads(row["scopes"])) == MERCHANT_SCOPES
    principal, _ = verify(client, token)
    assert principal.customer_id == "cliente1988" and principal.has("support:write")


def test_scopes_come_from_the_role_and_never_from_the_token(external):
    client, issuer, _, _ = external
    token = issuer.token(scope="kb:admin profiles:admin handoff:integrate", role="admin")
    principal, _ = verify(client, token)
    assert principal.role == "operator" and set(principal.scopes) == OPERATOR_SCOPES


def test_own_issuer_stays_the_default_next_to_the_external_one(external):
    client, issuer, _, _ = external
    own = client.post(
        "/v1/auth/token",
        data={"grant_type": "password", "username": "op_ana", "password": TEST_USER_PASSWORDS["op_ana"]},
    )
    assert own.status_code == 200, own.text
    assert get(client, "/v1/handoffs", own.json()["access_token"]).status_code == 200
    assert get(client, "/v1/handoffs", issuer.token()).status_code == 200


def test_external_token_without_jti_can_be_revoked(external):
    client, issuer, _, _ = external
    token = issuer.token()
    assert "jti" not in jwt.decode(token, options={"verify_signature": False})
    revoke = client.post("/v1/auth/revoke", headers={"Authorization": f"Bearer {token}"})
    assert revoke.status_code == 200
    assert_invalid(get(client, "/v1/handoffs", token))
    assert get(client, "/v1/handoffs", issuer.token(sub="another-operator")).status_code == 200


def test_revoking_an_external_token_never_revokes_a_local_one_with_the_same_jti(external):
    client, issuer, _, _ = external
    own = client.post(
        "/v1/auth/token",
        data={"grant_type": "password", "username": "op_ana", "password": TEST_USER_PASSWORDS["op_ana"]},
    ).json()["access_token"]
    local_jti = jwt.decode(own, options={"verify_signature": False})["jti"]
    foreign = issuer.token(jti=local_jti)  # an issuer the API does not control chose the same jti
    assert client.post("/v1/auth/revoke", headers={"Authorization": f"Bearer {foreign}"}).status_code == 200
    assert_invalid(get(client, "/v1/handoffs", foreign))
    assert get(client, "/v1/handoffs", own).status_code == 200
    conn = open_db(client.app.state.settings)
    try:
        rows = conn.execute("SELECT jti, principal_id FROM revoked_tokens").fetchall()
    finally:
        conn.close()
    # keyed by the issuer-prefixed jti, and naming the principal, not the raw `sub`
    assert [tuple(r) for r in rows] == [
        (f"{IDP}#{local_jti}", "operator:CgdvcF9hbmESBWxvY2Fs@https%3A%2F%2Fidp.example%2Fdex")
    ]


def test_an_external_merchant_with_a_local_jti_counts_its_messages_apart(external, settings):
    client, issuer, _, _ = external
    local = client.post(
        "/v1/auth/token",
        data={"grant_type": "password", "username": "cliente1988", "password": TEST_USER_PASSWORDS["cliente1988"]},
    ).json()["access_token"]
    jti = jwt.decode(local, options={"verify_signature": False})["jti"]
    foreign = issuer.token(sub="merchant-sub-1", groups=["assistant-merchants"], name="cliente1988", jti=jti)
    body = {"message": "Olá", "profile_id": "reference", "profile_version": 1, "router_mechanism": "llm"}
    for token in (local, foreign):
        sent = client.post("/v1/messages", headers={"Authorization": f"Bearer {token}"}, json=body)
        assert sent.status_code == 200, sent.text
    conn = open_db(settings)
    try:
        counters = {r["session_id"]: r["message_count"] for r in conn.execute("SELECT * FROM api_sessions")}
    finally:
        conn.close()
    assert counters == {jti: 1, f"{IDP}#{jti}": 1}  # the local counter is untouched by the external token


def test_ec_keys_are_accepted_when_the_issuer_allows_es256(offline, settings, idp):
    issuer, _, _ = idp
    issuer.add_key("ec1", kind="ec")
    settings.oidc_issuers = json.dumps([issuer_entry(algorithms=["ES256"])])
    client, _, _ = offline()
    assert get(client, "/v1/handoffs", issuer.token(kid="ec1", algorithm="ES256")).status_code == 200
    assert_invalid(get(client, "/v1/handoffs", issuer.token()))  # RS256 is not among its algorithms


# --- refused tokens -------------------------------------------------------------------------------------------------


def test_unknown_issuer_is_refused_with_invalid_issuer_and_nothing_is_fetched(external):
    client, issuer, network, _ = external
    stranger = FakeIssuer(OTHER_IDP)
    stranger.add_key("k1")
    assert_invalid(get(client, "/v1/handoffs", stranger.token()), "invalid_issuer")
    assert_invalid(get(client, "/v1/handoffs", issuer.token(iss=IDP + "/")), "invalid_issuer")  # exact comparison
    assert_invalid(get(client, "/v1/handoffs", issuer.token(iss=None)), "invalid_issuer")
    assert network.fetches == []


def test_wrong_signature_is_refused(external):
    client, issuer, _, _ = external
    impostor = FakeIssuer()
    impostor.add_key("k1")  # same issuer and kid, another key
    assert_invalid(get(client, "/v1/handoffs", impostor.token()))
    tampered = issuer.token().rsplit(".", 1)[0] + "." + impostor.token().rsplit(".", 1)[1]
    assert_invalid(get(client, "/v1/handoffs", tampered))


def test_wrong_or_missing_audience_is_refused(external):
    client, issuer, _, _ = external
    assert_invalid(get(client, "/v1/handoffs", issuer.token(aud="another-app")))
    assert_invalid(get(client, "/v1/handoffs", issuer.token(aud=None)))
    assert get(client, "/v1/handoffs", issuer.token(aud=["another-app", "merchant-assistant"])).status_code == 200


def test_time_claims_are_checked_with_a_small_explicit_tolerance(external):
    client, issuer, _, _ = external
    now = int(time.time())
    assert identity.EXTERNAL_LEEWAY_SECONDS == 30
    assert_invalid(get(client, "/v1/handoffs", issuer.token(iat=now - 700, exp=now - 60)))  # expired
    assert get(client, "/v1/handoffs", issuer.token(iat=now - 700, exp=now - 10)).status_code == 200  # tolerance
    assert_invalid(get(client, "/v1/handoffs", issuer.token(nbf=now + 120)))  # not yet valid
    assert get(client, "/v1/handoffs", issuer.token(nbf=now + 10)).status_code == 200
    assert_invalid(get(client, "/v1/handoffs", issuer.token(exp=None)))
    assert_invalid(get(client, "/v1/handoffs", issuer.token(iat=None)))
    assert_invalid(get(client, "/v1/handoffs", issuer.token(exp=now + 25 * 3600)))  # lifetime above 24 h


def test_only_the_configured_asymmetric_algorithms_are_accepted(external):
    client, issuer, _, _ = external
    payload = jwt.decode(issuer.token(), options={"verify_signature": False})
    unsigned = jwt.encode(payload, None, algorithm="none", headers={"kid": "k1"})
    assert_invalid(get(client, "/v1/handoffs", unsigned))
    public_pem = (
        issuer.private["k1"]
        .public_key()
        .public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    )
    signing_input = (
        f"{b64url(json.dumps({'alg': 'HS256', 'kid': 'k1'}).encode())}.{b64url(json.dumps(payload).encode())}"
    )
    signature = hmac.new(public_pem, signing_input.encode(), hashlib.sha256).digest()
    hmac_token = f"{signing_input}.{b64url(signature)}"
    assert_invalid(get(client, "/v1/handoffs", hmac_token))  # the public key used as an HMAC secret
    assert_invalid(get(client, "/v1/handoffs", issuer.token(algorithm="RS384")))  # not configured for this issuer
    assert_invalid(get(client, "/v1/handoffs", issuer.token(headers={"kid": ""})))
    assert_invalid(get(client, "/v1/handoffs", issuer.token(headers={"typ": "logout+jwt"})))


def test_unusable_subject_or_jti_is_refused(external):
    client, issuer, _, _ = external
    assert_invalid(get(client, "/v1/handoffs", issuer.token(sub="")))
    assert_invalid(get(client, "/v1/handoffs", issuer.token(sub="x" * 256)))
    assert_invalid(get(client, "/v1/handoffs", issuer.token(sub="op\nana")))
    assert_invalid(get(client, "/v1/handoffs", issuer.token(jti=123)))


# --- groups --------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "groups",
    [["visitors"], [], None, ["assistant-operators", "assistant-admins"], 42, [None, 7]],
    ids=["unrecognised", "empty", "missing", "two-roles", "not-a-list", "not-strings"],
)
def test_token_without_exactly_one_recognised_group_gets_no_role(external, groups):
    client, issuer, _, _ = external
    response = get(client, "/v1/handoffs", issuer.token(groups=groups))
    assert response.status_code == 403 and response.json()["error"]["code"] == "insufficient_scope"
    assert 'error="insufficient_scope"' in response.headers["www-authenticate"]
    assert get(client, "/v1/profiles", issuer.token(groups=groups)).status_code == 403


def test_groups_claim_may_be_a_single_string_and_repeated_groups_of_one_role_are_fine(offline, settings, idp):
    issuer, _, _ = idp
    settings.oidc_issuers = json.dumps(
        [issuer_entry(groups={"ops": "operator", "support": "operator"}, groups_claim="roles")]
    )
    client, _, _ = offline()
    assert get(client, "/v1/handoffs", issuer.token(groups=None, roles="ops")).status_code == 200
    assert get(client, "/v1/handoffs", issuer.token(groups=None, roles=["ops", "support"])).status_code == 200
    assert get(client, "/v1/handoffs", issuer.token(roles=None)).status_code == 403  # `groups` is not read


@pytest.mark.parametrize("name", [None, "", "not a merchant!", 7])
def test_merchant_group_without_a_usable_merchant_is_refused(external, name):
    client, issuer, _, _ = external
    assert_invalid(get(client, "/v1/profiles", issuer.token(groups=["assistant-merchants"], name=name)))


# --- role by verified e-mail (task 102a: the static users of Dex v2.41.1 emit no `groups`) -------------------------

DEX = "http://dex:5556/dex"


def example_issuers() -> str:
    """The commented `OIDC_ISSUERS` value of .env.example, the one the QA uses with the compose Dex."""
    lines = (PROJECT_ROOT / ".env.example").read_text(encoding="utf-8").splitlines()
    example = next(line for line in lines if line.startswith("# OIDC_ISSUERS='"))
    return example.removeprefix("# OIDC_ISSUERS='").removesuffix("'")


@pytest.fixture
def dex(offline, settings, monkeypatch):
    """The API with the example configuration and a fake Dex that, like the real static users, emits `email`,
    `email_verified` and `name` but no `groups`: returns (client, issuer)."""
    issuer = FakeIssuer(DEX)
    issuer.add_key("k1")
    monkeypatch.setattr(identity, "fetch_json", Network(issuer))
    settings.oidc_issuers = example_issuers()
    client, _, _ = offline()
    return client, issuer


def dex_token(issuer: FakeIssuer, email: str | None, name: str | None, **claims) -> str:
    return issuer.token(**({"sub": f"sub-{name}", "groups": None, "name": name, "email": email, "email_verified": True}
                           | claims))


def test_dex_operator_is_mapped_by_its_verified_email(dex, settings):
    client, issuer = dex
    token = dex_token(issuer, "op_ana@operador.example", "op_ana")
    assert get(client, "/v1/handoffs", token).status_code == 200
    principal, _ = verify(client, token)
    assert principal.principal_id == "operator:sub-op_ana@http%3A%2F%2Fdex%3A5556%2Fdex"
    assert principal.customer_id is None
    assert set(principal.scopes) == OPERATOR_SCOPES


def test_dex_merchant_is_mapped_by_its_email_and_takes_its_merchant_from_name(dex):
    client, issuer = dex
    token = dex_token(issuer, "cliente1988@lojista.example", "cliente1988")
    sent = client.post("/messages", json={"message": "Olá"}, headers={"Authorization": f"Bearer {token}"})
    assert sent.status_code == 200, sent.text
    principal, _ = verify(client, token)
    assert principal.role == "merchant" and principal.customer_id == "cliente1988"
    assert set(principal.scopes) == MERCHANT_SCOPES


@pytest.mark.parametrize(
    ("email", "extra"),
    [
        ("visitante@visitante.example", {}),  # the third static user: no role in the map
        ("op_ana@operador.example", {"email_verified": False}),
        ("op_ana@operador.example", {"email_verified": "true"}),  # only the JSON true counts
        ("op_ana@operador.example", {"email_verified": 1}),
        ("op_ana@operador.example", {"email_verified": None}),  # missing: fail closed
        (None, {}),
        ("OP_ANA@operador.example", {}),  # compared exactly, no normalisation
        ("op_ana@operador.example.evil", {}),
        ("x.op_ana@operador.example", {}),
        ("op_ana@operador.example ", {}),
        (["op_ana@operador.example", "cliente1988@lojista.example"], {}),  # two roles
        (["op_ana@operador.example"], {}),  # `email` is one string, never a list
        ("visitante@visitante.example", {"groups": ["merchant-assistant-operators"]}),  # `groups` is not read
    ],
    ids=[
        "visitor",
        "unverified",
        "verified-as-text",
        "verified-as-number",
        "verified-missing",
        "no-email",
        "case",
        "suffix",
        "prefix",
        "space",
        "two",
        "list",
        "groups",
    ],
)
def test_dex_tokens_without_a_mapped_verified_email_get_403(dex, email, extra):
    client, issuer = dex
    token = dex_token(issuer, email, "op_ana", **extra)
    response = get(client, "/v1/handoffs", token)
    assert response.status_code == 403 and response.json()["error"]["code"] == "insufficient_scope"


def test_dex_token_without_email_verified_gets_no_role(dex):
    """Fail closed: mapped by e-mail, a token that does not say `email_verified: true` gets 403."""
    client, issuer = dex
    token = dex_token(issuer, "op_ana@operador.example", "op_ana", email_verified=None)
    response = get(client, "/v1/handoffs", token)
    assert response.status_code == 403 and response.json()["error"]["code"] == "insufficient_scope"


def test_email_verified_does_not_affect_the_default_mapping_by_groups(external):
    client, issuer, _, _ = external
    for verified in (False, "no", None):
        token = issuer.token(email="op_ana@idp.example", email_verified=verified)
        assert get(client, "/v1/handoffs", token).status_code == 200


# --- discovery, JWKS cache and key rotation ------------------------------------------------------------------------


def test_discovery_and_jwks_are_cached_and_fetched_again_after_their_validity(external):
    client, issuer, network, clock = external
    for _ in range(3):
        assert get(client, "/v1/handoffs", issuer.token()).status_code == 200
    assert network.fetches == [f"{IDP}/.well-known/openid-configuration", f"{IDP}/keys"]
    clock.now += identity.JWKS_TTL_SECONDS - 1
    assert get(client, "/v1/handoffs", issuer.token()).status_code == 200
    assert len(network.fetches) == 2
    clock.now += 1
    assert get(client, "/v1/handoffs", issuer.token()).status_code == 200
    assert len(network.fetches) == 4


def test_key_rotation_is_picked_up_by_one_renewal(external):
    client, issuer, network, clock = external
    assert get(client, "/v1/handoffs", issuer.token()).status_code == 200
    issuer.add_key("k2")
    issuer.published.remove("k1")
    clock.now += 1
    assert get(client, "/v1/handoffs", issuer.token(kid="k2")).status_code == 200
    assert len(network.fetches) == 4  # one renewal: discovery and JWKS again
    assert_invalid(get(client, "/v1/handoffs", issuer.token(kid="k1")))  # the retired key is gone


def test_unknown_kids_renew_the_jwks_at_most_once_per_interval(external):
    client, issuer, network, clock = external
    assert get(client, "/v1/handoffs", issuer.token()).status_code == 200
    issuer.add_key("forged", publish=False)
    for _ in range(5):
        assert_invalid(get(client, "/v1/handoffs", issuer.token(kid="forged")))
    assert len(network.fetches) == 4  # the first fetch and a single renewal
    issuer.add_key("k2")
    clock.now += identity.JWKS_FORCED_RENEWAL_SECONDS - 1
    assert_invalid(get(client, "/v1/handoffs", issuer.token(kid="k2")))  # still inside the interval
    clock.now += 1
    assert get(client, "/v1/handoffs", issuer.token(kid="k2")).status_code == 200
    assert len(network.fetches) == 6


def test_unreachable_issuer_refuses_only_its_tokens_and_is_retried_later(offline, settings, idp, caplog):
    issuer, network, clock = idp
    second = FakeIssuer(OTHER_IDP)
    second.add_key("s1")
    network.issuers = (issuer, second)
    settings.oidc_issuers = json.dumps([issuer_entry(), issuer_entry(OTHER_IDP)])
    issuer.down = True
    client, _, _ = offline()
    assert client.get("/health").status_code == 200
    with caplog.at_level(logging.WARNING, logger="merchant_assistant.identity"):
        token = issuer.token()
        assert_invalid(get(client, "/v1/handoffs", token))
    assert any(IDP in r.getMessage() for r in caplog.records)
    assert all(token not in r.getMessage() for r in caplog.records)
    assert get(client, "/v1/handoffs", second.token(kid="s1")).status_code == 200  # the other issuer works
    own = client.post(
        "/v1/auth/token",
        data={"grant_type": "password", "username": "op_ana", "password": TEST_USER_PASSWORDS["op_ana"]},
    )
    assert get(client, "/v1/handoffs", own.json()["access_token"]).status_code == 200  # and so does the API's own
    fetched = len(network.fetches)
    issuer.down = False
    assert_invalid(get(client, "/v1/handoffs", issuer.token()))  # inside the retry interval: nothing is fetched
    assert len(network.fetches) == fetched
    clock.now += identity.ISSUER_RETRY_SECONDS
    assert get(client, "/v1/handoffs", issuer.token()).status_code == 200


def test_discovery_naming_another_issuer_or_an_unsafe_jwks_uri_is_refused(external, monkeypatch):
    client, issuer, _, clock = external
    issuer.discovery_issuer = IDP + "/"
    assert_invalid(get(client, "/v1/handoffs", issuer.token()))
    issuer.discovery_issuer = IDP
    original = issuer.serve
    unsafe = {"issuer": IDP, "jwks_uri": "http://keys.example/jwks"}
    monkeypatch.setattr(issuer, "serve", lambda url: unsafe if url.endswith("configuration") else original(url))
    clock.now += identity.ISSUER_RETRY_SECONDS
    assert_invalid(get(client, "/v1/handoffs", issuer.token()))  # plain http on a public host


def test_no_token_in_the_logs(external, caplog):
    client, issuer, _, _ = external
    issuer.add_key("nope", publish=False)
    tokens = [issuer.token(), issuer.token(aud="x"), issuer.token(groups=["visitors"]), issuer.token(kid="nope")]
    with caplog.at_level(logging.DEBUG):
        for token in tokens:
            get(client, "/v1/handoffs", token)
    text = "\n".join(r.getMessage() for r in caplog.records)
    assert all(token not in text and token.split(".")[2] not in text for token in tokens)


def test_cli_and_mcp_verifier_refuse_unknown_issuers_and_no_role(settings, idp, tmp_path):
    issuer, _, _ = idp
    settings.oidc_issuers = json.dumps([issuer_entry()])
    verifier = Identity(settings)
    conn = connect(tmp_path / "verifier.sqlite3")
    stranger = FakeIssuer(OTHER_IDP)
    stranger.add_key("k1")
    with pytest.raises(UnknownIssuer):
        verifier.verify(stranger.token(), conn)
    with pytest.raises(NoRole):
        verifier.verify(issuer.token(groups=["visitors"]), conn)
    assert issubclass(UnknownIssuer, InvalidToken) and issubclass(NoRole, InvalidToken)


# --- configuration -------------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value",
    [
        "not json",
        json.dumps(issuer_entry()),  # an object, not a list
        json.dumps([issuer_entry(algorithms=["none"])]),
        json.dumps([issuer_entry(algorithms=["HS256"])]),
        json.dumps([issuer_entry(algorithms=["RS256", "HS512"])]),
        json.dumps([issuer_entry(algorithms=[])]),
        json.dumps([issuer_entry(audience="")]),
        json.dumps([{k: v for k, v in issuer_entry().items() if k != "audience"}]),
        json.dumps([issuer_entry(groups={})]),
        json.dumps([issuer_entry(groups={"x": "demo"})]),
        json.dumps([issuer_entry(groups={"x": "service"})]),
        json.dumps([issuer_entry(customer_id_claim=None)]),
        json.dumps([issuer_entry(groups_claim="")]),
        json.dumps([issuer_entry("http://idp.example/dex")]),
        json.dumps([issuer_entry("https://idp.example/dex?x=1")]),
        json.dumps([issuer_entry("https://user:pw@idp.example/dex")]),
        json.dumps([issuer_entry("ftp://idp.example")]),
        json.dumps([issuer_entry("http://127.0.0.1:8000")]),  # the assistant's own issuer
        json.dumps([issuer_entry(), issuer_entry()]),
        json.dumps([issuer_entry(extra=True)]),
        json.dumps([issuer_entry(), issuer_entry(IDP + "/")]),  # the same issuer with a trailing slash
        json.dumps([issuer_entry("http://2852039166")]),  # an IPv4 address written as a number
        json.dumps([issuer_entry("http://0x7f000001")]),
        json.dumps([issuer_entry("http://[fe80::1]")]),
        json.dumps([issuer_entry("http://deadbeef")]),  # only hex digits
        json.dumps([issuer_entry("http://10.0.0.5:5556/dex")]),
        json.dumps([issuer_entry("http://dex:99999/dex")]),
        json.dumps([issuer_entry(groups_claim="email", groups={"*@operador.example": "operator"})]),
        json.dumps([issuer_entry(groups_claim="email", groups={"@operador.example": "operator"})]),
        json.dumps([issuer_entry(groups_claim="email", groups={"operador.example": "operator"})]),
        json.dumps([issuer_entry(groups_claim="email", groups={"op ana@operador.example": "operator"})]),
        json.dumps([issuer_entry(groups_claim="email", groups={"a@b@operador.example": "operator"})]),
    ],
)
def test_invalid_external_issuer_configuration_stops_the_startup(settings, offline, value):
    settings.oidc_issuers = value
    with pytest.raises(CredentialConfigError):
        configured_issuers(settings)
    with pytest.raises(CredentialConfigError):
        offline()


def test_valid_configurations(settings):
    settings.oidc_issuers = json.dumps(
        [
            issuer_entry("http://dex:5556/dex"),
            issuer_entry("http://localhost:5556/dex", groups={"ops": "operator"}, customer_id_claim=None),
            issuer_entry(OTHER_IDP, algorithms=["PS256", "ES384"], groups_claim="roles"),
        ]
    )
    dex, local, other = configured_issuers(settings)
    assert dex.label == "dex:5556/dex" and dex.algorithms == ("RS256",) and dex.groups_claim == "groups"
    assert local.customer_id_claim is None
    assert other.algorithms == ("PS256", "ES384") and other.groups_claim == "roles"
    settings.oidc_issuers = "  "
    assert configured_issuers(settings) == ()


def test_example_configuration_matches_the_dex_of_the_compose():
    """The commented `OIDC_ISSUERS` line of .env.example is valid and names the compose Dex, its client and users:
    roles by exact e-mail (its static users emit no `groups`), the merchant from `name` (the static `username`)."""
    settings = Settings(_env_file=None, oidc_issuers=example_issuers())
    (dex,) = configured_issuers(settings)
    config = yaml.safe_load((PROJECT_ROOT / "docker" / "dex" / "config.yaml").read_text(encoding="utf-8"))
    assert config["issuer"] == dex.issuer
    assert dex.audience in {c["id"] for c in config["staticClients"]}
    assert dex.groups_claim == "email" and dex.customer_id_claim == "name"
    users = {user["email"]: user for user in config["staticPasswords"]}
    assert set(dex.groups) < set(users)  # every mapped address is a static user, and one user maps to nothing
    assert sorted(dex.groups.values()) == ["merchant", "operator"]
    for email, role in dex.groups.items():
        if role == "merchant":
            assert re.fullmatch(settings.user_id_pattern, users[email]["username"])
    assert all("groups" not in user for user in config["staticPasswords"])  # Dex v2.41.1 would not emit them
    for client in config["staticClients"]:
        assert client["secret"].endswith("-fictitious")
    compose = yaml.safe_load((PROJECT_ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
    assert compose["services"]["dex"]["profiles"] == ["oidc"]
    assert "profiles" not in compose["services"]["api"]


# --- fetch helper over a loopback server ---------------------------------------------------------------------------


class _Handler(BaseHTTPRequestHandler):
    routes: dict[str, tuple[int, dict[str, str], bytes]] = {}

    def do_GET(self):  # noqa: N802
        status, headers, body = self.routes.get(self.path, (404, {}, b""))
        self.send_response(status)
        for name, value in headers.items():
            self.send_header(name, value)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


@pytest.fixture
def loopback():
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_fetch_json_follows_no_redirect_and_bounds_the_response(loopback):
    _Handler.routes = {
        "/ok": (200, {"Content-Type": "application/json"}, b'{"issuer": "x"}'),
        "/redirect": (302, {"Location": "/ok"}, b""),
        "/big": (200, {}, b'{"k": "' + b"a" * identity.FETCH_MAX_BYTES + b'"}'),
        "/list": (200, {}, b"[1, 2]"),
        "/text": (200, {}, b"<html>"),
        "/error": (500, {}, b"{}"),
    }
    assert identity.fetch_json(f"{loopback}/ok") == {"issuer": "x"}
    for path in ("/redirect", "/big", "/list", "/text", "/error", "/missing"):
        with pytest.raises(IssuerUnavailable):
            identity.fetch_json(f"{loopback}{path}")


def test_fetch_json_turns_connection_errors_into_an_unavailable_issuer():
    with pytest.raises(IssuerUnavailable):
        identity.fetch_json("http://127.0.0.1:9/.well-known/openid-configuration")


def test_app_starts_with_an_external_issuer_that_is_down(settings, offline, idp):
    issuer, network, _ = idp
    issuer.down = True
    settings.oidc_issuers = json.dumps([issuer_entry()])
    client, _, _ = offline()
    assert client.get("/health").status_code == 200 and network.fetches == []  # discovery happens on demand


# --- review round 2 -------------------------------------------------------------------------------------------------


def _b64url_decode(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _ecdsa_twin(token: str) -> str:
    """The same ES256 signature with s replaced by n - s: also valid for the same signed part."""
    head, signature = token.rsplit(".", 1)
    raw = _b64url_decode(signature)
    r, s = int.from_bytes(raw[:32], "big"), int.from_bytes(raw[32:], "big")
    order = 0xFFFFFFFF00000000FFFFFFFFFFFFFFFFBCE6FAADA7179E84F3B9CAC2FC632551  # P-256
    return f"{head}.{b64url(r.to_bytes(32, 'big') + (order - s).to_bytes(32, 'big'))}"


def test_revoked_token_without_jti_stays_revoked_under_another_signature_encoding(offline, settings, idp):
    issuer, _, _ = idp
    issuer.add_key("ec1", kind="ec")
    settings.oidc_issuers = json.dumps([issuer_entry(algorithms=["RS256", "ES256"])])
    client, _, _ = offline()
    for token, variant in (
        (rsa_token := issuer.token(), rsa_token + "=="),
        (ec_token := issuer.token(kid="ec1", algorithm="ES256", sub="ec-operator"), _ecdsa_twin(ec_token)),
    ):
        assert variant != token
        _, original = verify(client, token)
        _, twin = verify(client, variant)  # the variant verifies: it is the same signed token
        assert twin["jti"] == original["jti"]  # one per-token counter and one revocation for both
        assert client.post("/v1/auth/revoke", headers={"Authorization": f"Bearer {token}"}).status_code == 200
        assert_invalid(get(client, "/v1/handoffs", token))
        assert_invalid(get(client, "/v1/handoffs", variant))


def test_time_claims_written_as_text_are_refused_without_a_server_error(external):
    client, issuer, _, _ = external
    now = int(time.time())
    assert_invalid(get(client, "/v1/handoffs", issuer.token(exp=str(now + 600))))
    assert_invalid(get(client, "/v1/handoffs", issuer.token(iat=str(now))))
    assert_invalid(get(client, "/v1/handoffs", issuer.token(exp=True)))


@pytest.mark.parametrize("extra", [{"alg": "RS384"}, {"use": "enc"}])
def test_jwk_meant_for_another_algorithm_or_use_is_refused(external, extra):
    client, issuer, _, _ = external
    issuer.jwk_extra["k1"] = extra
    assert_invalid(get(client, "/v1/handoffs", issuer.token()))


def test_plain_http_issuer_needs_its_jwks_on_its_own_origin(offline, settings, idp, monkeypatch):
    issuer, network, clock = idp
    internal = FakeIssuer("http://metadata:8080/oidc")
    internal.add_key("i1")
    network.issuers = (issuer, internal)
    settings.oidc_issuers = json.dumps([issuer_entry("http://metadata:8080/oidc")])
    client, _, _ = offline()
    assert get(client, "/v1/handoffs", internal.token(kid="i1")).status_code == 200  # same origin
    keys_elsewhere = "http://metadata:80/latest/keys"
    internal.add_key("i2")
    served = {
        f"{internal.issuer}/.well-known/openid-configuration": {"issuer": internal.issuer, "jwks_uri": keys_elsewhere},
        keys_elsewhere: {"keys": [internal.jwk("i1"), internal.jwk("i2")]},  # the keys would be there
    }
    monkeypatch.setattr(identity, "fetch_json", lambda url: served[url])
    clock.now += identity.JWKS_TTL_SECONDS
    assert_invalid(get(client, "/v1/handoffs", internal.token(kid="i2")))  # another port is another origin
    served[f"{internal.issuer}/.well-known/openid-configuration"]["jwks_uri"] = "https://keys.example/oidc/keys"
    served["https://keys.example/oidc/keys"] = served[keys_elsewhere]
    clock.now += identity.ISSUER_RETRY_SECONDS
    assert get(client, "/v1/handoffs", internal.token(kid="i2")).status_code == 200  # https may be elsewhere


class SlowNetwork:
    """Wraps the fake network: while `gate` is closed, fetches wait for it (a slow or stalled issuer)."""

    def __init__(self, network: Network) -> None:
        self.network = network
        self.gate = threading.Event()
        self.gate.set()
        self.waiting = threading.Event()

    def __call__(self, url: str) -> dict:
        if not self.gate.is_set():
            self.waiting.set()
            assert self.gate.wait(timeout=10)
        return self.network(url)


def test_a_slow_fetch_never_holds_other_requests(offline, settings, idp, monkeypatch):
    issuer, network, clock = idp
    slow = SlowNetwork(network)
    monkeypatch.setattr(identity, "fetch_json", slow)
    settings.oidc_issuers = json.dumps([issuer_entry()])
    client, _, _ = offline()
    own = client.post(
        "/v1/auth/token",
        data={"grant_type": "password", "username": "op_ana", "password": TEST_USER_PASSWORDS["op_ana"]},
    ).json()["access_token"]
    results: list[int] = []

    def first_request():
        results.append(get(client, "/v1/handoffs", issuer.token()).status_code)

    # no keys yet and a fetch in progress: refused at once, and the API's own tokens are not delayed
    slow.gate.clear()
    fetching = threading.Thread(target=first_request)
    fetching.start()
    assert slow.waiting.wait(timeout=10)
    started = time.monotonic()
    assert_invalid(get(client, "/v1/handoffs", issuer.token(sub="another")))
    assert get(client, "/v1/handoffs", own).status_code == 200
    assert time.monotonic() - started < 2
    slow.gate.set()
    fetching.join(timeout=10)
    assert results == [200]

    # cached keys and a renewal in progress: the cached keys answer at once
    clock.now += identity.JWKS_TTL_SECONDS
    slow.waiting.clear()
    slow.gate.clear()
    fetching = threading.Thread(target=first_request)
    fetching.start()
    assert slow.waiting.wait(timeout=10)
    started = time.monotonic()
    assert get(client, "/v1/handoffs", issuer.token(sub="another")).status_code == 200
    assert time.monotonic() - started < 2
    slow.gate.set()
    fetching.join(timeout=10)
    assert results == [200, 200]


def test_cached_keys_keep_serving_while_renewals_fail_up_to_a_limit(external):
    client, issuer, network, clock = external
    assert get(client, "/v1/handoffs", issuer.token()).status_code == 200
    issuer.down = True
    clock.now += identity.JWKS_TTL_SECONDS
    assert get(client, "/v1/handoffs", issuer.token()).status_code == 200  # renewal failed, cached key used
    fetched = len(network.fetches)
    assert get(client, "/v1/handoffs", issuer.token()).status_code == 200
    assert len(network.fetches) == fetched  # no new fetch inside the retry interval
    clock.now = 1000.0 + identity.JWKS_MAX_STALE_SECONDS
    assert_invalid(get(client, "/v1/handoffs", issuer.token()))  # too old to trust


class _DripHandler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        self.send_response(200)
        self.send_header("Content-Length", "200")
        self.end_headers()
        try:
            for _ in range(200):
                self.wfile.write(b" ")
                self.wfile.flush()
                time.sleep(0.3)
        except OSError:
            pass

    def log_message(self, *args):
        pass


def test_fetch_json_deadline_ends_a_dripping_body(monkeypatch):
    monkeypatch.setattr(identity, "FETCH_DEADLINE_SECONDS", 1.0)
    server = ThreadingHTTPServer(("127.0.0.1", 0), _DripHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        started = time.monotonic()
        with pytest.raises(IssuerUnavailable, match="too slow"):
            identity.fetch_json(f"http://127.0.0.1:{server.server_address[1]}/slow")
        assert time.monotonic() - started < 3  # each byte arrives within the read timeout; the deadline ends it
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


class _RawDrip:
    """A raw loopback server that reads the request and then sends `head` at once and `drip` one byte at a time, so
    the status line or a header never ends within the deadline. `closed` is set when the client closes the
    connection."""

    def __init__(self, head: bytes, drip: bytes) -> None:
        self.head, self.drip = head, drip
        self.closed, self.stop = threading.Event(), threading.Event()
        self.listener = socket.create_server(("127.0.0.1", 0))
        self.url = f"http://127.0.0.1:{self.listener.getsockname()[1]}/.well-known/openid-configuration"
        self.thread = threading.Thread(target=self._serve, daemon=True)
        self.thread.start()

    def _serve(self) -> None:
        self.listener.settimeout(10)
        try:
            conn, _ = self.listener.accept()
        except OSError:
            return
        with conn:
            conn.settimeout(0.2)
            try:
                request = b""
                while b"\r\n\r\n" not in request:
                    request += conn.recv(4096)
                conn.sendall(self.head)
                for byte in self.drip:
                    if self.stop.is_set():
                        return
                    conn.sendall(bytes([byte]))
                    try:
                        if conn.recv(1) == b"":  # the client closed the connection
                            break
                    except TimeoutError:
                        continue
            except OSError:
                pass
            self.closed.set()

    def close(self) -> None:
        self.stop.set()
        self.listener.close()
        self.thread.join(timeout=5)


@pytest.mark.parametrize(
    ("head", "drip"),
    [
        (b"", b"HTTP/1.1 200 OK" + b" " * 200),  # the status line never ends
        (b"HTTP/1.1 200 OK\r\n", b"X-Slow: " + b"a" * 200),  # nor does a header
    ],
    ids=["status-line", "header"],
)
def test_fetch_json_deadline_covers_the_status_line_and_the_headers(monkeypatch, head, drip):
    monkeypatch.setattr(identity, "FETCH_DEADLINE_SECONDS", 1.0)
    server = _RawDrip(head, drip)
    try:
        started = time.monotonic()
        with pytest.raises(IssuerUnavailable, match="too slow"):
            identity.fetch_json(server.url)
        assert time.monotonic() - started < 2  # a byte every 0.2 s keeps each read under its timeout
        assert server.closed.wait(timeout=5)  # the connection is closed, and the helper with it
    finally:
        server.close()
