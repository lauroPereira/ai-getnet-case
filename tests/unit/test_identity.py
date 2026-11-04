"""v0.7.0 identity (task 63, ADR 0017, spec version 2): role scopes, demo accounts as PBKDF2 hashes, RS256 issuer and
the single verifier (signature, kid, typ, iss, aud, time claims, revocation, external JWKS), rate limit, and scope and
merchant checks with one audit row per tool call. Keys are generated in the tests; no network, no model."""

from __future__ import annotations

import json
import sqlite3
import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from pydantic import SecretStr

from merchant_assistant.api.identity import (
    ROLE_SCOPES,
    CredentialConfigError,
    Identity,
    InvalidToken,
    Principal,
    check_configuration,
    configured_accounts,
    hash_secret,
    hit_rate_limit,
    load_signing_key,
    verify_secret,
)
from merchant_assistant.config import PROJECT_ROOT, Settings
from merchant_assistant.data.clock import FixedClock
from merchant_assistant.data.db import connect
from merchant_assistant.data.seed import seed
from merchant_assistant.testing import TEST_TICKETING_SECRET, TEST_USER_PASSWORDS, passwords_setting
from merchant_assistant.tools.base import CustomerContext, ToolEnv
from merchant_assistant.tools.registry import TOOLS, execute

CLOCK = FixedClock("2026-10-26T10:00:00")


@pytest.fixture
def identity(settings) -> Identity:
    return Identity(settings)


@pytest.fixture
def db(settings) -> sqlite3.Connection:
    return connect(settings.db_path)


def test_role_scopes_follow_the_contract_table():
    assert set(ROLE_SCOPES["merchant"]) == {"support:read", "handoff:create", "conversation:read"}
    assert ROLE_SCOPES["demo"] == ROLE_SCOPES["merchant"]
    assert set(ROLE_SCOPES["operator"]) == {"handoff:operate", "support:read"}
    assert ROLE_SCOPES["service"] == ("handoff:integrate",)
    assert set(ROLE_SCOPES["admin"]) == {
        "kb:admin",
        "profiles:admin",
        "support:read",
        "handoff:create",
        "conversation:read",
    }
    assert "handoff:operate" not in ROLE_SCOPES["merchant"]


def test_principal_ids_and_audiences():
    assert Principal.merchant("cliente1988") == Principal(
        "merchant:cliente1988", "merchant", "cliente1988", ROLE_SCOPES["merchant"]
    )
    assert Principal.operator("op_ana").audience == ["merchant-assistant", "ticketing"]
    assert Principal.of("service", "ticketing").audience == ["merchant-assistant"]


def test_every_tool_declares_its_scope():
    assert {spec.scope for spec in TOOLS.values()} == {"support:read"}


# --- accounts -----------------------------------------------------------------------------------------------------


def test_pbkdf2_hash_round_trip_and_no_plaintext():
    stored = hash_secret("s3cret-value", 1_000)
    assert stored.startswith("pbkdf2_sha256$1000$") and "s3cret-value" not in stored
    assert verify_secret("s3cret-value", stored) and not verify_secret("s3cret-valuE", stored)
    assert hash_secret("s3cret-value", 1_000) != stored  # salted
    assert not verify_secret("x", "plain-text") and not verify_secret("x", "md5$1$a$b")


def test_configured_accounts_follow_d1(settings):
    accounts = {a.account_id: a.principal for a in configured_accounts(settings)}
    assert accounts["user:cliente1988"] == Principal.merchant("cliente1988")
    assert accounts["user:op_bruno"] == Principal.operator("op_bruno")
    assert accounts["client:ticketing-demo"].principal_id == "service:ticketing"
    assert "user:demo" not in accounts and "user:admin" not in accounts  # empty password = disabled
    settings.api_admin_password = SecretStr("admin-password-for-test")
    admin = {a.account_id: a.principal for a in configured_accounts(settings)}["user:admin"]
    assert (admin.principal_id, admin.role) == ("admin:default", "admin")


