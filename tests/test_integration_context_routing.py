import pytest

from conclave.context import ContextBundle, ContextSource, build_context_bundle
from conclave.errors import IntegrityError, ValidationError
from conclave.providers import EgressDecision, FixtureAdapter, prepare_request
from conclave.routing import ProviderCapability, TokenBudget, build_route


def source(classification="internal"):
    return ContextSource.seal(
        object_id="DOC-001", status="active", authority="Arthur",
        classification=classification, content="canonical facts",
    )


def bundle(classification="internal"):
    return build_context_bundle(
        packet_ref="TP-example-0123456789@v1",
        packet_content_hash="sha256:packet",
        sources=[source(classification)],
    )


def capabilities():
    roles = frozenset({"lead", "critic", "verifier", "synthesizer"})
    return [
        ProviderCapability(provider="adrian", roles=roles),
        ProviderCapability(provider="claude", roles=roles),
        ProviderCapability(provider="gemini", roles=roles),
    ]


def test_context_is_deterministic_and_frozen():
    first = bundle()
    second = bundle()
    assert first.content_hash == second.content_hash
    with pytest.raises(Exception):
        first.packet_ref = "changed"


def test_context_source_rejects_stale_hash():
    data = source().model_dump()
    data["content"] = "tampered"
    with pytest.raises(IntegrityError):
        ContextSource.model_validate(data)


def test_context_bundle_rejects_stale_hash():
    data = bundle().model_dump(mode="json")
    data["packet_ref"] = "TP-other-0123456789@v1"
    with pytest.raises(IntegrityError):
        ContextBundle.model_validate(data)


@pytest.mark.parametrize("risk,count", [
    ("routine", 1), ("important", 2),
    ("evidence-sensitive", 2), ("canonical", 4),
])
def test_adaptive_route_expands_only_with_risk(risk, count):
    route = build_route(
        packet_ref="TP-example-0123456789@v1", risk=risk,
        capabilities=capabilities(),
        budget=TokenBudget(max_input_tokens=10_000, max_output_tokens=4_000),
    )
    assert len(route.stages) == count


def test_lead_is_not_sole_critic_or_synthesizer():
    with pytest.raises(ValidationError, match="not eligible"):
        build_route(
            packet_ref="TP-example-0123456789@v1", risk="canonical",
            capabilities=capabilities(),
            budget=TokenBudget(max_input_tokens=10_000, max_output_tokens=4_000),
            preferred={"lead": "adrian", "critic": "adrian"},
        )
    route = build_route(
        packet_ref="TP-example-0123456789@v1", risk="canonical",
        capabilities=capabilities(),
        budget=TokenBudget(max_input_tokens=10_000, max_output_tokens=4_000),
        preferred={"lead": "adrian"},
    )
    assigned = {stage.role: stage.provider for stage in route.stages}
    assert assigned["critic"] != assigned["lead"]
    assert assigned["verifier"] not in {
        assigned["lead"], assigned["critic"]
    }
    assert assigned["synthesizer"] != assigned["lead"]


def test_budget_fails_closed():
    budget = TokenBudget(max_input_tokens=100, max_output_tokens=100)
    with pytest.raises(ValidationError, match="exceeds ceiling"):
        budget.enforce_input(101)


def test_egress_denied_by_default():
    with pytest.raises(ValidationError, match="not explicitly authorised"):
        prepare_request(
            bundle=bundle(), decision=EgressDecision(), provider="adrian",
            model="configured-model", transport="fixture", role="lead",
            prompt="work", max_output_tokens=100,
        )


def test_classification_exclusion_is_enforced():
    decision = EgressDecision(
        allowed=True, transports=frozenset({"fixture"}),
        classifications=frozenset({"internal"}),
        authority="Arthur", decision_ref="D7",
    )
    with pytest.raises(ValidationError, match="constitutional"):
        prepare_request(
            bundle=bundle("constitutional"), decision=decision, provider="adrian",
            model="configured-model", transport="fixture", role="lead",
            prompt="work", max_output_tokens=100,
        )


def test_fixture_adapter_exercises_normalized_contract():
    decision = EgressDecision(
        allowed=True, transports=frozenset({"fixture"}),
        classifications=frozenset({"internal"}),
        authority="Arthur", decision_ref="TEST-ONLY",
    )
    request = prepare_request(
        bundle=bundle(), decision=decision, provider="adrian",
        model="configured-model", transport="fixture", role="lead",
        prompt="perform fixture work", max_output_tokens=100,
    )
    response = FixtureAdapter(provider="adrian").execute(request)
    assert response.provider == "adrian"
    assert response.usage.input_tokens > 0
    assert response.finish_status == "completed"
