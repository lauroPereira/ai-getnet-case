# Interface and demonstration tunnel

The Streamlit interface shows the assistant to each role over the versioned `/v1` API: merchants and demo users
get Attendance and Results, operators get Ticketing, and admin also gets Administration. The tunnel profile lets
a visitor on another network sign in to it through one public address, for an announced window with one-off
credentials. The summary is in the [README](../../../README.md#streamlit-interface).

## Streamlit interface

The `ai-getnet-case-web` sibling project (see its README) is the Streamlit client of the versioned `/v1` API and,
for operators, of the ticketing service. It never reads backend files or receives provider keys.

- **Modes.** **Simulado** and **Gravado** run on fixtures; **Real (API)** signs in on the backend's login page
  (`/v1/auth/authorize`, opened by **Entrar**).
- **Areas by role.** Merchants and demo see Attendance and Results, operators see Ticketing, admin also sees
  Administration.
- **Session.** The client reuses one HTTP client per Streamlit session, revokes the token and clears the previous
  user's state at logout, and sends requests only after explicit actions.

```powershell
# In the web project, with its own Python environment:
python -m pip install -e ".[test]"                # the web project's own test extra
$env:BACKEND_API_URL = "http://localhost:8000"
$env:AUTH_ISSUER = "http://api:8000"              # the compose JWT_ISSUER; leave it unset for a local uvicorn
streamlit run app.py
```

Open the interface at `http://localhost:8501/`, the redirect registered in `OAUTH_REDIRECT_URIS`.

For a local HTTP exercise without a model key, use the synthetic backend harness with a new runtime directory under
`.pytest_cache`, then point `BACKEND_API_URL` to that loopback server. The harness has programmed providers, a fresh
isolated SQLite/Qdrant runtime and no provider credentials. The Results area lists the runs of the current browser
session.

## Open the demonstration through a tunnel

A visitor on another network reaches the demonstration through one public address: a [Cloudflare Quick Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/do-more-with-tunnels/trycloudflare/) (no account, ephemeral address) in front of a small proxy, `docker compose --profile tunnel up`. The proxy listens on `127.0.0.1:8080` and sends only `GET` and `POST /v1/auth/authorize` (the login page and its form) to the API; everything else, the Streamlit websocket included, goes to the interface on this host. No other API route is reachable through the tunnel. The API ignores forwarded headers, so every visitor counts as the proxy's address for the login attempt limit: stricter behind the tunnel, never looser. Without `--profile tunnel` nothing changes.

This guide was followed from a phone on a mobile network: sign-in by redirect, attendance, handoff and the operator's reply through the public address ([v1.0.0](../../evidence/v100-resultado.md)).

1. **Replace every example credential, then start the stack with the proxy.** The passwords in `.env.example` are public, and the login page will be too. In `.env`:
   - `API_DEMO_PASSWORD`: a new one-off password for the user `demo`; leave `API_ADMIN_PASSWORD` empty.
   - `DEMO_USER_PASSWORDS`: only the synthetic users you keep, each with a new random one-off password, for example `op_ana:<random>` if you will show the operator area. List at least one: an empty value does not turn the users off, it brings back the compose defaults, the published example passwords.
   - `TICKETING_CLIENT_SECRET`: a new random value (the API and the ticketing service read the same one); the same rule applies to an empty value.
   - Keep `BUDGET_LIMIT_USD` at the demonstration sublimit (US$1.00 by default) and `DEMO_SESSION_MESSAGE_LIMIT` at the paid actions one session may start.

   While a public address is registered (step 3), the API refuses to start if any credential still has a value published in this repository (`.env.example` or the test suite): `up --wait` fails, the API container stays unhealthy and its log names the accounts and variables to replace. Then:

   ```bash
   docker compose --profile tunnel up -d --wait
   ```

2. **Open the tunnel** and keep it running; it prints the public address, `https://<name>.trycloudflare.com`:

   ```bash
   cloudflared tunnel --url http://localhost:8080
   ```

3. **Register that address**, for this opening only. Append it to `OAUTH_REDIRECT_URIS` in `.env` (`...,merchant-assistant-web=https://<name>.trycloudflare.com/`) and run `docker compose --profile tunnel up -d --wait` again to recreate the API (it does not start while an example credential remains). Never commit the address.
4. **Start the interface** (web project) with the public address for the browser and the internal one for the server:

   ```bash
   export BACKEND_API_URL=http://localhost:8000 LOCK_BACKEND_URL=true AUTH_ISSUER=http://api:8000
   export AUTH_REDIRECT_URI=https://<name>.trycloudflare.com/
   export AUTH_AUTHORIZE_URL=https://<name>.trycloudflare.com/v1/auth/authorize
   streamlit run app.py
   ```

   Streamlit listens on every interface by default, which lets the proxy reach it at `host.docker.internal:8501` (set `STREAMLIT_UPSTREAM` for another address); keep port 8501 closed to other machines in the host firewall, so the tunnel is the only way in. The browser opens the login at `AUTH_AUTHORIZE_URL`; the interface's server exchanges, renews and revokes tokens only at `BACKEND_API_URL`.
5. **Share** `https://<name>.trycloudflare.com/` for an announced window, with the `demo` user and its one-off password; add an operator (`op_ana` and its one-off password) only to show the operator area. Never share `admin`. The visitor chooses **Real (API)**, clicks **Entrar** and signs in on the login page. The `demo` role has no administration; each session stops at `DEMO_SESSION_MESSAGE_LIMIT`, and every paid call stops at the budget limit.
6. **Close at the end of the window:** stop `cloudflared` (Ctrl+C) and the interface, run `docker compose stop tunnel`, remove the address from `OAUTH_REDIRECT_URIS`, clear `API_DEMO_PASSWORD`, restore the previous `DEMO_USER_PASSWORDS` and `TICKETING_CLIENT_SECRET` (the one-off passwords stop working) and run `docker compose up -d --wait`.

The quick tunnel serves an announced demonstration window; the same proxy runs behind another tunnel or a forwarded port for continuous use ([ADR 0026](../../architecture/decisions/0026-tunel-com-login-por-redirecionamento.md)).
