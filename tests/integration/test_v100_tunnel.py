"""v1.0.0 task 108 (spec leitura-acesso-v100 D6, ADR 0026, CA-74): the demonstration tunnel's single origin. The proxy
of the `tunnel` profile sends only GET and POST /v1/auth/authorize to the api and everything else to the interface; the
issuer's login page works at a public https origin with `iss` unchanged; forwarded headers are never trusted, so every
visitor behind the proxy counts as one address; with a public redirect URI registered the API does not start on the
published example credentials (round 2, review P1). Configuration and in-process only: no Docker, no proxy binary, no
network (the run through the real proxy and tunnel is the QA's)."""

from __future__ import annotations

import base64
import hashlib
import re
import secrets
from urllib.parse import parse_qs, urlsplit

import pytest
import yaml
from fastapi.testclient import TestClient
from pydantic import SecretStr

from merchant_assistant.api import identity
from merchant_assistant.api.app import create_app
from merchant_assistant.api.identity import CredentialConfigError, check_configuration
from merchant_assistant.config import PROJECT_ROOT
from merchant_assistant.testing import TEST_TICKETING_SECRET, TEST_USER_PASSWORDS, passwords_setting

PUBLIC = "https://demo-tunnel.example"  # stands for the ephemeral trycloudflare.com address, never versioned
PUBLIC_REDIRECT = f"{PUBLIC}/"
WEB = "merchant-assistant-web"
CADDY_IMAGE = "caddy:2.10.0-alpine"
STREAMLIT_UPSTREAM = "{$STREAMLIT_UPSTREAM:host.docker.internal:8501}"
DEMO_PASSWORD = secrets.token_urlsafe(16)  # a one-off value: drawn per run, never written in the repository


def _one_off(settings) -> None:
    """New values, as the guide asks before registering a public address: neither the examples of .env.example nor
    the test suite's values (merchant_assistant.testing), which are public too."""
    settings.demo_user_passwords = SecretStr(
        passwords_setting({user: secrets.token_urlsafe(16) for user in TEST_USER_PASSWORDS})
    )
    settings.ticketing_client_secret = SecretStr(secrets.token_urlsafe(16))


def _compose() -> dict:
    return yaml.safe_load((PROJECT_ROOT / "docker-compose.yml").read_text(encoding="utf-8"))


def _caddyfile() -> list:
    """The Caddyfile as nested [tokens, children] blocks (comments dropped); enough for this file's plain syntax."""
    root: list = []
    stack = [root]
    for raw in (PROJECT_ROOT / "docker/tunnel/Caddyfile").read_text(encoding="utf-8").splitlines():
        line = raw.split(" #")[0].strip() if not raw.strip().startswith("#") else ""
        if not line:
            continue
        if line == "}":
            stack.pop()
        elif line.endswith("{"):
            block = [line[:-1].split(), []]
            stack[-1].append(block)
            stack.append(block[1])
        else:
            stack[-1].append([line.split(), None])
    assert len(stack) == 1, "unbalanced braces"
    return root


def _site() -> list:
    globals_, site = _caddyfile()
    assert globals_[0] == [] and [tokens for tokens, _ in globals_[1]] == [["admin", "off"], ["auto_https", "off"]]
    assert site[0] == [":8080"]
    return site[1]


def route(method: str, path: str) -> str:
    """Where the proxy sends a request, read from the Caddyfile: `api` or `interface`."""
    matcher = next(children for tokens, children in _site() if tokens == ["@authorize"])
    rules = {tokens[0]: tokens[1:] for tokens, _ in matcher}
    return "api" if path in rules["path"] and method in rules["method"] else "interface"


# --- the proxy and the profile ------------------------------------------------------------------------------------


