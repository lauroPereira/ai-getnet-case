"""Synchronous, bounded HTTP clients for the internal pricing and charge APIs."""

from __future__ import annotations

from typing import Any

import httpx
from pydantic import ValidationError

from merchant_assistant.mocks.contracts import ChargeRecordResponse, PricingSimulationResponse
from merchant_assistant.tools.base import ToolError


class MockServiceClient:
    def __init__(self, base_url: str, *, timeout: float = 2.0, transport: httpx.BaseTransport | None = None) -> None:
        self.client = httpx.Client(base_url=base_url, timeout=timeout, transport=transport)

    def simulate(self, payload: dict[str, Any]) -> dict:
        try:
            response = self.client.post("/pricing/simulations", json=payload)
        except httpx.TimeoutException as exc:
            raise ToolError("TIMEOUT", "Pricing service timed out.") from exc
        except httpx.RequestError as exc:
            raise ToolError("UNAVAILABLE", "Pricing service is unavailable.") from exc
        return self._parse(response, PricingSimulationResponse, "Pricing")

    def charge(self, transaction_id: str, customer_id: str) -> dict:
        try:
            response = self.client.get(f"/charges/{transaction_id}", params={"customer_id": customer_id})
        except httpx.TimeoutException as exc:
            raise ToolError("TIMEOUT", "Charges service timed out.") from exc
        except httpx.RequestError as exc:
            raise ToolError("UNAVAILABLE", "Charges service is unavailable.") from exc
        return self._parse(response, ChargeRecordResponse, "Charges")

    @staticmethod
    def _parse(response: httpx.Response, model: type, label: str) -> dict:
        if response.status_code == 404:
            raise ToolError("NOT_FOUND", f"{label} evidence is not available for this sale.")
        if response.status_code == 403:
            raise ToolError("FORBIDDEN_RESOURCE", f"{label} evidence does not belong to this merchant.")
        if response.status_code >= 500:
            raise ToolError("UNAVAILABLE", f"{label} service returned an error.")
        if response.status_code >= 400:
            raise ToolError("INVALID_ARGUMENT", f"{label} service rejected the request.")
        try:
            return model.model_validate(response.json()).model_dump()
        except (ValueError, ValidationError) as exc:
            raise ToolError("UNAVAILABLE", f"{label} service returned an invalid response.") from exc

    def close(self) -> None:
        self.client.close()


def in_process_client() -> MockServiceClient:
    """Route client HTTP through the FastAPI ASGI app using an in-process transport."""
    from fastapi.testclient import TestClient

    from merchant_assistant.mocks.service import create_mocks_app

    app_client = TestClient(create_mocks_app())

    def dispatch(request: httpx.Request) -> httpx.Response:
        result = app_client.request(request.method, str(request.url), content=request.content, headers=request.headers)
        return httpx.Response(result.status_code, headers=result.headers, json=result.json())

    return MockServiceClient("http://mocks", transport=httpx.MockTransport(dispatch))
