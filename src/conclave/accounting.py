"""Immutable, reproducible provider usage and cost accounting.

This module records provider-reported usage and applies an externally supplied,
versioned rate card. It does not fetch prices, create invoices, or authorize a
charge.
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .errors import IntegrityError, ValidationError
from .hashing import hash_text
from .ledger import canonical_json
from .providers import ProviderResponse, ProviderUsage

USAGE_SCHEMA_VERSION = "provider-usage/0.1.0"
CATALOG_SCHEMA_VERSION = "price-catalog/0.1.0"
COST_SCHEMA_VERSION = "provider-cost/0.1.0"
MILLION = Decimal("1000000")


def _hash_body(model: BaseModel) -> str:
    return hash_text(canonical_json(
        model.model_dump(mode="json", exclude={"content_hash"})
    ))


class UsageRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = USAGE_SCHEMA_VERSION
    project_id: str = Field(min_length=1)
    packet_ref: str = Field(min_length=1)
    provider: str = Field(min_length=1)
    model: str = Field(min_length=1)
    transport: str = Field(min_length=1)
    role: str = Field(min_length=1)
    provider_request_id: str | None = None
    usage: ProviderUsage
    content_hash: str

    @model_validator(mode="after")
    def verify_hash(self) -> "UsageRecord":
        if self.content_hash != _hash_body(self):
            raise IntegrityError("usage record content_hash is stale")
        return self


class PriceRate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    provider: str = Field(min_length=1)
    model: str = Field(min_length=1)
    transport: str = Field(min_length=1)
    input_per_million: Decimal = Field(ge=0)
    cached_input_per_million: Decimal = Field(ge=0)
    output_per_million: Decimal = Field(ge=0)

    @property
    def key(self) -> tuple[str, str, str]:
        return self.provider, self.model, self.transport


class PriceCatalog(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = CATALOG_SCHEMA_VERSION
    catalog_id: str = Field(min_length=1)
    currency: str = Field(min_length=3, max_length=3)
    effective_at: str = Field(min_length=1)
    retrieved_at: str = Field(min_length=1)
    source_url: str = Field(min_length=1)
    rates: tuple[PriceRate, ...]
    content_hash: str

    @model_validator(mode="after")
    def verify(self) -> "PriceCatalog":
        keys = [rate.key for rate in self.rates]
        if len(keys) != len(set(keys)):
            raise ValidationError("price catalog rate identities must be unique")
        if self.currency != self.currency.upper():
            raise ValidationError("price catalog currency must be uppercase ISO 4217")
        if self.content_hash != _hash_body(self):
            raise IntegrityError("price catalog content_hash is stale")
        return self

    def rate_for(self, usage: UsageRecord) -> PriceRate:
        key = (usage.provider, usage.model, usage.transport)
        for rate in self.rates:
            if rate.key == key:
                return rate
        raise ValidationError(f"price catalog has no exact rate for {key!r}")


class CostRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = COST_SCHEMA_VERSION
    project_id: str
    packet_ref: str
    usage_record_hash: str
    price_catalog_id: str
    price_catalog_hash: str
    currency: str
    uncached_input_cost: Decimal
    cached_input_cost: Decimal
    output_cost: Decimal
    additional_charges: tuple["ChargeLine", ...] = ()
    total_cost: Decimal
    content_hash: str

    @model_validator(mode="after")
    def verify(self) -> "CostRecord":
        subtotal = (
            self.uncached_input_cost + self.cached_input_cost + self.output_cost
            + sum((line.amount for line in self.additional_charges), Decimal("0"))
        )
        if subtotal != self.total_cost:
            raise IntegrityError("cost record total does not equal its components")
        if self.content_hash != _hash_body(self):
            raise IntegrityError("cost record content_hash is stale")
        return self


class ChargeLine(BaseModel):
    """Optional provider charge outside the normalized token categories."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    category: str = Field(min_length=1)
    quantity: Decimal = Field(ge=0)
    unit: str = Field(min_length=1)
    amount: Decimal = Field(ge=0)
    provider_reference: str | None = None


def _seal(model_type, data: dict):
    draft = model_type.model_construct(**data, content_hash="pending")
    return model_type.model_validate({**data, "content_hash": _hash_body(draft)})


def build_usage_record(
    *, project_id: str, packet_ref: str, role: str,
    response: ProviderResponse,
) -> UsageRecord:
    return _seal(UsageRecord, {
        "schema_version": USAGE_SCHEMA_VERSION,
        "project_id": project_id,
        "packet_ref": packet_ref,
        "provider": response.provider,
        "model": response.model,
        "transport": response.transport,
        "role": role,
        "provider_request_id": response.provider_request_id,
        "usage": response.usage,
    })


def build_price_catalog(
    *, catalog_id: str, currency: str, effective_at: str, retrieved_at: str,
    source_url: str, rates: list[PriceRate],
) -> PriceCatalog:
    return _seal(PriceCatalog, {
        "schema_version": CATALOG_SCHEMA_VERSION,
        "catalog_id": catalog_id,
        "currency": currency,
        "effective_at": effective_at,
        "retrieved_at": retrieved_at,
        "source_url": source_url,
        "rates": tuple(sorted(rates, key=lambda rate: rate.key)),
    })


def calculate_cost(
    usage: UsageRecord, catalog: PriceCatalog,
    *, additional_charges: list[ChargeLine] | None = None,
) -> CostRecord:
    rate = catalog.rate_for(usage)
    cached = usage.usage.cached_input_tokens
    uncached = usage.usage.input_tokens - cached
    uncached_cost = Decimal(uncached) * rate.input_per_million / MILLION
    cached_cost = Decimal(cached) * rate.cached_input_per_million / MILLION
    output_cost = Decimal(usage.usage.output_tokens) * rate.output_per_million / MILLION
    extras = tuple(additional_charges or ())
    extras_total = sum((line.amount for line in extras), Decimal("0"))
    return _seal(CostRecord, {
        "schema_version": COST_SCHEMA_VERSION,
        "project_id": usage.project_id,
        "packet_ref": usage.packet_ref,
        "usage_record_hash": usage.content_hash,
        "price_catalog_id": catalog.catalog_id,
        "price_catalog_hash": catalog.content_hash,
        "currency": catalog.currency,
        "uncached_input_cost": uncached_cost,
        "cached_input_cost": cached_cost,
        "output_cost": output_cost,
        "additional_charges": extras,
        "total_cost": uncached_cost + cached_cost + output_cost + extras_total,
    })


def aggregate_costs(
    records: list[CostRecord], *, project_id: str,
    packet_ref: str | None = None,
) -> tuple[str, Decimal]:
    for record in records:
        if record.content_hash != _hash_body(record):
            raise IntegrityError("cannot aggregate a cost record with a stale hash")
    selected = [
        record for record in records
        if record.project_id == project_id
        and (packet_ref is None or record.packet_ref == packet_ref)
    ]
    currencies = {record.currency for record in selected}
    if len(currencies) > 1:
        raise ValidationError("cannot aggregate cost records with different currencies")
    currency = next(iter(currencies), "USD")
    return currency, sum((record.total_cost for record in selected), Decimal("0"))