def test_the_proxy_sends_only_the_authorize_route_to_the_api():
    site = _site()
    assert [tokens for tokens, _ in site] == [["@authorize"], ["handle", "@authorize"], ["handle"]]
    matcher, to_api, to_interface = (children for _, children in site)
    assert [tokens for tokens, _ in matcher] == [["path", "/v1/auth/authorize"], ["method", "GET", "POST"]]
    # the api always receives exactly the authorize path, whatever spelling the path matcher accepted
    assert [tokens for tokens, _ in to_api] == [["rewrite", "*", "/v1/auth/authorize"], ["reverse_proxy", "api:8000"]]
    assert [tokens for tokens, _ in to_interface] == [["reverse_proxy", STREAMLIT_UPSTREAM]]
    text = (PROJECT_ROOT / "docker/tunnel/Caddyfile").read_text(encoding="utf-8")
    assert len(re.findall(r"^\s*reverse_proxy\b", text, re.M)) == 2 and text.count("api:8000") == 1
    assert "trusted_proxies" not in text  # the proxy does not take forwarded headers from the tunnel either

    assert route("GET", "/v1/auth/authorize") == route("POST", "/v1/auth/authorize") == "api"
    for method, path in (
        ("HEAD", "/v1/auth/authorize"),
        ("PUT", "/v1/auth/authorize"),
        ("POST", "/v1/auth/token"),
        ("POST", "/v1/auth/revoke"),
        ("GET", "/v1/profiles"),
        ("POST", "/v1/messages"),
        ("GET", "/openapi.json"),
        ("GET", "/docs"),
        ("GET", "/health"),
        ("GET", "/metrics"),
        ("GET", "/.well-known/jwks.json"),
        ("GET", "/.well-known/openid-configuration"),
        ("GET", "/v1/auth/authorize/x"),
        ("GET", "/_stcore/stream"),
        ("GET", "/"),
    ):
        assert route(method, path) == "interface", (method, path)


def test_the_tunnel_profile_is_a_pinned_proxy_outside_the_default_set():
    services = _compose()["services"]
    proxy = services["tunnel"]
    assert proxy["image"] == CADDY_IMAGE and "build" not in proxy  # official image, fixed version, no own build
    _, _, tag = proxy["image"].partition(":")
    assert tag and tag != "latest"
    assert proxy["profiles"] == ["tunnel"]
    assert proxy["ports"] == ["127.0.0.1:8080:8080"]  # one local port; cloudflared publishes it
    assert proxy["volumes"] == ["./docker/tunnel/Caddyfile:/etc/caddy/Caddyfile:ro"]
    assert (PROJECT_ROOT / "docker/tunnel/Caddyfile").is_file()
    assert proxy["environment"] == {"STREAMLIT_UPSTREAM": "${STREAMLIT_UPSTREAM:-host.docker.internal:8501}"}
    assert "env_file" not in proxy  # the proxy never receives the provider keys
    assert proxy["extra_hosts"] == ["host.docker.internal:host-gateway"]
    assert proxy["depends_on"] == {"api": {"condition": "service_healthy"}}
    # without `--profile tunnel` nothing changes: the default set and the api's local-only port are the same
    assert {name for name, service in services.items() if "profiles" not in service} == {
        "qdrant",
        "mocks",
        "api",
        "ticketing",
    }
    assert [name for name, service in services.items() if "tunnel" in service.get("profiles", [])] == ["tunnel"]
    assert services["api"]["ports"] == ["127.0.0.1:8000:8000"]


def test_the_api_never_trusts_forwarded_headers():
    entrypoint = (PROJECT_ROOT / "docker/entrypoint.sh").read_text(encoding="utf-8")
    command = entrypoint[entrypoint.index("exec uvicorn") :].replace("\\\n", " ")
    assert "--no-proxy-headers" in command.split() and "--forwarded-allow-ips" not in command
    assert "--proxy-headers" not in command.split()


# --- the issuer behind the proxy ----------------------------------------------------------------------------------


def _pkce() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(48)
    return verifier, base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()


class Visitor:
    """The visitor's browser at the public origin: each request goes through `route`; what the proxy sends to the
    interface never reaches the api."""

    def __init__(self, app):
        self.client = TestClient(app, base_url=PUBLIC)
        self.to_interface: list[tuple[str, str]] = []

    def request(self, method: str, path: str, **kwargs):
        if route(method, urlsplit(path).path) != "api":
            self.to_interface.append((method, path))
            return None
        return self.client.request(method, path, follow_redirects=False, **kwargs)


def _authorize_params(challenge: str) -> dict[str, str]:
    return {
        "response_type": "code",
        "client_id": WEB,
        "redirect_uri": PUBLIC_REDIRECT,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "state": "st-tunnel",
    }


