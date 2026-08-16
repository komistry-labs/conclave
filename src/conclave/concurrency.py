"""Bounded concurrent execution for independent provider-review waves.

Lead, critic, and verifier stages may execute concurrently because each sees
only its own governed prompt and the same sealed Context Bundle. A synthesizer
is never admitted to a concurrent wave: it remains sequential and must follow
the captured independent runs.

Cancellation is cooperative. Queued work and retries observe the cancellation
event; an HTTP call already in flight cannot be forcefully interrupted by the
stdlib adapters and its result is preserved if it completes.
"""

from __future__ import annotations

import hashlib
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from .context import ContextBundle
from .errors import ConclaveError, ProviderError, ValidationError, WorkspaceError
from .execution import RunRecord, _execute_stage, run_path, write_run_record
from .hashing import hash_text
from .ledger import canonical_json
from .models import TaskPacket
from .providers import EgressDecision, ProviderAdapter
from .routing import RoutePlan
from .taskpacket import verify_content_hash
from .workspace import Workspace, utcnow

BATCH_SCHEMA_VERSION = "execution-batch/0.1.0"
BatchStatus = Literal[
    "completed", "partial_failure", "failed", "cancelled", "budget_exceeded"
]
StageStatus = Literal["completed", "budget_exceeded", "failed", "cancelled"]


class RetryPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    max_attempts: int = Field(1, ge=1, le=3)
    retry_provider_errors: bool = True


class BatchStageResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    stage_index: int = Field(ge=0)
    provider: str = Field(min_length=1)
    role: str = Field(min_length=1)
    status: StageStatus
    attempts: int = Field(ge=0, le=3)
    output_token_reservation: int = Field(gt=0)
    run_content_hash: str | None = None
    run_file: str | None = None
    error_code: Literal[
        "provider-execution-failed", "stage-validation-failed", "cancelled"
    ] | None = None

    @model_validator(mode="after")
    def _consistent(self) -> "BatchStageResult":
        has_run = self.run_content_hash is not None and self.run_file is not None
        if self.run_file is not None and Path(self.run_file).name != self.run_file:
            raise ValueError("run_file must be a basename inside the workspace runs directory")
        if self.status in ("completed", "budget_exceeded") and not has_run:
            raise ValueError("completed stage result must cite its Provider Run")
        if self.status in ("failed", "cancelled") and has_run:
            raise ValueError("failed or cancelled stage result cannot cite a Provider Run")
        if self.status in ("failed", "cancelled") and not self.error_code:
            raise ValueError("failed or cancelled stage result requires an error code")
        if self.status in ("completed", "budget_exceeded") and self.error_code:
            raise ValueError("completed stage result cannot carry an error code")
        if self.status in ("completed", "budget_exceeded", "failed") and self.attempts < 1:
            raise ValueError("a dispatched stage result requires at least one attempt")
        return self


class ExecutionBatchRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[BATCH_SCHEMA_VERSION] = BATCH_SCHEMA_VERSION
    batch_id: str
    packet_ref: str
    task_packet_hash: str
    context_bundle_hash: str
    route_plan_hash: str
    stage_indices: tuple[int, ...]
    max_workers: int = Field(ge=1, le=8)
    retry_policy: RetryPolicy
    fail_fast: bool
    started_at: str
    completed_at: str
    status: BatchStatus
    stage_results: tuple[BatchStageResult, ...]
    wave_input_tokens: int = Field(ge=0)
    wave_output_tokens: int = Field(ge=0)
    cumulative_input_tokens: int = Field(ge=0)
    cumulative_output_tokens: int = Field(ge=0)
    usage_complete: bool
    usage_note: str
    budget_defects: tuple[str, ...] = ()
    cancellation_note: str
    content_hash: str

    @model_validator(mode="after")
    def _verify(self) -> "ExecutionBatchRecord":
        if not self.stage_indices or tuple(sorted(set(self.stage_indices))) != self.stage_indices:
            raise ValidationError("batch stage indices are not non-empty, sorted and unique")
        if tuple(result.stage_index for result in self.stage_results) != self.stage_indices:
            raise ValidationError("batch results do not match stage indices")
        statuses = {result.status for result in self.stage_results}
        if self.budget_defects or "budget_exceeded" in statuses:
            expected = "budget_exceeded"
        elif statuses == {"completed"}:
            expected = "completed"
        elif statuses == {"cancelled"}:
            expected = "cancelled"
        elif "completed" in statuses:
            expected = "partial_failure"
        else:
            expected = "failed"
        if self.status != expected:
            raise ValidationError(
                f"batch status {self.status!r} does not match stage outcomes {expected!r}"
            )
        usage_complete = all(
            result.attempts == 1 and result.status in ("completed", "budget_exceeded")
            or result.attempts == 0 and result.status == "cancelled"
            for result in self.stage_results
        )
        if self.usage_complete != usage_complete:
            raise ValidationError("batch usage completeness does not match stage attempts")
        if self.content_hash != compute_batch_hash(self):
            raise ValidationError("execution batch content_hash is stale")
        return self


