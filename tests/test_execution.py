import pytest
from typer.testing import CliRunner

from conclave import ledger
from conclave.cli import app
from conclave.context import (
    ContextSource, build_context_bundle, write_context_bundle,
)
from conclave.errors import IntegrityError, ValidationError
from conclave.execution import execute_stage, read_run_record, write_run_record
from conclave.providers import (
    EgressDecision, FixtureAdapter, ProviderResponse, ProviderUsage,
)
from conclave.routing import (
    ProviderCapability, TokenBudget, build_route, write_route_plan,
)
from conclave.taskpacket import build_packet, write_packet
from conclave.workspace import Workspace


@pytest.fixture
def artifacts(tmp_path):
    ws = Workspace.create(tmp_path, principal="Arthur")
    packet = build_packet(objective="Execute fixture stage", created_by="Arthur")
    write_packet(ws, packet)
    bundle = build_context_bundle(
        packet_ref=packet.ref, packet_content_hash=packet.content_hash,
        sources=[ContextSource.seal(
            object_id="DOC-001", status="active", authority="Arthur",
            classification="internal", content="facts",
        )],
    )
    plan = build_route(
        packet_ref=packet.ref, risk="routine",
        capabilities=[ProviderCapability(
            provider="adrian", roles=frozenset({"lead"})
        )],
        budget=TokenBudget(max_input_tokens=100, max_output_tokens=20),
    )
    return ws, packet, bundle, plan


def decision(bundle):
    return EgressDecision(
        allowed=True, transports=frozenset({"fixture"}),
        classifications=frozenset(s.classification for s in bundle.sources),
        authority="CONCLAVE", decision_ref="LOCAL-FIXTURE-NO-EGRESS",
    )


def test_executes_and_round_trips(artifacts):
    ws, packet, bundle, plan = artifacts
    record = execute_stage(
        packet=packet, bundle=bundle, plan=plan, stage_index=0,
        adapter=FixtureAdapter(provider="adrian"),
        decision=decision(bundle), model="fixture-model",
        prompt="do fixture work", estimated_input_tokens=3,
    )
    assert record.status == "completed"
    assert record.egress_authority == "CONCLAVE"
    assert record.egress_decision_ref == "LOCAL-FIXTURE-NO-EGRESS"
    path, created = write_run_record(ws, record)
    assert created
    assert read_run_record(path) == record
    assert b"\r\n" not in path.read_bytes()
    assert "context_bundle_hash:" in record.request.prompt
    assert "canonical facts" not in record.request.prompt
    assert "facts" in record.request.prompt
    assert record.request.prompt.endswith("do fixture work\n")


def test_estimate_over_budget_prevents_adapter_call(artifacts):
    _, packet, bundle, plan = artifacts

    class MustNotRun(FixtureAdapter):
        def execute(self, request):
            raise AssertionError("adapter was called")

    with pytest.raises(ValidationError, match="estimated input"):
        execute_stage(
            packet=packet, bundle=bundle, plan=plan, stage_index=0,
            adapter=MustNotRun(provider="adrian"),
            decision=decision(bundle), model="fixture-model",
            prompt="work", estimated_input_tokens=101,
        )


def test_actual_overage_is_preserved():
    class OverageAdapter(FixtureAdapter):
        def execute(self, request):
            return ProviderResponse(
                provider=self.provider, model=request.model,
                transport=self.transport, text="large result",
                usage=ProviderUsage(input_tokens=101, output_tokens=21),
                finish_status="completed",
            )

    packet = build_packet(objective="Capture actual overage", created_by="Arthur")
    bundle = build_context_bundle(
        packet_ref=packet.ref,
        packet_content_hash=packet.content_hash,
        sources=[ContextSource.seal(
            object_id="DOC", status="active", authority="Arthur",
            classification="internal", content="facts",
        )],
    )
    plan = build_route(
        packet_ref=bundle.packet_ref, risk="routine",
        capabilities=[ProviderCapability(
            provider="adrian", roles=frozenset({"lead"})
        )],
        budget=TokenBudget(max_input_tokens=100, max_output_tokens=20),
    )
    record = execute_stage(
        packet=packet, bundle=bundle, plan=plan, stage_index=0,
        adapter=OverageAdapter(provider="adrian"),
        decision=decision(bundle), model="fixture-model",
        prompt="work", estimated_input_tokens=1,
    )
    assert record.status == "budget_exceeded"
    assert len(record.budget_defects) == 2
    assert record.response.text == "large result"


def test_provider_mismatch_refused(artifacts):
    _, packet, bundle, plan = artifacts
    with pytest.raises(ValidationError, match="does not match route"):
        execute_stage(
            packet=packet, bundle=bundle, plan=plan, stage_index=0,
            adapter=FixtureAdapter(provider="claude"),
            decision=decision(bundle), model="fixture-model",
            prompt="work", estimated_input_tokens=1,
        )


