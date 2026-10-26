"""FastAPI application: health, readiness, messages and (demo only) traces."""

from __future__ import annotations

import logging
import uuid
from typing import Protocol

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from merchant_assistant import __version__
from merchant_assistant.api.schemas import ErrorBody, ErrorDetail, MessageRequest, MessageResponse
from merchant_assistant.config import Settings, get_settings

log = logging.getLogger("merchant_assistant.api")


class Orchestrator(Protocol):
    def handle(self, request: MessageRequest, request_id: str) -> MessageResponse: ...

    def readiness(self) -> dict[str, bool | str]: ...

    def trace(self, request_id: str) -> dict | None: ...


class PlaceholderOrchestrator:
    """Used until the agent graph is wired: always asks for clarification."""

    def handle(self, request: MessageRequest, request_id: str) -> MessageResponse:
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


def _error(status: int, code: str, message: str, request_id: str) -> JSONResponse:
    body = ErrorBody(error=ErrorDetail(code=code, message=message, request_id=request_id))
    return JSONResponse(status_code=status, content=body.model_dump(), headers={"X-Request-ID": request_id})


def create_app(orchestrator: Orchestrator | None = None, settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(
        title="Getnet Merchant Assistant",
        version=__version__,
        description="Multi-agent support system: Router, Knowledge, Customer Support, Escalation and Personality.",
    )
    app.state.orchestrator = orchestrator or PlaceholderOrchestrator()
    app.state.settings = settings

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

    @app.get("/ready", tags=["ops"])
    def ready() -> JSONResponse:
        info = app.state.orchestrator.readiness()
        return JSONResponse(status_code=200 if info.get("ready") else 503, content=info)

    @app.post(
        "/messages",
        response_model=MessageResponse,
        responses={422: {"model": ErrorBody}, 500: {"model": ErrorBody}},
        tags=["assistant"],
    )
    def messages(payload: MessageRequest, request: Request) -> MessageResponse:
        return app.state.orchestrator.handle(payload, request.state.request_id)

    if settings.demo_mode:

        @app.get("/traces/{request_id}", tags=["demo"])
        def trace(request_id: str, request: Request):
            data = app.state.orchestrator.trace(request_id)
            if data is None:
                return _error(404, "not_found", "Trace not found.", request.state.request_id)
            return data

    return app
