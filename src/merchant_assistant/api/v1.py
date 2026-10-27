"""Authenticated versioned API for the Streamlit interface."""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import sqlite3
import time
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, Depends, Header, Request, Security
from fastapi.responses import JSONResponse, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field, SecretStr

from merchant_assistant.agents.common import format_history
from merchant_assistant.agents.router import enforce
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
from merchant_assistant.tools.base import CustomerContext, ToolEnv

router = APIRouter(prefix="/v1", tags=["v1"])
SESSION_TTL = timedelta(minutes=60)
COMPARISON_TTL = timedelta(minutes=5)


class SessionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    access_key: SecretStr


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


def _db(request: Request) -> sqlite3.Connection:
    return connect(request.app.state.settings.db_path)


def _utc() -> datetime:
    return datetime.now(UTC)


def _token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _error(status: int, code: str, message: str, request: Request) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "req_unknown")
    return JSONResponse(
        status_code=status, content={"error": {"code": code, "message": message, "request_id": request_id}}
    )


def _principal(request: Request, authorization: str | None = Header(default=None)) -> dict | JSONResponse:
    if not authorization or not authorization.startswith("Bearer "):
        return _error(401, "session_required", "A valid session is required.", request)
    token = authorization[7:].strip()
    if not token or len(token) > 256:
        return _error(401, "session_invalid", "Session is invalid or expired.", request)
    conn = _db(request)
    try:
        row = conn.execute(
            "SELECT p.principal_id,p.role,p.customer_id,s.session_id,s.expires_at,s.revoked_at "
            "FROM api_sessions s JOIN api_principals p USING(principal_id) WHERE s.token_digest=? AND p.active=1",
            (_token_digest(token),),
        ).fetchone()
    finally:
        conn.close()
    if row is None or row["revoked_at"] or datetime.fromisoformat(row["expires_at"]) <= _utc():
        return _error(401, "session_invalid", "Session is invalid or expired.", request)
    return dict(row)


def _require(request: Request, roles: tuple[str, ...] = ("demo", "admin")):
    principal = _principal(request)
    if isinstance(principal, JSONResponse):
        return principal
    if principal["role"] not in roles:
        return _error(403, "forbidden", "This action is not allowed for this session.", request)
    return principal


bearer_scheme = HTTPBearer(auto_error=False, scheme_name="SessionBearer")
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


AUTH = Depends(_auth_dep)
ADMIN = Depends(_admin_dep)


def _require_header(request: Request, authorization: str | None, roles: tuple[str, ...]):
    principal = _principal(request, authorization)
    if isinstance(principal, JSONResponse):
        return principal
    if principal["role"] not in roles:
        return _error(403, "forbidden", "This action is not allowed for this session.", request)
    return principal


def _ensure_not_error(principal: dict | JSONResponse):
    return isinstance(principal, JSONResponse)


@router.post("/sessions", status_code=201)
def create_session(payload: SessionRequest, request: Request):
    settings: Settings = request.app.state.settings
    supplied = payload.access_key.get_secret_value()
    configured = [
        ("admin", settings.api_admin_access_key),
        ("demo", settings.api_demo_access_key),
    ]
    matches = [
        (role, secret.get_secret_value())
        for role, secret in configured
        if secret and hmac.compare_digest(supplied, secret.get_secret_value())
    ]
    if len(matches) != 1:
        return _error(401, "invalid_access_key", "Access key is invalid or unavailable.", request)
    role, clear_key = matches[0]
    principal_id = f"{role}:default"
    customer_id = settings.api_demo_customer_id
    stamp = _utc()
    token, session_id = secrets.token_urlsafe(32), f"ses_{uuid.uuid4().hex}"
    expires = stamp + SESSION_TTL
    conn = _db(request)
    try:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(
            "INSERT INTO api_principals(principal_id,role,customer_id,access_key_digest,active) VALUES(?,?,?,?,1) "
            "ON CONFLICT(principal_id) DO UPDATE SET role=excluded.role,customer_id=excluded.customer_id,"
            "access_key_digest=excluded.access_key_digest,active=1",
            (principal_id, role, customer_id, _token_digest(clear_key)),
        )
        conn.execute(
            "INSERT INTO api_sessions VALUES (?,?,?,?,?,NULL)",
            (session_id, _token_digest(token), principal_id, stamp.isoformat(), expires.isoformat()),
        )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()
    return {"access_token": token, "token_type": "bearer", "expires_at": expires.isoformat(), "role": role}


@router.delete("/sessions/current", status_code=204)
def revoke_session(request: Request, principal=AUTH):
    if _ensure_not_error(principal):
        return principal
    conn = _db(request)
    try:
        conn.execute(
            "UPDATE api_sessions SET revoked_at=? WHERE session_id=?", (_utc().isoformat(), principal["session_id"])
        )
    finally:
        conn.close()
    return Response(status_code=204)


@router.get("/catalog/models", response_model=ModelCatalogResponse)
def model_catalog(request: Request, principal=AUTH):
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
def profiles(request: Request, principal=AUTH):
    if _ensure_not_error(principal):
        return principal
    conn = _db(request)
    try:
        return {"profiles": list_profiles(conn, role=principal["role"])}
    finally:
        conn.close()


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


