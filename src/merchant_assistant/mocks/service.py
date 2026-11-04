"""Internal HTTP API for separately maintained synthetic pricing and charge fixtures, and the synthetic merchant
endpoint that receives the assistant's `conversation.replied` webhook (v0.7.0, task 66)."""

from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from merchant_assistant.mocks.contracts import (
    ChargeRecordResponse,
    PricingSimulationRequest,
    PricingSimulationResponse,
)


def _load(name: str) -> dict[str, dict]:
    configured = os.environ.get("MOCK_SERVICES_DIR")
    fixtures = (
        Path(configured)
        if configured
        else Path(os.environ.get("DATA_DIR", Path(__file__).resolve().parents[3] / "data")) / "mock-services"
    )
    return json.loads((fixtures / name).read_text(encoding="utf-8"))


def simulate_record(request: PricingSimulationRequest) -> dict:
    item = _load("pricing-v1.json").get(request.transaction_id)
    if item is None:
        raise HTTPException(404, detail={"code": "PRICING_NOT_FOUND"})
    if item["customer_id"] != request.customer_id:
        raise HTTPException(403, detail={"code": "FORBIDDEN_RESOURCE"})
    if (
        item["transaction_id"] != request.transaction_id
        or item["currency"] != request.currency
        or item["conditions"] != request.conditions.model_dump()
        or (
            item["applicable"] and sum(row["gross_minor"] for row in item["installments"]) != request.gross_amount_minor
        )
    ):
        raise HTTPException(409, detail={"code": "PRICING_CONTEXT_MISMATCH"})
    return PricingSimulationResponse.model_validate(item).model_dump()


def charge_record(transaction_id: str, customer_id: str) -> dict:
    item = _load("charges-v1.json").get(transaction_id)
    if item is None:
        raise HTTPException(404, detail={"code": "CHARGE_NOT_FOUND"})
    if item["customer_id"] != customer_id:
        raise HTTPException(403, detail={"code": "FORBIDDEN_RESOURCE"})
    return ChargeRecordResponse.model_validate(item).model_dump()


def create_mocks_app(conversation_secret: str | None = None) -> FastAPI:
    """`conversation_secret` (default: `CONVERSATION_WEBHOOK_SECRET`) checks the signature of the merchant webhook."""
    from merchant_assistant.api.webhooks import verify_signature

    app = FastAPI(title="Merchant Synthetic Services", version="1.0.0")
    secret = os.environ.get("CONVERSATION_WEBHOOK_SECRET", "") if conversation_secret is None else conversation_secret
    received: list[dict] = []  # in memory: a demonstration receiver, emptied when the container restarts
    lock = threading.Lock()

    def refuse(status: int, code: str, message: str) -> JSONResponse:
        return JSONResponse(status_code=status, content={"error": {"code": code, "message": message}})

    @app.post("/merchant/events")
    async def merchant_event(request: Request):
        """Synthetic merchant endpoint for `conversation.replied` (spec v0.7.0, D11): signature checked, a repeated
        `id` is acknowledged without being stored twice."""
        if not secret:
            return refuse(503, "webhook_not_configured", "CONVERSATION_WEBHOOK_SECRET is not configured.")
        raw = await request.body()
        if not verify_signature(secret, request.headers.get("x-signature"), raw, time.time()):
            return refuse(401, "invalid_signature", "Invalid or expired webhook signature.")
        try:
            event = json.loads(raw)
        except ValueError:
            event = None
        valid = isinstance(event, dict) and isinstance(event.get("id"), str) and isinstance(event.get("data"), dict)
        if not valid:
            return refuse(400, "invalid_payload", "Expected the webhook envelope {id, type, created_at, data}.")
        with lock:
            if any(item["id"] == event["id"] for item in received):
                return {"status": "duplicate"}
            received.append(event)
        return {"status": "received"}

    @app.get("/merchant/events")
    def merchant_events(conversation_id: str | None = Query(default=None, max_length=64)):
        with lock:
            events = [e for e in received if conversation_id in (None, e["data"].get("conversation_id"))]
        return {"events": events}

    @app.post("/pricing/simulations", response_model=PricingSimulationResponse)
    def simulate(request: PricingSimulationRequest):
        return simulate_record(request)

    @app.get("/charges/{transaction_id}", response_model=ChargeRecordResponse)
    def charge(transaction_id: str, customer_id: str = Query(min_length=1, max_length=64)):
        return charge_record(transaction_id, customer_id)

    return app


app = create_mocks_app()