def test_login_through_the_proxy_at_a_public_https_origin_then_session_and_logout(offline, settings):
    settings.oauth_redirect_uris = f"{WEB}=http://localhost:8501/,{WEB}={PUBLIC_REDIRECT}"
    settings.api_demo_password = SecretStr(DEMO_PASSWORD)
    _one_off(settings)
    internal, _, _ = offline()  # the interface's server side, at the api's internal address
    visitor = Visitor(internal.app)
    verifier, challenge = _pkce()
    params = _authorize_params(challenge)

    page = visitor.request("GET", "/v1/auth/authorize", params=params)
    assert page.status_code == 200
    assert re.findall(r'<form method="post" action="([^"]*)"', page.text) == ["/v1/auth/authorize"]  # same origin
    assert "127.0.0.1:8000" not in page.text and "api:8000" not in page.text  # no internal address on the page
    assert page.headers["content-security-policy"].endswith(f"; form-action 'self' {PUBLIC}")

    form = params | {"username": "demo", "password": DEMO_PASSWORD}
    back = visitor.request("POST", "/v1/auth/authorize", data=form)
    assert back.status_code == 303
    location = urlsplit(back.headers["location"])
    assert f"{location.scheme}://{location.netloc}{location.path}" == PUBLIC_REDIRECT
    redirect = {key: values[0] for key, values in parse_qs(location.query).items()}
    assert redirect["state"] == "st-tunnel" and redirect["iss"] == settings.jwt_issuer  # iss unchanged
    assert redirect["iss"] != PUBLIC

    # the server side exchanges, renews and revokes at the internal address; the proxy would hand these to the
    # interface, never to the api
    for method, path in (("POST", "/v1/auth/token"), ("POST", "/v1/auth/revoke"), ("GET", "/v1/profiles")):
        assert visitor.request(method, path) is None
    assert visitor.to_interface == [("POST", "/v1/auth/token"), ("POST", "/v1/auth/revoke"), ("GET", "/v1/profiles")]
    exchange = {
        "grant_type": "authorization_code",
        "code": redirect["code"],
        "code_verifier": verifier,
        "redirect_uri": PUBLIC_REDIRECT,
        "client_id": WEB,
    }
    tokens = internal.post("/v1/auth/token", data=exchange)
    assert tokens.status_code == 200, tokens.text
    body = tokens.json()
    bearer = {"Authorization": f"Bearer {body['access_token']}"}
    assert internal.get("/v1/profiles", headers=bearer).status_code == 200  # the session is open
    rotated = internal.post(
        "/v1/auth/token", data={"grant_type": "refresh_token", "refresh_token": body["refresh_token"], "client_id": WEB}
    )
    assert rotated.status_code == 200
    bearer = {"Authorization": f"Bearer {rotated.json()['access_token']}"}
    logout = internal.post("/v1/auth/revoke", headers=bearer, data={"token": rotated.json()["refresh_token"]})
    assert logout.status_code == 200
    assert internal.get("/v1/profiles", headers=bearer).status_code == 401  # the logout revoked the login
    refused = internal.post(
        "/v1/auth/token",
        data={"grant_type": "refresh_token", "refresh_token": rotated.json()["refresh_token"], "client_id": WEB},
    )
    assert refused.status_code == 400


def test_an_unregistered_public_origin_gets_no_redirect(offline, settings):
    client, _, _ = offline()  # default registration: the interface on this host only
    visitor = Visitor(client.app)
    page = visitor.request("GET", "/v1/auth/authorize", params=_authorize_params(_pkce()[1]))
    assert page.status_code == 400 and "location" not in page.headers


def test_behind_the_proxy_every_visitor_counts_as_one_address(offline, settings, monkeypatch):
    """The login limit per address sees the proxy, not the visitor: forwarded headers do not split it per visitor, so
    it is stricter behind the proxy, never looser."""
    monkeypatch.setattr(identity, "utc_seconds", lambda: 1_800_000_010.0)  # one fixed 60 s window
    settings.oauth_redirect_uris = f"{WEB}={PUBLIC_REDIRECT}"
    _one_off(settings)
    settings.auth_attempts_per_ip_per_minute = 3
    client, _, _ = offline()
    visitor = Visitor(client.app)
    answers = []
    for n, user in enumerate(("cliente1988", "op_ana", "op_bruno", "cliente_demo_002")):
        spoofed = f"203.0.113.{n + 1}"
        headers = {"X-Forwarded-For": spoofed, "X-Real-IP": spoofed, "Forwarded": f"for={spoofed}"}
        form = _authorize_params(_pkce()[1]) | {"username": user, "password": "wrong"}
        answers.append(visitor.request("POST", "/v1/auth/authorize", data=form, headers=headers).status_code)
    assert answers == [400, 400, 400, 429]


# --- the published example credentials and a public login page (round 2, review P1) -------------------------------


def _compose_default(name: str) -> str:
    value = _compose()["services"]["api"]["environment"][name]
    match = re.fullmatch(r"\$\{" + name + r":-(.*)\}", value)
    assert match, name
    return match.group(1)


