from decimal import Decimal

import pytest

from conclave.accounting import (
    ChargeLine,
    PriceRate,
    aggregate_costs,
    build_price_catalog,
    build_usage_record,
    calculate_cost,
)
from conclave.errors import IntegrityError, ValidationError
from conclave.providers import ProviderResponse, ProviderUsage


def response(**usage):
    return ProviderResponse(
        provider="openai", model="configured-model", transport="api",
        text="answer", usage=ProviderUsage(**usage),
        finish_status="completed", provider_request_id="req-1",
    )


def catalog(currency="USD"):
    return build_price_catalog(
        catalog_id="official-2026-07-29", currency=currency,
        effective_at="2026-07-29T00:00:00Z",
        retrieved_at="2026-07-29T12:00:00Z",
        source_url="https://provider.example/official-pricing",
        rates=[PriceRate(
            provider="openai", model="configured-model", transport="api",
            input_per_million=Decimal("2"),
            cached_input_per_million=Decimal("0.5"),
            output_per_million=Decimal("10"),
        )],
    )


def usage(project="LAB-001", packet="TP-example-0123456789@v1", **tokens):
    return build_usage_record(
        project_id=project, packet_ref=packet, role="lead",
        response=response(**tokens),
    )


def test_provider_usage_enforces_subset_invariants():
    with pytest.raises(ValueError, match="cached"):
        ProviderUsage(input_tokens=2, cached_input_tokens=3, output_tokens=1)
    with pytest.raises(ValueError, match="reasoning"):
        ProviderUsage(input_tokens=1, output_tokens=2, reasoning_output_tokens=3)


def test_cost_uses_decimal_and_cached_rate():
    record = usage(
        input_tokens=1_000_000, cached_input_tokens=250_000,
        output_tokens=100_000, reasoning_output_tokens=20_000,
    )
    cost = calculate_cost(record, catalog())
    assert cost.uncached_input_cost == Decimal("1.5")
    assert cost.cached_input_cost == Decimal("0.125")
    assert cost.output_cost == Decimal("1")
    assert cost.total_cost == Decimal("2.625")


def test_optional_non_token_charge_is_extensible():
    cost = calculate_cost(
        usage(input_tokens=0, output_tokens=0), catalog(),
        additional_charges=[ChargeLine(
            category="tool.search", quantity=Decimal("2"), unit="query",
            amount=Decimal("0.02"), provider_reference="official-rate-card",
        )],
    )
    assert cost.total_cost == Decimal("0.02")


def test_price_catalog_is_deterministic_and_cites_source():
    first = catalog()
    second = catalog()
    assert first.content_hash == second.content_hash
    assert first.source_url.startswith("https://")


def test_exact_provider_model_transport_rate_is_required():
    record = usage(input_tokens=1, output_tokens=1).model_copy(
        update={"model": "different"}
    )
    with pytest.raises(ValidationError, match="no exact rate"):
        catalog().rate_for(record)


def test_usage_and_cost_records_detect_tampering():
    record = usage(input_tokens=10, output_tokens=10)
    with pytest.raises(IntegrityError):
        type(record).model_validate({**record.model_dump(), "role": "critic"})
    cost = calculate_cost(record, catalog())
    with pytest.raises(IntegrityError):
        type(cost).model_validate({
            **cost.model_dump(), "total_cost": Decimal("999")
        })


def test_aggregation_can_be_per_project_or_task():
    records = [
        calculate_cost(
            usage(packet="TP-a-0123456789@v1", input_tokens=1_000_000, output_tokens=0),
            catalog(),
        ),
        calculate_cost(
            usage(packet="TP-b-0123456789@v1", input_tokens=0, output_tokens=100_000),
            catalog(),
        ),
    ]
    assert aggregate_costs(records, project_id="LAB-001") == (
        "USD", Decimal("3")
    )
    assert aggregate_costs(
        records, project_id="LAB-001", packet_ref="TP-a-0123456789@v1"
    ) == ("USD", Decimal("2"))


def test_mixed_currency_aggregation_is_refused():
    record = usage(input_tokens=1, output_tokens=1)
    records = [calculate_cost(record, catalog("USD"))]
    eur = calculate_cost(record, catalog("EUR")).model_copy(
        update={"project_id": "LAB-001"}
    )
    with pytest.raises(ValidationError, match="different currencies"):
        aggregate_costs([*records, eur], project_id="LAB-001")


def test_aggregation_rejects_stale_record():
    record = calculate_cost(
        usage(input_tokens=1, output_tokens=1), catalog()
    ).model_copy(update={"total_cost": Decimal("999")})
    with pytest.raises(IntegrityError, match="stale hash"):
        aggregate_costs([record], project_id="LAB-001")
