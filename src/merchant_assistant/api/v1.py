"""Authenticated versioned API for the Streamlit interface."""

from __future__ import annotations

import base64
import hashlib
import json
import sqlite3
import time
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Literal
from urllib.parse import parse_qs, unquote_plus

from fastapi import APIRouter, Depends, Header, Request, Security
from fastapi.responses import JSONResponse, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field

from merchant_assistant import comparisons, handoffs
from merchant_assistant import scenarios as scenario_catalog
from merchant_assistant.agents.common import format_history
from merchant_assistant.agents.router import enforce
from merchant_assistant.api.identity import (
    DEFAULT_PUBLIC_CLIENT,
    HANDOFF_OPERATE,
    PUBLIC_CLIENTS,
    SERVICE_CLIENTS,
    InvalidToken,
    Principal,
    hit_rate_limit,
    remember_principal,
)
from merchant_assistant.api.schemas import ErrorBody, MessageRequest
from merchant_assistant.config import Settings
from merchant_assistant.conversations import ConversationNotFound, ConversationStore
from merchant_assistant.data.clock import SystemClock
from merchant_assistant.data.db import connect
from merchant_assistant.guardrails.input import check_input
from merchant_assistant.llm.base import CallSpec, LLMError
from merchant_assistant.observability.traces import TraceRecorder
from merchant_assistant.orchestration.budget import BudgetExceeded
from merchant_assistant.orchestration.run import RunContext
from merchant_assistant.orchestration.state import RouterDecision
from merchant_assistant.profiles import (
    CATALOG,
    bootstrap_profiles,
    create_draft,
    digest,
    get_profile,
    list_profiles,
    publish,
    update_draft,
)
from merchant_assistant.rag.kb import KBBuildFailure
from merchant_assistant.tools.base import CustomerContext, ToolEnv

router = APIRouter(prefix="/v1", tags=["v1"])
COMPARISON_TTL = timedelta(minutes=5)


class ProfileCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=80)
    agents: dict
    demo_allowed: bool = False


class ProfileDraftRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=1)
    agents: dict


class PublishRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=1)


class V1MessageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: str = Field(min_length=1, max_length=2000)
    conversation_id: str | None = Field(default=None, pattern=r"^conv_[A-Za-z0-9]{8,40}$")
    profile_id: str = Field(min_length=1, max_length=80)
    profile_version: int = Field(ge=1)
    router_mechanism: str = Field(pattern=r"^(llm|jev)$")
    comparison_id: str | None = None
    scenario_id: str | None = Field(default=None, min_length=1, max_length=64)


class EvaluationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    confirmed: bool
    max_cost_usd: float = Field(ge=0, le=5)
    expected_estimate_digest: str = Field(min_length=1, max_length=128)
    repeat: bool = False


class ComparisonProfileRef(BaseModel):
    model_config = ConfigDict(extra="forbid")
    profile_id: str = Field(min_length=1, max_length=80)
    profile_version: int = Field(ge=1)


class ComparisonEstimateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    profiles: list[ComparisonProfileRef] = Field(min_length=2, max_length=3)
    scenario_ids: list[str] = Field(min_length=1, max_length=3)
    repetitions: int = Field(default=1, ge=1, le=2)
    router_mechanism: str = Field(default="llm", pattern=r"^(llm|jev)$")
    reuse_recorded: bool = True


class ComparisonCreateRequest(ComparisonEstimateRequest):
    confirmed: bool
    max_cost_usd: float = Field(ge=0, le=5)
    expected_estimate_digest: str = Field(min_length=1, max_length=128)


class CompareRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: str = Field(min_length=1, max_length=2000)
    conversation_id: str | None = Field(default=None, pattern=r"^conv_[A-Za-z0-9]{8,40}$")
    profile_id: str
    profile_version: int = Field(ge=1)
    selected_mechanism: str = Field(pattern=r"^(llm|jev)$")


class ModelParameterSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["integer"]
    minimum: int
    maximum_by_agent: dict[str, int]
    description: str
    documentation_url: str


class ModelCatalogItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provider: str
    model: str
    agents: list[str]
    capabilities: list[str]
    parameters: dict[str, ModelParameterSpec]
    price: dict[str, Any]
    price_tier: str | None
    model_version: str


class ModelCatalogResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    models: list[ModelCatalogItem]
    verified_at: str
    sources: dict[str, str]


class KBDraftRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    content: str = Field(min_length=1, max_length=65536)
    expected_revision: int = Field(ge=0)


class KBEstimateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    revisions: dict[str, int] = Field(default_factory=dict)


class KBBuildRequest(KBEstimateRequest):
    expected_active_version_id: str
    expected_digest: str
    confirmed: bool
    max_cost_usd: float = Field(ge=0, le=5)


class KBTestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    confirmed: bool
    max_cost_usd: float = Field(ge=0, le=5)


class KBTransitionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_active_version_id: str
    confirmed: bool


def _db(request: Request) -> sqlite3.Connection:
    return connect(request.app.state.settings.db_path)


def _utc() -> datetime:
    return datetime.now(UTC)


def _token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _error(
    status: int, code: str, message: str, request: Request, headers: dict[str, str] | None = None
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "req_unknown")
    return JSONResponse(
        status_code=status,
        content={"error": {"code": code, "message": message, "request_id": request_id}},
        headers=headers,
    )


def rate_limited(request: Request, principal: dict) -> JSONResponse | None:
    """Per-principal limit (spec v0.7.0, D5), checked before any model call. Returns the 429 response or None."""
    settings: Settings = request.app.state.settings
    conn = _db(request)
    try:
        retry_after = hit_rate_limit(conn, principal["principal_id"], settings.rate_limit_per_minute)
    finally:
        conn.close()
    if retry_after is None:
        return None
    return _error(
        429,
        "rate_limited",
        "Too many requests for this session; retry after the indicated seconds.",
        request,
        headers={"Retry-After": str(retry_after)},
    )


def _unauthorized(request: Request, code: str, message: str) -> JSONResponse:
    error = "" if code == "token_required" else ', error="invalid_token"'
    return _error(
        401, code, message, request, headers={"WWW-Authenticate": f'Bearer realm="merchant-assistant"{error}'}
    )


def _principal(request: Request, authorization: str | None = Header(default=None)) -> dict | JSONResponse:
    """Verifies the bearer token (the single verifier of `api.identity`) and returns the principal as the dict the
    routes use. `session_id` is the token's `jti` (per-token counters such as the demo action limit)."""
    if not authorization or not authorization.startswith("Bearer "):
        return _unauthorized(request, "token_required", "A bearer access token is required.")
    token = authorization[7:].strip()
    if not token or len(token) > 8192:
        return _unauthorized(request, "invalid_token", "The access token is invalid, expired or revoked.")
    conn = _db(request)
    try:
        principal, claims = request.app.state.identity.verify(token, conn)
        remember_principal(conn, principal)
    except InvalidToken:
        return _unauthorized(request, "invalid_token", "The access token is invalid, expired or revoked.")
    finally:
        conn.close()
    return {
        "principal_id": principal.principal_id,
        "role": principal.role,
        "customer_id": principal.customer_id,
        "scopes": principal.scopes,
        "session_id": claims["jti"],
        "expires_at": datetime.fromtimestamp(claims["exp"], UTC).isoformat(),
        "client_id": claims.get("client_id"),
        "_claims": claims,
    }


