"""Governed Context Bundle export for manual relay."""

import pytest
from typer.testing import CliRunner

from conclave import ledger
from conclave.cli import app
from conclave.context import ContextSource, build_context_bundle, write_context_bundle
from conclave.contextrelay import (
    build_context_relay_prompt,
    read_context_relay_export,
    write_context_relay_export,
)
from conclave.errors import IntegrityError, ValidationError, WorkspaceError
from conclave.reconcile import reconcile
from conclave.relay import read_export_records
from conclave.routing import (
    ProviderCapability,
    TokenBudget,
    build_route,
    write_route_plan,
)
from conclave.taskpacket import build_packet, write_packet
from conclave.workspace import Workspace


@pytest.fixture
def prepared(tmp_path):
    ws = Workspace.create(tmp_path, principal="Arthur")
    packet = build_packet(
        objective="Draft RA-001 Part I without inventing constitutional authority.",
        created_by="Arthur",
        target_objects=[{
            "object_id": "RA-001",
            "section_id": "RA-001-PART-I",
        }],
        read_only_objects=[
            {"object_id": "ADR-0006"},
            {"object_id": "RA-001-CONSTITUTIONAL-DEFERRAL"},
        ],
        assigned_providers=[
            {"provider": "adrian", "role": "institutional_architect"},
            {"provider": "claude", "role": "governance_critic"},
            {"provider": "gemini", "role": "external_verifier"},
        ],
    )
    write_packet(ws, packet)
    bundle = build_context_bundle(
        packet_ref=packet.ref,
        packet_content_hash=packet.content_hash,
        sources=[
            ContextSource.seal(
                object_id="ADR-0006",
                status="Accepted",
                authority="Arthur",
                classification="constitutional",
                content="Arthur is the sole constitutional authority.\n",
            ),
            ContextSource.seal(
                object_id="RA-001-CONSTITUTIONAL-DEFERRAL",
                status="Active",
                authority="Arthur",
                classification="constitutional",
                content="Ratification is deferred until KOS-CONSTITUTION exists.\n",
            ),
        ],
    )
    context_path, _ = write_context_bundle(ws, bundle)
    plan = build_route(
        packet_ref=packet.ref,
        risk="canonical",
        capabilities=[
            ProviderCapability(provider="adrian", roles=frozenset({"lead"})),
            ProviderCapability(
                provider="claude",
                roles=frozenset({"critic", "synthesizer"}),
            ),
            ProviderCapability(provider="gemini", roles=frozenset({"verifier"})),
        ],
        preferred={
            "lead": "adrian",
            "critic": "claude",
            "verifier": "gemini",
            "synthesizer": "claude",
        },
        budget=TokenBudget(
            max_input_tokens=50000,
            max_output_tokens=12000,
            per_stage_output_tokens={
                "lead": 3000,
                "critic": 3000,
                "verifier": 3000,
                "synthesizer": 3000,
            },
        ),
    )
    route_path, _ = write_route_plan(ws, plan)
    return ws, packet, bundle, context_path, plan, route_path


def _export(prepared, *, stage_index=0, instruction="Produce the governed draft."):
    ws, packet, bundle, _, plan, _ = prepared
    return write_context_relay_export(
        ws=ws,
        packet=packet,
        bundle=bundle,
        plan=plan,
        stage_index=stage_index,
        instruction=instruction,
        config=ws.load_config(),
    )


def test_prompt_projects_exact_sealed_context_and_execution_identity(prepared):
    ws, packet, bundle, _, plan, _ = prepared
    prompt = build_context_relay_prompt(
        packet=packet,
        bundle=bundle,
        plan=plan,
        stage_index=0,
        instruction="Produce the governed draft.",
        config=ws.load_config(),
    )
    assert packet.ref in prompt
    assert packet.content_hash in prompt
    assert bundle.content_hash in prompt
    assert plan.content_hash in prompt
    assert "stage_index         : 0" in prompt
    assert "provider            : adrian" in prompt
    assert "role                : lead" in prompt
    for source in bundle.sources:
        assert source.object_id in prompt
        assert source.content_hash in prompt
        assert source.content in prompt
    assert "Produce the governed draft." in prompt
    assert "No provider API call" in prompt


def test_export_is_canonical_write_once_and_idempotent(prepared):
    record, prompt_path, manifest_path, created = _export(prepared)
    assert created
    assert b"\r\n" not in prompt_path.read_bytes()
    assert b"\r\n" not in manifest_path.read_bytes()
    assert read_context_relay_export(manifest_path) == record

    same, same_prompt, same_manifest, created = _export(prepared)
    assert not created
    assert same == record
    assert same_prompt == prompt_path
    assert same_manifest == manifest_path


