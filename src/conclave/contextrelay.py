"""Governed Context Bundle export for manual provider relay.

This is the local, no-network counterpart to live route execution. It binds a
verified Task Packet, sealed Context Bundle, frozen Route Plan, route stage,
and operator instruction into one content-addressed prompt. The accompanying
manifest is immutable evidence of exactly what was prepared for relay.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator
import yaml

from .context import ContextBundle, render_context_prompt
from .errors import IntegrityError, ValidationError, WorkspaceError
from .hashing import hash_file, hash_text, write_canonical
from .ledger import canonical_json
from .models import ProviderAssignment, TaskPacket
from .relay import build_prompt, hash_suffix
from .routing import RoutePlan
from .taskpacket import verify_content_hash
from .workspace import Workspace, utcnow

CONTEXT_RELAY_SCHEMA_VERSION = "context-relay-export/0.1.0"


class ContextRelayExport(BaseModel):
    """Sealed evidence for one governed manual-relay prompt."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = CONTEXT_RELAY_SCHEMA_VERSION
    packet_ref: str = Field(min_length=1)
    packet_content_hash: str = Field(min_length=1)
    context_bundle_hash: str = Field(min_length=1)
    route_plan_hash: str = Field(min_length=1)
    stage_index: int = Field(ge=0)
    provider: str = Field(min_length=1)
    role: str = Field(min_length=1)
    prompt_file: str = Field(min_length=1)
    prompt_hash: str = Field(min_length=1)
    exported_at: str = Field(min_length=1)
    content_hash: str = Field(min_length=1)

    @model_validator(mode="after")
    def verify(self) -> "ContextRelayExport":
        if self.content_hash != compute_export_hash(self):
            raise IntegrityError("context relay export content_hash is stale")
        return self

    def as_export_record(self) -> dict:
        """Return the provenance shape consumed by Handoff import."""
        task_id, version = self.packet_ref.rsplit("@v", 1)
        return {
            "event_type": "context_prompt_exported",
            "export_id": Path(self.prompt_file).stem,
            "exported_at": self.exported_at,
            "prompt_schema_version": CONTEXT_RELAY_SCHEMA_VERSION,
            "task_id": task_id,
            "version": int(version),
            "packet_ref": self.packet_ref,
            "packet_content_hash": self.packet_content_hash,
            "context_bundle_hash": self.context_bundle_hash,
            "route_plan_hash": self.route_plan_hash,
            "stage_index": self.stage_index,
            "provider": self.provider,
            "role": self.role,
            "prompt_file": self.prompt_file,
            "prompt_hash": self.prompt_hash,
            "manifest_hash": self.content_hash,
        }


def _export_body(record: ContextRelayExport) -> dict:
    return record.model_dump(mode="json", exclude={"content_hash"})


def compute_export_hash(record: ContextRelayExport) -> str:
    return hash_text(canonical_json(_export_body(record)))


def _validate_inputs(
    packet: TaskPacket,
    bundle: ContextBundle,
    plan: RoutePlan,
    stage_index: int,
) -> ProviderAssignment:
    if not verify_content_hash(packet):
        raise ValidationError("Task Packet does not verify against its content_hash")
    if packet.ref != bundle.packet_ref or packet.ref != plan.packet_ref:
        raise ValidationError(
            "Task Packet, Context Bundle, and Route Plan references differ"
        )
    if packet.content_hash != bundle.packet_content_hash:
        raise ValidationError(
            "Context Bundle packet_content_hash does not match the verified Task Packet"
        )
    if stage_index < 0 or stage_index >= len(plan.stages):
        raise ValidationError(f"stage index {stage_index} is outside the route")

    stage = plan.stages[stage_index]
    if stage.provider not in {item.provider for item in packet.assigned_providers}:
        raise ValidationError(
            f"route provider {stage.provider!r} is not assigned to {packet.ref}"
        )
    return ProviderAssignment(provider=stage.provider, role=stage.role)


def build_context_relay_prompt(
    *,
    packet: TaskPacket,
    bundle: ContextBundle,
    plan: RoutePlan,
    stage_index: int,
    instruction: str,
    config: dict,
) -> str:
    """Render the exact deterministic prompt prepared for manual relay."""
    if not instruction.strip():
        raise ValidationError("provider instruction must not be empty")
    assignment = _validate_inputs(packet, bundle, plan, stage_index)
    task_prompt = build_prompt(packet, assignment, config)
    before_format, marker, after_format = task_prompt.partition(
        "## Required response format"
    )
    if not marker:
        raise IntegrityError("Task Packet prompt is missing its response contract")

    provenance = "\n".join([
        "# CONCLAVE governed manual-relay stage",
        "",
        "This file was prepared locally. No provider API call was made.",
        "Relay it only to the named provider. Do not add another provider's prompt",
        "or response.",
        "",
        "## Sealed execution identity",
        "",
        "```",
        f"packet_ref          : {packet.ref}",
        f"packet_content_hash : {packet.content_hash}",
        f"context_bundle_hash : {bundle.content_hash}",
        f"route_plan_hash     : {plan.content_hash}",
        f"stage_index         : {stage_index}",
        f"provider            : {assignment.provider}",
        f"role                : {assignment.role}",
        "transport           : manual-relay",
        "```",
        "",
    ])
    context_projection = render_context_prompt(bundle, instruction)
    return (
        provenance
        + before_format
        + context_projection
        + "\n\n"
        + marker
        + after_format
    )