def insufficient_scope(request: Request, message: str) -> JSONResponse:
    """`403 insufficient_scope` with the RFC 6750 challenge."""
    challenge = 'Bearer realm="merchant-assistant", error="insufficient_scope"'
    return _error(403, "insufficient_scope", message, request, headers={"WWW-Authenticate": challenge})


def _require(request: Request, roles: tuple[str, ...] = ("demo", "admin")):
    principal = _principal(request)
    if isinstance(principal, JSONResponse):
        return principal
    if principal["role"] not in roles:
        return insufficient_scope(request, "This action is not allowed for this token.")
    return principal


bearer_scheme = HTTPBearer(
    auto_error=False,
    scheme_name="SessionBearer",
    bearerFormat="JWT",
    description="Access token from POST /v1/auth/token (RS256, typ at+jwt).",
)
bearer_credentials = Security(bearer_scheme)


def _auth_dep(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = bearer_credentials,
):
    authorization = f"Bearer {credentials.credentials}" if credentials else None
    return _principal(request, authorization)


def _admin_dep(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = bearer_credentials,
):
    authorization = f"Bearer {credentials.credentials}" if credentials else None
    return _require_header(request, authorization, ("admin",))


READER_ROLES = ("merchant", "demo", "admin")


def acting_merchant(request: Request, principal: dict) -> dict:
    """D20 (revised): the admin has no merchant in its token; on the /v1 routes that need one (messages, comparisons,
    Router comparison, evaluations, conversations) it acts on the demo's synthetic merchant, as in v0.6.0. The
    principal row itself keeps no merchant."""
    if principal["role"] == "admin":
        return principal | {"customer_id": request.app.state.settings.api_demo_customer_id or None}
    return principal


def _reader_dep(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = bearer_credentials,
):
    """D21: workbench routes (profiles, KB, catalog, scenarios, runs, comparisons, messages) are for merchant, demo
    and admin tokens; operators work in the queue and services only integrate."""
    principal = _auth_dep(request, credentials)
    if isinstance(principal, JSONResponse):
        return principal
    if principal["role"] in READER_ROLES:
        return acting_merchant(request, principal)
    challenge = 'Bearer realm="merchant-assistant", error="insufficient_scope"'
    return _error(
        403,
        "insufficient_scope",
        "This route is for merchant, demo and admin tokens.",
        request,
        headers={"WWW-Authenticate": challenge},
    )


AUTH = Depends(_auth_dep)
ADMIN = Depends(_admin_dep)
READER = Depends(_reader_dep)


def _require_header(request: Request, authorization: str | None, roles: tuple[str, ...]):
    principal = _principal(request, authorization)
    if isinstance(principal, JSONResponse):
        return principal
    if principal["role"] not in roles:
        return insufficient_scope(request, "This action is not allowed for this token.")
    return principal


def _ensure_not_error(principal: dict | JSONResponse):
    return isinstance(principal, JSONResponse)


# D18: merchant tokens see the same profiles as the demo and count in the same per-token action limit.
LIMITED_ROLES = ("demo", "merchant")


def profile_role(principal: dict) -> str:
    """Role used for profile visibility: merchant tokens see what the demo sees."""
    return "demo" if principal["role"] in LIMITED_ROLES else principal["role"]


OPERATOR_FORBIDDEN = "Operators and services act only on the merchant of a handoff case, never on their own."


def operator_forbidden(request: Request, principal: dict) -> JSONResponse | None:
    """Operators and services have no merchant of their own: attendance routes refuse them (spec v0.7.0)."""
    if principal["role"] in ("operator", "service"):
        return insufficient_scope(request, OPERATOR_FORBIDDEN)
    return None


TOKEN_FORM = {
    "requestBody": {
        "required": True,
        "content": {
            "application/x-www-form-urlencoded": {
                "schema": {
                    "type": "object",
                    "required": ["grant_type"],
                    "properties": {
                        "grant_type": {"type": "string", "enum": ["password", "client_credentials"]},
                        "username": {"type": "string"},
                        "password": {"type": "string", "format": "password"},
                        "client_id": {"type": "string"},
                        "client_secret": {"type": "string", "format": "password"},
                        "scope": {"type": "string"},
                    },
                }
            }
        },
    }
}


NO_STORE = {"Cache-Control": "no-store", "Pragma": "no-cache"}


class OAuthError(BaseModel):
    """RFC 6749 §5.2 error body, used only by the token endpoint."""

    error: Literal["invalid_request", "invalid_client", "invalid_grant", "unsupported_grant_type", "rate_limited"]
    error_description: str


def _token_error(status: int, code: str, description: str, headers: dict[str, str] | None = None) -> JSONResponse:
    extra = {"WWW-Authenticate": 'Basic realm="merchant-assistant"'} if code == "invalid_client" else {}
    return JSONResponse(
        status_code=status,
        content={"error": code, "error_description": description},
        headers=NO_STORE | extra | (headers or {}),
    )


def _basic_client(request: Request) -> tuple[str, str] | None:
    header = request.headers.get("authorization", "")
    if not header.startswith("Basic "):
        return None
    try:
        decoded = base64.b64decode(header[6:].strip()).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return None
    client_id, sep, secret = decoded.partition(":")
    return (unquote_plus(client_id), unquote_plus(secret)) if sep else None


@router.post(
    "/auth/token",
    openapi_extra=TOKEN_FORM,
    responses={400: {"model": OAuthError}, 401: {"model": OAuthError}, 429: {"model": OAuthError}},
    tags=["auth"],
)
async def auth_token(request: Request):
    """OAuth 2.0 token endpoint (RFC 6749, form encoded). `password` for the synthetic demo users and
    `client_credentials` for services. The response is `{access_token, token_type, expires_in, scope}`; a failure
    never says which field was wrong."""
    body = (await request.body()).decode("utf-8", errors="replace")
    form = {key: values[0] for key, values in parse_qs(body, keep_blank_values=True).items()}
    grant = form.get("grant_type", "")
    if grant == "password":
        client_id = form.get("client_id") or DEFAULT_PUBLIC_CLIENT
        subject, secret = form.get("username", ""), form.get("password", "")
        account = f"user:{subject}"
    elif grant == "client_credentials":
        client_id, secret = _basic_client(request) or (form.get("client_id", ""), form.get("client_secret", ""))
        subject, account = client_id, f"client:{client_id}"
    elif not grant:
        return _token_error(400, "invalid_request", "The request is missing a required parameter.")
    else:
        return _token_error(400, "unsupported_grant_type", "Use password or client_credentials.")
    if not subject or not secret:
        return _token_error(400, "invalid_request", "The request is missing a required parameter.")
    if grant == "password" and client_id not in PUBLIC_CLIENTS:
        return _token_error(401, "invalid_client", "Client authentication failed.")
    settings: Settings = request.app.state.settings
    identity = request.app.state.identity
    conn = _db(request)
    try:
        # D19: attempts per account and client address, counted before any password hashing.
        address = request.client.host if request.client else "unknown"
        waits = [
            hit_rate_limit(conn, f"auth:{account}@{address}", settings.auth_attempts_per_minute),
            hit_rate_limit(conn, f"auth-ip:{address}", settings.auth_attempts_per_ip_per_minute),  # spraying
        ]
        retry_after = max((w for w in waits if w is not None), default=None)
        if retry_after is not None:
            return _token_error(
                429, "rate_limited", "Too many attempts; retry later.", headers={"Retry-After": str(retry_after)}
            )
        if grant == "password":
            principal = identity.authenticate(conn, account, secret)
            if principal is None:
                return _token_error(400, "invalid_grant", "Invalid username or password.")
        else:
            principal = identity.authenticate(conn, account, secret) if client_id in SERVICE_CLIENTS else None
            if principal is None:
                return _token_error(401, "invalid_client", "Client authentication failed.")
        remember_principal(conn, principal)
    finally:
        conn.close()
    return JSONResponse(identity.issue(principal, client_id), headers=NO_STORE)