@dataclass(frozen=True)
class ConcurrentOutcome:
    record: ExecutionBatchRecord
    runs: tuple[RunRecord, ...]


@dataclass(frozen=True)
class StoredConcurrentOutcome:
    record: ExecutionBatchRecord
    batch_path: Path
    batch_created: bool
    run_paths: tuple[tuple[Path, bool], ...]


def _batch_body(record: ExecutionBatchRecord) -> dict:
    return record.model_dump(mode="json", exclude={"content_hash"})


def compute_batch_hash(record: ExecutionBatchRecord) -> str:
    return hash_text(canonical_json(_batch_body(record)))


def read_batch(path: Path) -> ExecutionBatchRecord:
    if not path.exists():
        raise WorkspaceError(f"no execution batch at {path}")
    return ExecutionBatchRecord.model_validate(
        yaml.safe_load(path.read_text(encoding="utf-8"))
    )


def batch_path(ws: Workspace, record: ExecutionBatchRecord) -> Path:
    suffix = record.content_hash.split(":", 1)[-1][:12]
    return ws.batches_dir / f"{record.batch_id}__{suffix}.yaml"


def _validate_wave(
    *, packet: TaskPacket, bundle: ContextBundle, plan: RoutePlan,
    stage_indices: tuple[int, ...], prior_runs: tuple[RunRecord, ...],
) -> None:
    if not verify_content_hash(packet):
        raise ValidationError("Task Packet does not verify against its content_hash")
    if packet.ref != bundle.packet_ref or packet.ref != plan.packet_ref:
        raise ValidationError("Task Packet, Context Bundle, and Route Plan references differ")
    if packet.content_hash != bundle.packet_content_hash:
        raise ValidationError("Context Bundle does not bind to the verified Task Packet")
    if not stage_indices or tuple(sorted(set(stage_indices))) != stage_indices:
        raise ValidationError("stage indices must be a non-empty sorted unique tuple")
    if stage_indices[-1] >= len(plan.stages):
        raise ValidationError("a concurrent stage index is outside the route")

    prior_by_index = {run.stage_index: run for run in prior_runs}
    if len(prior_by_index) != len(prior_runs):
        raise ValidationError("prior runs contain a duplicate stage")
    expected_prior = tuple(range(stage_indices[0]))
    if tuple(sorted(prior_by_index)) != expected_prior:
        raise ValidationError("prior runs must cover every stage before the wave exactly once")
    for run in prior_runs:
        if run.packet_ref != packet.ref or run.route_plan_hash != plan.content_hash:
            raise ValidationError("a prior run belongs to different governed inputs")
        if run.status != "completed":
            raise ValidationError("a non-completed prior run blocks the concurrent wave")

    expected_wave = tuple(range(stage_indices[0], stage_indices[-1] + 1))
    if stage_indices != expected_wave:
        raise ValidationError("a concurrent wave must be contiguous")
    for index in stage_indices:
        stage = plan.stages[index]
        if not stage.independent:
            raise ValidationError(f"stage {index} is not marked independent")
        if stage.role == "synthesizer":
            raise ValidationError("a synthesizer cannot execute in a concurrent wave")


def _reservations(
    plan: RoutePlan, stage_indices: tuple[int, ...], prior_runs: tuple[RunRecord, ...]
) -> dict[int, int]:
    remaining = plan.budget.max_output_tokens - sum(
        run.response.usage.output_tokens for run in prior_runs
    )
    if remaining <= 0:
        raise ValidationError("route output token ceiling is already exhausted")
    explicit: dict[int, int] = {}
    unspecified: list[int] = []
    for index in stage_indices:
        role = plan.stages[index].role
        if role in plan.budget.per_stage_output_tokens:
            explicit[index] = plan.budget.per_stage_output_tokens[role]
        else:
            unspecified.append(index)
    used = sum(explicit.values())
    if used > remaining:
        raise ValidationError("explicit stage output reservations exceed remaining route budget")
    pool = remaining - used
    if unspecified and pool < len(unspecified):
        raise ValidationError("remaining route budget cannot reserve one token per stage")
    allocations = dict(explicit)
    if unspecified:
        share, remainder = divmod(pool, len(unspecified))
        for position, index in enumerate(unspecified):
            allocations[index] = share + (1 if position < remainder else 0)
    return allocations


