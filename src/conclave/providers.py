"""Provider-neutral execution contract with fail-closed egress."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Protocol

import yaml
from pydantic import BaseModel, ConfigDict, Field

from .context import Classification, ContextBundle
from .errors import ValidationError
from .identity import sha256_bytes
from .workspace import Workspace

EGRESS_SCHEMA_VERSION = "egress-decision/0.1.0"


class EgressPolicy(BaseModel):
    """An explicit principal-authored decision consumed by live execution."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = EGRESS_SCHEMA_VERSION
    allowed: bool = False
    transports: frozenset[str] = frozenset()
    classifications: frozenset[Classification] = frozenset()
    authority: str = Field(min_length=1)
    decision_ref: str = Field(min_length=1)


def egress_policy_hash(policy: EgressPolicy) -> str:
    payload = json.dumps(
        policy.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return sha256_bytes(payload)


class EgressDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    allowed: bool = False
    transports: frozenset[str] = frozenset()
    classifications: frozenset[Classification] = frozenset()
    authority: str | None = None
    decision_ref: str | None = None

    def authorize(self, *, transport: str, bundle: ContextBundle) -> None:
        if not self.allowed or not self.authority or not self.decision_ref:
            raise ValidationError("provider egress is not explicitly authorised")
        if transport not in self.transports:
            raise ValidationError(f"transport {transport!r} is not authorised")
        blocked = sorted({
            source.classification for source in bundle.sources
            if source.classification not in self.classifications
        })
        if blocked:
            raise ValidationError(
                f"context classifications are not authorised for egress: {blocked}"
            )


def read_egress_decision(
    path: Path,
    *,
    principal: str,
    workspace: Workspace | None = None,
    identity_verification_reference: str | None = None,
    signed_evidence_binding_reference: str | None = None,
) -> EgressDecision:
    """Read an explicit egress policy and bind it to the workspace principal."""
    if not path.exists():
        raise ValidationError(f"no egress decision at {path}")
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        policy = EgressPolicy.model_validate(raw)
    except (OSError, ValueError, TypeError) as exc:
        raise ValidationError(f"invalid egress decision: {exc}") from exc
    if policy.schema_version != EGRESS_SCHEMA_VERSION:
        raise ValidationError(
            f"unsupported egress decision schema {policy.schema_version!r}"
        )
    if policy.authority != principal:
        raise ValidationError(
            "egress decision authority does not match the workspace principal"
        )
    if not policy.allowed:
        raise ValidationError("egress decision does not permit live provider calls")
    if workspace is not None:
        from .gating import enforce_principal_gate

        enforce_principal_gate(
            workspace,
            operation="egress_decision",
            actor_id=policy.authority,
            target_reference=policy.decision_ref,
            target_hash=egress_policy_hash(policy),
            identity_verification_reference=identity_verification_reference,
            signed_evidence_binding_reference=signed_evidence_binding_reference,
        )
    return EgressDecision(
        allowed=policy.allowed,
        transports=policy.transports,
        classifications=policy.classifications,
        authority=policy.authority,
        decision_ref=policy.decision_ref,
    )


class ProviderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    provider: str
    model: str
    transport: str
    role: str
    prompt: str
    context_bundle_hash: str
    max_output_tokens: int = Field(gt=0)


class ProviderUsage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    input_tokens: int = Field(ge=0)
    cached_input_tokens: int = Field(0, ge=0)
    output_tokens: int = Field(ge=0)
    reasoning_output_tokens: int = Field(0, ge=0)

    def model_post_init(self, __context: Any) -> None:
        if self.cached_input_tokens > self.input_tokens:
            raise ValueError("cached input tokens cannot exceed total input tokens")
        if self.reasoning_output_tokens > self.output_tokens:
            raise ValueError("reasoning output tokens cannot exceed total output tokens")


class ProviderResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    provider: str
    model: str
    transport: str
    text: str
    structured_output: dict[str, Any] | None = None
    usage: ProviderUsage
    finish_status: str
    provider_request_id: str | None = None


class ProviderAdapter(Protocol):
    provider: str
    transport: str

    def execute(self, request: ProviderRequest) -> ProviderResponse: ...


@dataclass
class FixtureAdapter:
    """Deterministic adapter for integration and negative tests."""

    provider: str
    response_text: str = "fixture response"
    transport: str = "fixture"

    def execute(self, request: ProviderRequest) -> ProviderResponse:
        if request.provider != self.provider or request.transport != self.transport:
            raise ValidationError("request does not match fixture adapter identity")
        return ProviderResponse(
            provider=self.provider, model=request.model, transport=self.transport,
            text=self.response_text,
            usage=ProviderUsage(
                input_tokens=max(1, len(request.prompt.split())),
                output_tokens=max(1, len(self.response_text.split())),
            ),
            finish_status="completed", provider_request_id="fixture-1",
        )


def prepare_request(
    *, bundle: ContextBundle, decision: EgressDecision, provider: str,
    model: str, transport: str, role: str, prompt: str, max_output_tokens: int,
) -> ProviderRequest:
    decision.authorize(transport=transport, bundle=bundle)
    return ProviderRequest(
        provider=provider, model=model, transport=transport, role=role,
        prompt=prompt, context_bundle_hash=bundle.content_hash,
        max_output_tokens=max_output_tokens,
    )
