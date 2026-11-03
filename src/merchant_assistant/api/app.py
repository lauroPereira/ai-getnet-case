"""FastAPI application: health, readiness, messages (session required) and, in demo mode, traces and
conversations of the session's own merchant."""

from __future__ import annotations

import logging
import uuid
from contextlib import asynccontextmanager
from typing import Protocol

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from merchant_assistant import __version__
from merchant_assistant.api.identity import Identity, Principal, check_configuration
from merchant_assistant.api.schemas import ErrorBody, ErrorDetail, MessageRequest, MessageResponse
from merchant_assistant.api.v1 import AUTH, OPERATOR_FORBIDDEN, rate_limited
from merchant_assistant.api.v1 import router as v1_router
from merchant_assistant.config import Settings, get_settings
from merchant_assistant.conversations import ConversationNotFound
from merchant_assistant.data.db import connect

log = logging.getLogger("merchant_assistant.api")


MESSAGE_ROLES = ("merchant", "demo")  # operators, services and admin have no merchant of their own here
MESSAGES_DESCRIPTION = """Sends one merchant message. A bearer access token is required: the merchant comes from the
token's principal, never from the payload (`user_id` is optional and, when present, must match it, otherwise
`403 identity_mismatch`). Operator, service and admin tokens receive `403`.

Two calls: get a token (OAuth 2.0 password grant), then send the message with it.

```bash
TOKEN=$(curl -s localhost:8000/v1/auth/token -d grant_type=password -d username=cliente1988 \
  -d password=cliente1988-fictitious | python -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')
curl -s localhost:8000/messages -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"message": "When will the money from yesterday sales be deposited?"}'
```

In this page: get the token with `POST /v1/auth/token`, press **Authorize** and paste the `access_token`. The
passwords of `.env.example` are fictitious examples; replace them before exposing the API."""


class Orchestrator(Protocol):
    def handle(
        self, request: MessageRequest, request_id: str, *, principal: Principal | None = None
    ) -> MessageResponse: ...

    def readiness(self) -> dict[str, bool | str]: ...

    def trace(self, request_id: str) -> dict | None: ...


class PlaceholderOrchestrator:
    """Used until the agent graph is wired: always asks for clarification."""

    def handle(
        self, request: MessageRequest, request_id: str, *, principal: Principal | None = None
    ) -> MessageResponse:
        from merchant_assistant.api.schemas import Resolution

        return MessageResponse(
            answer="Could you tell me a bit more about what you need?",
            status="needs_clarification",
            route="clarify",
            agents=[],
            language="en",
            request_id=request_id,
            conversation_id=request.conversation_id or f"conv_{uuid.uuid4().hex[:16]}",
            resolution=Resolution(state="awaiting_customer"),
        )

    def readiness(self) -> dict[str, bool | str]:
        return {"ready": False, "reason": "orchestrator not configured"}

    def trace(self, request_id: str) -> dict | None:
        return None

    def conversation(self, conversation_id: str) -> dict | None:
        return None


def _error(status: int, code: str, message: str, request_id: str) -> JSONResponse:
    body = ErrorBody(error=ErrorDetail(code=code, message=message, request_id=request_id))
    return JSONResponse(status_code=status, content=body.model_dump(), headers={"X-Request-ID": request_id})


def _has_handoff_case(settings: Settings, conversation_id: str | None) -> bool:
    if not conversation_id:
        return False
    conn = connect(settings.db_path)
    try:
        return (
            conn.execute("SELECT 1 FROM handoff_cases WHERE conversation_id=? LIMIT 1", (conversation_id,)).fetchone()
            is not None
        )
    finally:
        conn.close()


def can_read(settings: Settings, principal: Principal, customer_id: str | None, conversation_id: str | None) -> bool:
    """Demo routes (spec v0.7.0, D14): merchant and demo read only their own merchant's data; an operator only
    conversations that have a handoff case; admin reads everything."""
    if principal.role == "admin":
        return True
    if principal.role == "operator":
        return _has_handoff_case(settings, conversation_id)
    return customer_id is not None and customer_id == principal.customer_id


def message_refusal(principal: Principal, user_id: str | None) -> tuple[str, str] | None:
    """`POST /messages` for an authenticated principal: only merchant-bound roles, and a `user_id`, when sent, must
    be the principal's merchant. Returns (code, message) of the 403 or None."""
    if principal.role not in MESSAGE_ROLES or not principal.customer_id:
        return "insufficient_scope", OPERATOR_FORBIDDEN
    if user_id is not None and user_id != principal.customer_id:
        return "identity_mismatch", "user_id does not match the session's merchant."
    return None


