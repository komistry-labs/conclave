import yaml
import pytest
from typer.testing import CliRunner

from conclave import ledger
from conclave.cli import app
from conclave.concurrency import execute_concurrent, write_concurrent_outcome
from conclave.context import ContextSource, build_context_bundle, write_context_bundle
from conclave.errors import ValidationError
from conclave.orchestration import orchestrate_batch
from conclave.providers import EgressDecision, FixtureAdapter
from conclave.reconcile import reconcile
from conclave.routing import ProviderCapability, TokenBudget, build_route, write_route_plan
from conclave.synthesis import (
    SynthesisContinuationRecord, execute_synthesis, read_synthesis,
)
from conclave.taskpacket import build_packet, write_packet
from conclave.workspace import Workspace


def submission(packet, provider, role, *, action="read", object_id="DOC-001"):
    return {
        "handoff_packet": "handoff-packet/0.1.0",
        "packet_ref": packet.ref,
        "packet_content_hash": packet.content_hash,
        "provider": provider,
        "role": role,
        "status": "submitted",
        "objects_touched": [{"object_id": object_id, "action": action}],
        "output": {
            "type": role,
            "summary": f"{role} complete",
            "body": f"{provider} {role} evidence",
        },
        "findings": [{
            "finding_id": f"F-{role}", "key": "shared-control",
            "severity": "low", "dimension": "governance",
            "claim": f"{provider} finding",
        }],
        "assumptions": [],
        "abstentions": [],
        "unresolved": [],
        "evidence_used": ["DOC-001"],
        "recommended_next_action": "accept",
    }


def make_source(tmp_path, *, risk="canonical"):
    ws = Workspace.create(tmp_path, principal="Arthur")
    packet = build_packet(
        objective="Governed sequential synthesis", created_by="Arthur",
        target_objects=[{"object_id": "DOC-001"}],
    )
    write_packet(ws, packet)
    bundle = build_context_bundle(
        packet_ref=packet.ref, packet_content_hash=packet.content_hash,
        sources=[ContextSource.seal(
            object_id="DOC-001", status="active", authority="Arthur",
            classification="internal", content="canonical fixture facts",
        )],
    )
    context_path, _ = write_context_bundle(ws, bundle)
    route = build_route(
        packet_ref=packet.ref, risk=risk,
        capabilities=[
            ProviderCapability(provider="adrian", roles=frozenset({"lead"})),
            ProviderCapability(
                provider="claude", roles=frozenset({"critic", "synthesizer"})
            ),
            ProviderCapability(provider="gemini", roles=frozenset({"verifier"})),
        ],
        budget=TokenBudget(max_input_tokens=20000, max_output_tokens=5000),
    )
    route_path, _ = write_route_plan(ws, route)
    decision = EgressDecision(
        allowed=True, transports=frozenset({"fixture"}),
        classifications=frozenset({"internal"}), authority="CONCLAVE",
        decision_ref="LOCAL-FIXTURE-NO-EGRESS",
    )
    indices = tuple(
        index for index, stage in enumerate(route.stages)
        if stage.role != "synthesizer"
    )
    wave = execute_concurrent(
        packet=packet, bundle=bundle, plan=route, stage_indices=indices,
        adapters={
            index: FixtureAdapter(
                provider=route.stages[index].provider,
                response_text="```yaml\n" + yaml.safe_dump(
                    submission(
                        packet, route.stages[index].provider,
                        route.stages[index].role,
                    ),
                    sort_keys=False,
                ) + "```\n",
            )
            for index in indices
        },
        decisions={index: decision for index in indices},
        models={index: f"model-{index}" for index in indices},
        prompts={index: f"independent instruction {index}" for index in indices},
        estimated_input_tokens={index: 10 for index in indices},
    )
    stored = write_concurrent_outcome(ws, wave)
    source = orchestrate_batch(ws, stored.batch_path)
    expected_pause = (
        "awaiting_sequential_synthesizer"
        if risk == "canonical" else "awaiting_human_decision"
    )
    assert source.record.pause_state == expected_pause
    return ws, packet, bundle, route, context_path, route_path, source, decision


def synth_adapter(packet, *, action="read", object_id="DOC-001"):
    body = submission(
        packet, "claude", "synthesizer", action=action, object_id=object_id
    )
    return FixtureAdapter(
        provider="claude",
        response_text="```yaml\n" + yaml.safe_dump(body, sort_keys=False) + "```\n",
    )


def execute(tmp_path, *, action="read", object_id="DOC-001"):
    ws, packet, bundle, route, context_path, route_path, source, decision = (
        make_source(tmp_path)
    )
    outcome = execute_synthesis(
        ws=ws, source_file=source.path,
        adapter=synth_adapter(packet, action=action, object_id=object_id),
        decision=decision, model="synth-model", operator_instruction="Synthesize.",
        estimated_input_tokens=100,
    )
    return ws, packet, bundle, route, context_path, route_path, source, decision, outcome


def test_sequential_synthesis_reaches_human_decision_pause(tmp_path):
    ws, _, _, _, _, _, source, _, outcome = execute(tmp_path)
    assert outcome.record.pause_state == "awaiting_human_decision"
    assert outcome.record.council_review_status == "ready_for_human_review"
    assert outcome.record.source_orchestration_hash == source.record.content_hash
    assert outcome.record.action_execution_allowed is False
    assert outcome.record.human_decision_required is True
    assert len(outcome.council.review.submissions) == 4
    assert outcome.council.review.decision_block.decision == "pending"
    assert not list(ws.decisions_dir.glob("*.yaml"))


