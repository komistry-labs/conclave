"""Single-stage provider execution and immutable response capture."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from .context import ContextBundle, render_context_prompt
from .errors import IntegrityError, ValidationError, WorkspaceError
from .hashing import hash_text
from .ledger import canonical_json
from .providers import (
    EgressDecision, ProviderAdapter, ProviderRequest, ProviderResponse,
    prepare_request,
)
from .routing import RoutePlan
from .models import TaskPacket
from .taskpacket import verify_content_hash
from .workspace import Workspace, utcnow

RUN_SCHEMA_VERSION = "provider-run/0.2.0"
RunStatus = Literal["completed", "budget_exceeded"]


class RunRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = RUN_SCHEMA_VERSION
    packet_ref: str = Field(min_length=1)
    context_bundle_hash: str = Field(min_length=1)
    route_plan_hash: str = Field(min_length=1)
    stage_index: int = Field(ge=0)
    role: str = Field(min_length=1)
    egress_authority: str = Field(min_length=1)
    egress_decision_ref: str = Field(min_length=1)
    request: ProviderRequest
    response: ProviderResponse
    started_at: str
    completed_at: str
    status: RunStatus
    budget_defects: tuple[str, ...] = ()
    content_hash: str

    @model_validator(mode="after")
    def verify(self) -> "RunRecord":
        if self.role != self.request.role:
            raise ValidationError("run role and request role differ")
        if self.request.provider != self.response.provider:
            raise ValidationError("request and response provider differ")
        if self.request.model != self.response.model:
            raise ValidationError("request and response model differ")
        if self.request.transport != self.response.transport:
            raise ValidationError("request and response transport differ")
        if self.status == "completed" and self.budget_defects:
            raise ValidationError("completed run may not carry budget defects")
        if self.status == "budget_exceeded" and not self.budget_defects:
            raise ValidationError("budget_exceeded run must state its defects")
        if self.content_hash != compute_run_hash(self):
            raise IntegrityError("run record content_hash is stale")
        return self


def _run_body(record: RunRecord) -> dict:
    return record.model_dump(mode="json", exclude={"content_hash"})


def compute_run_hash(record: RunRecord) -> str:
    return hash_text(canonical_json(_run_body(record)))


def execute_stage(
    *, packet: TaskPacket, bundle: ContextBundle, plan: RoutePlan, stage_index: int,
    adapter: ProviderAdapter, decision: EgressDecision, model: str,
    prompt: str, estimated_input_tokens: int,
    prior_runs: list[RunRecord] | None = None,
) -> RunRecord:
    if not verify_content_hash(packet):
        raise ValidationError("Task Packet does not verify against its content_hash")
    if packet.ref != bundle.packet_ref or packet.ref != plan.packet_ref:
        raise ValidationError("Task Packet, Context Bundle, and Route Plan references differ")
    if packet.content_hash != bundle.packet_content_hash:
        raise ValidationError(
            "Context Bundle packet_content_hash does not match the verified Task Packet"
        )
    if stage_index < 0 or stage_index >= len(plan.stages):
        raise ValidationError(f"stage index {stage_index} is outside the route")
    stage = plan.stages[stage_index]
    if adapter.provider != stage.provider:
        raise ValidationError(
            f"adapter provider {adapter.provider!r} does not match route "
            f"provider {stage.provider!r}"
        )
    prior_runs = prior_runs or []
    predecessor_counts = {
        index: sum(run.stage_index == index for run in prior_runs)
        for index in range(stage_index)
    }
    if set(run.stage_index for run in prior_runs) != set(range(stage_index)):
        raise ValidationError(
            "prior runs must contain every earlier route stage and no other stage"
        )
    if any(count != 1 for count in predecessor_counts.values()):
        raise ValidationError("each earlier route stage must have exactly one prior run")
    for prior in prior_runs:
        if prior.route_plan_hash != plan.content_hash:
            raise ValidationError("prior run belongs to a different Route Plan")
        if prior.packet_ref != packet.ref:
            raise ValidationError("prior run belongs to a different Task Packet")
        if prior.status != "completed":
            raise ValidationError("a non-completed prior run blocks further execution")
    prior_input = sum(run.response.usage.input_tokens for run in prior_runs)
    prior_output = sum(run.response.usage.output_tokens for run in prior_runs)
    plan.budget.enforce_input(prior_input + estimated_input_tokens)
    remaining_output = plan.budget.max_output_tokens - prior_output
    if remaining_output <= 0:
        raise ValidationError("route output token ceiling is already exhausted")
    stage_ceiling = plan.budget.per_stage_output_tokens.get(
        stage.role, remaining_output
    )
    output_ceiling = min(stage_ceiling, remaining_output)
    governed_prompt = render_context_prompt(bundle, prompt)
    request = prepare_request(
        bundle=bundle, decision=decision, provider=stage.provider, model=model,
        transport=adapter.transport, role=stage.role, prompt=governed_prompt,
        max_output_tokens=output_ceiling,
    )
    started_at = utcnow()
    response = adapter.execute(request)
    completed_at = utcnow()
    defects = []
    if prior_input + response.usage.input_tokens > plan.budget.max_input_tokens:
        defects.append(
            f"cumulative input {prior_input + response.usage.input_tokens} exceeds ceiling "
            f"{plan.budget.max_input_tokens}"
        )
    if prior_output + response.usage.output_tokens > plan.budget.max_output_tokens:
        defects.append(
            f"cumulative output {prior_output + response.usage.output_tokens} exceeds ceiling "
            f"{plan.budget.max_output_tokens}"
        )
    if response.usage.output_tokens > stage_ceiling and stage_ceiling < remaining_output:
        defects.append(
            f"actual output {response.usage.output_tokens} exceeds stage ceiling "
            f"{stage_ceiling}"
        )
    status: RunStatus = "budget_exceeded" if defects else "completed"
    data = {
        "schema_version": RUN_SCHEMA_VERSION,
        "packet_ref": plan.packet_ref,
        "context_bundle_hash": bundle.content_hash,
        "route_plan_hash": plan.content_hash,
        "stage_index": stage_index,
        "role": stage.role,
        "egress_authority": decision.authority,
        "egress_decision_ref": decision.decision_ref,
        "request": request,
        "response": response,
        "started_at": started_at,
        "completed_at": completed_at,
        "status": status,
        "budget_defects": tuple(defects),
    }
    draft = RunRecord.model_construct(**data, content_hash="pending")
    return RunRecord.model_validate({
        **data, "content_hash": compute_run_hash(draft),
    })


def run_path(ws: Workspace, record: RunRecord) -> Path:
    task_id, version = record.packet_ref.rsplit("@v", 1)
    suffix = record.content_hash.split(":", 1)[-1][:12]
    return ws.runs_dir / f"{task_id}__v{version}__s{record.stage_index}__{suffix}.yaml"


def write_run_record(ws: Workspace, record: RunRecord) -> tuple[Path, bool]:
    path = run_path(ws, record)
    if path.exists():
        existing = read_run_record(path)
        if existing.content_hash != record.content_hash:
            raise WorkspaceError(f"different run record already exists at {path}")
        return path, False
    path.parent.mkdir(parents=True, exist_ok=True)
    text = yaml.safe_dump(
        record.model_dump(mode="json"), sort_keys=False, allow_unicode=True
    )
    path.write_bytes(text.replace("\r\n", "\n").encode("utf-8"))
    return path, True


def read_run_record(path: Path) -> RunRecord:
    if not path.exists():
        raise WorkspaceError(f"no run record at {path}")
    return RunRecord.model_validate(
        yaml.safe_load(path.read_text(encoding="utf-8"))
    )