@router.post("/auth/revoke", tags=["auth"], responses={401: {"model": ErrorBody}})
def auth_revoke(request: Request, principal=AUTH):
    """Revokes the presented token (its `jti`) until it expires (RFC 7009 style: `200` with an empty body)."""
    if _ensure_not_error(principal):
        return principal
    conn = _db(request)
    try:
        request.app.state.identity.revoke(conn, principal["_claims"])
    finally:
        conn.close()
    return Response(status_code=200)


@router.get("/catalog/models", response_model=ModelCatalogResponse)
def model_catalog(request: Request, principal=READER):
    if _ensure_not_error(principal):
        return principal
    price_data = json.loads((Path(__file__).parents[1] / "llm" / "prices.json").read_text(encoding="utf-8"))
    models = []
    for item in CATALOG.values():
        price = price_data["models"].get(item["model"])
        if price is None:
            continue
        parameters = {
            name: {
                **definition,
                "maximum_by_agent": {
                    agent: maximum
                    for agent, maximum in definition["maximum_by_agent"].items()
                    if agent in item["agents"]
                },
            }
            for name, definition in item.get("parameters", {}).items()
        }
        models.append(
            {
                **item,
                "agents": list(item["agents"]),
                "capabilities": list(item["capabilities"]),
                "parameters": parameters,
                "price": {k: v for k, v in price.items() if k not in ("provider", "tier", "model_version")},
                "price_tier": price.get("tier"),
                "model_version": price.get("model_version", item["model"]),
            }
        )
    return {"models": models, "verified_at": price_data["verified_at"], "sources": price_data["sources"]}


@router.get("/profiles")
def profiles(request: Request, principal=READER):
    if _ensure_not_error(principal):
        return principal
    conn = _db(request)
    try:
        return {"profiles": list_profiles(conn, role=profile_role(principal))}
    finally:
        conn.close()


def _kb(request: Request):
    service = getattr(request.app.state.orchestrator, "knowledge_base", None)
    if service is None:
        return None
    return service


@router.get("/kb/documents")
def kb_documents(request: Request, principal=READER):
    if _ensure_not_error(principal):
        return principal
    service = _kb(request)
    return (
        service.list_documents(admin=principal["role"] == "admin")
        if service
        else _error(503, "kb_unavailable", "Knowledge base is unavailable.", request)
    )


@router.get("/kb/documents/{document_id}")
def kb_document(document_id: str, request: Request, principal=READER):
    if _ensure_not_error(principal):
        return principal
    try:
        return _kb(request).document(document_id, admin=principal["role"] == "admin")
    except LookupError:
        return _error(404, "not_found", "Document not found.", request)


@router.put("/kb/drafts/{document_id}")
def kb_save_draft(document_id: str, payload: KBDraftRequest, request: Request, principal=ADMIN):
    if _ensure_not_error(principal):
        return principal
    try:
        return _kb(request).save_draft(document_id, payload.content, payload.expected_revision)
    except LookupError:
        return _error(404, "not_found", "Document not found.", request)
    except PermissionError:
        return _error(403, "source_read_only", "Official source documents are read-only.", request)
    except RuntimeError:
        return _error(409, "version_conflict", "Draft revision changed; reload before saving.", request)
    except ValueError as exc:
        return _error(422, "invalid_document", str(exc), request)


@router.get("/kb/drafts/{document_id}/diff")
def kb_diff(document_id: str, request: Request, principal=ADMIN):
    if _ensure_not_error(principal):
        return principal
    try:
        return _kb(request).diff(document_id)
    except LookupError:
        return _error(404, "not_found", "Draft not found.", request)


@router.post("/kb/versions/estimate")
def kb_estimate(payload: KBEstimateRequest, request: Request, principal=ADMIN):
    if _ensure_not_error(principal):
        return principal
    try:
        return _kb(request).estimate(payload.revisions)
    except LookupError:
        return _error(404, "not_found", "Document not found.", request)
    except RuntimeError:
        return _error(409, "version_conflict", "Draft revision changed; reload the estimate.", request)
    except Exception:
        return _error(503, "estimate_unavailable", "Could not estimate this candidate.", request)


@router.post("/kb/versions", status_code=201)
def kb_build(payload: KBBuildRequest, request: Request, principal=ADMIN):
    if _ensure_not_error(principal):
        return principal
    try:
        return _kb(request).create_version(
            payload.revisions,
            payload.expected_active_version_id,
            payload.expected_digest,
            payload.confirmed,
            payload.max_cost_usd,
        )
    except BudgetExceeded:
        return _error(429, "budget_exceeded", "The candidate exceeds the confirmed budget.", request)
    except LookupError:
        return _error(404, "not_found", "Document not found.", request)
    except KBBuildFailure:
        return _error(503, "candidate_build_failed", "Candidate build failed; active version was preserved.", request)
    except RuntimeError as exc:
        return _error(409, "version_conflict", str(exc), request)
    except Exception:
        return _error(503, "candidate_build_failed", "Candidate build failed; active version was preserved.", request)


@router.get("/kb/versions")
def kb_versions(request: Request, principal=READER):
    if _ensure_not_error(principal):
        return principal
    return _kb(request).versions(admin=principal["role"] == "admin")


@router.get("/kb/versions/{version_id}")
def kb_version(version_id: str, request: Request, principal=READER):
    if _ensure_not_error(principal):
        return principal
    try:
        return _kb(request).version(version_id, admin=principal["role"] == "admin")
    except LookupError:
        return _error(404, "not_found", "Version not found.", request)


@router.post("/kb/versions/{version_id}/test")
def kb_test(version_id: str, payload: KBTestRequest, request: Request, principal=ADMIN):
    if _ensure_not_error(principal):
        return principal
    try:
        return _kb(request).test_version(version_id, confirmed=payload.confirmed, max_cost_usd=payload.max_cost_usd)
    except BudgetExceeded:
        return _error(429, "budget_exceeded", "The test exceeds the confirmed budget.", request)
    except (LookupError, RuntimeError):
        return _error(409, "version_not_testable", "This version is not ready to test.", request)
    except ValueError:
        return _error(422, "confirmation_required", "Explicit confirmation is required.", request)