@pytest.mark.parametrize("value", ["intruder:some-password", "cliente1988", "cliente1988:", "op_ana:a,op_ana:b"])
def test_invalid_credential_configuration_stops_the_startup(settings, value):
    from merchant_assistant.api.app import create_app

    settings.demo_user_passwords = SecretStr(value)
    with pytest.raises(CredentialConfigError):
        configured_accounts(settings)
    with pytest.raises(CredentialConfigError):
        create_app(settings=settings)


def _example_value(name: str) -> str:
    for line in (PROJECT_ROOT / ".env.example").read_text(encoding="utf-8").splitlines():
        if line.startswith(f"{name}="):
            return line.split("=", 1)[1]
    raise AssertionError(f"{name} missing from .env.example")


def test_env_example_credentials_are_fictitious_valid_and_match_compose():
    passwords, secret = _example_value("DEMO_USER_PASSWORDS"), _example_value("TICKETING_CLIENT_SECRET")
    settings = Settings(
        _env_file=None, demo_user_passwords=SecretStr(passwords), ticketing_client_secret=SecretStr(secret)
    )
    accounts = configured_accounts(settings)
    assert {a.account_id for a in accounts} == {
        "user:cliente1988",
        "user:cliente_demo_002",
        "user:op_ana",
        "user:op_bruno",
        "client:ticketing-demo",
    }
    assert all(a.secret.endswith("-fictitious") for a in accounts)
    assert _example_value("API_DEMO_PASSWORD") == "" and _example_value("API_ADMIN_PASSWORD") == ""
    assert _example_value("JWT_PRIVATE_KEY_PATH") == ""
    warnings = check_configuration(settings)
    assert len(warnings) == 1 and "example credentials" in warnings[0] and "fictitious" not in warnings[0]
    compose = (PROJECT_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert f"${{DEMO_USER_PASSWORDS:-{passwords}}}" in compose
    assert f"${{TICKETING_CLIENT_SECRET:-{secret}}}" in compose
    assert "${JWT_ISSUER:-http://api:8000}" in compose


def test_no_warning_without_example_values(settings):
    assert check_configuration(settings) == []


def test_accounts_are_stored_as_hashes_and_rehashed_only_when_changed(settings, identity, db):
    assert identity.authenticate(db, "user:cliente1988", TEST_USER_PASSWORDS["cliente1988"]) == Principal.merchant(
        "cliente1988"
    )
    rows = {r["account_id"]: r["secret_hash"] for r in db.execute("SELECT * FROM auth_accounts")}
    assert len(rows) == 5
    dump = "\n".join(str(tuple(r)) for r in db.execute("SELECT * FROM auth_accounts"))
    assert not any(password in dump for password in [*TEST_USER_PASSWORDS.values(), TEST_TICKETING_SECRET])
    Identity(settings).sync_accounts(db)  # a new process with the same configuration keeps the hashes
    assert {r["account_id"]: r["secret_hash"] for r in db.execute("SELECT * FROM auth_accounts")} == rows
    settings.demo_user_passwords = SecretStr(passwords_setting({"cliente1988": "a-new-password"}))
    fresh = Identity(settings)
    assert fresh.authenticate(db, "user:cliente1988", TEST_USER_PASSWORDS["cliente1988"]) is None
    assert fresh.authenticate(db, "user:cliente1988", "a-new-password") is not None
    assert fresh.authenticate(db, "user:op_ana", TEST_USER_PASSWORDS["op_ana"]) is None  # no longer configured
    assert fresh.authenticate(db, "user:nobody", "x") is None


# --- tokens -------------------------------------------------------------------------------------------------------


def claims_of(identity, token):
    return identity.decode(token)


def test_issued_token_follows_the_rfc9068_profile(identity):
    response = identity.issue(Principal.merchant("cliente_demo_002"), "merchant-assistant-web")
    assert response["token_type"] == "Bearer" and response["expires_in"] == 3600
    assert response["scope"] == "support:read handoff:create conversation:read"
    header = jwt.get_unverified_header(response["access_token"])
    assert (header["alg"], header["typ"], header["kid"]) == ("RS256", "at+jwt", identity.key.kid)
    claims = claims_of(identity, response["access_token"])
    assert claims["iss"] == "http://127.0.0.1:8000" and claims["aud"] == ["merchant-assistant"]
    assert claims["sub"] == "merchant:cliente_demo_002" and claims["customer_id"] == "cliente_demo_002"
    assert claims["role"] == "merchant" and claims["client_id"] == "merchant-assistant-web"
    assert claims["exp"] - claims["iat"] == 3600 and claims["nbf"] == claims["iat"] and claims["jti"]
    operator = claims_of(identity, identity.issue(Principal.operator("op_ana"), "web")["access_token"])
    assert operator["aud"] == ["merchant-assistant", "ticketing"] and "customer_id" not in operator
    service = identity.issue(Principal.of("service", "ticketing"), "ticketing-demo")
    assert service["expires_in"] == 600 and service["scope"] == "handoff:integrate"
    assert "customer_id" not in claims_of(identity, service["access_token"])


def test_verifier_returns_the_principal(identity, db):
    token = identity.issue(Principal.merchant("cliente1988"), "web")["access_token"]
    principal, claims = identity.verify(token, db)
    assert principal == Principal.merchant("cliente1988") and claims["sub"] == "merchant:cliente1988"
    demo = identity.issue(Principal.of("demo", "default", "cliente1988"), "web")["access_token"]
    assert identity.verify(demo, db)[0].customer_id == "cliente1988"  # demo merchant from the server configuration


def _forge(key, claims: dict, *, kid: str, typ: str = "at+jwt") -> str:
    return jwt.encode(claims, key, algorithm="RS256", headers={"typ": typ, "kid": kid})


def _claims(identity, **changes) -> dict:
    now = int(time.time())
    base = {
        "iss": identity.issuer,
        "sub": "merchant:cliente1988",
        "aud": ["merchant-assistant"],
        "exp": now + 600,
        "iat": now,
        "nbf": now,
        "jti": "jti-test",
        "client_id": "web",
        "role": "merchant",
        "scope": "support:read handoff:create conversation:read",
        "customer_id": "cliente1988",
    }
    return {k: v for k, v in (base | changes).items() if v is not None}


@pytest.mark.parametrize(
    "changes",
    [
        {"iss": "http://evil.example"},
        {"aud": ["ticketing"]},
        {"exp": -31},  # relative to now: beyond the 30 s tolerance
        {"nbf": 120},  # relative to now: not valid yet
        {"jti": None},
        {"customer_id": None},  # merchant without its merchant
        {"customer_id": "cliente_demo_002"},  # sub and customer_id disagree
        {"role": "superuser"},
    ],
)
def test_verifier_refuses_bad_claims(identity, db, changes):
    now = int(time.time())  # time claims are given relative to the moment the test runs
    changes = {k: now + v if k in ("exp", "nbf") else v for k, v in changes.items()}
    token = _forge(identity.key.private_key, _claims(identity, **changes), kid=identity.key.kid)
    with pytest.raises(InvalidToken):
        identity.verify(token, db)


def test_verifier_accepts_the_clock_tolerance(identity, db):
    token = _forge(identity.key.private_key, _claims(identity, exp=int(time.time()) - 10), kid=identity.key.kid)
    assert identity.verify(token, db)[0].principal_id == "merchant:cliente1988"


def test_verifier_refuses_tampering_other_keys_and_types(identity, db):
    token = identity.issue(Principal.merchant("cliente1988"), "web")["access_token"]
    header, payload, signature = token.split(".")
    tampered_payload = jwt.utils.base64url_encode(
        json.dumps(_claims(identity, sub="merchant:cliente_demo_002", customer_id="cliente_demo_002")).encode()
    ).decode()
    other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    for bad in (
        f"{header}.{tampered_payload}.{signature}",
        token[:-4] + ("AAAA" if not token.endswith("AAAA") else "BBBB"),
        _forge(other_key, _claims(identity), kid=identity.key.kid),  # same kid, another key
        _forge(other_key, _claims(identity), kid="unknown-kid"),
        _forge(identity.key.private_key, _claims(identity), kid=identity.key.kid, typ="JWT"),
        jwt.encode(
            _claims(identity),
            "hmac-secret-with-thirty-two-bytes",
            algorithm="HS256",
            headers={"typ": "at+jwt", "kid": identity.key.kid},
        ),
        "not-a-jwt",
        "",
    ):
        with pytest.raises(InvalidToken):
            identity.verify(bad, db)


def test_role_table_bounds_the_scopes_of_any_issuer(identity, db):
    claims = _claims(identity, scope="support:read handoff:operate kb:admin")
    principal, _ = identity.verify(_forge(identity.key.private_key, claims, kid=identity.key.kid), db)
    assert principal.scopes == ("support:read",)


def test_revoked_token_is_refused_until_it_expires(identity, db):
    token = identity.issue(Principal.merchant("cliente1988"), "web")["access_token"]
    _, claims = identity.verify(token, db)
    identity.revoke(db, claims)
    with pytest.raises(InvalidToken):
        identity.verify(token, db)
    assert identity.verify(identity.issue(Principal.merchant("cliente1988"), "web")["access_token"], db)


def test_signing_key_is_created_once_and_kid_is_its_thumbprint(tmp_path):
    path = tmp_path / "jwt" / "signing_key.pem"
    first = load_signing_key(path)
    assert path.exists() and load_signing_key(path).kid == first.kid
    assert first.public_jwk["kid"] == first.kid and "d" not in first.public_jwk  # public part only
    assert jwt.PyJWK(first.public_jwk).key_id == first.kid


def test_external_jwks_replaces_the_local_key(settings, db, monkeypatch):
    external_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(external_key.public_key())) | {"kid": "ext-1", "use": "sig"}
    monkeypatch.setattr(jwt.PyJWKClient, "fetch_data", lambda self: {"keys": [jwk]})
    settings.jwt_jwks_url = "https://idp.example/.well-known/jwks.json"
    settings.jwt_issuer = "https://idp.example"
    external = Identity(settings)
    claims = _claims(external, sub="operator:op_ana", role="operator", customer_id=None, scope="handoff:operate")
    principal, _ = external.verify(_forge(external_key, claims, kid="ext-1"), db)
    assert principal == Principal("operator:op_ana", "operator", None, ("handoff:operate",))
    local = Identity(settings.model_copy(update={"jwt_jwks_url": None}))
    with pytest.raises(InvalidToken):  # the local key is not in the external JWKS
        external.verify(local.issue(Principal.merchant("cliente1988"), "web")["access_token"], db)


