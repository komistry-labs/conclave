"""Governed sequential synthesis after an independent provider wave."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from .concurrency import ExecutionBatchRecord, read_batch
from .context import ContextBundle, read_context_bundle, render_context_prompt
from .council import (
    CouncilOutcome, CouncilReview, read_council, review_task,
    verify_council_content_hash,
)
from .errors import ValidationError, WorkspaceError
from .execution import RunRecord, execute_stage, read_run_record, write_run_record
from .handoff import (
    HandoffPacket, raw_dir, raw_filename, verify_handoff_content_hash,
)
from .hashing import hash_file, hash_text
from .ledger import canonical_json
from .models import TaskPacket
from .orchestration import OrchestrationRecord, read_orchestration
from .providers import EgressDecision, ProviderAdapter
from .routing import RoutePlan, read_route_plan
from .runhandoff import ConversionResult, _submission, convert_run
from .scope import (
    ReviewOutcome, ScopeReview, read_handoff, read_review, review_handoff,
    verify_review_content_hash,
)
from .taskpacket import read_packet, verify_content_hash
from .workspace import Workspace, utcnow

SYNTHESIS_SCHEMA_VERSION = "synthesis-continuation/0.1.0"
SynthesisPause = Literal[
    "awaiting_human_decision", "blocked_by_governance", "ambiguous_submissions"
]


class SynthesisContinuationRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[SYNTHESIS_SCHEMA_VERSION] = SYNTHESIS_SCHEMA_VERSION
    continuation_id: str
    source_orchestration_id: str
    source_orchestration_hash: str
    source_orchestration_file: str
    execution_batch_hash: str
    packet_ref: str
    task_packet_hash: str
    context_bundle_hash: str
    route_plan_hash: str
    synthesizer_stage_index: int = Field(ge=0)
    synthesizer_provider: str = Field(min_length=1)
    synthesizer_model: str = Field(min_length=1)
    egress_decision_ref: str = Field(min_length=1)
    source_stage_run_hashes: tuple[str, ...]
    synthesis_prompt_hash: str
    synthesis_run_hash: str
    synthesis_run_file: str
    handoff_hash: str
    handoff_file: str
    scope_review_hash: str
    scope_file: str
    scope_status: str
    council_review_id: str
    council_review_hash: str
    council_yaml_file: str
    council_markdown_file: str
    council_review_status: str
    started_at: str
    completed_at: str
    pause_state: SynthesisPause
    human_decision_required: Literal[True] = True
    action_execution_allowed: Literal[False] = False
    authority_note: str = (
        "CONCLAVE preserved independent evidence, captured one sequential synthesis, "
        "and paused. Only the constitutional authority may decide; this record "
        "authorises and executes nothing."
    )
    content_hash: str

    @model_validator(mode="after")
    def _verify(self) -> "SynthesisContinuationRecord":
        expected = _pause_for(self.council_review_status)
        if self.pause_state != expected:
            raise ValidationError("synthesis pause state contradicts Council status")
        if not self.source_stage_run_hashes:
            raise ValidationError("synthesis continuation requires predecessor runs")
        if self.content_hash != compute_synthesis_hash(self):
            raise ValidationError("synthesis continuation content_hash is stale")
        return self


@dataclass(frozen=True)
class SynthesisOutcome:
    record: SynthesisContinuationRecord
    path: Path
    created: bool
    run: RunRecord
    run_path: Path
    run_created: bool
    conversion: ConversionResult
    scope: ReviewOutcome
    council: CouncilOutcome


@dataclass(frozen=True)
class _Inputs:
    source: OrchestrationRecord
    source_path: Path
    packet: TaskPacket
    bundle: ContextBundle
    route: RoutePlan
    route_path: Path
    batch: ExecutionBatchRecord
    prior_runs: tuple[RunRecord, ...]
    handoffs: tuple[HandoffPacket, ...]


def _body(record: SynthesisContinuationRecord) -> dict:
    return record.model_dump(mode="json", exclude={"content_hash"})


def compute_synthesis_hash(record: SynthesisContinuationRecord) -> str:
    return hash_text(canonical_json(_body(record)))


def read_synthesis(path: Path) -> SynthesisContinuationRecord:
    if not path.exists():
        raise WorkspaceError(f"no synthesis continuation at {path}")
    return SynthesisContinuationRecord.model_validate(
        yaml.safe_load(path.read_text(encoding="utf-8"))
    )


def _pause_for(council_status: str) -> SynthesisPause:
    mapping = {
        "ready_for_human_review": "awaiting_human_decision",
        "blocked_by_governance": "blocked_by_governance",
        "ambiguous_submissions": "ambiguous_submissions",
    }
    if council_status not in mapping:
        raise ValidationError(
            f"sequential synthesis did not complete the Council: {council_status!r}"
        )
    return mapping[council_status]  # type: ignore[return-value]


def _one_by_hash(directory: Path, digest: str, reader, label: str):
    matches = []
    for path in directory.glob("*.yaml"):
        value = reader(path)
        if value.content_hash == digest:
            matches.append((value, path))
    if len(matches) != 1:
        raise ValidationError(
            f"expected exactly one stored {label} matching {digest}, found {len(matches)}"
        )
    return matches[0]


def _preflight(ws: Workspace, source_file: Path) -> _Inputs:
    source_file = Path(source_file).resolve()
    if source_file.parent != ws.orchestrations_dir.resolve():
        raise ValidationError(
            "source orchestration must be a stored artifact inside this workspace"
        )
    source = read_orchestration(source_file)
    if source.pause_state != "awaiting_sequential_synthesizer":
        raise ValidationError(
            "source orchestration is not paused for a sequential synthesizer"
        )

    batch, _ = _one_by_hash(
        ws.batches_dir, source.execution_batch_hash, read_batch, "Execution Batch"
    )
    route, route_path = _one_by_hash(
        ws.routes_dir, source.route_plan_hash, read_route_plan, "Route Plan"
    )
    bundle, _ = _one_by_hash(
        ws.context_dir, batch.context_bundle_hash, read_context_bundle, "Context Bundle"
    )
    task_id, version_text = source.packet_ref.rsplit("@v", 1)
    packet = read_packet(ws, task_id, int(version_text))
    if not verify_content_hash(packet) or packet.content_hash != source.task_packet_hash:
        raise ValidationError("source orchestration Task Packet does not verify")
    if bundle.packet_ref != packet.ref or bundle.packet_content_hash != packet.content_hash:
        raise ValidationError("stored Context Bundle binds different task evidence")
    if route.packet_ref != packet.ref or batch.route_plan_hash != route.content_hash:
        raise ValidationError("stored Route Plan binds different task evidence")
    if batch.task_packet_hash != packet.content_hash or \
            batch.context_bundle_hash != bundle.content_hash:
        raise ValidationError("stored Execution Batch binds different task evidence")
    if batch.status != "completed":
        raise ValidationError("source Execution Batch is not completed")

    final_index = len(route.stages) - 1
    if final_index < 1 or route.stages[final_index].role != "synthesizer":
        raise ValidationError("Route Plan has no final synthesizer stage")
    expected_indices = tuple(range(final_index))
    actual_indices = tuple(stage.stage_index for stage in source.processed_stages)
    if actual_indices != expected_indices or batch.stage_indices != expected_indices:
        raise ValidationError(
            "source orchestration does not contain every pre-synthesizer stage exactly once"
        )

    prior_runs: list[RunRecord] = []
    handoffs: list[HandoffPacket] = []
    scope_hashes: list[str] = []
    for stage in source.processed_stages:
        batch_result = batch.stage_results[stage.stage_index]
        if batch_result.run_content_hash != stage.run_content_hash or \
                batch_result.run_file != stage.run_file:
            raise ValidationError(
                f"source stage {stage.stage_index} differs from its Execution Batch"
            )
        run_path = ws.runs_dir / stage.run_file
        run = read_run_record(run_path)
        if run.content_hash != stage.run_content_hash or run.status != "completed":
            raise ValidationError(f"source stage {stage.stage_index} Run does not verify")
        if run.stage_index != stage.stage_index or \
                run.route_plan_hash != route.content_hash or \
                run.context_bundle_hash != bundle.content_hash or \
                run.packet_ref != packet.ref:
            raise ValidationError(f"source stage {stage.stage_index} Run binds different inputs")
        handoff = read_handoff(ws.inbox_dir / stage.handoff_file)
        if not verify_handoff_content_hash(handoff) or \
                handoff.content_hash != stage.handoff_content_hash:
            raise ValidationError(f"source stage {stage.stage_index} Handoff does not verify")
        route_stage = route.stages[stage.stage_index]
        if handoff.run_record_hash != run.content_hash or \
                handoff.route_plan_hash != route.content_hash or \
                handoff.route_stage_index != stage.stage_index or \
                (handoff.provider, handoff.role) != \
                (route_stage.provider, route_stage.role):
            raise ValidationError(
                f"source stage {stage.stage_index} Handoff binds different inputs"
            )
        scope = read_review(ws.root / "scope" / stage.scope_file)
        if not verify_review_content_hash(scope) or \
                scope.content_hash != stage.scope_review_hash or \
                scope.handoff_packet_hash != handoff.content_hash:
            raise ValidationError(f"source stage {stage.stage_index} Scope Review does not verify")
        prior_runs.append(run)
        handoffs.append(handoff)
        scope_hashes.append(scope.content_hash or "")

    council_path = ws.council_dir / source.council_yaml_file
    council = read_council(council_path)
    if not verify_council_content_hash(council) or \
            council.content_hash != source.council_review_hash or \
            council.review_status != "incomplete" or \
            council.route_plan_hash != route.content_hash:
        raise ValidationError("source Council Review does not verify as incomplete")
    if set(council.source_handoff_hashes) != {
        handoff.content_hash for handoff in handoffs
    } or set(council.source_scope_review_hashes) != set(scope_hashes):
        raise ValidationError("source Council Review cites different independent evidence")

    return _Inputs(
        source, source_file, packet, bundle, route, route_path, batch,
        tuple(prior_runs), tuple(handoffs),
    )


def build_synthesis_instruction(inputs: _Inputs, operator_instruction: str) -> str:
    if not operator_instruction.strip():
        raise ValidationError("synthesizer instruction must not be empty")
    evidence = []
    for source_stage, run, handoff in zip(
        inputs.source.processed_stages, inputs.prior_runs, inputs.handoffs
    ):
        evidence.append({
            "stage_index": run.stage_index,
            "provider": handoff.provider,
            "role": handoff.role,
            "run_content_hash": run.content_hash,
            "handoff_content_hash": handoff.content_hash,
            "scope_review_hash": source_stage.scope_review_hash,
            "scope_status": source_stage.scope_status,
            "submission": handoff.model_dump(
                mode="json", exclude={"imported_at", "content_hash"}
            ),
        })
    evidence_yaml = yaml.safe_dump(
        {"independent_submissions": evidence}, sort_keys=True, allow_unicode=True
    ).strip()
    return "\n".join([
        "# CONCLAVE governed sequential synthesis",
        "",
        f"source_orchestration_id: {inputs.source.orchestration_id}",
        f"source_orchestration_hash: {inputs.source.content_hash}",
        f"route_plan_hash: {inputs.route.content_hash}",
        "",
        "The submissions below are immutable advisory evidence. Synthesize them",
        "without erasing disagreement, inventing consensus, or claiming approval.",
        "Return one complete Handoff Packet for your assigned synthesizer role.",
        "A human decision remains mandatory and no action is authorised.",
        "",
        "## Independent evidence",
        "",
        "```yaml",
        evidence_yaml,
        "```",
        "",
        "## Operator instruction",
        "",
        operator_instruction.strip(),
        "",
    ])


def synthesis_target(ws: Workspace, source_file: Path) -> tuple[int, str]:
    """Return the verified final stage index and provider without executing it."""
    inputs = _preflight(ws, source_file)
    index = len(inputs.route.stages) - 1
    return index, inputs.route.stages[index].provider


def _existing_run(
    ws: Workspace, *, inputs: _Inputs, stage_index: int, model: str,
    decision_ref: str, expected_prompt_hash: str,
) -> tuple[RunRecord, Path] | None:
    matches = []
    for path in ws.runs_dir.glob("*.yaml"):
        run = read_run_record(path)
        if run.route_plan_hash == inputs.route.content_hash and run.stage_index == stage_index:
            matches.append((run, path))
    if not matches:
        return None
    if len(matches) != 1:
        raise ValidationError("multiple synthesizer Runs exist for the same Route Plan")
    run, path = matches[0]
    if run.response.model != model or run.egress_decision_ref != decision_ref:
        raise ValidationError("stored synthesizer Run uses different execution parameters")
    if hash_text(run.request.prompt) != expected_prompt_hash:
        raise ValidationError("stored synthesizer Run uses a different synthesis prompt")
    if run.status != "completed":
        raise ValidationError("stored synthesizer Run is not completed")
    submission = _submission(run)
    stage = inputs.route.stages[stage_index]
    for field_name, expected in {
        "packet_ref": inputs.packet.ref,
        "packet_content_hash": inputs.packet.content_hash,
        "provider": stage.provider,
        "role": "synthesizer",
    }.items():
        if submission.get(field_name) != expected:
            raise ValidationError(
                f"stored synthesizer Handoff field {field_name!r} differs from inputs"
            )
    return run, path


def _load_existing_outcome(
    ws: Workspace, path: Path, record: SynthesisContinuationRecord,
) -> SynthesisOutcome:
    run_path = ws.runs_dir / record.synthesis_run_file
    run = read_run_record(run_path)
    handoff_path = ws.inbox_dir / record.handoff_file
    handoff = read_handoff(handoff_path)
    scope_path = ws.root / "scope" / record.scope_file
    scope = read_review(scope_path)
    council_path = ws.council_dir / record.council_yaml_file
    council = read_council(council_path)
    raw_path = raw_dir(ws) / raw_filename(handoff.raw_response_hash)
    if run.content_hash != record.synthesis_run_hash or \
            hash_text(run.request.prompt) != record.synthesis_prompt_hash or \
            not verify_handoff_content_hash(handoff) or \
            handoff.content_hash != record.handoff_hash or \
            not verify_review_content_hash(scope) or \
            scope.content_hash != record.scope_review_hash or \
            not verify_council_content_hash(council) or \
            council.content_hash != record.council_review_hash or \
            not raw_path.exists() or \
            hash_file(raw_path, binary=True) != handoff.raw_response_hash:
        raise ValidationError("stored synthesis continuation dependencies do not verify")
    conversion = ConversionResult(
        handoff, handoff_path,
        raw_path, False,
    )
    review_outcome = ReviewOutcome(scope, scope_path, False)
    council_outcome = CouncilOutcome(
        council, council_path, ws.council_dir / record.council_markdown_file, False
    )
    return SynthesisOutcome(
        record, path, False, run, run_path, False,
        conversion, review_outcome, council_outcome,
    )


def execute_synthesis(
    *, ws: Workspace, source_file: Path, adapter: ProviderAdapter,
    decision: EgressDecision, model: str, operator_instruction: str,
    estimated_input_tokens: int,
) -> SynthesisOutcome:
    inputs = _preflight(ws, source_file)
    stage_index = len(inputs.route.stages) - 1
    stage = inputs.route.stages[stage_index]
    if adapter.provider != stage.provider:
        raise ValidationError("synthesizer adapter does not match the final route stage")
    if not decision.decision_ref:
        raise ValidationError("synthesizer execution requires an explicit decision reference")

    instruction = build_synthesis_instruction(inputs, operator_instruction)
    expected_prompt_hash = hash_text(render_context_prompt(inputs.bundle, instruction))
    existing_records = []
    for path in ws.synthesis_dir.glob("*.yaml"):
        record = read_synthesis(path)
        if record.source_orchestration_hash == inputs.source.content_hash:
            existing_records.append((record, path))
    if existing_records:
        if len(existing_records) != 1:
            raise ValidationError("multiple continuations cite the source orchestration")
        record, path = existing_records[0]
        if record.synthesizer_model != model or \
                record.egress_decision_ref != decision.decision_ref or \
                record.synthesis_prompt_hash != expected_prompt_hash:
            raise ValidationError("existing continuation uses different synthesis parameters")
        return _load_existing_outcome(ws, path, record)

    started_at = utcnow()
    existing_run = _existing_run(
        ws, inputs=inputs, stage_index=stage_index, model=model,
        decision_ref=decision.decision_ref, expected_prompt_hash=expected_prompt_hash,
    )
    if existing_run:
        run, run_path = existing_run
        run_created = False
    else:
        run = execute_stage(
            packet=inputs.packet, bundle=inputs.bundle, plan=inputs.route,
            stage_index=stage_index, adapter=adapter, decision=decision, model=model,
            prompt=instruction, estimated_input_tokens=estimated_input_tokens,
            prior_runs=list(inputs.prior_runs),
        )
        submission = _submission(run)
        for field_name, expected in {
            "packet_ref": inputs.packet.ref,
            "packet_content_hash": inputs.packet.content_hash,
            "provider": stage.provider,
            "role": "synthesizer",
        }.items():
            if submission.get(field_name) != expected:
                raise ValidationError(
                    f"synthesizer Handoff field {field_name!r} differs from governed inputs"
                )
        run_path, run_created = write_run_record(ws, run)

    conversion = convert_run(ws, run_path)
    scope = review_handoff(ws, conversion.handoff_path)
    council = review_task(
        ws, inputs.packet.task_id, inputs.packet.version, route_path=inputs.route_path
    )
    pause = _pause_for(council.review.review_status)
    completed_at = utcnow()
    identity = canonical_json({
        "source_orchestration_hash": inputs.source.content_hash,
        "synthesis_run_hash": run.content_hash,
        "council_review_hash": council.review.content_hash,
    })
    continuation_id = "SC-" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]
    data = {
        "schema_version": SYNTHESIS_SCHEMA_VERSION,
        "continuation_id": continuation_id,
        "source_orchestration_id": inputs.source.orchestration_id,
        "source_orchestration_hash": inputs.source.content_hash,
        "source_orchestration_file": inputs.source_path.name,
        "execution_batch_hash": inputs.batch.content_hash,
        "packet_ref": inputs.packet.ref,
        "task_packet_hash": inputs.packet.content_hash,
        "context_bundle_hash": inputs.bundle.content_hash,
        "route_plan_hash": inputs.route.content_hash,
        "synthesizer_stage_index": stage_index,
        "synthesizer_provider": stage.provider,
        "synthesizer_model": model,
        "egress_decision_ref": decision.decision_ref,
        "source_stage_run_hashes": tuple(run.content_hash for run in inputs.prior_runs),
        "synthesis_prompt_hash": hash_text(run.request.prompt),
        "synthesis_run_hash": run.content_hash,
        "synthesis_run_file": run_path.name,
        "handoff_hash": conversion.packet.content_hash,
        "handoff_file": conversion.handoff_path.name,
        "scope_review_hash": scope.review.content_hash,
        "scope_file": scope.path.name,
        "scope_status": scope.review.scope_status,
        "council_review_id": council.review.council_review_id,
        "council_review_hash": council.review.content_hash,
        "council_yaml_file": council.yaml_path.name,
        "council_markdown_file": council.markdown_path.name,
        "council_review_status": council.review.review_status,
        "started_at": started_at,
        "completed_at": completed_at,
        "pause_state": pause,
    }
    draft = SynthesisContinuationRecord.model_construct(**data, content_hash="pending")
    record = SynthesisContinuationRecord.model_validate({
        **data, "content_hash": compute_synthesis_hash(draft),
    })
    suffix = record.content_hash.split(":", 1)[-1][:12]
    path = ws.synthesis_dir / f"{continuation_id}__{suffix}.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        existing = read_synthesis(path)
        if existing.content_hash != record.content_hash:
            raise WorkspaceError(f"different synthesis continuation exists at {path}")
        return _load_existing_outcome(ws, path, existing)
    text = yaml.safe_dump(record.model_dump(mode="json"), sort_keys=False, allow_unicode=True)
    path.write_bytes(text.replace("\r\n", "\n").encode("utf-8"))
    return SynthesisOutcome(
        record, path, True, run, run_path, run_created, conversion, scope, council
    )
