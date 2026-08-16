import threading
from dataclasses import dataclass, field

import pytest

from conclave.concurrency import (
    RetryPolicy, execute_concurrent, read_batch, write_concurrent_outcome,
)
from conclave.context import ContextSource, build_context_bundle
from conclave.errors import ProviderError, ValidationError
from conclave.execution import execute_stage
from conclave.providers import (
    EgressDecision, FixtureAdapter, ProviderResponse, ProviderUsage,
)
from conclave.routing import ProviderCapability, TokenBudget, build_route
from conclave.taskpacket import build_packet
from conclave.workspace import Workspace


def setup_wave(tmp_path, *, risk="important", max_input=100, max_output=21):
    ws = Workspace.create(tmp_path, principal="Arthur")
    packet = build_packet(objective="Concurrent independent review", created_by="Arthur")
    bundle = build_context_bundle(
        packet_ref=packet.ref, packet_content_hash=packet.content_hash,
        sources=[ContextSource.seal(
            object_id="DOC-001", status="active", authority="Arthur",
            classification="internal", content="shared governed facts",
        )],
    )
    capabilities = [
        ProviderCapability(provider="adrian", roles=frozenset({"lead"})),
        ProviderCapability(
            provider="claude", roles=frozenset({"critic", "synthesizer"})
        ),
        ProviderCapability(provider="gemini", roles=frozenset({"verifier"})),
    ]
    plan = build_route(
        packet_ref=packet.ref, risk=risk, capabilities=capabilities,
        budget=TokenBudget(max_input_tokens=max_input, max_output_tokens=max_output),
    )
    return ws, packet, bundle, plan


def decision(bundle, transport="fixture"):
    return EgressDecision(
        allowed=True, transports=frozenset({transport}),
        classifications=frozenset(source.classification for source in bundle.sources),
        authority="Arthur", decision_ref="D7-CONCURRENT-TEST",
    )


def arguments(bundle, plan, adapters):
    indices = tuple(range(len(adapters)))
    return dict(
        stage_indices=indices,
        adapters={index: adapter for index, adapter in enumerate(adapters)},
        decisions={index: decision(bundle) for index in indices},
        models={index: f"model-{index}" for index in indices},
        prompts={index: f"isolated prompt {index}" for index in indices},
        estimated_input_tokens={index: 2 for index in indices},
    )


def test_independent_stages_really_overlap(tmp_path):
    _, packet, bundle, plan = setup_wave(tmp_path)
    barrier = threading.Barrier(2)

    @dataclass
    class BarrierAdapter(FixtureAdapter):
        def execute(self, request):
            barrier.wait(timeout=2)
            return super().execute(request)

    adapters = [BarrierAdapter(provider="adrian"), BarrierAdapter(provider="claude")]
    outcome = execute_concurrent(
        packet=packet, bundle=bundle, plan=plan, max_workers=2,
        **arguments(bundle, plan, adapters),
    )
    assert outcome.record.status == "completed"
    assert [result.stage_index for result in outcome.record.stage_results] == [0, 1]
    assert [run.stage_index for run in outcome.runs] == [0, 1]


def test_results_are_deterministic_by_stage_not_completion_order(tmp_path):
    _, packet, bundle, plan = setup_wave(tmp_path)
    release = threading.Event()

    @dataclass
    class OrderedAdapter(FixtureAdapter):
        wait: bool = False

        def execute(self, request):
            if self.wait:
                release.wait(timeout=2)
            else:
                release.set()
            return super().execute(request)

    adapters = [
        OrderedAdapter(provider="adrian", wait=True),
        OrderedAdapter(provider="claude", wait=False),
    ]
    outcome = execute_concurrent(
        packet=packet, bundle=bundle, plan=plan, max_workers=2,
        **arguments(bundle, plan, adapters),
    )
    assert tuple(result.stage_index for result in outcome.record.stage_results) == (0, 1)


def test_prompts_remain_provider_isolated(tmp_path):
    _, packet, bundle, plan = setup_wave(tmp_path)

    @dataclass
    class CaptureAdapter(FixtureAdapter):
        seen: list[str] = field(default_factory=list)

        def execute(self, request):
            self.seen.append(request.prompt)
            return super().execute(request)

    adapters = [CaptureAdapter(provider="adrian"), CaptureAdapter(provider="claude")]
    execute_concurrent(
        packet=packet, bundle=bundle, plan=plan, **arguments(bundle, plan, adapters)
    )
    assert "isolated prompt 0" in adapters[0].seen[0]
    assert "isolated prompt 1" not in adapters[0].seen[0]
    assert "isolated prompt 1" in adapters[1].seen[0]
    assert "isolated prompt 0" not in adapters[1].seen[0]