def execute_concurrent(
    *, packet: TaskPacket, bundle: ContextBundle, plan: RoutePlan,
    stage_indices: tuple[int, ...], adapters: dict[int, ProviderAdapter],
    decisions: dict[int, EgressDecision], models: dict[int, str],
    prompts: dict[int, str], estimated_input_tokens: dict[int, int],
    prior_runs: tuple[RunRecord, ...] = (), max_workers: int = 3,
    retry_policy: RetryPolicy | None = None, fail_fast: bool = False,
    cancel_event: threading.Event | None = None,
) -> ConcurrentOutcome:
    retry_policy = retry_policy or RetryPolicy()
    _validate_wave(
        packet=packet, bundle=bundle, plan=plan, stage_indices=stage_indices,
        prior_runs=prior_runs,
    )
    if max_workers < 1 or max_workers > 8:
        raise ValidationError("max_workers must be between 1 and 8")
    required = set(stage_indices)
    for name, mapping in (
        ("adapters", adapters), ("decisions", decisions), ("models", models),
        ("prompts", prompts), ("estimated_input_tokens", estimated_input_tokens),
    ):
        if set(mapping) != required:
            raise ValidationError(f"{name} must contain exactly the concurrent stage indices")
    if any(value < 0 for value in estimated_input_tokens.values()):
        raise ValidationError("estimated input tokens cannot be negative")
    if any(not value.strip() for value in models.values()):
        raise ValidationError("models must not be empty")
    if any(not value.strip() for value in prompts.values()):
        raise ValidationError("prompts must not be empty")
    # Governance and identity preflight for the entire wave. One invalid stage
    # prevents every provider call; partial egress is never an accident.
    for index in stage_indices:
        stage = plan.stages[index]
        adapter = adapters[index]
        if adapter.provider != stage.provider:
            raise ValidationError(
                f"adapter provider {adapter.provider!r} does not match route provider "
                f"{stage.provider!r} at stage {index}"
            )
        decisions[index].authorize(transport=adapter.transport, bundle=bundle)

    prior_input = sum(run.response.usage.input_tokens for run in prior_runs)
    estimated_total = prior_input + sum(estimated_input_tokens.values())
    plan.budget.enforce_input(estimated_total)
    reservations = _reservations(plan, stage_indices, prior_runs)
    cancellation = cancel_event or threading.Event()
    started_at = utcnow()
    runs_by_index: dict[int, RunRecord] = {}
    results_by_index: dict[int, BatchStageResult] = {}

    def worker(index: int) -> tuple[BatchStageResult, RunRecord | None]:
        stage = plan.stages[index]
        if cancellation.is_set():
            return BatchStageResult(
                stage_index=index, provider=stage.provider, role=stage.role,
                status="cancelled", attempts=0,
                output_token_reservation=reservations[index], error_code="cancelled",
            ), None
        attempts = 0
        while attempts < retry_policy.max_attempts:
            if cancellation.is_set():
                return BatchStageResult(
                    stage_index=index, provider=stage.provider, role=stage.role,
                    status="cancelled", attempts=attempts,
                    output_token_reservation=reservations[index], error_code="cancelled",
                ), None
            attempts += 1
            try:
                run = _execute_stage(
                    packet=packet, bundle=bundle, plan=plan, stage_index=index,
                    adapter=adapters[index], decision=decisions[index],
                    model=models[index], prompt=prompts[index],
                    estimated_input_tokens=estimated_input_tokens[index],
                    prior_runs=list(prior_runs), enforce_predecessors=False,
                    output_ceiling_override=reservations[index],
                )
                path = run_path(Workspace(Path(".")), run).name
                return BatchStageResult(
                    stage_index=index, provider=stage.provider, role=stage.role,
                    status=run.status, attempts=attempts,
                    output_token_reservation=reservations[index],
                    run_content_hash=run.content_hash, run_file=path,
                ), run
            except ProviderError:
                if not retry_policy.retry_provider_errors or attempts >= retry_policy.max_attempts:
                    if fail_fast:
                        cancellation.set()
                    return BatchStageResult(
                        stage_index=index, provider=stage.provider, role=stage.role,
                        status="failed", attempts=attempts,
                        output_token_reservation=reservations[index],
                        error_code="provider-execution-failed",
                    ), None
            except ConclaveError:
                if fail_fast:
                    cancellation.set()
                return BatchStageResult(
                    stage_index=index, provider=stage.provider, role=stage.role,
                    status="failed", attempts=attempts,
                    output_token_reservation=reservations[index],
                    error_code="stage-validation-failed",
                ), None
            except Exception:
                if fail_fast:
                    cancellation.set()
                return BatchStageResult(
                    stage_index=index, provider=stage.provider, role=stage.role,
                    status="failed", attempts=attempts,
                    output_token_reservation=reservations[index],
                    error_code="provider-execution-failed",
                ), None
        raise AssertionError("retry loop exhausted without a result")

    with ThreadPoolExecutor(max_workers=min(max_workers, len(stage_indices))) as pool:
        futures = {pool.submit(worker, index): index for index in stage_indices}
        for future in as_completed(futures):
            index = futures[future]
            result, run = future.result()
            results_by_index[index] = result
            if run is not None:
                runs_by_index[index] = run

    stage_results = tuple(results_by_index[index] for index in stage_indices)
    runs = tuple(runs_by_index[index] for index in sorted(runs_by_index))
    wave_input = sum(run.response.usage.input_tokens for run in runs)
    wave_output = sum(run.response.usage.output_tokens for run in runs)
    prior_output = sum(run.response.usage.output_tokens for run in prior_runs)
    cumulative_input = prior_input + wave_input
    cumulative_output = prior_output + wave_output
    defects: list[str] = []
    if cumulative_input > plan.budget.max_input_tokens:
        defects.append(
            f"cumulative input {cumulative_input} exceeds ceiling {plan.budget.max_input_tokens}"
        )
    if cumulative_output > plan.budget.max_output_tokens:
        defects.append(
            f"cumulative output {cumulative_output} exceeds ceiling {plan.budget.max_output_tokens}"
        )
    statuses = {result.status for result in stage_results}
    if defects or "budget_exceeded" in statuses:
        status: BatchStatus = "budget_exceeded"
    elif statuses == {"completed"}:
        status = "completed"
    elif statuses == {"cancelled"}:
        status = "cancelled"
    elif "completed" in statuses:
        status = "partial_failure"
    else:
        status = "failed"
    usage_complete = all(
        result.attempts == 1 and result.status in ("completed", "budget_exceeded")
        or result.attempts == 0 and result.status == "cancelled"
        for result in stage_results
    )
    completed_at = utcnow()
    identity = canonical_json({
        "route_plan_hash": plan.content_hash, "stage_indices": stage_indices,
        "started_at": started_at,
        "results": [
            {
                "stage_index": result.stage_index, "status": result.status,
                "run_content_hash": result.run_content_hash,
            }
            for result in stage_results
        ],
    })
    batch_id = "XB-" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]
    data = {
        "schema_version": BATCH_SCHEMA_VERSION,
        "batch_id": batch_id,
        "packet_ref": packet.ref,
        "task_packet_hash": packet.content_hash,
        "context_bundle_hash": bundle.content_hash,
        "route_plan_hash": plan.content_hash,
        "stage_indices": stage_indices,
        "max_workers": max_workers,
        "retry_policy": retry_policy,
        "fail_fast": fail_fast,
        "started_at": started_at,
        "completed_at": completed_at,
        "status": status,
        "stage_results": stage_results,
        "wave_input_tokens": wave_input,
        "wave_output_tokens": wave_output,
        "cumulative_input_tokens": cumulative_input,
        "cumulative_output_tokens": cumulative_output,
        "usage_complete": usage_complete,
        "usage_note": (
            "complete for normalized Provider Responses only" if usage_complete else
            "incomplete: failed provider attempts may have consumed unreported tokens"
        ),
        "budget_defects": tuple(defects),
        "cancellation_note": (
            "cooperative only: queued work and retries stop; in-flight provider calls "
            "cannot be forcefully interrupted and completed results are preserved"
        ),
    }
    draft = ExecutionBatchRecord.model_construct(**data, content_hash="pending")
    return ConcurrentOutcome(
        ExecutionBatchRecord.model_validate({
            **data, "content_hash": compute_batch_hash(draft),
        }), runs,
    )


def write_concurrent_outcome(
    ws: Workspace, outcome: ConcurrentOutcome
) -> StoredConcurrentOutcome:
    stored_runs = tuple(write_run_record(ws, run) for run in outcome.runs)
    path = batch_path(ws, outcome.record)
    if path.exists():
        existing = read_batch(path)
        if existing.content_hash != outcome.record.content_hash:
            raise WorkspaceError(f"different execution batch already exists at {path}")
        return StoredConcurrentOutcome(outcome.record, path, False, stored_runs)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = yaml.safe_dump(
        outcome.record.model_dump(mode="json"), sort_keys=False, allow_unicode=True
    )
    path.write_bytes(text.replace("\r\n", "\n").encode("utf-8"))
    return StoredConcurrentOutcome(outcome.record, path, True, stored_runs)