def context_relay_filename(
    packet: TaskPacket,
    bundle: ContextBundle,
    plan: RoutePlan,
    stage_index: int,
    provider: str,
) -> str:
    return (
        f"{packet.task_id}__v{packet.version}__s{stage_index}__{provider}"
        f"__c{hash_suffix(bundle.content_hash)}"
        f"__r{hash_suffix(plan.content_hash)}.md"
    )


def context_relay_dir(ws: Workspace) -> Path:
    return ws.outbox_dir / "context"


def manifest_path_for_prompt(prompt_path: Path) -> Path:
    return prompt_path.with_suffix(".yaml")


def write_context_relay_export(
    *,
    ws: Workspace,
    packet: TaskPacket,
    bundle: ContextBundle,
    plan: RoutePlan,
    stage_index: int,
    instruction: str,
    config: dict,
) -> tuple[ContextRelayExport, Path, Path, bool]:
    """Write prompt and manifest once; identical retries are idempotent."""
    assignment = _validate_inputs(packet, bundle, plan, stage_index)
    prompt = build_context_relay_prompt(
        packet=packet,
        bundle=bundle,
        plan=plan,
        stage_index=stage_index,
        instruction=instruction,
        config=config,
    )
    prompt_hash = hash_text(prompt)
    prompt_path = context_relay_dir(ws) / context_relay_filename(
        packet, bundle, plan, stage_index, assignment.provider
    )
    manifest_path = manifest_path_for_prompt(prompt_path)

    if prompt_path.exists() and hash_file(prompt_path) != prompt_hash:
        raise WorkspaceError(
            f"a different governed prompt already exists at {prompt_path}"
        )
    if manifest_path.exists():
        record = read_context_relay_export(manifest_path)
        if (
            record.prompt_hash != prompt_hash
            or record.prompt_file != prompt_path.name
        ):
            raise WorkspaceError(
                f"a different context relay manifest already exists at {manifest_path}"
            )
        if not prompt_path.exists():
            raise IntegrityError(
                f"context relay manifest exists but prompt is missing: {prompt_path}"
            )
        return record, prompt_path, manifest_path, False

    if not prompt_path.exists():
        write_canonical(prompt_path, prompt)

    data = {
        "schema_version": CONTEXT_RELAY_SCHEMA_VERSION,
        "packet_ref": packet.ref,
        "packet_content_hash": packet.content_hash,
        "context_bundle_hash": bundle.content_hash,
        "route_plan_hash": plan.content_hash,
        "stage_index": stage_index,
        "provider": assignment.provider,
        "role": assignment.role,
        "prompt_file": prompt_path.name,
        "prompt_hash": prompt_hash,
        "exported_at": utcnow(),
    }
    draft = ContextRelayExport.model_construct(**data, content_hash="pending")
    record = ContextRelayExport.model_validate({
        **data,
        "content_hash": compute_export_hash(draft),
    })
    write_canonical(
        manifest_path,
        yaml.safe_dump(
            record.model_dump(mode="json"),
            sort_keys=False,
            allow_unicode=True,
        ),
    )
    return record, prompt_path, manifest_path, True


def read_context_relay_export(path: Path) -> ContextRelayExport:
    path = Path(path)
    if not path.exists():
        raise WorkspaceError(f"no context relay export at {path}")
    record = ContextRelayExport.model_validate(
        yaml.safe_load(path.read_text(encoding="utf-8"))
    )
    prompt_path = path.parent / record.prompt_file
    if not prompt_path.exists():
        raise IntegrityError(f"context relay prompt is missing: {prompt_path}")
    if hash_file(prompt_path) != record.prompt_hash:
        raise IntegrityError(f"context relay prompt hash mismatch: {prompt_path}")
    return record


def read_context_relay_records(ws: Workspace) -> list[dict]:
    base = context_relay_dir(ws)
    if not base.exists():
        return []
    return [
        read_context_relay_export(path).as_export_record()
        for path in sorted(base.glob("*.yaml"))
    ]
