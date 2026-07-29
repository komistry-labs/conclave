import yaml
from pathlib import Path
from typer.testing import CliRunner

from conclave import ledger
from conclave.cli import app
from conclave.context import (
    ContextSource, build_context_bundle, write_context_bundle,
)
from conclave.providers import FixtureAdapter, read_egress_decision
from conclave.routing import (
    ProviderCapability, TokenBudget, build_route, write_route_plan,
)
from conclave.taskpacket import build_packet, write_packet
from conclave.workspace import Workspace


def setup_live_workspace(tmp_path):
    ws = Workspace.create(tmp_path, principal="Arthur")
    packet = build_packet(objective="live stage", created_by="Arthur")
    write_packet(ws, packet)
    bundle = build_context_bundle(
        packet_ref=packet.ref, packet_content_hash=packet.content_hash,
        sources=[ContextSource.seal(
            object_id="DOC-001", status="active", authority="Arthur",
            classification="internal", content="facts",
        )],
    )
    context_path, _ = write_context_bundle(ws, bundle)
    plan = build_route(
        packet_ref=packet.ref, risk="routine",
        capabilities=[
            ProviderCapability(provider="adrian", roles=frozenset({"lead"}))
        ],
        budget=TokenBudget(max_input_tokens=1000, max_output_tokens=100),
    )
    route_path, _ = write_route_plan(ws, plan)
    prompt_path = tmp_path / "prompt.txt"
    prompt_path.write_text("perform governed work", encoding="utf-8")
    return ws, context_path, route_path, prompt_path


def write_policy(tmp_path, **overrides):
    data = {
        "schema_version": "egress-decision/0.1.0",
        "allowed": True,
        "transports": ["openai-responses-api"],
        "classifications": ["internal"],
        "authority": "Arthur",
        "decision_ref": "D7-TEST-AUTHORITY",
        **overrides,
    }
    path = tmp_path / "egress.yaml"
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


def command_args(context_path, route_path, prompt_path, policy_path):
    return [
        "run", "live",
        "--context", str(context_path),
        "--route", str(route_path),
        "--prompt", str(prompt_path),
        "--egress-decision", str(policy_path),
        "--model", "gpt-test",
        "--estimated-input-tokens", "3",
    ]


def test_live_command_refuses_non_principal_policy_before_adapter(
    tmp_path, monkeypatch
):
    ws, context_path, route_path, prompt_path = setup_live_workspace(tmp_path)
    policy = write_policy(tmp_path, authority="Not Arthur")
    monkeypatch.setenv("CONCLAVE_HOME", str(ws.root))

    class MustNotConstruct:
        def __init__(self, **kwargs):
            raise AssertionError("adapter was constructed")

    monkeypatch.setattr(
        "conclave.live_providers.OpenAIAdapter", MustNotConstruct
    )
    result = CliRunner().invoke(
        app, command_args(context_path, route_path, prompt_path, policy)
    )
    assert result.exit_code == 1
    assert "authority does not match" in result.output
    assert list(ws.runs_dir.glob("*.yaml")) == []


def test_live_command_uses_route_adapter_and_captures_run(
    tmp_path, monkeypatch
):
    ws, context_path, route_path, prompt_path = setup_live_workspace(tmp_path)
    policy = write_policy(tmp_path)
    ledger.initialise(ws, ws.load_config())
    monkeypatch.setenv("CONCLAVE_HOME", str(ws.root))

    def adapter_factory(*, provider, timeout_seconds):
        assert provider == "adrian"
        assert timeout_seconds == 120.0
        return FixtureAdapter(
            provider=provider,
            transport="openai-responses-api",
            response_text="normalized live response",
        )

    monkeypatch.setattr(
        "conclave.live_providers.OpenAIAdapter", adapter_factory
    )
    result = CliRunner().invoke(
        app, command_args(context_path, route_path, prompt_path, policy)
    )
    assert result.exit_code == 0, result.output
    assert "provider: adrian" in result.output
    assert "model: gpt-test" in result.output
    assert "tokens:" in result.output
    assert list(ws.runs_dir.glob("*.yaml"))
    event = ledger.read_events(ws)[-1]
    assert event["event_type"] == "provider_run_captured"
    assert event["payload"]["egress_decision_ref"] == "D7-TEST-AUTHORITY"


def test_release_d7_policy_is_machine_readable_and_narrow():
    policy_path = (
        Path(__file__).resolve().parents[1]
        / "policies"
        / "D7-PROVIDER-EGRESS-v1.yaml"
    )
    decision = read_egress_decision(policy_path, principal="Arthur")
    assert decision.transports == frozenset({
        "openai-responses-api",
        "anthropic-messages-api",
        "gemini-generate-content-api",
    })
    assert decision.classifications == frozenset({"public", "internal"})
    assert "restricted" not in decision.classifications
    assert "constitutional" not in decision.classifications