def _new_context(request: Request, conn: sqlite3.Connection, request_id: str, customer_id: str, models: dict):
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
            conn, clock, CustomerContext(customer_id, known), dict(orchestrator.faults), orchestrator.mock_services
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
def compare(payload: CompareRequest, request: Request, principal=AUTH):
    if _ensure_not_error(principal):
        return principal
    conn = _db(request)
    request_id = request.state.request_id
    try:
        bootstrap_profiles(conn)
        profile = get_profile(conn, payload.profile_id, payload.profile_version, role=principal["role"])
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
        context, _ = _new_context(request, conn, request_id, principal["customer_id"] or "admin", profile["agents"])
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
        return _error(
            429,
            f"{exc.scope}_budget_exceeded",
            "Router comparison was blocked by the configured budget; no incomplete comparison was saved.",
            request,
        )
    except RuntimeError:
        return _error(503, "provider_unavailable", "A configured model provider is unavailable.", request)
    except LLMError:
        return _error(503, "provider_unavailable", "Router provider failed; no fallback was used.", request)
    finally:
        conn.close()


@router.post("/messages")
def messages_v1(payload: V1MessageRequest, request: Request, principal=AUTH):
    if _ensure_not_error(principal):
        return principal
    conn = _db(request)
    request_id = request.state.request_id
    try:
        bootstrap_profiles(conn)
        profile = get_profile(conn, payload.profile_id, payload.profile_version, role=principal["role"])
        if profile is None:
            return _error(404, "not_found", "Profile not found.", request)
        customer_id = principal["customer_id"]
        if not customer_id:
            return _error(
                422, "admin_scope_required", "Admin sessions require a configured synthetic customer.", request
            )
        history, state, state_digest = _read_conversation(
            conn, payload.conversation_id, customer_id, SystemClock(request.app.state.settings.timezone)
        )
        selected = None
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
            decisions = json.loads(comp["decisions"])
            selected = decisions[payload.router_mechanism]
            conn.execute(
                "UPDATE router_comparisons SET consumed_at=? WHERE comparison_id=? AND consumed_at IS NULL",
                (_utc().isoformat(), payload.comparison_id),
            )
            conn.execute("COMMIT")
        actual_models = {name: f"{config['provider']}:{config['model']}" for name, config in profile["agents"].items()}
        if payload.router_mechanism == "jev":
            actual_models["router"] = "typesafe:jev-1.14.0"
        execution_mode = "simulated" if type(request.app.state.orchestrator.llm).__name__ == "ScriptedLLM" else "real"
        snapshot = {
            "profile_id": profile["profile_id"],
            "profile_version": profile["version"],
            "profile_digest": profile["digest"],
            "agents": profile["agents"],
            "models": actual_models,
            "router_mechanism": payload.router_mechanism,
            "prompt_versions": {"router": "router.v5"},
            "knowledge_base": "current",
            "execution_mode": execution_mode,
            "comparison_id": payload.comparison_id,
            "estimate_basis": "peak-conservative catalog rate",
            "effective_parameters_by_agent": {},
        }
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
        agent_models = {
            key: value
            for key, value in profile["agents"].items()
            if key != "router" or payload.router_mechanism == "llm"
        }
        router_llm = (
            request.app.state.orchestrator._profile_llm("router", {"provider": "typesafe", "model": "jev-1.14.0"})
            if payload.router_mechanism == "jev"
            else None
        )
        response = request.app.state.orchestrator.handle(
            MessageRequest(message=payload.message, user_id=customer_id, conversation_id=payload.conversation_id),
            request_id,
            agent_models=agent_models,
            router_llm=router_llm,
            router_decision=RouterDecision.model_validate(selected["decision"]) if selected else None,
        )
        trace_data = request.app.state.orchestrator.trace(request_id)
        if trace_data and any(str(error).startswith("router:") for error in trace_data.get("errors", [])):
            failure = {"code": "router_unavailable", "message": "Router provider failed; no fallback was used."}
            conn.execute(
                "UPDATE run_snapshots SET snapshot=? WHERE request_id=?",
                (json.dumps(snapshot | {"error": failure}, sort_keys=True), request_id),
            )
            return _error(503, "router_unavailable", failure["message"], request)
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
            }
            if selected:
                trace_summary["effective_parameters_by_agent"] = dict(
                    trace_summary["effective_parameters_by_agent"]
                    | {"router": selected.get("effective_parameters", {})}
                )
            result["run"].update(trace_summary)
            snapshot.update(trace_summary)
        conn.execute(
            "UPDATE run_snapshots SET snapshot=? WHERE request_id=?",
            (json.dumps(snapshot | {"result": result["message"]}, sort_keys=True), request_id),
        )
        return result
    except ConversationNotFound:
        return _error(404, "not_found", "Conversation not found.", request)
    except RuntimeError:
        return _error(503, "provider_unavailable", "A configured model provider is unavailable.", request)
    except (LLMError, ValueError):
        return _error(503, "provider_unavailable", "The selected model could not complete the request.", request)
    finally:
        conn.close()


@router.get("/runs/{request_id}")
def run(request_id: str, request: Request, principal=AUTH):
    if _ensure_not_error(principal):
        return principal
    conn = _db(request)
    try:
        row = conn.execute(
            "SELECT * FROM run_snapshots WHERE request_id=? AND principal_id=?", (request_id, principal["principal_id"])
        ).fetchone()
        if row is None:
            return _error(404, "not_found", "Run not found.", request)
        return json.loads(row["snapshot"])
    finally:
        conn.close()


@router.get("/conversations/{conversation_id}")
def conversation(conversation_id: str, request: Request, principal=AUTH):
    if _ensure_not_error(principal):
        return principal
    if not principal["customer_id"]:
        return _error(403, "forbidden", "Conversation is outside this session scope.", request)
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
