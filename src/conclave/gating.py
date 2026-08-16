"""Increment 19C opt-in identity and evidence workflow gates.

Identity evidence supplements the existing principal and governance checks.  It
never creates authority, membership, approval, or a decision by itself.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Literal

import yaml

from .errors import ValidationError
from .evidence import (
    SignedEvidenceBinding,
    evidence_reliance_state,
    read_signed_binding,
    verified_workspace_id,
)
from .identity import (
    ActorIdentityBinding,
    IdentityVerificationResult,
    read_record,
    write_immutable_record,
)
from .ledger import append_event, record_event
from .workspace import Workspace

IdentityMode = Literal["local", "verify", "attested"]
GateOperation = Literal[
    "identity_binding_import",
    "egress_decision",
    "authority_decision",
    "signed_ledger_checkpoint",
    "evidence_receipt",
]

MODE_ORDER: dict[str, int] = {"local": 0, "verify": 1, "attested": 2}


@dataclass(frozen=True)
class GateOutcome:
    operation: GateOperation
    mode: IdentityMode
    target_reference: str
    target_hash: str
    actor_id: str
    identity_verification_hash: str | None
    signed_evidence_binding_hash: str | None
    admitted: bool = True
    authority_effect: Literal["none"] = "none"
    membership_effect: Literal["none"] = "none"


def identity_mode(ws: Workspace) -> IdentityMode:
    value = (ws.load_config().get("identity") or {}).get("mode", "local")
    if value not in MODE_ORDER:
        raise ValidationError(f"workspace identity mode {value!r} is unsupported")
    return value  # type: ignore[return-value]


def set_identity_mode(
    ws: Workspace, mode: IdentityMode, *, confirmed_principal: str
) -> tuple[IdentityMode, bool]:
    """Explicitly strengthen a workspace mode; never silently downgrade it."""

    config = ws.load_config()
    principal = config.get("principal")
    constitutional = (config.get("authority") or {}).get("constitutional_authority")
    if not principal or principal != constitutional or confirmed_principal != principal:
        raise ValidationError("exact workspace-principal confirmation did not match")
    current = identity_mode(ws)
    if MODE_ORDER[mode] < MODE_ORDER[current]:
        raise ValidationError("identity mode downgrade is refused")
    if mode == current:
        return current, False
    # Strong modes depend on a verified workspace identity derived from genesis.
    if mode != "local":
        verified_workspace_id(ws)
    identity = dict(config.get("identity") or {})
    identity["mode"] = mode
    config["identity"] = identity
    payload = yaml.safe_dump(config, sort_keys=False, allow_unicode=True).encode("utf-8")
    temporary = ws.config_path.with_name(ws.config_path.name + ".identity-mode.tmp")
    with temporary.open("xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, ws.config_path)
    return mode, True


def _stored_record_path(ws: Workspace, reference: str, area: Path, label: str) -> Path:
    if "\\" in reference or ":" in reference or reference.startswith("/"):
        raise ValidationError(f"{label} reference is not canonical workspace-relative POSIX")
    pure = PurePosixPath(reference)
    if not reference or any(part in {"", ".", ".."} for part in pure.parts):
        raise ValidationError(f"{label} reference contains traversal")
    allowed_parts = area.relative_to(ws.root).parts
    if pure.parts[: len(allowed_parts)] != allowed_parts:
        raise ValidationError(f"{label} reference is outside its allowlisted area")
    path = ws.root.joinpath(*pure.parts)
    resolved = path.resolve()
    if resolved.parent != area.resolve() or not resolved.is_relative_to(ws.root.resolve()):
        raise ValidationError(f"{label} reference escapes its allowlisted area")
    current = ws.root
    for part in pure.parts:
        current = current / part
        try:
            attrs = getattr(current.lstat(), "st_file_attributes", 0)
        except OSError as exc:
            raise ValidationError(f"{label} is missing or unreadable") from exc
        if current.is_symlink() or attrs & 0x400:
            raise ValidationError(f"{label} path contains a symlink or reparse point")
    if not path.is_file():
        raise ValidationError(f"{label} is not a regular file")
    return path


def _identity_pass(
    ws: Workspace,
    *,
    actor_id: str,
    target_reference: str,
    verification_reference: str,
) -> IdentityVerificationResult:
    verification_path = _stored_record_path(
        ws, verification_reference, ws.identity_verifications_dir, "identity verification"
    )
    result = read_record(verification_path, IdentityVerificationResult)
    if result.status != "PASS" or result.reason_codes:
        raise ValidationError("gated operation requires an identity PASS")
    if not result.verifier_implementation.is_frozen_baseline():
        raise ValidationError("identity PASS does not use the frozen IDM baseline")
    binding_path = _stored_record_path(
        ws, result.actor_binding_reference, ws.identity_bindings_dir, "actor binding"
    )
    binding = read_record(binding_path, ActorIdentityBinding)
    if binding.content_hash != result.actor_binding_hash:
        raise ValidationError("identity PASS cites a different actor binding hash")
    if result.eid != binding.eid or result.mid != binding.mid or result.vid != binding.vid:
        raise ValidationError("identity PASS and actor binding identities differ")
    if (
        binding.actor_id != actor_id
        or binding.actor_kind != "human"
        or binding.expected_authority_level != "human_principal"
    ):
        raise ValidationError("identity PASS is not bound to the human principal")
    if binding.workspace_id != verified_workspace_id(ws):
        raise ValidationError("identity PASS belongs to a different workspace")
    if binding.task_scope not in {target_reference, "workspace:*"}:
        raise ValidationError("identity PASS does not cover the gated target")
    return result


def _attested_binding(
    ws: Workspace,
    *,
    target_reference: str,
    target_hash: str,
    binding_reference: str,
) -> SignedEvidenceBinding:
    path = _stored_record_path(
        ws, binding_reference, ws.signing_bindings_dir, "signed evidence binding"
    )
    binding = read_signed_binding(path)
    if (
        binding.verification_status != "PASS"
        or binding.reason_codes
        or not binding.request_binding_verified
        or binding.payload is None
    ):
        raise ValidationError("attested mode requires a verified signed evidence binding")
    if evidence_reliance_state(ws, binding.signing_request_hash) == "BLOCKED_CONFLICT":
        raise ValidationError("conflicting evidence blocks workflow reliance")
    if evidence_reliance_state(ws, binding.signing_request_hash) != "VERIFIED_NOT_GATED":
        raise ValidationError("signed evidence is not independently reliable")
    if (
        binding.payload.artifact_reference != target_reference
        or binding.payload.artifact_content_hash != target_hash
    ):
        raise ValidationError("signed evidence does not bind the gated target")
    return binding


def enforce_principal_gate(
    ws: Workspace,
    *,
    operation: GateOperation,
    actor_id: str,
    target_reference: str,
    target_hash: str,
    identity_verification_reference: str | None = None,
    signed_evidence_binding_reference: str | None = None,
) -> GateOutcome:
    """Apply the configured mode without replacing the human-principal check."""

    principal = ws.load_config().get("principal")
    if actor_id != principal:
        raise ValidationError("gated actor is not the configured workspace principal")
    mode = identity_mode(ws)
    if mode == "local":
        return GateOutcome(operation, mode, target_reference, target_hash, actor_id, None, None)
    if identity_verification_reference is None:
        raise ValidationError(f"identity mode {mode!r} requires an identity verification")
    identity = _identity_pass(
        ws,
        actor_id=actor_id,
        target_reference=target_reference,
        verification_reference=identity_verification_reference,
    )
    evidence: SignedEvidenceBinding | None = None
    if mode == "attested":
        if signed_evidence_binding_reference is None:
            raise ValidationError("attested mode requires a signed evidence binding")
        evidence = _attested_binding(
            ws,
            target_reference=target_reference,
            target_hash=target_hash,
            binding_reference=signed_evidence_binding_reference,
        )
    return GateOutcome(
        operation,
        mode,
        target_reference,
        target_hash,
        actor_id,
        identity.content_hash,
        evidence.content_hash if evidence else None,
    )


def import_actor_binding(
    ws: Workspace, source: Path, *, confirmed_principal: str
) -> tuple[ActorIdentityBinding, Path, bool]:
    """Import one public binding claim; this does not verify or activate it."""

    principal = ws.load_config().get("principal")
    if confirmed_principal != principal:
        raise ValidationError("exact workspace-principal confirmation did not match")
    binding = read_record(Path(source), ActorIdentityBinding)
    if binding.workspace_id != verified_workspace_id(ws):
        raise ValidationError("actor binding belongs to a different workspace")
    expected = {
        "human": "human_principal",
        "advisory_agent": "advisory_agent",
        "system": "system",
    }[binding.actor_kind]
    if binding.expected_authority_level != expected:
        raise ValidationError("actor binding attempts to change its authority ceiling")
    digest = binding.content_hash.split(":", 1)[1]
    path, created = write_immutable_record(
        ws.identity_bindings_dir / f"{digest}.json", binding
    )
    record_event(
        ws,
        event_type="actor_identity_binding_imported",
        actor="conclave",
        authority_level="system",
        subject_refs=[binding.actor_id],
        artifact_hashes={"actor_identity_binding": binding.content_hash},
        payload={
            "binding_file": path.relative_to(ws.root).as_posix(),
            "claim_status": "awaiting-verification",
            "authority_effect": "none",
            "membership_effect": "none",
            "action_execution_allowed": False,
        },
    )
    return binding, path, created


def record_evidence_receipt(
    ws: Workspace,
    *,
    signed_evidence_binding_reference: str,
    identity_verification_reference: str,
    confirmed_principal: str,
) -> tuple[dict, bool]:
    """Record principal receipt of one verified envelope; never approval semantics."""

    if identity_mode(ws) != "attested":
        raise ValidationError("signed evidence receipts require attested mode")
    principal = ws.load_config().get("principal")
    if confirmed_principal != principal:
        raise ValidationError("exact workspace-principal confirmation did not match")
    path = _stored_record_path(
        ws,
        signed_evidence_binding_reference,
        ws.signing_bindings_dir,
        "signed evidence binding",
    )
    binding = read_signed_binding(path)
    if binding.payload is None:
        raise ValidationError("signed evidence binding has no verified payload")
    gate = enforce_principal_gate(
        ws,
        operation="evidence_receipt",
        actor_id=principal,
        target_reference=binding.payload.artifact_reference,
        target_hash=binding.payload.artifact_content_hash,
        identity_verification_reference=identity_verification_reference,
        signed_evidence_binding_reference=signed_evidence_binding_reference,
    )
    return append_event(
        ws,
        event_type="evidence_receipt_recorded",
        actor=principal,
        authority_level="human_principal",
        subject_refs=[binding.payload.artifact_reference],
        artifact_hashes={
            "signed_evidence_binding": binding.content_hash,
            "evidence_envelope": binding.envelope_hash,
            "identity_verification": gate.identity_verification_hash or "",
        },
        payload={
            "identity_mode": "attested",
            "receipt_only": True,
            "authority_effect": "none",
            "membership_effect": "none",
            "decision_effect": "none",
            "action_execution_allowed": False,
        },
    )
