"""v0.13.0 task 97 (spec D1, CA-68, issuer part): authorization code with PKCE S256 and the issuer's login page,
rotating refresh tokens with the family revoked when a spent token appears again, revocation of refresh and access
tokens, the `password` grant kept and marked as demonstration, and `api_principals.issuer`. Scripted model, keys
generated in the tests, no network, no cost."""

from __future__ import annotations

import base64
import hashlib
import logging
import secrets
import sqlite3
from urllib.parse import parse_qs, urlsplit

import jwt
import pytest
from pydantic import SecretStr

from merchant_assistant.api import identity
from merchant_assistant.api.app import create_app
from merchant_assistant.api.identity import CredentialConfigError, registered_redirects
from merchant_assistant.testing import TEST_USER_PASSWORDS, passwords_setting

WEB = "merchant-assistant-web"
URI = "http://localhost:8501/"
OTHER_URI = "http://127.0.0.1:8501/"  # also registered for the same client by default
MERCHANT = "cliente1988"
MERCHANT_SCOPES = {"support:read", "handoff:create", "conversation:read", "support:write"}


def pkce() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    return verifier, challenge


def authorize_params(challenge: str, **override) -> dict[str, str]:
    return {
        "response_type": "code",
        "client_id": WEB,
        "redirect_uri": URI,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "state": "st-abc123",
    } | override


def query(response) -> dict[str, str]:
    return {k: v[0] for k, v in parse_qs(urlsplit(response.headers["location"]).query).items()}


def login(client, username=MERCHANT, password=None, *, redirect_uri=URI, challenge=None):
    """GET the page, POST the form; returns the redirect (303) response and the PKCE verifier."""
    verifier, own_challenge = pkce()
    params = authorize_params(challenge or own_challenge, redirect_uri=redirect_uri)
    page = client.get("/v1/auth/authorize", params=params, follow_redirects=False)
    assert page.status_code == 200, page.text
    form = params | {"username": username, "password": password or TEST_USER_PASSWORDS[username]}
    return client.post("/v1/auth/authorize", data=form, follow_redirects=False), verifier


def code_for(client, **kwargs) -> tuple[str, str]:
    response, verifier = login(client, **kwargs)
    assert response.status_code == 303, response.text
    return query(response)["code"], verifier


def exchange(client, code, verifier, *, redirect_uri=URI, client_id=WEB):
    return client.post(
        "/v1/auth/token",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "code_verifier": verifier,
            "redirect_uri": redirect_uri,
            "client_id": client_id,
        },
    )


def refresh(client, token, client_id=WEB):
    return client.post(
        "/v1/auth/token", data={"grant_type": "refresh_token", "refresh_token": token, "client_id": client_id}
    )


def tokens(client) -> dict:
    code, verifier = code_for(client)
    response = exchange(client, code, verifier)
    assert response.status_code == 200, response.text
    return response.json()