# --- rate limit and tool calls ------------------------------------------------------------------------------------


def test_rate_limit_fixed_window_with_fixed_clock(tmp_path):
    conn = connect(tmp_path / "db.sqlite3")
    now = 1_800_000_010.0  # 10 s into a 60 s window
    assert [hit_rate_limit(conn, "merchant:a", 3, now) for _ in range(3)] == [None, None, None]
    assert hit_rate_limit(conn, "merchant:a", 3, now) == 50
    assert hit_rate_limit(conn, "merchant:b", 3, now) is None  # per principal
    assert hit_rate_limit(conn, "merchant:a", 3, now + 50) is None  # next window
    windows = conn.execute("SELECT COUNT(*) FROM rate_limit_hits WHERE principal_id='merchant:a'").fetchone()[0]
    assert windows == 1  # past windows are cleaned


@pytest.fixture
def conn(tmp_path):
    c = connect(tmp_path / "db.sqlite3")
    seed(c, CLOCK)
    return c


def audit_rows(conn):
    return [dict(r) for r in conn.execute("SELECT principal_id, customer_id, tool, scope, outcome FROM audit_events")]


def test_scope_is_checked_before_the_tool_runs_and_the_refusal_is_audited(conn):
    operator_without_support = Principal("operator:op_x", "operator", None, ("handoff:operate",))
    context = CustomerContext.for_principal(
        operator_without_support, "cliente1988", True, authorized_customer_id="cliente1988"
    )
    out = execute("get_payout_status", {"receivable_ids": ["rcv_002_0001"]}, ToolEnv(conn, CLOCK, context))
    assert not out.ok and out.error["code"] == "FORBIDDEN_SCOPE" and out.data is None
    assert audit_rows(conn) == [
        {
            "principal_id": "operator:op_x",
            "customer_id": "cliente1988",
            "tool": "get_payout_status",
            "scope": "support:read",
            "outcome": "forbidden_scope",
        }
    ]


