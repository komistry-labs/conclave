"""Deterministic adaptive routing and token-budget enforcement."""

from __future__ import annotations

from typing import Literal
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator
import yaml

from .errors import ValidationError, WorkspaceError
from .hashing import hash_text
from .ledger import canonical_json
from .workspace import Workspace

ROUTE_SCHEMA_VERSION = "route-plan/0.1.0"
RiskTier = Literal["routine", "important", "evidence-sensitive", "canonical"]
Role = Literal["lead", "critic", "verifier", "synthesizer"]

DEFAULT_STAGES: dict[str, tuple[Role, ...]] = {
    "routine": ("lead",),
    "important": ("lead", "critic"),
    "evidence-sensitive": ("lead", "verifier"),
    "canonical": ("lead", "critic", "verifier", "synthesizer"),
}


class TokenBudget(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    max_input_tokens: int = Field(gt=0)
    max_output_tokens: int = Field(gt=0)
    per_stage_output_tokens: dict[Role, int] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_stage_limits(self) -> "TokenBudget":
        if any(value <= 0 for value in self.per_stage_output_tokens.values()):
            raise ValueError("per-stage token ceilings must be positive")
        if sum(self.per_stage_output_tokens.values()) > self.max_output_tokens:
            raise ValueError("per-stage output ceilings exceed total output ceiling")
        return self

    def enforce_input(self, estimated_tokens: int) -> None:
        if estimated_tokens > self.max_input_tokens:
            raise ValidationError(
                f"estimated input {estimated_tokens} exceeds ceiling "
                f"{self.max_input_tokens}"
            )


class ProviderCapability(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    provider: str = Field(min_length=1)
    roles: frozenset[Role]


class RouteStage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    role: Role
    provider: str = Field(min_length=1)
    independent: bool = True


class RoutePlan(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = ROUTE_SCHEMA_VERSION
    packet_ref: str
    risk: RiskTier
    stages: tuple[RouteStage, ...]
    budget: TokenBudget
    reasons: tuple[str, ...]
    content_hash: str

    @model_validator(mode="after")
    def verify(self) -> "RoutePlan":
        roles = tuple(stage.role for stage in self.stages)
        if roles != DEFAULT_STAGES[self.risk]:
            raise ValidationError(
                f"route stages {roles!r} do not match frozen {self.risk!r} policy"
            )
        by_role = {stage.role: stage.provider for stage in self.stages}
        lead = by_role.get("lead")
        if by_role.get("critic") == lead:
            raise ValidationError("lead provider may not be its own critic")
        if by_role.get("synthesizer") == lead:
            raise ValidationError("lead provider may not be its own synthesizer")
        actual = compute_route_hash(self)
        if self.content_hash != actual:
            raise ValidationError("route plan content_hash is stale")
        return self


def _route_body(plan: RoutePlan) -> dict:
    return plan.model_dump(mode="json", exclude={"content_hash"})


def compute_route_hash(plan: RoutePlan) -> str:
    return hash_text(canonical_json(_route_body(plan)))


def build_route(
    *, packet_ref: str, risk: RiskTier, capabilities: list[ProviderCapability],
    budget: TokenBudget, preferred: dict[Role, str] | None = None,
) -> RoutePlan:
    preferred = preferred or {}
    capabilities_by_provider = {item.provider: item.roles for item in capabilities}
    stages: list[RouteStage] = []
    lead: str | None = None
    independent_reviewers: set[str] = set()
    for role in DEFAULT_STAGES[risk]:
        candidates = sorted(
            provider for provider, roles in capabilities_by_provider.items()
            if role in roles
        )
        if role in ("critic", "verifier"):
            candidates = [
                provider for provider in candidates
                if provider != lead and provider not in independent_reviewers
            ]
        elif role == "synthesizer" and lead in candidates:
            candidates.remove(lead)
        wanted = preferred.get(role)
        if wanted:
            if wanted not in candidates:
                raise ValidationError(
                    f"preferred provider {wanted!r} is not eligible for role {role!r}"
                )
            candidates.remove(wanted)
            candidates.insert(0, wanted)
        if not candidates:
            raise ValidationError(f"no eligible provider for role {role!r}")
        selected = candidates[0]
        if role == "lead":
            lead = selected
        if role in ("critic", "verifier"):
            independent_reviewers.add(selected)
        stages.append(RouteStage(role=role, provider=selected))

    draft = RoutePlan.model_construct(
        schema_version=ROUTE_SCHEMA_VERSION, packet_ref=packet_ref, risk=risk,
        stages=tuple(stages), budget=budget,
        reasons=(f"frozen default route for {risk} risk",),
        content_hash="pending",
    )
    return RoutePlan.model_validate({
        **_route_body(draft),
        "content_hash": compute_route_hash(draft),
    })


def route_path(ws: Workspace, plan: RoutePlan) -> Path:
    task_id, version = plan.packet_ref.rsplit("@v", 1)
    suffix = plan.content_hash.split(":", 1)[-1][:12]
    return ws.routes_dir / f"{task_id}__v{version}__{suffix}.yaml"


def write_route_plan(ws: Workspace, plan: RoutePlan) -> tuple[Path, bool]:
    path = route_path(ws, plan)
    if path.exists():
        existing = read_route_plan(path)
        if existing.content_hash != plan.content_hash:
            raise WorkspaceError(f"different route plan already exists at {path}")
        return path, False
    path.parent.mkdir(parents=True, exist_ok=True)
    text = yaml.safe_dump(
        plan.model_dump(mode="json"), sort_keys=False, allow_unicode=True
    )
    path.write_bytes(text.replace("\r\n", "\n").encode("utf-8"))
    return path, True


def read_route_plan(path: Path) -> RoutePlan:
    if not path.exists():
        raise WorkspaceError(f"no route plan at {path}")
    return RoutePlan.model_validate(
        yaml.safe_load(path.read_text(encoding="utf-8"))
    )