def test_synthesis_is_idempotent_and_does_not_recall_provider(tmp_path):
    ws, packet, _, _, _, _, source, decision, first = execute(tmp_path)

    class MustNotRun(FixtureAdapter):
        def execute(self, request):
            raise AssertionError("provider was called again")

    before = first.path.read_bytes()
    second = execute_synthesis(
        ws=ws, source_file=source.path,
        adapter=MustNotRun(provider="claude"), decision=decision,
        model="synth-model", operator_instruction="Synthesize.",
        estimated_input_tokens=100,
    )
    assert not second.created and not second.run_created
    assert second.path.read_bytes() == before
    assert read_synthesis(second.path) == first.record


def test_noncanonical_source_is_refused_before_adapter_call(tmp_path):
    ws, _, _, _, _, _, source, _ = make_source(tmp_path, risk="important")

    class MustNotRun(FixtureAdapter):
        def execute(self, request):
            raise AssertionError("provider was called")

    with pytest.raises(ValidationError, match="not paused"):
        execute_synthesis(
            ws=ws, source_file=source.path,
            adapter=MustNotRun(provider="claude"),
            decision=EgressDecision(), model="x",
            operator_instruction="Synthesize.", estimated_input_tokens=1,
        )


def test_external_source_copy_is_refused(tmp_path):
    ws, packet, _, _, _, _, source, decision = make_source(tmp_path)
    external = tmp_path / "copied-orchestration.yaml"
    external.write_bytes(source.path.read_bytes())
    with pytest.raises(ValidationError, match="inside this workspace"):
        execute_synthesis(
            ws=ws, source_file=external, adapter=synth_adapter(packet),
            decision=decision, model="synth-model",
            operator_instruction="Synthesize.", estimated_input_tokens=100,
        )


def test_malformed_synthesis_is_not_persisted(tmp_path):
    ws, _, _, _, _, _, source, decision = make_source(tmp_path)
    before = len(list(ws.runs_dir.glob("*.yaml")))
    with pytest.raises(ValidationError, match="not a Handoff submission"):
        execute_synthesis(
            ws=ws, source_file=source.path,
            adapter=FixtureAdapter(provider="claude", response_text="plain prose"),
            decision=decision, model="synth-model",
            operator_instruction="Synthesize.", estimated_input_tokens=100,
        )
    assert len(list(ws.runs_dir.glob("*.yaml"))) == before
    assert not list(ws.synthesis_dir.glob("*.yaml"))


def test_wrong_synthesizer_provider_is_refused(tmp_path):
    ws, _, _, _, _, _, source, decision = make_source(tmp_path)
    with pytest.raises(ValidationError, match="adapter"):
        execute_synthesis(
            ws=ws, source_file=source.path,
            adapter=FixtureAdapter(provider="gemini"), decision=decision,
            model="synth-model", operator_instruction="Synthesize.",
            estimated_input_tokens=100,
        )


def test_synthesizer_scope_expansion_blocks_human_decision_surface(tmp_path):
    _, _, _, _, _, _, _, _, outcome = execute(tmp_path, object_id="DOC-999")
    assert outcome.record.pause_state == "blocked_by_governance"
    assert outcome.record.scope_status == "expansion_detected"
    assert outcome.record.action_execution_allowed is False


def test_record_schema_cannot_authorise_action(tmp_path):
    *_, outcome = execute(tmp_path)
    data = outcome.record.model_dump(mode="json")
    data["action_execution_allowed"] = True
    with pytest.raises(ValueError):
        SynthesisContinuationRecord.model_validate(data)


def test_prompt_binds_and_preserves_all_independent_evidence(tmp_path):
    *_, source, _, outcome = execute(tmp_path)
    prompt = outcome.run.request.prompt
    for stage in source.record.processed_stages:
        assert stage.run_content_hash in prompt
        assert stage.handoff_content_hash in prompt
    assert "inventing consensus" in prompt
    assert "decision: pending" not in prompt


def test_cli_records_synthesis_chain_and_stops(tmp_path, monkeypatch):
    ws, packet, _, _, _, _, source, _ = make_source(tmp_path)
    ledger.initialise(ws, ws.load_config())
    instruction = tmp_path / "instruction.md"
    response = tmp_path / "response.md"
    instruction.write_text("Synthesize.", encoding="utf-8")
    response.write_text(synth_adapter(packet).response_text, encoding="utf-8")
    monkeypatch.setenv("CONCLAVE_HOME", str(ws.root))
    result = CliRunner().invoke(app, [
        "orchestrate", "synthesize-fixture", str(source.path),
        "--instruction", str(instruction), "--response", str(response),
        "--estimated-input-tokens", "100",
    ])
    assert result.exit_code == 0, result.output
    assert "SYNTHESIS PAUSED: AWAITING_HUMAN_DECISION" in result.output
    assert "action execution: not authorised" in result.output
    events = ledger.read_events(ws)
    assert events[-1]["event_type"] == "synthesis_continuation_recorded"
    assert not any(event["event_type"] == "human_decision_recorded" for event in events)


def test_reconciliation_discovers_synthesis_continuation(tmp_path):
    ws, *_rest, outcome = execute(tmp_path)
    ledger.initialise(ws, ws.load_config())
    reconcile(ws)
    events = ledger.read_events(ws)
    assert any(
        event["event_type"] == "synthesis_continuation_recorded"
        and event["artifact_hashes"]["synthesis_continuation"]
        == outcome.record.content_hash
        for event in events
    )


def test_synthesis_record_is_lf_and_round_trips(tmp_path):
    *_, outcome = execute(tmp_path)
    assert b"\r\n" not in outcome.path.read_bytes()
    assert read_synthesis(outcome.path) == outcome.record