def test_output_budget_is_reserved_before_dispatch(tmp_path):
    _, packet, bundle, plan = setup_wave(tmp_path, max_output=21)

    @dataclass
    class CaptureCeiling(FixtureAdapter):
        ceiling: int = 0

        def execute(self, request):
            self.ceiling = request.max_output_tokens
            return super().execute(request)

    adapters = [CaptureCeiling(provider="adrian"), CaptureCeiling(provider="claude")]
    execute_concurrent(
        packet=packet, bundle=bundle, plan=plan, **arguments(bundle, plan, adapters)
    )
    assert [adapter.ceiling for adapter in adapters] == [11, 10]


def test_aggregate_actual_input_overage_is_recorded(tmp_path):
    _, packet, bundle, plan = setup_wave(tmp_path, max_input=10)

    @dataclass
    class InputOverage(FixtureAdapter):
        def execute(self, request):
            return ProviderResponse(
                provider=self.provider, model=request.model, transport=self.transport,
                text="result", usage=ProviderUsage(input_tokens=6, output_tokens=1),
                finish_status="completed",
            )

    adapters = [InputOverage(provider="adrian"), InputOverage(provider="claude")]
    outcome = execute_concurrent(
        packet=packet, bundle=bundle, plan=plan,
        **arguments(bundle, plan, adapters),
    )
    assert outcome.record.status == "budget_exceeded"
    assert outcome.record.cumulative_input_tokens == 12
    assert "exceeds ceiling 10" in outcome.record.budget_defects[0]


def test_retry_is_bounded_and_unknown_usage_is_disclosed(tmp_path):
    _, packet, bundle, plan = setup_wave(tmp_path)

    @dataclass
    class Flaky(FixtureAdapter):
        calls: int = 0

        def execute(self, request):
            self.calls += 1
            if self.calls == 1:
                raise ProviderError("secret echoed by provider")
            return super().execute(request)

    adapters = [Flaky(provider="adrian"), FixtureAdapter(provider="claude")]
    outcome = execute_concurrent(
        packet=packet, bundle=bundle, plan=plan,
        retry_policy=RetryPolicy(max_attempts=2),
        **arguments(bundle, plan, adapters),
    )
    assert outcome.record.stage_results[0].attempts == 2
    assert not outcome.record.usage_complete
    assert "unreported tokens" in outcome.record.usage_note
    assert "secret echoed" not in outcome.record.model_dump_json()


def test_preset_cancellation_prevents_all_adapter_calls(tmp_path):
    _, packet, bundle, plan = setup_wave(tmp_path)
    cancelled = threading.Event()
    cancelled.set()

    class MustNotRun(FixtureAdapter):
        def execute(self, request):
            raise AssertionError("cancelled adapter was called")

    adapters = [MustNotRun(provider="adrian"), MustNotRun(provider="claude")]
    outcome = execute_concurrent(
        packet=packet, bundle=bundle, plan=plan, cancel_event=cancelled,
        **arguments(bundle, plan, adapters),
    )
    assert outcome.record.status == "cancelled"
    assert [result.attempts for result in outcome.record.stage_results] == [0, 0]


def test_fail_fast_cancels_queued_stage_but_preserves_failure(tmp_path):
    _, packet, bundle, plan = setup_wave(tmp_path)

    class Fails(FixtureAdapter):
        def execute(self, request):
            raise ProviderError("do not persist this detail")

    class MustNotRun(FixtureAdapter):
        def execute(self, request):
            raise AssertionError("queued adapter was called")

    adapters = [Fails(provider="adrian"), MustNotRun(provider="claude")]
    outcome = execute_concurrent(
        packet=packet, bundle=bundle, plan=plan, max_workers=1, fail_fast=True,
        **arguments(bundle, plan, adapters),
    )
    assert [result.status for result in outcome.record.stage_results] == [
        "failed", "cancelled"
    ]
    assert "do not persist" not in outcome.record.model_dump_json()


