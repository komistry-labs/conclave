import pytest
import yaml
from typer.testing import CliRunner

from conclave import ledger
from conclave.cli import app
from conclave.context import (
    ContextSource, build_context_bundle, read_context_bundle, write_context_bundle,
)
from conclave.routing import (
    ProviderCapability, TokenBudget, build_route, read_route_plan, write_route_plan,
)
from conclave.workspace import Workspace
from conclave.taskpacket import build_packet, write_packet


@pytest.fixture
def ws(tmp_path):
    return Workspace.create(tmp_path, principal="Arthur")


def test_context_bundle_write_once_round_trip(ws):
    bundle = build_context_bundle(
        packet_ref="TP-example-0123456789@v1",
        packet_content_hash="sha256:packet",
        sources=[ContextSource.seal(
            object_id="DOC-001", status="active", authority="Arthur",
            classification="internal", content="facts",
        )],
    )
    path, created = write_context_bundle(ws, bundle)
    assert created
    assert read_context_bundle(path) == bundle
    same_path, created = write_context_bundle(ws, bundle)
    assert same_path == path
    assert not created
    assert b"\r\n" not in path.read_bytes()


def test_route_plan_write_once_round_trip(ws):
    all_roles = frozenset({"lead", "critic", "verifier", "synthesizer"})
    plan = build_route(
        packet_ref="TP-example-0123456789@v1", risk="important",
        capabilities=[
            ProviderCapability(provider="a", roles=all_roles),
            ProviderCapability(provider="b", roles=all_roles),
        ],
        budget=TokenBudget(max_input_tokens=1000, max_output_tokens=500),
    )
    path, created = write_route_plan(ws, plan)
    assert created
    assert read_route_plan(path) == plan
    _, created = write_route_plan(ws, plan)
    assert not created
    assert b"\r\n" not in path.read_bytes()


def _task(ws):
    packet = build_packet(
        objective="Exercise context and route commands", created_by="Arthur"
    )
    write_packet(ws, packet)
    return packet


def test_context_create_command_records_artifact(ws, tmp_path, monkeypatch):
    packet = _task(ws)
    ledger.initialise(ws, ws.load_config())
    manifest = tmp_path / "context.yaml"
    manifest.write_text(yaml.safe_dump({"sources": [{
        "object_id": "DOC-001", "status": "active", "authority": "Arthur",
        "classification": "internal", "content": "facts",
    }]}), encoding="utf-8")
    monkeypatch.setenv("CONCLAVE_HOME", str(ws.root))
    result = CliRunner().invoke(app, [
        "context", "create", packet.task_id, "--manifest", str(manifest),
    ])
    assert result.exit_code == 0, result.output
    assert "created:" in result.output
    assert list(ws.context_dir.glob("*.yaml"))
    assert ledger.read_events(ws)[-1]["event_type"] == "context_bundle_created"


def test_route_plan_command_records_artifact(ws, monkeypatch):
    packet = _task(ws)
    ledger.initialise(ws, ws.load_config())
    monkeypatch.setenv("CONCLAVE_HOME", str(ws.root))
    result = CliRunner().invoke(app, [
        "route", "plan", packet.task_id, "--risk", "important",
        "--max-input-tokens", "1000", "--max-output-tokens", "500",
        "-c", "adrian:lead", "-c", "claude:critic",
    ])
    assert result.exit_code == 0, result.output
    assert "lead: adrian" in result.output
    assert "critic: claude" in result.output
    assert list(ws.routes_dir.glob("*.yaml"))
    assert ledger.read_events(ws)[-1]["event_type"] == "route_plan_created"
