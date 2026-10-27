"""Typed request and response contracts for the internal mock services."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PricingConditions(StrictModel):
    payment_type: str
    installments: int = Field(ge=1)
    channel: str
    pricing_plan: str


class PricingSimulationRequest(StrictModel):
    customer_id: str
    transaction_id: str
    operation: Literal["sale_fee"] = "sale_fee"
    gross_amount_minor: int = Field(gt=0)
    currency: str = "BRL"
    conditions: PricingConditions
    pricing_version: str = "pricing_mock_v1"


class AmountComponent(StrictModel):
    name: str
    amount_minor: int = Field(ge=0)


class InstallmentAmount(StrictModel):
    number: int = Field(ge=1)
    gross_minor: int = Field(ge=0)
    fee_minor: int = Field(ge=0)
    net_minor: int = Field(ge=0)


class PricingSimulationResponse(StrictModel):
    customer_id: str
    transaction_id: str
    rule_id: str
    rule_version: str
    applicable: bool
    conditions: PricingConditions
    currency: str
    components: list[AmountComponent]
    installments: list[InstallmentAmount]
    expected_fee_minor: int | None = Field(default=None, ge=0)


class ChargeRecordResponse(StrictModel):
    customer_id: str
    transaction_id: str
    recorded: bool
    conditions: PricingConditions
    currency: str
    components: list[AmountComponent]
    installments: list[InstallmentAmount]
    charged_fee_minor: int | None = Field(default=None, ge=0)