def test_synthesizer_is_never_concurrent_and_can_follow_wave(tmp_path):
    _, packet, bundle, plan = setup_wave(tmp_path, risk="canonical", max_output=100)
    adapters = [
        FixtureAdapter(provider="adrian"), FixtureAdapter(provider="claude"),
        FixtureAdapter(provider="gemini"),
    ]
    wave = execute_concurrent(
        packet=packet, bundle=bundle, plan=plan,
        **arguments(bundle, plan, adapters),
    )
    with pytest.raises(ValidationError, match="synthesizer"):
        execute_concurrent(
            packet=packet, bundle=bundle, plan=plan,
            stage_indices=(3,), adapters={3: FixtureAdapter(provider="claude")},
            decisions={3: decision(bundle)}, models={3: "model-3"},
            prompts={3: "synthesize"}, estimated_input_tokens={3: 1},
            prior_runs=wave.runs,
        )
    final = execute_stage(
        packet=packet, bundle=bundle, plan=plan, stage_index=3,
        adapter=FixtureAdapter(provider="claude"), decision=decision(bundle),
        model="model-3", prompt="synthesize", estimated_input_tokens=1,
        prior_runs=list(wave.runs),
    )
    assert final.role == "synthesizer"


def test_write_round_trip_is_sorted_and_lf(tmp_path):
    ws, packet, bundle, plan = setup_wave(tmp_path)
    adapters = [FixtureAdapter(provider="adrian"), FixtureAdapter(provider="claude")]
    outcome = execute_concurrent(
        packet=packet, bundle=bundle, plan=plan,
        **arguments(bundle, plan, adapters),
    )
    stored = write_concurrent_outcome(ws, outcome)
    assert stored.batch_created
    assert read_batch(stored.batch_path) == outcome.record
    assert b"\r\n" not in stored.batch_path.read_bytes()
    assert [path.name for path, _ in stored.run_paths] == sorted(
        path.name for path, _ in stored.run_paths
    )


def test_reconciliation_discovers_batch_but_not_duplicate_run_semantics(tmp_path):
    from conclave import ledger
    from conclave.reconcile import reconcile

    ws, packet, bundle, plan = setup_wave(tmp_path)
    ledger.initialise(ws, ws.load_config())
    adapters = [FixtureAdapter(provider="adrian"), FixtureAdapter(provider="claude")]
    stored = write_concurrent_outcome(
        ws,
        execute_concurrent(
            packet=packet, bundle=bundle, plan=plan,
            **arguments(bundle, plan, adapters),
        ),
    )
    report = reconcile(ws)
    events = ledger.read_events(ws)
    assert any(event["event_type"] == "execution_batch_recorded" for event in events)
    assert any(
        event["artifact_hashes"].get("execution_batch") == stored.record.content_hash
        for event in events
    )
    before = len(events)
    reconcile(ws)
    assert len(ledger.read_events(ws)) == before


def test_wave_preflight_refuses_gap_and_mismatched_maps(tmp_path):
    _, packet, bundle, plan = setup_wave(tmp_path, risk="canonical")
    with pytest.raises(ValidationError, match="contiguous"):
        execute_concurrent(
            packet=packet, bundle=bundle, plan=plan,
            stage_indices=(0, 2),
            adapters={0: FixtureAdapter(provider="adrian"),
                      2: FixtureAdapter(provider="gemini")},
            decisions={0: decision(bundle), 2: decision(bundle)},
            models={0: "m0", 2: "m2"}, prompts={0: "p0", 2: "p2"},
            estimated_input_tokens={0: 1, 2: 1},
        )


def test_one_invalid_egress_decision_prevents_every_provider_call(tmp_path):
    _, packet, bundle, plan = setup_wave(tmp_path)

    class MustNotRun(FixtureAdapter):
        def execute(self, request):
            raise AssertionError("adapter was called before whole-wave preflight")

    adapters = {0: MustNotRun(provider="adrian"), 1: MustNotRun(provider="claude")}
    decisions = {
        0: decision(bundle),
        1: EgressDecision(
            allowed=False, transports=frozenset({"fixture"}),
            classifications=frozenset({"internal"}), authority="Arthur",
            decision_ref="DENIED",
        ),
    }
    with pytest.raises(ValidationError, match="not explicitly authorised"):
        execute_concurrent(
            packet=packet, bundle=bundle, plan=plan, stage_indices=(0, 1),
            adapters=adapters, decisions=decisions,
            models={0: "m0", 1: "m1"}, prompts={0: "p0", 1: "p1"},
            estimated_input_tokens={0: 1, 1: 1},
        )