@router.post("/kb/versions/{version_id}/activate")
def kb_activate(version_id: str, payload: KBTransitionRequest, request: Request, principal=ADMIN):
    if _ensure_not_error(principal):
        return principal
    try:
        return _kb(request).transition(
            version_id,
            action="activate",
            expected_active=payload.expected_active_version_id,
            confirmed=payload.confirmed,
            actor=principal["principal_id"],
        )
    except (LookupError, RuntimeError):
        return _error(409, "version_conflict", "Version is not activatable or the active version changed.", request)
    except ValueError:
        return _error(422, "confirmation_required", "Explicit confirmation is required.", request)


@router.post("/kb/versions/{version_id}/rollback")
def kb_rollback(version_id: str, payload: KBTransitionRequest, request: Request, principal=ADMIN):
    if _ensure_not_error(principal):
        return principal
    try:
        return _kb(request).transition(
            version_id,
            action="rollback",
            expected_active=payload.expected_active_version_id,
            confirmed=payload.confirmed,
            actor=principal["principal_id"],
        )
    except (LookupError, RuntimeError):
        return _error(409, "version_conflict", "Version is not the intact previous version or active changed.", request)
    except ValueError:
        return _error(422, "confirmation_required", "Explicit confirmation is required.", request)


@router.post("/profiles", status_code=201)
def profiles_create(payload: ProfileCreateRequest, request: Request, principal=ADMIN):
    if _ensure_not_error(principal):
        return principal
    conn = _db(request)
    try:
        conn.execute("BEGIN IMMEDIATE")
        result = create_draft(conn, payload.name, payload.agents, demo_allowed=payload.demo_allowed)
        conn.execute("COMMIT")
        return result
    except ValueError as exc:
        conn.execute("ROLLBACK")
        return _error(422, "incompatible_profile", str(exc), request)
    finally:
        conn.close()


@router.put("/profiles/{profile_id}/draft")
def profiles_update(profile_id: str, payload: ProfileDraftRequest, request: Request, principal=ADMIN):
    if _ensure_not_error(principal):
        return principal
    conn = _db(request)
    try:
        conn.execute("BEGIN IMMEDIATE")
        result = update_draft(conn, profile_id, payload.expected_version, payload.agents)
        conn.execute("COMMIT")
        return result
    except LookupError:
        conn.execute("ROLLBACK")
        return _error(404, "not_found", "Profile not found.", request)
    except PermissionError as exc:
        conn.execute("ROLLBACK")
        return _error(409, "immutable_profile", str(exc), request)
    except RuntimeError as exc:
        conn.execute("ROLLBACK")
        return _error(409, "version_conflict", str(exc), request)
    except ValueError as exc:
        conn.execute("ROLLBACK")
        return _error(422, "incompatible_profile", str(exc), request)
    finally:
        conn.close()


@router.post("/profiles/{profile_id}/publish")
def profiles_publish(profile_id: str, payload: PublishRequest, request: Request, principal=ADMIN):
    if _ensure_not_error(principal):
        return principal
    conn = _db(request)
    try:
        conn.execute("BEGIN IMMEDIATE")
        result = publish(conn, profile_id, payload.expected_version)
        conn.execute("COMMIT")
        return result
    except LookupError:
        conn.execute("ROLLBACK")
        return _error(404, "not_found", "Profile not found.", request)
    except PermissionError as exc:
        conn.execute("ROLLBACK")
        return _error(409, "immutable_profile", str(exc), request)
    except RuntimeError as exc:
        conn.execute("ROLLBACK")
        return _error(409, "version_conflict", str(exc), request)
    except ValueError as exc:
        conn.execute("ROLLBACK")
        return _error(422, "incompatible_profile", str(exc), request)
    finally:
        conn.close()


def _router_spec(request: Request, message: str, history: list[dict], case: dict) -> CallSpec:
    settings: Settings = request.app.state.settings
    from merchant_assistant.llm.prompts import load_prompt

    p = load_prompt(settings.prompts_dir, "router")
    return CallSpec(
        agent="router",
        instructions=p.render(),
        input=(
            f"Conversation so far (oldest first):\n{format_history(history)}\n\n"
            f"Current case: state={case.get('state', 'in_progress')}, topic={case.get('topic')}\n\n"
            f"Merchant message:\n<<<\n{message}\n>>>"
        ),
        effort="none",
        max_output_tokens=300,
        context={"message": message, "history": history, "case": case},
    )


def _read_conversation(
    conn: sqlite3.Connection, conversation_id: str | None, customer_id: str, clock: SystemClock
) -> tuple[list[dict], dict, str]:
    if not conversation_id:
        state = {"conversation_id": None, "customer_id": customer_id, "state": "in_progress", "topic": None}
        return [], state, digest(state)
    row = conn.execute("SELECT * FROM conversations WHERE conversation_id=?", (conversation_id,)).fetchone()
    if row is None:
        state = {"conversation_id": conversation_id, "customer_id": customer_id, "state": "in_progress", "topic": None}
        return [], state, digest(state)
    if row["customer_id"] != customer_id:
        raise ConversationNotFound(conversation_id)
    store = ConversationStore(conn, clock)
    history = store.history(conversation_id)
    state = {
        "conversation_id": conversation_id,
        "customer_id": customer_id,
        "state": row["state"],
        "topic": row["topic"],
        "technical_cycles": row["technical_cycles"],
        "updated_at": row["updated_at"],
        "history": history,
    }
    return history, state, digest(state)


def _new_context(
    request: Request, conn: sqlite3.Connection, request_id: str, customer_id: str, models: dict, principal: dict
):
    orchestrator = request.app.state.orchestrator
    clock = SystemClock(request.app.state.settings.timezone)
    known = conn.execute("SELECT 1 FROM customers WHERE customer_id=?", (customer_id,)).fetchone() is not None
    context = RunContext(
        request_id=request_id,
        settings=request.app.state.settings,
        llm=orchestrator.llm,
        index=orchestrator.index,
        budget=orchestrator.budget,
        trace=TraceRecorder(request_id),
        tools=ToolEnv(
            conn,
            clock,
            CustomerContext.for_principal(Principal.from_session(principal), customer_id, known),
            dict(orchestrator.faults),
            orchestrator.mock_services,
        ),
        clock=clock,
        agent_llms={"router": orchestrator._profile_llm("router", models["router"])},
    )
    return context, clock


def _decision(request: Request, context: RunContext, spec: CallSpec, mechanism: str, models: dict) -> dict:
    config = {"provider": "typesafe", "model": "jev-1.14.0"} if mechanism == "jev" else models["router"]
    llm = request.app.state.orchestrator._profile_llm("router", config)
    before = context.cost_usd
    result = llm.parse(spec, RouterDecision, context)
    decision = enforce(result.value, new_conversation=not spec.context.get("history"))
    parameters_for = getattr(llm, "effective_parameters_for", None)
    if callable(parameters_for):
        effective_parameters = parameters_for(spec)
    else:
        effective_parameters = (
            {"max_output_tokens": spec.max_output_tokens} if config.get("provider") in {"openai", "deepseek"} else {}
        )
    return {
        "decision": decision.model_dump(),
        "model": result.model,
        "usage": result.usage.__dict__,
        "cost_estimate_usd": round(context.cost_usd - before, 8),
        "effective_parameters": dict(effective_parameters),
    }