def bearer(body: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {body['access_token']}"}


def db(settings):
    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row
    return conn


def assert_refused(response):
    assert response.status_code == 400 and response.json() == {
        "error": "invalid_grant",
        "error_description": "The authorization code or refresh token is invalid, expired or revoked.",
    }
    assert response.headers["cache-control"] == "no-store"


# --- discovery and contract ---------------------------------------------------------------------------------------


def test_discovery_and_openapi_are_additive_and_mark_password_as_demonstration(offline):
    client, _, _ = offline()
    discovery = client.get("/.well-known/openid-configuration").json()
    assert discovery["authorization_endpoint"] == "http://127.0.0.1:8000/v1/auth/authorize"
    assert discovery["code_challenge_methods_supported"] == ["S256"]
    assert discovery["response_types_supported"] == ["code"]
    assert {"authorization_code", "refresh_token", "password", "client_credentials"} == set(
        discovery["grant_types_supported"]
    )
    schema = client.get("/openapi.json").json()
    authorize = schema["paths"]["/v1/auth/authorize"]["get"]
    assert "security" not in authorize and "text/html" in authorize["responses"]["200"]["content"]
    assert {p["name"] for p in authorize["parameters"]} == {
        "response_type",
        "client_id",
        "redirect_uri",
        "code_challenge",
        "code_challenge_method",
        "state",
    }
    form = schema["paths"]["/v1/auth/token"]["post"]["requestBody"]["content"]["application/x-www-form-urlencoded"]
    grant = form["schema"]["properties"]["grant_type"]
    assert grant["enum"] == ["authorization_code", "refresh_token", "password", "client_credentials"]
    assert "demonstration only" in grant["description"]
    assert "demonstration only" in schema["paths"]["/v1/auth/token"]["post"]["description"]
    assert {"code", "code_verifier", "redirect_uri", "refresh_token", "username", "password"} <= set(
        form["schema"]["properties"]
    )
    revoke = schema["paths"]["/v1/auth/revoke"]["post"]
    assert revoke["security"] == [{"SessionBearer": []}] and revoke["requestBody"]["required"] is False


def test_password_grant_still_works_without_a_refresh_token(offline):
    client, _, _ = offline()
    response = client.post(
        "/v1/auth/token",
        data={"grant_type": "password", "username": MERCHANT, "password": TEST_USER_PASSWORDS[MERCHANT]},
    )
    assert response.status_code == 200 and set(response.json()) == {"access_token", "token_type", "expires_in", "scope"}


# --- authorization endpoint and login page ------------------------------------------------------------------------


def test_login_by_redirection_issues_code_then_tokens_with_the_role_scopes(offline, settings):
    client, _, _ = offline()
    verifier, challenge = pkce()
    params = authorize_params(challenge)
    page = client.get("/v1/auth/authorize", params=params, follow_redirects=False)
    assert page.status_code == 200 and page.headers["content-type"].startswith("text/html")
    assert (
        page.headers["x-frame-options"] == "DENY"
        and "frame-ancestors 'none'" in page.headers["content-security-policy"]
    )
    assert page.headers["cache-control"] == "no-store" and "<script" not in page.text
    assert f'value="{challenge}"' in page.text and 'action="/v1/auth/authorize"' in page.text

    form = params | {"username": MERCHANT, "password": TEST_USER_PASSWORDS[MERCHANT]}
    back = client.post("/v1/auth/authorize", data=form, follow_redirects=False)
    assert back.status_code == 303 and back.headers["location"].startswith(URI + "?")
    assert back.headers["cache-control"] == "no-store"
    returned = query(back)
    assert set(returned) == {"code", "state", "iss"}
    assert returned["state"] == "st-abc123" and returned["iss"] == "http://127.0.0.1:8000"
    assert len(returned["code"]) >= 43

    issued = exchange(client, returned["code"], verifier)
    assert issued.status_code == 200 and issued.headers["cache-control"] == "no-store"
    body = issued.json()
    assert set(body) == {"access_token", "token_type", "expires_in", "scope", "refresh_token"}
    assert body["token_type"] == "Bearer" and body["expires_in"] == 3600
    assert set(body["scope"].split()) == MERCHANT_SCOPES
    claims = jwt.decode(body["access_token"], options={"verify_signature": False})
    assert (claims["sub"], claims["customer_id"], claims["client_id"]) == (f"merchant:{MERCHANT}", MERCHANT, WEB)
    assert client.get("/v1/profiles", headers=bearer(body)).status_code == 200

    conn = db(settings)
    try:  # only digests are stored; the issuer of the principal is recorded
        code_row = conn.execute("SELECT * FROM auth_codes").fetchone()
        refresh_row = conn.execute("SELECT * FROM refresh_tokens").fetchone()
        assert code_row["code_hash"] == hashlib.sha256(returned["code"].encode()).hexdigest()
        assert refresh_row["token_hash"] == hashlib.sha256(body["refresh_token"].encode()).hexdigest()
        dump = "\n".join(conn.iterdump())
        assert returned["code"] not in dump and body["refresh_token"] not in dump and verifier not in dump
        principal = conn.execute("SELECT issuer FROM api_principals WHERE principal_id=?", (f"merchant:{MERCHANT}",))
        assert principal.fetchone()["issuer"] == "http://127.0.0.1:8000"
    finally:
        conn.close()


def test_operator_logs_in_by_redirection_with_its_own_scopes(offline):
    client, _, _ = offline()
    code, verifier = code_for(client, username="op_ana")
    body = exchange(client, code, verifier).json()
    assert body["scope"] == "handoff:operate support:read"
    claims = jwt.decode(body["access_token"], options={"verify_signature": False})
    assert claims["sub"] == "operator:op_ana" and claims["aud"] == ["merchant-assistant", "ticketing"]


@pytest.mark.parametrize(
    "override",
    [
        {"redirect_uri": "http://localhost:8501/evil"},
        {"redirect_uri": "http://localhost:8501"},  # no normalisation: the trailing slash matters
        {"redirect_uri": "http://localhost:8502/"},
        {"redirect_uri": "https://attacker.example/"},
        {"redirect_uri": ""},
        {"client_id": "rogue-app"},
        {"client_id": "merchant-assistant-cli"},  # a public client without a registered URI
        {"client_id": ""},
    ],
)
def test_unregistered_client_or_redirect_uri_gets_an_error_page_and_no_redirect(offline, override):
    client, _, _ = offline()
    params = authorize_params(pkce()[1], **override)
    page = client.get("/v1/auth/authorize", params=params, follow_redirects=False)
    assert page.status_code == 400 and "location" not in page.headers
    assert "não registrado" in page.text and "<form" not in page.text
    form = params | {"username": MERCHANT, "password": TEST_USER_PASSWORDS[MERCHANT]}
    posted = client.post("/v1/auth/authorize", data=form, follow_redirects=False)
    assert posted.status_code == 400 and "location" not in posted.headers


@pytest.mark.parametrize(
    ("override", "error"),
    [
        ({"code_challenge": ""}, "invalid_request"),  # PKCE is required
        ({"code_challenge_method": "plain"}, "invalid_request"),
        ({"code_challenge_method": ""}, "invalid_request"),
        ({"code_challenge": "short"}, "invalid_request"),
        ({"code_challenge": "a" * 42 + "="}, "invalid_request"),
        ({"response_type": "token"}, "unsupported_response_type"),
        ({"response_type": ""}, "unsupported_response_type"),
    ],
)
def test_authorization_errors_go_back_to_the_client_with_state(offline, override, error):
    client, _, _ = offline()
    params = authorize_params(pkce()[1], **override)
    response = client.get("/v1/auth/authorize", params=params, follow_redirects=False)
    assert response.status_code == 302 and response.headers["location"].startswith(URI + "?")
    returned = query(response)
    assert returned["error"] == error and returned["state"] == "st-abc123" and "code" not in returned
    assert returned["iss"] == "http://127.0.0.1:8000"
    posted = client.post(
        "/v1/auth/authorize",
        data=params | {"username": MERCHANT, "password": TEST_USER_PASSWORDS[MERCHANT]},
        follow_redirects=False,
    )
    assert posted.status_code == 303 and query(posted)["error"] == error and "code" not in query(posted)


def test_state_is_required(offline):
    client, _, _ = offline()
    response = client.get("/v1/auth/authorize", params=authorize_params(pkce()[1], state=""), follow_redirects=False)
    assert response.status_code == 302 and query(response)["error"] == "invalid_request"
    assert "state" not in query(response)


def test_reflected_values_are_escaped_on_the_page(offline):
    client, _, _ = offline()
    hostile = 'x"><script>alert(1)</script>'
    page = client.get("/v1/auth/authorize", params=authorize_params(pkce()[1], state=hostile))
    assert page.status_code == 200 and "<script>" not in page.text
    assert "&quot;&gt;&lt;script&gt;" in page.text


def test_login_page_forms_post_only_to_the_page_and_the_registered_redirect_origin(offline, settings):
    settings.oauth_redirect_uris = f"{WEB}={URI},{WEB}=https://web.example:8443/callback?tenant=demo"
    client, _, _ = offline()
    page = client.get("/v1/auth/authorize", params=authorize_params(pkce()[1]), follow_redirects=False)
    assert page.headers["content-security-policy"].endswith("; form-action 'self' http://localhost:8501")
    remote = authorize_params(pkce()[1], redirect_uri="https://web.example:8443/callback?tenant=demo")
    page = client.get("/v1/auth/authorize", params=remote, follow_redirects=False)
    assert page.headers["content-security-policy"].endswith("; form-action 'self' https://web.example:8443")
    wrong = client.post(
        "/v1/auth/authorize", data=authorize_params(pkce()[1]) | {"username": MERCHANT, "password": "x"}
    )
    assert "form-action 'self' http://localhost:8501" in wrong.headers["content-security-policy"]
    error = client.get("/v1/auth/authorize", params=authorize_params(pkce()[1], client_id="rogue"))
    assert error.status_code == 400 and error.headers["content-security-policy"].endswith("; form-action 'none'")


def test_wrong_password_shows_the_page_again_without_a_code_and_attempts_are_limited(offline, settings, monkeypatch):
    monkeypatch.setattr(identity, "utc_seconds", lambda: 1_800_000_010.0)  # one fixed 60 s window
    settings.auth_attempts_per_minute = 2
    client, _, _ = offline()
    for password in ("wrong-1", "wrong-2"):
        response, _ = login(client, password=password)
        assert response.status_code == 400 and "location" not in response.headers
        assert "Usuário ou senha inválidos." in response.text and password not in response.text
    unknown, _ = login(client, username="op_bruno", password="nope")
    assert unknown.status_code == 400 and "Usuário ou senha inválidos." in unknown.text
    blocked, _ = login(client)  # even the right password: counted before any hashing, shared with the token route
    assert blocked.status_code == 429 and 1 <= int(blocked.headers["retry-after"]) <= 60
    token_route = client.post(
        "/v1/auth/token",
        data={"grant_type": "password", "username": MERCHANT, "password": TEST_USER_PASSWORDS[MERCHANT]},
    )
    assert token_route.status_code == 429
    conn = db(settings)
    try:
        assert conn.execute("SELECT COUNT(*) FROM auth_codes").fetchone()[0] == 0
    finally:
        conn.close()


def test_service_client_cannot_log_in_on_the_page(offline):
    client, _, _ = offline()
    response, _ = login(client, username="ticketing-demo", password="test-ticketing-client-secret")
    assert response.status_code == 400 and "location" not in response.headers


# --- authorization code exchange ----------------------------------------------------------------------------------


def test_wrong_code_verifier_is_refused_and_spends_the_code(offline):
    client, _, _ = offline()
    code, verifier = code_for(client)
    assert_refused(exchange(client, code, pkce()[0]))  # a valid verifier of another login
    assert_refused(exchange(client, code, verifier))  # the code was spent by the first attempt
    code, verifier = code_for(client)
    assert_refused(exchange(client, code, "short"))
    code, _ = code_for(client)
    assert_refused(exchange(client, code, pkce()[1]))  # the challenge itself is not the verifier


def test_redirect_uri_must_be_the_one_of_the_code(offline):
    client, _, _ = offline()
    assert OTHER_URI in registered_redirects(client.app.state.settings)[WEB]
    code, verifier = code_for(client)
    assert_refused(exchange(client, code, verifier, redirect_uri=OTHER_URI))
    code, verifier = code_for(client, redirect_uri=OTHER_URI)
    assert exchange(client, code, verifier, redirect_uri=OTHER_URI).status_code == 200


def test_code_is_bound_to_its_client_and_unknown_clients_are_refused(offline):
    client, _, _ = offline()
    code, verifier = code_for(client)
    unknown = exchange(client, code, verifier, client_id="rogue-app")
    assert unknown.status_code == 401 and unknown.json()["error"] == "invalid_client"
    assert exchange(client, code, verifier).status_code == 200  # the refused client did not touch the code
    for missing in ("code", "code_verifier", "redirect_uri", "client_id"):
        form = {"grant_type": "authorization_code", "code": "c", "code_verifier": "v", "redirect_uri": URI}
        form |= {"client_id": WEB}
        form.pop(missing)
        response = client.post("/v1/auth/token", data=form)
        assert response.status_code == 400 and response.json()["error"] == "invalid_request"
    assert_refused(exchange(client, "not-a-code", pkce()[0]))


def test_code_of_one_registered_client_is_refused_for_another_registered_client(offline, settings):
    settings.oauth_redirect_uris = f"{WEB}={URI},merchant-assistant-cli={URI}"
    client, _, _ = offline()
    code, verifier = code_for(client)
    assert_refused(exchange(client, code, verifier, client_id="merchant-assistant-cli"))
    assert_refused(exchange(client, code, verifier))  # the refused presentation spent the code


def test_reused_code_is_refused_and_revokes_the_tokens_it_issued(offline):
    client, _, _ = offline()
    code, verifier = code_for(client)
    first = exchange(client, code, verifier)
    assert first.status_code == 200
    assert_refused(exchange(client, code, verifier))
    assert client.get("/v1/profiles", headers=bearer(first.json())).status_code == 401  # access token revoked
    assert_refused(refresh(client, first.json()["refresh_token"]))  # and the refresh token


def test_code_expires_after_a_minute(offline, monkeypatch):
    client, _, _ = offline()
    start = 1_800_000_000.0
    monkeypatch.setattr(identity, "utc_seconds", lambda: start)
    code, verifier = code_for(client)
    monkeypatch.setattr(identity, "utc_seconds", lambda: start + 61)
    assert_refused(exchange(client, code, verifier))
    monkeypatch.setattr(identity, "utc_seconds", lambda: start)
    code, verifier = code_for(client)
    monkeypatch.setattr(identity, "utc_seconds", lambda: start + 59)
    assert exchange(client, code, verifier).status_code == 200


# --- refresh tokens -----------------------------------------------------------------------------------------------


def test_refresh_rotates_and_keeps_the_scopes(offline):
    client, _, _ = offline()
    first = tokens(client)
    second = refresh(client, first["refresh_token"])
    assert second.status_code == 200 and second.headers["cache-control"] == "no-store"
    body = second.json()
    assert set(body) == {"access_token", "token_type", "expires_in", "scope", "refresh_token"}
    assert body["refresh_token"] != first["refresh_token"] and body["access_token"] != first["access_token"]
    assert set(body["scope"].split()) == MERCHANT_SCOPES == set(first["scope"].split())
    old, new = (
        jwt.decode(t, options={"verify_signature": False}) for t in (first["access_token"], body["access_token"])
    )
    assert {k: old[k] for k in ("sub", "customer_id", "client_id", "role", "scope")} == {
        k: new[k] for k in ("sub", "customer_id", "client_id", "role", "scope")
    }
    assert client.get("/v1/profiles", headers=bearer(body)).status_code == 200
    third = refresh(client, body["refresh_token"])
    assert third.status_code == 200 and third.json()["refresh_token"] not in (
        first["refresh_token"],
        body["refresh_token"],
    )


def test_refresh_never_grants_scopes_beyond_the_role(offline, settings):
    client, _, _ = offline()
    first = tokens(client)
    with db(settings) as conn:  # a stored grant wider than the role (tampered or from an older role table)
        conn.execute(
            "UPDATE refresh_tokens SET scope=? WHERE token_hash=?",
            (first["scope"] + " kb:admin handoff:operate", identity.secret_digest(first["refresh_token"])),
        )
    conn.close()
    second = refresh(client, first["refresh_token"])
    assert second.status_code == 200 and set(second.json()["scope"].split()) == MERCHANT_SCOPES
    claims = jwt.decode(second.json()["access_token"], options={"verify_signature": False})
    assert set(claims["scope"].split()) == MERCHANT_SCOPES


def test_reused_refresh_token_revokes_the_whole_family(offline, settings):
    client, _, _ = offline()
    first = tokens(client)
    second = refresh(client, first["refresh_token"]).json()
    third = refresh(client, second["refresh_token"]).json()
    other_login = tokens(client)  # another family of the same merchant
    assert_refused(refresh(client, first["refresh_token"]))  # a spent token appears again
    assert_refused(refresh(client, third["refresh_token"]))  # the latest one of the family stops working
    for body in (first, second, third):  # and every access token issued in the family
        assert client.get("/v1/profiles", headers=bearer(body)).status_code == 401
    assert client.get("/v1/profiles", headers=bearer(other_login)).status_code == 200
    assert refresh(client, other_login["refresh_token"]).status_code == 200
    conn = db(settings)
    try:
        states = conn.execute(
            "SELECT family_id, COUNT(*) AS n, SUM(revoked_at IS NOT NULL) AS revoked FROM refresh_tokens GROUP BY 1"
        ).fetchall()
        assert sorted((r["n"], r["revoked"]) for r in states) == [(2, 0), (3, 3)]
    finally:
        conn.close()


def test_refresh_by_another_client_revokes_the_family(offline):
    client, _, _ = offline()
    first = tokens(client)
    assert_refused(refresh(client, first["refresh_token"], client_id="merchant-assistant-cli"))
    assert_refused(refresh(client, first["refresh_token"]))
    unknown = refresh(client, first["refresh_token"], client_id="rogue-app")
    assert unknown.status_code == 401 and unknown.json()["error"] == "invalid_client"
    missing = client.post("/v1/auth/token", data={"grant_type": "refresh_token", "client_id": WEB})
    assert missing.status_code == 400 and missing.json()["error"] == "invalid_request"
    assert_refused(refresh(client, "not-a-refresh-token"))


def test_refresh_token_expires_when_idle_and_the_family_has_a_maximum_life(offline, monkeypatch):
    client, _, _ = offline()
    now = [1_800_000_000.0]
    monkeypatch.setattr(identity, "utc_seconds", lambda: now[0])
    idle = tokens(client)
    now[0] += identity.REFRESH_TTL_SECONDS + 1
    assert_refused(refresh(client, idle["refresh_token"]))

    now[0] = 1_800_000_000.0
    current = tokens(client)["refresh_token"]
    for _ in range(3):  # rotating every 7 h keeps the login alive, but never past 24 h
        now[0] += 7 * 60 * 60
        response = refresh(client, current)
        assert response.status_code == 200
        current = response.json()["refresh_token"]
    now[0] = 1_800_000_000.0 + identity.REFRESH_FAMILY_TTL_SECONDS
    assert_refused(refresh(client, current))


def test_deactivated_account_cannot_refresh_and_its_family_is_revoked(offline, settings):
    client, _, _ = offline()
    body = tokens(client)
    without = {k: v for k, v in TEST_USER_PASSWORDS.items() if k != MERCHANT}
    settings.demo_user_passwords = SecretStr(passwords_setting(without))
    assert_refused(refresh(client, body["refresh_token"]))
    settings.demo_user_passwords = SecretStr(passwords_setting(TEST_USER_PASSWORDS))
    assert_refused(refresh(client, body["refresh_token"]))  # coming back does not revive the family


# --- revocation ---------------------------------------------------------------------------------------------------


def test_revoke_route_revokes_the_access_token_and_the_refresh_family(offline):
    client, _, _ = offline()
    mine, kept = tokens(client), tokens(client)
    rotated = refresh(client, mine["refresh_token"]).json()
    response = client.post("/v1/auth/revoke", headers=bearer(rotated), data={"token": rotated["refresh_token"]})
    assert response.status_code == 200 and response.content == b""
    assert client.get("/v1/profiles", headers=bearer(rotated)).status_code == 401
    assert client.get("/v1/profiles", headers=bearer(mine)).status_code == 401  # same family
    assert_refused(refresh(client, rotated["refresh_token"]))
    assert client.get("/v1/profiles", headers=bearer(kept)).status_code == 200  # another login is untouched
    assert refresh(client, kept["refresh_token"]).status_code == 200


def test_revoke_ignores_the_refresh_token_of_another_principal(offline):
    client, _, _ = offline()
    merchant = tokens(client)
    code, verifier = code_for(client, username="op_ana")
    operator = exchange(client, code, verifier).json()
    response = client.post("/v1/auth/revoke", headers=bearer(operator), data={"token": merchant["refresh_token"]})
    assert response.status_code == 200
    assert client.get("/v1/profiles", headers=bearer(merchant)).status_code == 200
    assert refresh(client, merchant["refresh_token"]).status_code == 200
    assert client.post("/v1/auth/revoke", data={"token": merchant["refresh_token"]}).status_code == 401  # bearer


def test_revoking_only_the_access_token_keeps_the_refresh_token(offline):
    client, _, _ = offline()
    body = tokens(client)
    assert client.post("/v1/auth/revoke", headers=bearer(body)).status_code == 200
    assert client.get("/v1/profiles", headers=bearer(body)).status_code == 401
    assert refresh(client, body["refresh_token"]).status_code == 200


# --- secrets and configuration ------------------------------------------------------------------------------------


def test_no_code_refresh_token_verifier_or_password_in_the_logs(offline, caplog):
    client, _, _ = offline()
    with caplog.at_level(logging.DEBUG):
        response, verifier = login(client)
        code = query(response)["code"]
        body = exchange(client, code, verifier).json()
        rotated = refresh(client, body["refresh_token"]).json()
        assert_refused(refresh(client, body["refresh_token"]))
    logs = "\n".join(r.getMessage() for r in caplog.records)
    for secret in (code, verifier, body["refresh_token"], rotated["refresh_token"], TEST_USER_PASSWORDS[MERCHANT]):
        assert secret not in logs
    assert body["access_token"] not in logs


@pytest.mark.parametrize(
    "value",
    [
        "merchant-assistant-web=http://web.example/",  # http only on the loopback
        "merchant-assistant-web=https://web.example/#frag",
        "merchant-assistant-web=https://user:pw@web.example/",
        "merchant-assistant-web=/relative",
        "ticketing-demo=https://web.example/",  # only public clients
        "rogue=https://web.example/",
        "https://web.example/",
        "merchant-assistant-web=",
    ],
)
def test_invalid_redirect_configuration_stops_the_startup(settings, value):
    settings.oauth_redirect_uris = value
    with pytest.raises(CredentialConfigError, match="OAUTH_REDIRECT_URIS"):
        create_app(settings=settings)


def test_redirect_configuration_accepts_https_and_loopback(settings):
    settings.oauth_redirect_uris = (
        "merchant-assistant-web=https://web.example/callback?x=1, merchant-assistant-web=http://[::1]:8501/,"
        "merchant-assistant-cli=http://127.0.0.1:9999/cb"
    )
    assert registered_redirects(settings) == {
        WEB: ("https://web.example/callback?x=1", "http://[::1]:8501/"),
        "merchant-assistant-cli": ("http://127.0.0.1:9999/cb",),
    }
    settings.oauth_redirect_uris = ""
    assert registered_redirects(settings) == {}


def test_redirect_keeps_the_query_of_a_registered_uri(offline, settings):
    settings.oauth_redirect_uris = "merchant-assistant-web=https://web.example/callback?tenant=demo"
    client, _, _ = offline()
    response, verifier = login(client, redirect_uri="https://web.example/callback?tenant=demo")
    assert response.status_code == 303
    location = urlsplit(response.headers["location"])
    returned = parse_qs(location.query)
    assert location.netloc == "web.example" and returned["tenant"] == ["demo"] and "code" in returned
    issued = exchange(client, returned["code"][0], verifier, redirect_uri="https://web.example/callback?tenant=demo")
    assert issued.status_code == 200


def test_empty_registration_turns_the_redirect_login_off(offline, settings):
    settings.oauth_redirect_uris = ""
    client, _, _ = offline()
    page = client.get("/v1/auth/authorize", params=authorize_params(pkce()[1]), follow_redirects=False)
    assert page.status_code == 400 and "location" not in page.headers
    response = exchange(client, "c", pkce()[0])
    assert response.status_code == 401 and response.json()["error"] == "invalid_client"
