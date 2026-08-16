from pathlib import Path

import yaml
from typer.testing import CliRunner

from conclave import ledger
from conclave.cli import app
from conclave.context import ContextSource, build_context_bundle, write_context_bundle
from conclave.providers import FixtureAdapter
from conclave.routing import ProviderCapability, TokenBudget, build_route, write_route_plan
from conclave.taskpacket import build_packet, write_packet
from conclave.workspace import Workspace


def setup_cli(tmp_path):
    ws = Workspace.create(tmp_path, principal="Arthur")
    packet = build_packet(objective="Concurrent live CLI", created_by="Arthur")
    write_packet(ws, packet)
    bundle = build_context_bundle(
        packet_ref=packet.ref, packet_content_hash=packet.content_hash,
        sources=[ContextSource.seal(
            object_id="DOC", status="active", authority="Arthur",
            classification="internal", content="facts",
        )],
    )
    context_path, _ = write_context_bundle(ws, bundle)
    plan = build_route(
        packet_ref=packet.ref, risk="important",
        capabilities=[
            ProviderCapability(provider="adrian", roles=frozenset({"lead"})),
            ProviderCapability(provider="claude", roles=frozenset({"critic"})),
        ],
        budget=TokenBudget(max_input_tokens=100, max_output_tokens=20),
    )
    route_path, _ = write_route_plan(ws, plan)
    policy = tmp_path / "egress.yaml"
    policy.write_text(yaml.safe_dump({
        "schema_version": "egress-decision/0.1.0", "allowed": True,
        "transports": ["openai-responses-api", "anthropic-messages-api"],
        "classifications": ["internal"], "authority": "Arthur",
        "decision_ref": "D7-CONCURRENT-CLI",
    }, sort_keys=False), encoding="utf-8")
    prompts = []
    for index in range(2):
        path = tmp_path / f"prompt-{index}.txt"
        path.write_text(f"isolated {index}", encoding="utf-8")
        prompts.append(path)
    return ws, context_path, route_path, policy, prompts


def args(context, route, policy, prompts):
    return [
        "run", "concurrent-live", "--context", str(context),
        "--route", str(route), "--egress-decision", str(policy),
        "--model", "0:gpt-test", "--model", "1:claude-test",
        "--prompt", f"0:{prompts[0]}", "--prompt", f"1:{prompts[1]}",
        "--estimated-input", "0:2", "--estimated-input", "1:2",
        "--max-workers", "2",
    ]


def test_concurrent_live_cli_uses_registered_adapters_and_records_ledger(
    tmp_path, monkeypatch
):
    ws, context, route, policy, prompts = setup_cli(tmp_path)
    ledger.initialise(ws, ws.load_config())
    monkeypatch.setenv("CONCLAVE_HOME", str(ws.root))

    monkeypatch.setattr(
        "conclave.live_providers.OpenAIAdapter",
        lambda *, provider, timeout_seconds: FixtureAdapter(
            provider=provider, transport="openai-responses-api", response_text="lead"
        ),
    )
    monkeypatch.setattr(
        "conclave.live_providers.ClaudeAdapter",
        lambda *, timeout_seconds: FixtureAdapter(
            provider="claude", transport="anthropic-messages-api", response_text="critic"
        ),
    )
    result = CliRunner().invoke(app, args(context, route, policy, prompts))
    assert result.exit_code == 0, result.output
    assert "CONCURRENT WAVE COMPLETED" in result.output
    assert len(list(ws.runs_dir.glob("*.yaml"))) == 2
    assert len(list(ws.batches_dir.glob("*.yaml"))) == 1
    event_types = [event["event_type"] for event in ledger.read_events(ws)]
    assert event_types[-3:] == [
        "provider_run_captured", "provider_run_captured", "execution_batch_recorded"
    ]


def test_concurrent_live_cli_refuses_missing_stage_mapping_before_calls(
    tmp_path, monkeypatch
):
    ws, context, route, policy, prompts = setup_cli(tmp_path)
    monkeypatch.setenv("CONCLAVE_HOME", str(ws.root))

    class MustNotCall(FixtureAdapter):
        def execute(self, request):
            raise AssertionError("adapter was called")

    monkeypatch.setattr(
        "conclave.live_providers.OpenAIAdapter",
        lambda **kwargs: MustNotCall(
            provider="adrian", transport="openai-responses-api"
        ),
    )
    monkeypatch.setattr(
        "conclave.live_providers.ClaudeAdapter",
        lambda **kwargs: MustNotCall(
            provider="claude", transport="anthropic-messages-api"
        ),
    )
    incomplete = args(context, route, policy, prompts)
    model_position = incomplete.index("1:claude-test")
    del incomplete[model_position - 1:model_position + 1]
    result = CliRunner().invoke(app, incomplete)
    assert result.exit_code == 1
    assert "models must contain exactly" in result.output
    assert not list(ws.runs_dir.glob("*.yaml"))


def test_concurrent_live_cli_refuses_duplicate_provider_cost(tmp_path, monkeypatch):
    ws, context, route, policy, prompts = setup_cli(tmp_path)
    ledger.initialise(ws, ws.load_config())
    monkeypatch.setenv("CONCLAVE_HOME", str(ws.root))
    monkeypatch.setattr(
        "conclave.live_providers.OpenAIAdapter",
        lambda *, provider, timeout_seconds: FixtureAdapter(
            provider=provider, transport="openai-responses-api"
        ),
    )
    monkeypatch.setattr(
        "conclave.live_providers.ClaudeAdapter",
        lambda *, timeout_seconds: FixtureAdapter(
            provider="claude", transport="anthropic-messages-api"
        ),
    )
    first = CliRunner().invoke(app, args(context, route, policy, prompts))
    assert first.exit_code == 0, first.output
    before = len(list(ws.runs_dir.glob("*.yaml")))
    second = CliRunner().invoke(app, args(context, route, policy, prompts))
    assert second.exit_code == 1
    assert "refusing duplicate provider calls" in second.output
    assert len(list(ws.runs_dir.glob("*.yaml"))) == before