def test_same_provider_can_receive_distinct_stage_bound_prompts(prepared):
    critic, critic_prompt, _, _ = _export(prepared, stage_index=1)
    synth, synth_prompt, _, _ = _export(prepared, stage_index=3)
    assert critic.provider == synth.provider == "claude"
    assert critic.role == "critic"
    assert synth.role == "synthesizer"
    assert critic_prompt != synth_prompt
    assert "__s1__" in critic_prompt.name
    assert "__s3__" in synth_prompt.name
    assert "type: critique" in critic_prompt.read_text(encoding="utf-8")
    assert "type: synthesis" in synth_prompt.read_text(encoding="utf-8")


def test_export_record_is_available_to_handoff_provenance(prepared):
    record, _, _, _ = _export(prepared)
    records = read_export_records(prepared[0])
    match = [item for item in records if item["prompt_hash"] == record.prompt_hash]
    assert len(match) == 1
    assert match[0]["event_type"] == "context_prompt_exported"
    assert match[0]["context_bundle_hash"] == record.context_bundle_hash
    assert match[0]["route_plan_hash"] == record.route_plan_hash


def test_tampered_prompt_is_refused(prepared):
    _, prompt_path, manifest_path, _ = _export(prepared)
    prompt_path.write_text("tampered\n", encoding="utf-8")
    with pytest.raises((IntegrityError, ValidationError), match="prompt"):
        read_context_relay_export(manifest_path)
    with pytest.raises(WorkspaceError, match="different governed prompt"):
        _export(prepared)


def test_mismatched_packet_hash_is_refused(prepared):
    ws, packet, _, _, plan, _ = prepared
    wrong = build_context_bundle(
        packet_ref=packet.ref,
        packet_content_hash="sha256:not-the-packet",
        sources=[],
    )
    with pytest.raises(ValidationError, match="packet_content_hash"):
        build_context_relay_prompt(
            packet=packet,
            bundle=wrong,
            plan=plan,
            stage_index=0,
            instruction="work",
            config=ws.load_config(),
        )


def test_reference_and_stage_mismatches_are_refused(prepared):
    ws, packet, bundle, _, plan, _ = prepared
    other_plan = build_route(
        packet_ref="TP-other-0123456789@v1",
        risk="routine",
        capabilities=[
            ProviderCapability(provider="adrian", roles=frozenset({"lead"}))
        ],
        budget=TokenBudget(max_input_tokens=100, max_output_tokens=100),
    )
    with pytest.raises(ValidationError, match="references differ"):
        build_context_relay_prompt(
            packet=packet,
            bundle=bundle,
            plan=other_plan,
            stage_index=0,
            instruction="work",
            config=ws.load_config(),
        )
    with pytest.raises(ValidationError, match="outside the route"):
        build_context_relay_prompt(
            packet=packet,
            bundle=bundle,
            plan=plan,
            stage_index=99,
            instruction="work",
            config=ws.load_config(),
        )


def test_cli_exports_and_records_without_provider_call(prepared, tmp_path, monkeypatch):
    ws, _, _, context_path, _, route_path = prepared
    ledger.initialise(ws, ws.load_config())
    instruction = tmp_path / "instruction.txt"
    instruction.write_text("Produce the governed draft.\n", encoding="utf-8")
    monkeypatch.setenv("CONCLAVE_HOME", str(ws.root))

    result = CliRunner().invoke(app, [
        "relay",
        "export-context",
        "--context",
        str(context_path),
        "--route",
        str(route_path),
        "--instruction",
        str(instruction),
        "--stage-index",
        "0",
    ])
    assert result.exit_code == 0, result.output
    assert "No provider API call was made." in result.output
    assert ledger.read_events(ws)[-1]["event_type"] == (
        "context_relay_prompt_exported"
    )


def test_reconciliation_recovers_context_relay_ledger_event(prepared):
    ws = prepared[0]
    record, _, _, _ = _export(prepared)
    ledger.initialise(ws, ws.load_config())
    report = reconcile(ws)
    recovered = [
        event for event in report.created
        if event["event_type"] == "context_relay_prompt_exported"
    ]
    assert len(recovered) == 1
    assert recovered[0]["artifact_hashes"]["context_relay_manifest"] == (
        record.content_hash
    )
