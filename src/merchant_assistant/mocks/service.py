"""Internal HTTP API for separately maintained synthetic pricing and charge fixtures."""

from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query

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


def create_mocks_app() -> FastAPI:
    app = FastAPI(title="Merchant Synthetic Services", version="1.0.0")

    @app.post("/pricing/simulations", response_model=PricingSimulationResponse)
    def simulate(request: PricingSimulationRequest):
        return simulate_record(request)

    @app.get("/charges/{transaction_id}", response_model=ChargeRecordResponse)
    def charge(transaction_id: str, customer_id: str = Query(min_length=1, max_length=64)):
        return charge_record(transaction_id, customer_id)

    return app


app = create_mocks_app()