def test_prior_usage_enforces_route_wide_budget(artifacts):
    _, packet, bundle, _ = artifacts
    plan = build_route(
        packet_ref=packet.ref, risk="important",
        capabilities=[
            ProviderCapability(provider="adrian", roles=frozenset({"lead"})),
            ProviderCapability(provider="claude", roles=frozenset({"critic"})),
        ],
        budget=TokenBudget(max_input_tokens=100, max_output_tokens=20),
    )
    first = execute_stage(
        packet=packet, bundle=bundle, plan=plan, stage_index=0,
        adapter=FixtureAdapter(provider="adrian"),
        decision=decision(bundle), model="fixture-model",
        prompt="first", estimated_input_tokens=1,
    )
    with pytest.raises(ValidationError, match="estimated input"):
        execute_stage(
            packet=packet, bundle=bundle, plan=plan, stage_index=1,
            adapter=FixtureAdapter(provider="claude"),
            decision=decision(bundle), model="fixture-model",
            prompt="second", estimated_input_tokens=100,
            prior_runs=[first],
        )


def test_tampered_run_rejected(artifacts):
    _, packet, bundle, plan = artifacts
    record = execute_stage(
        packet=packet, bundle=bundle, plan=plan, stage_index=0,
        adapter=FixtureAdapter(provider="adrian"),
        decision=decision(bundle), model="fixture-model",
        prompt="work", estimated_input_tokens=1,
    )
    with pytest.raises((IntegrityError, ValidationError)):
        type(record).model_validate({
            **record.model_dump(mode="json"), "role": "critic"
        })


def test_request_context_hash_must_match_run_record(artifacts):
    _, packet, bundle, plan = artifacts
    record = execute_stage(
        packet=packet, bundle=bundle, plan=plan, stage_index=0,
        adapter=FixtureAdapter(provider="adrian"),
        decision=decision(bundle), model="fixture-model",
        prompt="work", estimated_input_tokens=1,
    )
    data = record.model_dump(mode="json")
    data["request"]["context_bundle_hash"] = "sha256:" + "0" * 64
    with pytest.raises(ValidationError, match="Context Bundle hashes differ"):
        type(record).model_validate(data)


def test_context_packet_hash_mismatch_prevents_adapter_call(artifacts):
    _, packet, bundle, plan = artifacts

    class MustNotRun(FixtureAdapter):
        def execute(self, request):
            raise AssertionError("adapter was called")

    mismatched = build_context_bundle(
        packet_ref=packet.ref,
        packet_content_hash="sha256:" + "0" * 64,
        sources=list(bundle.sources),
    )
    with pytest.raises(ValidationError, match="packet_content_hash"):
        execute_stage(
            packet=packet, bundle=mismatched, plan=plan, stage_index=0,
            adapter=MustNotRun(provider="adrian"),
            decision=decision(mismatched), model="fixture-model",
            prompt="work", estimated_input_tokens=1,
        )


def test_later_stage_requires_every_predecessor(artifacts):
    _, packet, bundle, _ = artifacts
    plan = build_route(
        packet_ref=packet.ref, risk="important",
        capabilities=[
            ProviderCapability(provider="adrian", roles=frozenset({"lead"})),
            ProviderCapability(provider="claude", roles=frozenset({"critic"})),
        ],
        budget=TokenBudget(max_input_tokens=100, max_output_tokens=20),
    )
    with pytest.raises(ValidationError, match="every earlier route stage"):
        execute_stage(
            packet=packet, bundle=bundle, plan=plan, stage_index=1,
            adapter=FixtureAdapter(provider="claude"),
            decision=decision(bundle), model="fixture-model",
            prompt="work", estimated_input_tokens=1,
        )


def test_fixture_cli_captures_run_and_ledger(artifacts, tmp_path, monkeypatch):
    ws, _, bundle, plan = artifacts
    context_path, _ = write_context_bundle(ws, bundle)
    route_path, _ = write_route_plan(ws, plan)
    prompt = tmp_path / "prompt.txt"
    response = tmp_path / "response.txt"
    prompt.write_text("fixture prompt", encoding="utf-8")
    response.write_text("fixture response", encoding="utf-8")
    ledger.initialise(ws, ws.load_config())
    monkeypatch.setenv("CONCLAVE_HOME", str(ws.root))
    result = CliRunner().invoke(app, [
        "run", "fixture", "--context", str(context_path),
        "--route", str(route_path), "--prompt", str(prompt),
        "--response", str(response), "--estimated-input-tokens", "2",
    ])
    assert result.exit_code == 0, result.output
    assert "status: completed" in result.output
    assert list(ws.runs_dir.glob("*.yaml"))
    assert ledger.read_events(ws)[-1]["event_type"] == "provider_run_captured"
