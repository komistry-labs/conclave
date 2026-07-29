import yaml
import json
import pytest
from typer.testing import CliRunner

from conclave import ledger
from conclave.cli import app
from conclave.context import ContextSource, build_context_bundle
from conclave.errors import ValidationError
from conclave.execution import execute_stage, write_run_record
from conclave.providers import EgressDecision, FixtureAdapter
from conclave.providers import ProviderRequest, ProviderResponse, ProviderUsage
from conclave.routing import ProviderCapability, TokenBudget, build_route
from conclave.routing import write_route_plan
from conclave.runhandoff import convert_run
from conclave.taskpacket import build_packet, write_packet
from conclave.workspace import Workspace


@pytest.fixture
def completed(tmp_path):
    ws = Workspace.create(tmp_path, principal="Arthur")
    packet = build_packet(
        objective="Convert run to handoff", created_by="Arthur",
        target_objects=[{"object_id": "DOC-001"}],
        assigned_providers=[{"provider": "adrian", "role": "critic"}],
    )
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
        budget=TokenBudget(max_input_tokens=1000, max_output_tokens=1000),
    )
    write_route_plan(ws, plan)
    submission = {
        "handoff_packet": "handoff-packet/0.1.0",
        "packet_ref": packet.ref,
        "packet_content_hash": packet.content_hash,
        "provider": "adrian", "role": "lead", "status": "submitted",
        "objects_touched": [{"object_id": "DOC-001", "action": "read"}],
        "output": {"type": "draft", "summary": "done", "body": "work"},
        "findings": [], "assumptions": [], "abstentions": [],
        "unresolved": [], "evidence_used": [],
        "recommended_next_action": "accept",
    }
    response_text = "```yaml\n" + yaml.safe_dump(submission, sort_keys=False) + "```\n"
    decision = EgressDecision(
        allowed=True, transports=frozenset({"fixture"}),
        classifications=frozenset({"internal"}),
        authority="CONCLAVE", decision_ref="LOCAL-FIXTURE-NO-EGRESS",
    )
    run = execute_stage(
        packet=packet, bundle=bundle, plan=plan, stage_index=0,
        adapter=FixtureAdapter(provider="adrian", response_text=response_text),
        decision=decision, model="fixture-model", prompt="work",
        estimated_input_tokens=1,
    )
    run_path, _ = write_run_record(ws, run)
    return ws, packet, run, run_path


def test_completed_run_converts_and_preserves_provenance(completed):
    ws, _, run, run_path = completed
    result = convert_run(ws, run_path)
    assert result.created
    assert result.packet.run_record_hash == run.content_hash
    assert result.packet.context_bundle_hash == run.context_bundle_hash
    assert result.packet.route_plan_hash == run.route_plan_hash
    assert result.raw_path.read_text(encoding="utf-8") == run.response.text


def test_conversion_is_idempotent(completed):
    ws, _, _, run_path = completed
    first = convert_run(ws, run_path)
    second = convert_run(ws, run_path)
    assert not second.created
    assert second.handoff_path == first.handoff_path


def test_budget_exceeded_run_is_refused(completed):
    ws, _, run, _ = completed
    data = run.model_dump(mode="json", exclude={"content_hash"})
    data["status"] = "budget_exceeded"
    data["budget_defects"] = ["actual output exceeds ceiling"]
    from conclave.execution import RunRecord, compute_run_hash
    from conclave.providers import ProviderRequest, ProviderResponse
    draft = RunRecord.model_construct(
        **{
            **data,
            "request": ProviderRequest.model_validate(data["request"]),
            "response": ProviderResponse.model_validate(data["response"]),
            "budget_defects": tuple(data["budget_defects"]),
        },
        content_hash="pending",
    )
    exceeded = RunRecord.model_validate({
        **data, "content_hash": compute_run_hash(draft)
    })
    path, _ = write_run_record(ws, exceeded)
    with pytest.raises(ValidationError, match="only completed"):
        convert_run(ws, path)


def test_route_is_authoritative_over_static_assignment(completed):
    ws, packet, _, run_path = completed
    assert packet.assigned_providers[0].role == "critic"
    result = convert_run(ws, run_path)
    assert result.packet.role == "lead"


def test_structured_output_is_preserved_with_text(completed):
    ws, _, run, _ = completed
    block = yaml.safe_load(
        run.response.text.split("```yaml\n", 1)[1].rsplit("```", 1)[0]
    )
    response = ProviderResponse(
        provider=run.response.provider, model=run.response.model,
        transport=run.response.transport, text="provider explanatory text",
        structured_output=block,
        usage=ProviderUsage(input_tokens=1, output_tokens=1),
        finish_status="completed", provider_request_id="structured-1",
    )
    data = run.model_dump(mode="json", exclude={"content_hash"})
    data["request"] = ProviderRequest.model_validate(data["request"])
    data["response"] = response
    data["budget_defects"] = tuple(data["budget_defects"])
    from conclave.execution import RunRecord, compute_run_hash
    draft = RunRecord.model_construct(**data, content_hash="pending")
    structured_run = RunRecord.model_validate({
        **data, "content_hash": compute_run_hash(draft)
    })
    path, _ = write_run_record(ws, structured_run)
    result = convert_run(ws, path)
    preserved = json.loads(result.raw_path.read_text(encoding="utf-8"))
    assert preserved["text"] == "provider explanatory text"
    assert preserved["structured_output"] == block


def test_cli_converts_and_creates_scope_review(completed, monkeypatch):
    ws, _, _, run_path = completed
    ledger.initialise(ws, ws.load_config())
    monkeypatch.setenv("CONCLAVE_HOME", str(ws.root))
    result = CliRunner().invoke(app, ["run", "handoff", str(run_path)])
    assert result.exit_code == 0, result.output
    assert "created handoff" in result.output
    assert "created scope" in result.output
    event_types = [event["event_type"] for event in ledger.read_events(ws)]
    assert event_types[-3:] == [
        "provider_response_preserved",
        "handoff_packet_imported",
        "scope_review_created",
    ]