@router.post("/router/compare", status_code=201, responses={429: {"model": ErrorBody}})
def compare(payload: CompareRequest, request: Request, principal=READER):
    if _ensure_not_error(principal):
        return principal
    if forbidden := operator_forbidden(request, principal):
        return forbidden
    if limited := rate_limited(request, principal):
        return limited
    conn = _db(request)
    request_id = request.state.request_id
    context, consumed = None, False

    def refund_without_calls():
        if consumed and (context is None or context.model_calls == 0):
            refund_demo_messages(conn, principal, 1)

    try:
        bootstrap_profiles(conn)
        profile = get_profile(conn, payload.profile_id, payload.profile_version, role=profile_role(principal))
        if profile is None:
            return _error(404, "not_found", "Profile not found.", request)
        guarded = check_input(payload.message)
        if guarded.blocked:
            return _error(422, "input_blocked", "This message cannot be routed by either mechanism.", request)
        history, state, state_digest = _read_conversation(
            conn,
            payload.conversation_id,
            principal["customer_id"] or "admin",
            SystemClock(request.app.state.settings.timezone),
        )
        spec = _router_spec(request, guarded.masked, history, state)
        if not consume_demo_messages(conn, principal, 1, request.app.state.settings):
            return _error(429, "demo_message_limit_reached", DEMO_LIMIT_MESSAGE, request)
        consumed = True
        context, _ = _new_context(
            request, conn, request_id, principal["customer_id"] or "admin", profile["agents"], principal
        )
        started = time.perf_counter()
        llm_result = _decision(request, context, spec, "llm", profile["agents"])
        jev_result = _decision(request, context, spec, "jev", profile["agents"])
        comparison_id = f"cmp_{uuid.uuid4().hex}"
        expires = _utc() + COMPARISON_TTL
        decisions = {"llm": llm_result, "jev": jev_result}
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(
            "INSERT INTO router_comparisons VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                comparison_id,
                principal["principal_id"],
                principal["customer_id"] or "admin",
                payload.conversation_id,
                digest(payload.message),
                state_digest,
                payload.profile_id,
                profile["version"],
                payload.selected_mechanism,
                json.dumps(decisions, sort_keys=True),
                expires.isoformat(),
                None,
                _utc().isoformat(),
            ),
        )
        conn.execute("COMMIT")
        execution_mode = "simulated" if type(request.app.state.orchestrator.llm).__name__ == "ScriptedLLM" else "real"
        return {
            "comparison_id": comparison_id,
            "decisions": decisions,
            "selected_mechanism": payload.selected_mechanism,
            "expires_at": expires.isoformat(),
            "execution_mode": execution_mode,
            "duration_ms": int((time.perf_counter() - started) * 1000),
            "cost_estimate_usd": context.cost_usd,
            "estimate_basis": "peak-conservative catalog rate",
        }
    except ConversationNotFound:
        return _error(404, "not_found", "Conversation not found.", request)
    except BudgetExceeded as exc:
        refund_without_calls()
        return _error(
            429,
            f"{exc.scope}_budget_exceeded",
            "Router comparison was blocked by the configured budget; no incomplete comparison was saved.",
            request,
        )
    except RuntimeError:
        refund_without_calls()
        return _error(503, "provider_unavailable", "A configured model provider is unavailable.", request)
    except LLMError:
        return _error(503, "provider_unavailable", "Router provider failed; no fallback was used.", request)
    finally:
        conn.close()


