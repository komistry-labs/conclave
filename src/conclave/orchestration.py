"""Idempotent batch-to-Council orchestration with an explicit pause state."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from .concurrency import ExecutionBatchRecord, read_batch
from .council import CouncilOutcome, review_task
from .errors import ValidationError, WorkspaceError
from .execution import RunRecord, read_run_record
from .hashing import hash_text
from .ledger import canonical_json
from .routing import RoutePlan, read_route_plan
from .runhandoff import ConversionResult, _submission, convert_run
from .scope import ReviewOutcome, review_handoff
from .taskpacket import read_packet, verify_content_hash
from .workspace import Workspace, utcnow

ORCHESTRATION_SCHEMA_VERSION = "batch-orchestration/0.1.0"
PauseState = Literal[
    "awaiting_human_decision",
    "awaiting_sequential_synthesizer",
    "blocked_by_governance",
    "ambiguous_submissions",
    "awaiting_provider_submissions",
]


class OrchestratedStage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    stage_index: int = Field(ge=0)
    provider: str
    role: str
    run_content_hash: str
    run_file: str
    handoff_content_hash: str
    handoff_file: str
    raw_response_hash: str
    raw_file: str
    scope_review_hash: str
    scope_file: str
    scope_status: str


class OrchestrationRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[ORCHESTRATION_SCHEMA_VERSION] = ORCHESTRATION_SCHEMA_VERSION
    orchestration_id: str
    execution_batch_id: str
    execution_batch_hash: str
    packet_ref: str
    task_packet_hash: str
    route_plan_hash: str
    started_at: str
    completed_at: str
    processed_stages: tuple[OrchestratedStage, ...]
    council_review_id: str
    council_review_hash: str
    council_review_status: str
    council_yaml_file: str
    council_markdown_file: str
    council_submission_count: int = Field(ge=0)
    missing_route_stages: tuple[str, ...] = ()
    pause_state: PauseState
    human_decision_required: Literal[True] = True
    action_execution_allowed: Literal[False] = False
    authority_note: str = (
        "CONCLAVE assembled evidence and paused. Only the constitutional authority "
        "may decide; this record authorises and executes nothing."
    )
    content_hash: str

    @model_validator(mode="after")
    def _verify(self) -> "OrchestrationRecord":
        indices = tuple(stage.stage_index for stage in self.processed_stages)
        if indices != tuple(sorted(set(indices))):
            raise ValidationError("orchestration stages are not sorted and unique")
        expected = pause_state_for(
            self.council_review_status,
            missing_roles=tuple(
                item.rsplit(":", 1)[-1] for item in self.missing_route_stages
            ),
        )
        if self.pause_state != expected:
            raise ValidationError("orchestration pause state contradicts Council status")
        if self.content_hash != compute_orchestration_hash(self):
            raise ValidationError("orchestration content_hash is stale")
        return self


@dataclass(frozen=True)
class OrchestrationOutcome:
    record: OrchestrationRecord
    path: Path
    created: bool
    batch: ExecutionBatchRecord
    conversions: tuple[ConversionResult, ...]
    scopes: tuple[ReviewOutcome, ...]
    council: CouncilOutcome


def _body(record: OrchestrationRecord) -> dict:
    return record.model_dump(mode="json", exclude={"content_hash"})


def compute_orchestration_hash(record: OrchestrationRecord) -> str:
    return hash_text(canonical_json(_body(record)))


def read_orchestration(path: Path) -> OrchestrationRecord:
    if not path.exists():
        raise WorkspaceError(f"no orchestration record at {path}")
    return OrchestrationRecord.model_validate(
        yaml.safe_load(path.read_text(encoding="utf-8"))
    )


def _matching_route(ws: Workspace, route_hash: str) -> tuple[RoutePlan, Path]:
    matches: list[tuple[RoutePlan, Path]] = []
    for path in ws.routes_dir.glob("*.yaml"):
        route = read_route_plan(path)
        if route.content_hash == route_hash:
            matches.append((route, path))
    if len(matches) != 1:
        raise ValidationError(
            f"expected exactly one stored Route Plan matching {route_hash}, "
            f"found {len(matches)}"
        )
    return matches[0]


def _preflight_runs(
    ws: Workspace, batch: ExecutionBatchRecord, route: RoutePlan
) -> tuple[tuple[RunRecord, Path], ...]:
    if batch.status != "completed":
        raise ValidationError(
            f"execution batch status is {batch.status!r}; only completed batches orchestrate"
        )
    verified: list[tuple[RunRecord, Path]] = []
    for result in batch.stage_results:
        if result.status != "completed" or not result.run_file or not result.run_content_hash:
            raise ValidationError(f"stage {result.stage_index} has no completed Provider Run")
        path = ws.runs_dir / result.run_file
        run = read_run_record(path)
        if run.content_hash != result.run_content_hash:
            raise ValidationError(f"stage {result.stage_index} Run hash differs from batch")
        if run.packet_ref != batch.packet_ref or run.route_plan_hash != route.content_hash:
            raise ValidationError(f"stage {result.stage_index} Run binds different inputs")
        if run.context_bundle_hash != batch.context_bundle_hash:
            raise ValidationError(
                f"stage {result.stage_index} Run binds a different Context Bundle"
            )
        if run.stage_index != result.stage_index:
            raise ValidationError(f"stage {result.stage_index} Run index differs from batch")
        stage = route.stages[result.stage_index]
        if (result.provider, result.role) != (stage.provider, stage.role):
            raise ValidationError(
                f"stage {result.stage_index} batch identity differs from route"
            )
        if (run.response.provider, run.role) != (stage.provider, stage.role):
            raise ValidationError(f"stage {result.stage_index} Run identity differs from route")
        # Validate every response before the first downstream write. This avoids
        # a malformed later response leaving a misleading partially assembled run.
        submission = _submission(run)
        expected = {
            "packet_ref": run.packet_ref,
            "packet_content_hash": batch.task_packet_hash,
            "provider": run.response.provider,
            "role": run.role,
        }
        for field_name, value in expected.items():
            if submission.get(field_name) != value:
                raise ValidationError(
                    f"stage {result.stage_index} Handoff field {field_name!r} differs "
                    "from governed execution evidence"
                )
        verified.append((run, path))
    return tuple(sorted(verified, key=lambda item: item[0].stage_index))


def pause_state_for(
    council_status: str, *, missing_roles: tuple[str, ...]
) -> PauseState:
    if council_status == "ready_for_human_review":
        return "awaiting_human_decision"
    if council_status == "blocked_by_governance":
        return "blocked_by_governance"
    if council_status == "ambiguous_submissions":
        return "ambiguous_submissions"
    if council_status == "incomplete":
        if "synthesizer" in missing_roles:
            return "awaiting_sequential_synthesizer"
        return "awaiting_provider_submissions"
    raise ValidationError(f"unknown Council Review status {council_status!r}")


def orchestration_path(ws: Workspace, record: OrchestrationRecord) -> Path:
    suffix = record.content_hash.split(":", 1)[-1][:12]
    return ws.orchestrations_dir / f"{record.orchestration_id}__{suffix}.yaml"


def orchestrate_batch(ws: Workspace, batch_file: Path) -> OrchestrationOutcome:
    batch_file = Path(batch_file).resolve()
    if batch_file.parent != ws.batches_dir.resolve():
        raise ValidationError(
            "execution batch must be a stored artifact inside this workspace"
        )
    batch = read_batch(batch_file)
    route, route_path = _matching_route(ws, batch.route_plan_hash)
    task_id, version_text = batch.packet_ref.rsplit("@v", 1)
    packet = read_packet(ws, task_id, int(version_text))
    if not verify_content_hash(packet) or packet.content_hash != batch.task_packet_hash:
        raise ValidationError("execution batch does not bind to the verified Task Packet")
    if route.packet_ref != packet.ref:
        raise ValidationError("execution batch Route Plan cites a different Task Packet")
    runs = _preflight_runs(ws, batch, route)

    started_at = utcnow()
    conversions: list[ConversionResult] = []
    scopes: list[ReviewOutcome] = []
    stages: list[OrchestratedStage] = []
    for run, run_file in runs:
        conversion = convert_run(ws, run_file)
        scope = review_handoff(ws, conversion.handoff_path)
        conversions.append(conversion)
        scopes.append(scope)
        stages.append(OrchestratedStage(
            stage_index=run.stage_index,
            provider=run.response.provider,
            role=run.role,
            run_content_hash=run.content_hash,
            run_file=run_file.name,
            handoff_content_hash=conversion.packet.content_hash or "",
            handoff_file=conversion.handoff_path.name,
            raw_response_hash=conversion.packet.raw_response_hash,
            raw_file=conversion.raw_path.name,
            scope_review_hash=scope.review.content_hash or "",
            scope_file=scope.path.name,
            scope_status=scope.review.scope_status,
        ))

    council = review_task(ws, packet.task_id, packet.version, route_path=route_path)
    missing_roles = tuple(
        route.stages[index].role
        for index in range(len(route.stages))
        if f"s{index}:{route.stages[index].provider}:{route.stages[index].role}"
        in council.review.missing_providers
    )
    pause = pause_state_for(council.review.review_status, missing_roles=missing_roles)
    completed_at = utcnow()
    identity = canonical_json({
        "execution_batch_hash": batch.content_hash,
        "council_review_hash": council.review.content_hash,
    })
    orchestration_id = "OR-" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]
    existing_paths = sorted(ws.orchestrations_dir.glob(f"{orchestration_id}__*.yaml"))
    if existing_paths:
        if len(existing_paths) != 1:
            raise ValidationError(
                f"multiple orchestration records share identity {orchestration_id}"
            )
        existing = read_orchestration(existing_paths[0])
        if existing.execution_batch_hash != batch.content_hash or \
                existing.council_review_hash != council.review.content_hash:
            raise ValidationError("existing orchestration record does not match its sources")
        return OrchestrationOutcome(
            existing, existing_paths[0], False, batch,
            tuple(conversions), tuple(scopes), council,
        )
    data = {
        "schema_version": ORCHESTRATION_SCHEMA_VERSION,
        "orchestration_id": orchestration_id,
        "execution_batch_id": batch.batch_id,
        "execution_batch_hash": batch.content_hash,
        "packet_ref": packet.ref,
        "task_packet_hash": packet.content_hash,
        "route_plan_hash": route.content_hash,
        "started_at": started_at,
        "completed_at": completed_at,
        "processed_stages": tuple(stages),
        "council_review_id": council.review.council_review_id,
        "council_review_hash": council.review.content_hash,
        "council_review_status": council.review.review_status,
        "council_yaml_file": council.yaml_path.name,
        "council_markdown_file": council.markdown_path.name,
        "council_submission_count": len(council.review.submissions),
        "missing_route_stages": tuple(council.review.missing_providers),
        "pause_state": pause,
    }
    draft = OrchestrationRecord.model_construct(**data, content_hash="pending")
    record = OrchestrationRecord.model_validate({
        **data, "content_hash": compute_orchestration_hash(draft),
    })
    path = orchestration_path(ws, record)
    if path.exists():
        existing = read_orchestration(path)
        if existing.content_hash != record.content_hash:
            raise WorkspaceError(f"different orchestration record already exists at {path}")
        return OrchestrationOutcome(
            existing, path, False, batch, tuple(conversions), tuple(scopes), council
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    text = yaml.safe_dump(record.model_dump(mode="json"), sort_keys=False, allow_unicode=True)
    path.write_bytes(text.replace("\r\n", "\n").encode("utf-8"))
    return OrchestrationOutcome(
        record, path, True, batch, tuple(conversions), tuple(scopes), council
    )
