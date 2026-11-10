"""Minimal login page of the assistant's issuer (v0.13.0, spec D1, task 97): plain HTML, no framework, no script.

The page carries the authorization request (client, exact `redirect_uri`, PKCE challenge, `state`) in hidden fields
and posts it back with the user's credentials to `POST /v1/auth/authorize`. Every value is HTML-escaped; the password
is never echoed. The headers forbid framing and caching."""

from __future__ import annotations

import re
from html import escape
from urllib.parse import urlsplit

from fastapi.responses import HTMLResponse

PAGE_HEADERS = {
    "Cache-Control": "no-store",
    "Pragma": "no-cache",
    "X-Frame-Options": "DENY",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
}
_CSP = "default-src 'none'; style-src 'unsafe-inline'; frame-ancestors 'none'; base-uri 'none'"
_ORIGIN = re.compile(r"https?://[A-Za-z0-9.\-]+(:[0-9]{1,5})?|https?://\[[0-9A-Fa-f:.]+\](:[0-9]{1,5})?")
AUTHORIZE_FIELDS = ("response_type", "client_id", "redirect_uri", "code_challenge", "code_challenge_method", "state")

_STYLE = (
    "body{font-family:system-ui,sans-serif;background:#f4f4f4;margin:0}"
    "main{max-width:22rem;margin:4rem auto;background:#fff;padding:2rem;border-radius:8px}"
    "h1{font-size:1.25rem;color:#c00}label{display:block;margin-top:1rem}"
    "input[type=text],input[type=password]{width:100%;padding:.5rem;box-sizing:border-box}"
    "button{margin-top:1.5rem;width:100%;padding:.6rem;background:#c00;color:#fff;border:0;border-radius:4px}"
    ".error{color:#900;margin-top:1rem}.note{color:#555;font-size:.85rem;margin-top:1.5rem}"
)


def _document(title: str, body: str) -> str:
    return (
        '<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>{escape(title)}</title><style>{_STYLE}</style></head><body><main>{body}</main></body></html>"
    )


def _headers(form_action: str) -> dict[str, str]:
    return PAGE_HEADERS | {"Content-Security-Policy": f"{_CSP}; form-action {form_action}"}


def _form_action(redirect_uri: str) -> str:
    """The form posts to the page itself and its answer redirects to the registered `redirect_uri`; browsers that
    apply `form-action` to that redirect need its origin listed too."""
    parts = urlsplit(redirect_uri)
    origin = f"{parts.scheme}://{parts.netloc}"
    return f"'self' {origin}" if _ORIGIN.fullmatch(origin) else "'self'"


def login_page(params: dict[str, str], *, error: str | None = None, username: str = "", status: int = 200):
    """The login form for a validated authorization request (its `redirect_uri` is a registered one)."""
    hidden = "".join(
        f'<input type="hidden" name="{name}" value="{escape(params.get(name, ""), quote=True)}">'
        for name in AUTHORIZE_FIELDS
    )
    message = f'<p class="error" role="alert">{escape(error)}</p>' if error else ""
    body = (
        "<h1>Assistente do lojista</h1><p>Entre para continuar.</p>"
        f'<form method="post" action="/v1/auth/authorize">{hidden}'
        '<label for="username">Usuário</label>'
        f'<input id="username" name="username" type="text" autocomplete="username" required '
        f'value="{escape(username, quote=True)}">'
        '<label for="password">Senha</label>'
        '<input id="password" name="password" type="password" autocomplete="current-password" required>'
        f'{message}<button type="submit">Entrar</button></form>'
        '<p class="note">Ambiente de demonstração com dados sintéticos.</p>'
    )
    headers = _headers(_form_action(params.get("redirect_uri", "")))
    return HTMLResponse(_document("Entrar", body), status_code=status, headers=headers)


def error_page(message: str, status: int = 400):
    """Shown instead of redirecting when the client or its `redirect_uri` is not registered (RFC 6749, 4.1.2.1)."""
    body = f'<h1>Não foi possível entrar</h1><p class="error" role="alert">{escape(message)}</p>'
    return HTMLResponse(_document("Erro", body), status_code=status, headers=_headers("'none'"))