class RunFailure(Exception):
    """A run that cannot be reported as an answer (for example the selected Router failed)."""

    def __init__(self, status: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


def _execution_mode(orchestrator) -> str:
    return "simulated" if type(orchestrator.llm).__name__ == "ScriptedLLM" else "real"


def consume_demo_messages(conn: sqlite3.Connection, principal: dict, count: int, settings: Settings) -> bool:
    """Atomically count `count` paid actions (messages, new comparison executions, Router comparisons and AI
    evaluations) against the demo limit of one access token; False when it would be exceeded. Refusals that make no
    model call are not counted: callers consume only after their validations, and refund when the budget refuses
    first. From v0.7.0 the counter row (`api_sessions`) is keyed by the token's `jti`."""
    if principal["role"] not in LIMITED_ROLES:
        return True
    conn.execute(
        "INSERT OR IGNORE INTO api_sessions(session_id,token_digest,principal_id,created_at,expires_at,revoked_at) "
        "VALUES (?,?,?,?,?,NULL)",
        (
            principal["session_id"],
            _token_digest(f"jti:{principal['session_id']}"),
            principal["principal_id"],
            _utc().isoformat(),
            principal["expires_at"],
        ),
    )
    cursor = conn.execute(
        "UPDATE api_sessions SET message_count=message_count+? WHERE session_id=? AND message_count+?<=?",
        (count, principal["session_id"], count, settings.demo_session_message_limit),
    )
    return cursor.rowcount == 1


def refund_demo_messages(conn: sqlite3.Connection, principal: dict, count: int) -> None:
    """Give back actions counted for a request that ended without any model call (for example a budget refusal)."""
    if principal["role"] in LIMITED_ROLES and count:
        conn.execute(
            "UPDATE api_sessions SET message_count=MAX(message_count-?,0) WHERE session_id=?",
            (count, principal["session_id"]),
        )


def model_calls_made(orchestrator, request_id: str) -> int:
    """Model calls recorded in the trace of a run (informational; 0 when the run left no trace)."""
    trace = orchestrator.trace(request_id)
    return int((trace or {}).get("model_calls") or 0)


def paid_attempts(budget, request_id: str) -> int | None:
    """Paid calls reserved for `request_id` in the persistent ledger (reserved or settled; a cancelled reservation
    never reached the provider). None when the ledger cannot be read: callers then never give an action back."""
    guard = getattr(budget, "primary", budget)  # CombinedBudgetGuard: the primary row exists only after both
    guard = getattr(guard, "guard", guard)  # FixedBudgetGuard wraps a BudgetGuard
    path = getattr(guard, "path", None)
    if not isinstance(path, str) or not path or path == ":memory:":
        return None
    try:
        conn = sqlite3.connect(path, timeout=10)
        try:
            row = conn.execute(
                "SELECT COUNT(*) FROM ledger WHERE request_id=? AND status IN ('reserved','settled')", (request_id,)
            ).fetchone()
        finally:
            conn.close()
    except sqlite3.Error:
        return None
    return int(row[0])


DEMO_LIMIT_MESSAGE = (
    "This demo session reached its limit of paid actions. End the session and start a new one, "
    "or ask the administrator."
)


def execute_run(
    app_state,
    conn: sqlite3.Connection,
    *,
    request_id: str,
    principal: dict,
    customer_id: str,
    profile: dict,
    message: str,
    mechanism: str,
    conversation_id: str | None = None,
    selected: dict | None = None,
    router_comparison_id: str | None = None,
    scenario_id: str | None = None,
    purpose: str = "attendance",
    profile_comparison_id: str | None = None,
    domain_db_path=None,
    knowledge=None,
    history_turns: int = 0,
) -> dict:
    """Run one attendance with a published profile and store its snapshot (shared by messages and comparisons)."""
    from merchant_assistant.llm.prompts import prompt_versions

    orchestrator, settings = app_state.orchestrator, app_state.settings
    actual_models = {name: f"{config['provider']}:{config['model']}" for name, config in profile["agents"].items()}
    if mechanism == "jev":
        actual_models["router"] = "typesafe:jev-1.14.0"
    snapshot = {
        "profile_id": profile["profile_id"],
        "profile_version": profile["version"],
        "profile_digest": profile["digest"],
        "agents": profile["agents"],
        "models": actual_models,
        "router_mechanism": mechanism,
        "prompt_versions": {"router": "router.v5"},
        "prompt_set": prompt_versions(settings.prompts_dir),
        "knowledge_base": "current",
        "execution_mode": _execution_mode(orchestrator),
        "comparison_id": router_comparison_id,
        "scenario_id": scenario_id,
        "purpose": purpose,
        "message": check_input(message).masked,
        "history_turns": history_turns,
        "estimate_basis": "peak-conservative catalog rate",
        "effective_parameters_by_agent": {},
    }
    tags = {"purpose": purpose, "scenario_id": scenario_id}
    if profile_comparison_id:
        snapshot["profile_comparison_id"] = profile_comparison_id
        tags["profile_comparison_id"] = profile_comparison_id
    conn.execute(
        "INSERT INTO run_snapshots VALUES (?,?,?,?,?,?,?)",
        (
            request_id,
            principal["principal_id"],
            customer_id,
            profile["profile_id"],
            profile["version"],
            json.dumps(snapshot, sort_keys=True),
            _utc().isoformat(),
        ),
    )
    # Every agent of the profile is listed: with mechanism "jev" the orchestrator replaces the Router entry by
    # `router_llm` (the TypeSafe adapter), so the Router is never served by the default or the profile LLM (P1-QA-01).
    agent_models = dict(profile["agents"])
    router_llm = (
        orchestrator._profile_llm("router", {"provider": "typesafe", "model": "jev-1.14.0"})
        if mechanism == "jev"
        else None
    )
    response = orchestrator.handle(
        MessageRequest(message=message, user_id=customer_id, conversation_id=conversation_id),
        request_id,
        agent_models=agent_models,
        router_llm=router_llm,
        router_decision=RouterDecision.model_validate(selected["decision"]) if selected else None,
        db_path=domain_db_path,
        knowledge=knowledge,
        trace_tags=tags,
        principal=Principal.from_session(principal),
        channel="web",
    )
    trace_data = orchestrator.trace(request_id)
    if trace_data and any(str(error).startswith("router:") for error in trace_data.get("errors", [])):
        failure = {"code": "router_unavailable", "message": "Router provider failed; no fallback was used."}
        conn.execute(
            "UPDATE run_snapshots SET snapshot=? WHERE request_id=?",
            (json.dumps(snapshot | {"error": failure}, sort_keys=True), request_id),
        )
        raise RunFailure(503, failure["code"], failure["message"])
    result = {"message": response.model_dump(), "run": snapshot}
    if trace_data:
        trace_summary = {
            "duration_ms": trace_data.get("duration_ms"),
            "model_calls": trace_data.get("model_calls"),
            "tool_calls": trace_data.get("tool_calls"),
            "models_by_agent": trace_data.get("detail", {}).get("models_by_agent", {}),
            "effective_parameters_by_agent": trace_data.get("detail", {}).get("effective_parameters_by_agent", {}),
            "tools": trace_data.get("detail", {}).get("tools", []),
            "sources": [source.model_dump() for source in response.sources],
            "cost_estimate_usd": trace_data.get("detail", {}).get("cost_estimate_usd"),
            "cost_estimate_basis": trace_data.get("detail", {}).get("cost_estimate_basis", {}),
            "cost_is_estimate": True,
            "knowledge_base_version_id": trace_data.get("detail", {}).get("knowledge_base_version_id"),
            "knowledge_base_collection": trace_data.get("detail", {}).get("knowledge_base_collection"),
        }
        if selected:
            trace_summary["effective_parameters_by_agent"] = dict(
                trace_summary["effective_parameters_by_agent"] | {"router": selected.get("effective_parameters", {})}
            )
        result["run"].update(trace_summary)
        snapshot.update(trace_summary)
    conn.execute(
        "UPDATE run_snapshots SET snapshot=? WHERE request_id=?",
        (json.dumps(snapshot | {"result": result["message"]}, sort_keys=True), request_id),
    )
    return result


@router.get("/scenarios")
def scenarios_list(request: Request, principal=READER):
    if _ensure_not_error(principal):
        return principal
    data = scenario_catalog.catalog(request.app.state.settings.data_dir)
    return {
        "version": data["version"],
        "scenarios": [scenario_catalog.public_view(item) for item in data["scenarios"].values()],
    }


@router.post("/messages", responses={429: {"model": ErrorBody}})
def messages_v1(payload: V1MessageRequest, request: Request, principal=READER):
    if _ensure_not_error(principal):
        return principal
    if forbidden := operator_forbidden(request, principal):
        return forbidden
    if limited := rate_limited(request, principal):
        return limited
    conn = _db(request)
    request_id = request.state.request_id
    settings: Settings = request.app.state.settings
    try:
        bootstrap_profiles(conn)
        profile = get_profile(conn, payload.profile_id, payload.profile_version, role=profile_role(principal))
        if profile is None:
            return _error(404, "not_found", "Profile not found.", request)
        customer_id = principal["customer_id"]
        if not customer_id:
            return _error(
                422, "admin_scope_required", "Admin sessions require a configured synthetic customer.", request
            )
        if payload.scenario_id is not None:
            scenario = scenario_catalog.get(settings.data_dir, payload.scenario_id)
            if scenario is None:
                return _error(422, "unknown_scenario", "Scenario is not in the catalog; reload the scenarios.", request)
            if scenario["message"] != payload.message:
                return _error(
                    422,
                    "scenario_message_mismatch",
                    "The message differs from the selected scenario; send it as a free message instead.",
                    request,
                )
        history, state, state_digest = _read_conversation(
            conn, payload.conversation_id, customer_id, SystemClock(settings.timezone)
        )
        selected = None
        if not payload.comparison_id and not consume_demo_messages(conn, principal, 1, settings):
            return _error(429, "demo_message_limit_reached", DEMO_LIMIT_MESSAGE, request)
        if payload.comparison_id:
            conn.execute("BEGIN IMMEDIATE")
            comp = conn.execute(
                "SELECT * FROM router_comparisons WHERE comparison_id=? AND principal_id=?",
                (payload.comparison_id, principal["principal_id"]),
            ).fetchone()
            if (
                comp is None
                or comp["consumed_at"]
                or datetime.fromisoformat(comp["expires_at"]) <= _utc()
                or comp["message_digest"] != digest(payload.message)
                or comp["state_digest"] != state_digest
                or comp["profile_id"] != payload.profile_id
                or comp["profile_version"] != payload.profile_version
                or comp["selected_mechanism"] != payload.router_mechanism
                or comp["conversation_id"] != payload.conversation_id
            ):
                conn.execute("ROLLBACK")
                return _error(409, "comparison_conflict", "Comparison is stale, mismatched, or already used.", request)
            if not consume_demo_messages(conn, principal, 1, settings):  # same transaction: nothing is consumed
                conn.execute("ROLLBACK")
                return _error(429, "demo_message_limit_reached", DEMO_LIMIT_MESSAGE, request)
            decisions = json.loads(comp["decisions"])
            selected = decisions[payload.router_mechanism]
            conn.execute(
                "UPDATE router_comparisons SET consumed_at=? WHERE comparison_id=? AND consumed_at IS NULL",
                (_utc().isoformat(), payload.comparison_id),
            )
            conn.execute("COMMIT")
        try:
            return execute_run(
                request.app.state,
                conn,
                request_id=request_id,
                principal=principal,
                customer_id=customer_id,
                profile=profile,
                message=payload.message,
                mechanism=payload.router_mechanism,
                conversation_id=payload.conversation_id,
                selected=selected,
                router_comparison_id=payload.comparison_id,
                scenario_id=payload.scenario_id,
                history_turns=len(history),
            )
        except RunFailure as exc:
            return _error(exc.status, exc.code, exc.message, request)
        finally:  # the action was counted above; give it back when the run ended without any model call
            if paid_attempts(request.app.state.orchestrator.budget, request_id) == 0:  # unknown never refunds
                refund_demo_messages(conn, principal, 1)
    except ConversationNotFound:
        return _error(404, "not_found", "Conversation not found.", request)
    except RuntimeError:
        return _error(503, "provider_unavailable", "A configured model provider is unavailable.", request)
    except (LLMError, ValueError):
        return _error(503, "provider_unavailable", "The selected model could not complete the request.", request)
    finally:
        conn.close()


STEP_DETAIL_FIELDS = ("prompt", "mode", "hits", "citations", "agent", "arguments", "topic", "tools", "failed", "reused")


def _steps(trace: dict | None) -> list[dict]:
    if not trace:
        return []
    steps = []
    for step in trace.get("steps", []):
        detail = step.get("detail") or {}
        steps.append(
            {
                "seq": step["seq"],
                "step": step["step"],
                "status": step["status"],
                "duration_ms": step["duration_ms"],
                **{key: detail[key] for key in STEP_DETAIL_FIELDS if key in detail},
            }
        )
    return steps


def _owned_snapshot(conn: sqlite3.Connection, request_id: str, principal: dict) -> dict | None:
    row = conn.execute(
        "SELECT * FROM run_snapshots WHERE request_id=? AND principal_id=?", (request_id, principal["principal_id"])
    ).fetchone()
    return (json.loads(row["snapshot"]) | {"_customer_id": row["customer_id"]}) if row else None


def run_checks(app_state, conn: sqlite3.Connection, request_id: str, snapshot: dict, principal: dict) -> dict:
    """Deterministic checks for a persisted run: scenario labels when present, label-independent otherwise."""
    from merchant_assistant.evaluation.runner import persisted_checks

    customer_id = snapshot.get("_customer_id") or principal.get("customer_id")
    markers = [
        value
        for row in conn.execute("SELECT customer_id,display_name FROM customers WHERE customer_id<>?", (customer_id,))
        for value in (row["customer_id"], row["display_name"])
    ]
    scenario_id = snapshot.get("scenario_id")
    scenario = scenario_catalog.get(app_state.settings.data_dir, scenario_id) if scenario_id else None
    case = scenario_catalog.as_case(scenario, customer_id) if scenario else None
    return persisted_checks(
        snapshot.get("result"), app_state.orchestrator.trace(request_id), case, foreign_markers=markers
    )


def list_evaluations(conn: sqlite3.Connection, request_id: str, principal: dict) -> list[dict]:
    from merchant_assistant.evaluation import on_demand

    return on_demand.list_for(conn, request_id, principal["principal_id"])


@router.get("/runs/{request_id}")
def run(request_id: str, request: Request, principal=READER):
    if _ensure_not_error(principal):
        return principal
    conn = _db(request)
    try:
        snapshot = _owned_snapshot(conn, request_id, principal)
        if snapshot is None:
            return _error(404, "not_found", "Run not found.", request)
        trace = request.app.state.orchestrator.trace(request_id)
        snapshot["checks"] = run_checks(request.app.state, conn, request_id, snapshot, principal)
        snapshot["evaluations"] = list_evaluations(conn, request_id, principal)
        snapshot["steps"] = _steps(trace)
        snapshot["route"] = (snapshot.get("result") or {}).get("route")
        snapshot["prompts_used"] = sorted({step["prompt"] for step in snapshot["steps"] if step.get("prompt")})
        snapshot.pop("_customer_id", None)
        return snapshot
    finally:
        conn.close()


@router.post("/runs/{request_id}/evaluations/estimate")
def evaluation_estimate(request_id: str, request: Request, principal=READER):
    from merchant_assistant.evaluation import on_demand
    from merchant_assistant.llm.pricing import PriceUnknown

    if _ensure_not_error(principal):
        return principal
    conn = _db(request)
    try:
        snapshot = _owned_snapshot(conn, request_id, principal)
        if snapshot is None:
            return _error(404, "not_found", "Run not found.", request)
        if "result" not in snapshot:
            return _error(409, "run_not_evaluable", "This run has no persisted reply to evaluate.", request)
        return on_demand.estimate(request.app.state, conn, request_id, snapshot, principal)
    except PriceUnknown:
        return _error(503, "evaluator_price_unknown", "The evaluator price is unknown; evaluation is blocked.", request)
    finally:
        conn.close()


@router.post("/runs/{request_id}/evaluations", status_code=201, responses={429: {"model": ErrorBody}})
def evaluation_create(request_id: str, payload: EvaluationRequest, request: Request, principal=READER):
    from merchant_assistant.evaluation import on_demand
    from merchant_assistant.llm.pricing import PriceUnknown

    if _ensure_not_error(principal):
        return principal
    if limited := rate_limited(request, principal):
        return limited
    conn = _db(request)
    try:
        snapshot = _owned_snapshot(conn, request_id, principal)
        if snapshot is None:
            return _error(404, "not_found", "Run not found.", request)
        if "result" not in snapshot:
            return _error(409, "run_not_evaluable", "This run has no persisted reply to evaluate.", request)
        status, body = on_demand.evaluate(
            request.app.state,
            conn,
            request_id,
            snapshot,
            principal,
            confirmed=payload.confirmed,
            max_cost_usd=payload.max_cost_usd,
            expected_digest=payload.expected_estimate_digest,
            repeat=payload.repeat,
        )
        if status >= 400:
            return _error(status, body["code"], body["message"], request)
        return JSONResponse(status_code=status, content=body)
    except PriceUnknown:
        return _error(503, "evaluator_price_unknown", "The evaluator price is unknown; evaluation is blocked.", request)
    finally:
        conn.close()


@router.post("/comparisons/estimate")
def comparison_estimate(payload: ComparisonEstimateRequest, request: Request, principal=READER):
    if _ensure_not_error(principal):
        return principal
    conn = _db(request)
    try:
        bootstrap_profiles(conn)
        return comparisons.plan(request.app.state, conn, principal, payload.model_dump())
    except comparisons.ComparisonError as exc:
        return _error(exc.status, exc.code, exc.message, request)
    finally:
        conn.close()


@router.post("/comparisons", status_code=202, responses={429: {"model": ErrorBody}})
def comparison_create(payload: ComparisonCreateRequest, request: Request, principal=READER):
    if _ensure_not_error(principal):
        return principal
    if limited := rate_limited(request, principal):
        return limited
    if not principal["customer_id"]:
        return _error(422, "admin_scope_required", "Admin sessions require a configured synthetic customer.", request)
    selection = payload.model_dump(exclude={"confirmed", "max_cost_usd", "expected_estimate_digest"})
    try:
        comparison_id = comparisons.start(
            request.app,
            principal,
            selection,
            confirmed=payload.confirmed,
            max_cost_usd=payload.max_cost_usd,
            expected_digest=payload.expected_estimate_digest,
        )
    except comparisons.ComparisonError as exc:
        return _error(exc.status, exc.code, exc.message, request)
    return JSONResponse(status_code=202, content={"comparison_id": comparison_id, "state": "running"})


@router.get("/comparisons/{comparison_id}")
def comparison_read(comparison_id: str, request: Request, principal=READER):
    if _ensure_not_error(principal):
        return principal
    conn = _db(request)
    try:
        return comparisons.read(request.app.state, conn, principal, comparison_id)
    except comparisons.ComparisonError as exc:
        return _error(exc.status, exc.code, exc.message, request)
    finally:
        conn.close()


@router.get("/conversations/{conversation_id}")
def conversation(conversation_id: str, request: Request, principal=AUTH):
    if _ensure_not_error(principal):
        return principal
    principal = acting_merchant(request, principal)
    if not principal["customer_id"]:
        return insufficient_scope(request, "Conversation is outside this token's scope.")
    conn = _db(request)
    try:
        row = conn.execute(
            "SELECT * FROM conversations WHERE conversation_id=? AND customer_id=?",
            (conversation_id, principal["customer_id"]),
        ).fetchone()
        if row is None:
            return _error(404, "not_found", "Conversation not found.", request)
        return ConversationStore(conn, SystemClock(request.app.state.settings.timezone)).get(conversation_id)
    finally:
        conn.close()


# --- operator queue (task 64) -------------------------------------------------------------------------------------


class HandoffActionRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [{"action": "reply", "text": "Your payout was sent today.", "idempotency_key": "ui-7f3a9c21"}]
        },
    )
    action: Literal["approve", "reply", "reject"]
    text: str | None = Field(
        default=None, max_length=4000, description="Reply text (reply) or instruction to the agent (reject)."
    )
    idempotency_key: str = Field(pattern=r"^[A-Za-z0-9_-]{8,80}$")