def test_scope_is_checked_before_the_agent_allowlist(conn):
    no_scope = CustomerContext.for_principal(Principal("demo:x", "demo", "cliente1988", ()), "cliente1988", True)
    out = execute("get_complaint_history", {}, ToolEnv(conn, CLOCK, no_scope), agent="customer_support")
    assert out.error["code"] == "FORBIDDEN_SCOPE"


def test_operator_acts_only_for_the_merchant_it_is_authorized_for(conn):
    operator = Principal.of("operator", "op_ana", None)
    unbound = CustomerContext.for_principal(operator, "cliente1988", True)  # no case: no merchant
    assert execute("get_device_status", {}, ToolEnv(conn, CLOCK, unbound)).error["code"] == "FORBIDDEN_CUSTOMER"
    case_bound = CustomerContext.for_principal(operator, "cliente1988", True, authorized_customer_id="cliente1988")
    assert execute("get_device_status", {}, ToolEnv(conn, CLOCK, case_bound)).ok
    assert [r["outcome"] for r in audit_rows(conn)] == ["forbidden_customer", "ok"]
    assert {r["principal_id"] for r in audit_rows(conn)} == {"operator:op_ana"}


def test_merchant_cannot_act_for_another_merchant(conn):
    other = CustomerContext.for_principal(Principal.merchant("cliente_demo_002"), "cliente1988", True)
    out = execute("get_contract_snapshot", {}, ToolEnv(conn, CLOCK, other))
    assert out.error["code"] == "FORBIDDEN_CUSTOMER"