def create_app(orchestrator: Orchestrator | None = None, settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    for warning in check_configuration(settings):  # an invalid credential configuration stops the startup here
        log.warning(warning)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield
        close = getattr(app.state.orchestrator, "close", None)
        if close:
            close()

    app = FastAPI(
        lifespan=lifespan,
        title="Getnet Merchant Assistant",
        version=__version__,
        description="Multi-agent support system: Router, Knowledge, Customer Support, Escalation and Personality.",
    )
    app.state.orchestrator = orchestrator or PlaceholderOrchestrator()
    app.state.settings = settings
    app.state.identity = Identity(settings)
    app.include_router(v1_router)

    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        request.state.request_id = f"req_{uuid.uuid4().hex[:20]}"
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError):
        fields = sorted({".".join(str(p) for p in e["loc"] if p != "body") for e in exc.errors()})
        return _error(422, "invalid_request", f"Invalid fields: {', '.join(fields)}", request.state.request_id)

    @app.exception_handler(Exception)
    async def unhandled_handler(request: Request, exc: Exception):
        log.exception("unhandled error", extra={"request_id": getattr(request.state, "request_id", None)})
        return _error(500, "internal_error", "Unexpected error. Please try again.", request.state.request_id)

    @app.get("/health", tags=["ops"])
    def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    @app.get("/.well-known/jwks.json", tags=["auth"])
    def jwks() -> JSONResponse:
        """Public signing keys of the assistant's token issuer (RS256, `kid` = RFC 7638 thumbprint)."""
        return JSONResponse(app.state.identity.jwks(), headers={"Cache-Control": "public, max-age=300"})

    @app.get("/.well-known/openid-configuration", tags=["auth"])
    def openid_configuration() -> dict:
        return app.state.identity.openid_configuration()

    @app.get("/ready", tags=["ops"])
    def ready() -> JSONResponse:
        info = app.state.orchestrator.readiness()
        return JSONResponse(status_code=200 if info.get("ready") else 503, content=info)

    @app.post(
        "/messages",
        response_model=MessageResponse,
        responses={
            401: {"model": ErrorBody},
            403: {"model": ErrorBody},
            404: {"model": ErrorBody},
            422: {"model": ErrorBody},
            429: {"model": ErrorBody},
            500: {"model": ErrorBody},
        },
        tags=["assistant"],
        description=MESSAGES_DESCRIPTION,
    )
    def messages(payload: MessageRequest, request: Request, principal=AUTH) -> MessageResponse:
        if isinstance(principal, JSONResponse):
            return principal
        request_id = request.state.request_id
        caller = Principal.from_session(principal)
        if refusal := message_refusal(caller, payload.user_id):
            response = _error(403, *refusal, request_id)
            if refusal[0] == "insufficient_scope":
                response.headers["WWW-Authenticate"] = 'Bearer realm="merchant-assistant", error="insufficient_scope"'
            return response
        if limited := rate_limited(request, principal):
            return limited
        bound = payload.model_copy(update={"user_id": caller.customer_id})
        try:
            return app.state.orchestrator.handle(bound, request_id, principal=caller)
        except ConversationNotFound:
            return _error(
                404, "conversation_not_found", "Conversation not found for this user.", request.state.request_id
            )

    if settings.demo_mode:

        @app.get("/traces/{request_id}", tags=["demo"])
        def trace(request_id: str, request: Request, principal=AUTH):
            if isinstance(principal, JSONResponse):
                return principal
            data = app.state.orchestrator.trace(request_id)
            conversation_id = (data or {}).get("detail", {}).get("conversation_id")
            owner = (data or {}).get("user_id")
            if data is None or not can_read(settings, Principal.from_session(principal), owner, conversation_id):
                return _error(404, "not_found", "Trace not found.", request.state.request_id)
            return data

        @app.get("/conversations/{conversation_id}", tags=["demo"])
        def conversation(conversation_id: str, request: Request, principal=AUTH):
            if isinstance(principal, JSONResponse):
                return principal
            data = app.state.orchestrator.conversation(conversation_id)
            owner = (data or {}).get("customer_id")
            if data is None or not can_read(settings, Principal.from_session(principal), owner, conversation_id):
                return _error(404, "not_found", "Conversation not found.", request.state.request_id)
            return data

    return app