def _operator_id(
    request: Request, principal: dict | JSONResponse, tool: str, case_id: str | None = None
) -> str | JSONResponse:
    """Queue routes need an operator token with `handoff:operate`; the operator id comes from the token. A refusal at
    this gate is audited (D23)."""
    if isinstance(principal, JSONResponse):
        return principal
    if principal["role"] != "operator" or HANDOFF_OPERATE not in principal["scopes"]:
        conn = _db(request)
        try:
            handoffs.audit_access(conn, tool, "insufficient_scope", principal["principal_id"], case_id)
        finally:
            conn.close()
        return insufficient_scope(request, "The operator queue requires the handoff:operate scope.")
    return principal["principal_id"].split(":", 1)[1]


def _handoff_error(request: Request, exc: handoffs.HandoffError) -> JSONResponse:
    return _error(exc.status, exc.code, exc.message, request)


@router.get("/handoffs", tags=["handoffs"], responses={403: {"model": ErrorBody}})
def handoffs_list(request: Request, state: str | None = None, principal=AUTH):
    """Operator queue, newest first; `state` = open, claimed, answered, rejected or closed."""
    operator = _operator_id(request, principal, "handoff.list")
    if isinstance(operator, JSONResponse):
        return operator
    conn = _db(request)
    try:
        return {"cases": handoffs.list_cases(conn, state, actor=principal["principal_id"])}
    except handoffs.HandoffError as exc:
        return _handoff_error(request, exc)
    finally:
        conn.close()