def _with_compose_defaults(settings) -> None:
    """What the api receives when `.env` leaves these empty: the fictitious values published in the repository."""
    settings.demo_user_passwords = SecretStr(_compose_default("DEMO_USER_PASSWORDS"))
    settings.ticketing_client_secret = SecretStr(_compose_default("TICKETING_CLIENT_SECRET"))


def _variables_to_replace(error: CredentialConfigError) -> str:
    return str(error).split("Set new one-off values in ", 1)[1].split(" (", 1)[0]


def test_a_public_redirect_with_the_compose_defaults_stops_the_startup(settings):
    _with_compose_defaults(settings)
    settings.oauth_redirect_uris = f"{WEB}=http://localhost:8501/,{WEB}={PUBLIC_REDIRECT}"
    with pytest.raises(CredentialConfigError) as refused:
        create_app(settings=settings)  # before any orchestrator, so no login page is ever served
    message = str(refused.value)
    for account in (
        "user:cliente1988",
        "user:cliente_demo_002",
        "user:op_ana",
        "user:op_bruno",
        "client:ticketing-demo",
    ):
        assert account in message
    assert _variables_to_replace(refused.value) == "DEMO_USER_PASSWORDS, TICKETING_CLIENT_SECRET"
    for _, password in (pair.split(":", 1) for pair in _compose_default("DEMO_USER_PASSWORDS").split(",")):
        assert password not in message  # names the accounts, never echoes a value


@pytest.mark.parametrize(
    "field, value, variable",
    [
        ("demo_user_passwords", "op_ana:op-ana-fictitious", "DEMO_USER_PASSWORDS"),
        ("api_demo_password", "demo-fictitious", "API_DEMO_PASSWORD"),
        ("api_admin_password", "admin-fictitious", "API_ADMIN_PASSWORD"),
        ("ticketing_client_secret", "ticketing-demo-secret-fictitious", "TICKETING_CLIENT_SECRET"),
        ("telegram_client_secret", "telegram-operator-fictitious", "TELEGRAM_CLIENT_SECRET"),
        # the test suite's values are published too (merchant_assistant.testing)
        ("demo_user_passwords", f"op_ana:{TEST_USER_PASSWORDS['op_ana']}", "DEMO_USER_PASSWORDS"),
        ("api_demo_password", TEST_USER_PASSWORDS["cliente1988"], "API_DEMO_PASSWORD"),
        ("ticketing_client_secret", TEST_TICKETING_SECRET, "TICKETING_CLIENT_SECRET"),
        ("telegram_client_secret", TEST_TICKETING_SECRET, "TELEGRAM_CLIENT_SECRET"),
    ],
)
def test_each_example_credential_stops_a_public_startup(settings, field, value, variable):
    settings.oauth_redirect_uris = f"{WEB}={PUBLIC_REDIRECT}"
    _one_off(settings)
    setattr(settings, field, SecretStr(value))
    with pytest.raises(CredentialConfigError) as refused:
        check_configuration(settings)
    assert _variables_to_replace(refused.value) == variable


def test_loopback_redirects_keep_the_example_values_as_a_warning(offline, settings):
    _with_compose_defaults(settings)
    settings.oauth_redirect_uris = f"{WEB}=http://localhost:8501/,{WEB}=http://127.0.0.1:8501/,{WEB}=http://[::1]:8501/"
    warnings = check_configuration(settings)
    assert len(warnings) == 1 and "user:op_ana" in warnings[0]  # as before: a warning, the api starts
    client, _, _ = offline()
    assert client.get("/health").status_code == 200


def test_a_public_redirect_with_new_values_starts(offline, settings):
    settings.oauth_redirect_uris = f"{WEB}={PUBLIC_REDIRECT}"
    settings.api_demo_password = SecretStr(DEMO_PASSWORD)
    _one_off(settings)  # new values, not empty
    assert check_configuration(settings) == []
    client, _, _ = offline()
    assert client.get("/health").status_code == 200


def test_the_tunnel_guide_asks_for_new_credentials_and_retires_them():
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    section = readme.split("#### Open the demonstration through a tunnel", 1)[1].split("\n### ", 1)[0]
    for text in (
        "`API_DEMO_PASSWORD`: a new one-off password",
        "`DEMO_USER_PASSWORDS`: only the synthetic users you keep, each with a new random one-off password",
        "an empty value does not turn the users off, it brings back the compose defaults",
        "`TICKETING_CLIENT_SECRET`: a new random value",
        "the API refuses to start if any credential still has a value published in this repository "
        "(`.env.example` or the test suite)",
        "Never share `admin`",
        "restore the previous `DEMO_USER_PASSWORDS` and `TICKETING_CLIENT_SECRET`",
    ):
        assert text in section, text