def test_context_without_principal_fails_closed(conn):
    out = execute("get_contract_snapshot", {}, ToolEnv(conn, CLOCK, CustomerContext("cliente1988", True)))
    assert out.error["code"] == "FORBIDDEN_SCOPE"
    assert audit_rows(conn)[0]["principal_id"] is None


def test_every_call_leaves_one_audit_row_whatever_the_result(conn):
    env = ToolEnv(conn, CLOCK, CustomerContext.for_principal(Principal.merchant("cliente1988"), "cliente1988", True))
    calls = [
        ("get_contract_snapshot", {}),  # ok
        ("get_payout_status", {"receivable_ids": ["rcv_002_0001"]}),  # another merchant's resource
        ("find_authorization_events", {"limit": 500}),  # invalid argument
        ("drop_tables", {}),  # unknown tool: no scope
    ]
    for name, args in calls:
        execute(name, args, env)
    rows = conn.execute("SELECT tool, scope, outcome, resource_id, principal_id FROM audit_events ORDER BY id")
    assert [tuple(r) for r in rows] == [
        ("get_contract_snapshot", "support:read", "ok", None, "merchant:cliente1988"),
        ("get_payout_status", "support:read", "forbidden", "rcv_002_0001", "merchant:cliente1988"),
        ("find_authorization_events", "support:read", "invalid_argument", None, "merchant:cliente1988"),
        ("drop_tables", None, "invalid_argument", None, "merchant:cliente1988"),
    ]