@router.get("/handoffs/{case_id}", tags=["handoffs"], responses={403: {"model": ErrorBody}, 404: {"model": ErrorBody}})
def handoffs_show(case_id: str, request: Request, principal=AUTH):
    """Summary, pending question, draft, masked conversation, events and deliveries of one case."""
    operator = _operator_id(request, principal, "handoff.read", case_id)
    if isinstance(operator, JSONResponse):
        return operator
    conn = _db(request)
    try:
        return handoffs.get_case(conn, case_id, actor=principal["principal_id"])
    except handoffs.HandoffError as exc:
        return _handoff_error(request, exc)
    finally:
        conn.close()


@router.post(
    "/handoffs/{case_id}/claim",
    tags=["handoffs"],
    responses={
        403: {"model": ErrorBody},
        404: {"model": ErrorBody},
        409: {"model": ErrorBody},
        429: {"model": ErrorBody},
    },
)
def handoffs_claim(case_id: str, request: Request, principal=AUTH):
    """Claims the case for the operator of the token (D9). Claiming one's own case again is idempotent."""
    operator = _operator_id(request, principal, "handoff.claim", case_id)
    if isinstance(operator, JSONResponse):
        return operator
    if limited := rate_limited(request, principal):
        return limited
    conn = _db(request)
    try:
        return handoffs.claim(conn, case_id, operator, actor=principal["principal_id"])
    except handoffs.HandoffError as exc:
        return _handoff_error(request, exc)
    finally:
        conn.close()


@router.post(
    "/handoffs/{case_id}/actions",
    tags=["handoffs"],
    responses={
        403: {"model": ErrorBody},
        404: {"model": ErrorBody},
        409: {"model": ErrorBody},
        422: {"model": ErrorBody},
        429: {"model": ErrorBody},
    },
)
def handoffs_act(case_id: str, payload: HandoffActionRequest, request: Request, principal=AUTH):
    """`approve`, `reply` or `reject` (D9, D10, D14). The same `idempotency_key` returns the stored record with
    `replayed: true`; a case already resumed by another action is `409 already_resumed`."""
    operator = _operator_id(request, principal, f"handoff.{payload.action}", case_id)
    if isinstance(operator, JSONResponse):
        return operator
    if limited := rate_limited(request, principal):
        return limited
    conn = _db(request)
    try:
        return handoffs.act(
            conn,
            case_id,
            operator,
            payload.action,
            payload.text,
            payload.idempotency_key,
            actor=principal["principal_id"],
            resume=getattr(request.app.state.orchestrator, "resume_handoff", None),
        )
    except handoffs.HandoffError as exc:
        return _handoff_error(request, exc)
    finally:
        conn.close()
