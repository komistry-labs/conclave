"""Immutable ledger-checkpoint candidates and attested receipt recording."""

from __future__ import annotations

from pathlib import Path, PurePosixPath
from typing import Literal

from pydantic import Field

from .errors import ValidationError
from .identity import HashedRecord, read_record, seal_record, write_immutable_record
from .ledger import GENESIS_EVENT, LEDGER_SCHEMA_VERSION, append_event, read_events, verify
from .workspace import Workspace

CHECKPOINT_SCHEMA = "conclave-ledger-checkpoint/0.1.0"


class LedgerCheckpoint(HashedRecord):
    profile: Literal["conclave-ledger-checkpoint"] = "conclave-ledger-checkpoint"
    schema_version: Literal["conclave-ledger-checkpoint/0.1.0"] = CHECKPOINT_SCHEMA
    workspace_id: str = Field(pattern=r"^workspace:sha256:[0-9a-f]{64}$")
    ledger_schema_version: Literal["conclave-ledger/0.1.0"] = LEDGER_SCHEMA_VERSION
    entry_count: int = Field(ge=1)
    chain_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    authority_effect: Literal["none"] = "none"
    decision_effect: Literal["none"] = "none"
    membership_effect: Literal["none"] = "none"
    action_execution_allowed: Literal[False] = False


def _workspace_id(ws: Workspace) -> str:
    report = verify(ws)
    events = read_events(ws)
    if not report.ok or not events or events[0].get("event_type") != GENESIS_EVENT:
        raise ValidationError("checkpoint requires a valid workspace genesis")
    return "workspace:" + events[0]["entry_hash"]


def prepare_ledger_checkpoint(ws: Workspace) -> tuple[LedgerCheckpoint, Path, bool]:
    report = verify(ws)
    if not report.ok or report.final_chain_hash is None:
        raise ValidationError("ledger checkpoint requires a valid initialized ledger")
    checkpoint = seal_record(LedgerCheckpoint, {
        "profile": "conclave-ledger-checkpoint",
        "schema_version": CHECKPOINT_SCHEMA,
        "workspace_id": _workspace_id(ws),
        "ledger_schema_version": LEDGER_SCHEMA_VERSION,
        "entry_count": report.entry_count,
        "chain_hash": report.final_chain_hash,
        "authority_effect": "none",
        "decision_effect": "none",
        "membership_effect": "none",
        "action_execution_allowed": False,
    })
    digest = checkpoint.content_hash.split(":", 1)[1]
    return checkpoint, *write_immutable_record(
        ws.ledger_dir / f"checkpoint-{digest}.json", checkpoint
    )


def read_ledger_checkpoint(path: Path) -> LedgerCheckpoint:
    return read_record(path, LedgerCheckpoint)


def record_signed_checkpoint(
    ws: Workspace,
    *,
    checkpoint_reference: str,
    identity_verification_reference: str,
    signed_evidence_binding_reference: str,
    confirmed_principal: str,
) -> tuple[dict, bool]:
    from .gating import enforce_principal_gate, identity_mode

    if identity_mode(ws) != "attested":
        raise ValidationError("signed ledger checkpoint recording requires attested mode")
    principal = ws.load_config().get("principal")
    if confirmed_principal != principal:
        raise ValidationError("exact workspace-principal confirmation did not match")
    if "\\" in checkpoint_reference or ":" in checkpoint_reference or checkpoint_reference.startswith("/"):
        raise ValidationError("checkpoint reference is not canonical workspace-relative POSIX")
    pure = PurePosixPath(checkpoint_reference)
    if (
        any(part in {"", ".", ".."} for part in pure.parts)
        or pure.parts[:1] != ("ledger",)
    ):
        raise ValidationError("checkpoint reference is not canonical workspace-relative POSIX")
    candidate = ws.root.joinpath(*pure.parts)
    path = candidate.resolve()
    if path.parent != ws.ledger_dir.resolve() or not candidate.is_file():
        raise ValidationError("checkpoint must be stored in this workspace ledger area")
    current = ws.root
    for part in pure.parts:
        current = current / part
        attrs = getattr(current.lstat(), "st_file_attributes", 0)
        if current.is_symlink() or attrs & 0x400:
            raise ValidationError("checkpoint path contains a symlink or reparse point")
    checkpoint = read_ledger_checkpoint(path)
    if checkpoint.workspace_id != _workspace_id(ws):
        raise ValidationError("checkpoint belongs to a different workspace")
    # The checkpoint is a historical prefix. Verify that exact entry still
    # exists at its recorded position and retains the same chain hash.
    events = read_events(ws)
    if len(events) < checkpoint.entry_count:
        raise ValidationError("ledger is shorter than the checkpoint")
    if events[checkpoint.entry_count - 1].get("entry_hash") != checkpoint.chain_hash:
        raise ValidationError("ledger no longer contains the checkpointed prefix")
    gate = enforce_principal_gate(
        ws,
        operation="signed_ledger_checkpoint",
        actor_id=principal,
        target_reference=checkpoint.content_hash,
        target_hash=checkpoint.content_hash,
        identity_verification_reference=identity_verification_reference,
        signed_evidence_binding_reference=signed_evidence_binding_reference,
    )
    return append_event(
        ws,
        event_type="signed_ledger_checkpoint_recorded",
        actor=principal,
        authority_level="human_principal",
        subject_refs=[checkpoint.content_hash],
        artifact_hashes={
            "ledger_checkpoint": checkpoint.content_hash,
            "identity_verification": gate.identity_verification_hash or "",
            "signed_evidence_binding": gate.signed_evidence_binding_hash or "",
        },
        payload={
            "checkpoint_file": path.relative_to(ws.root).as_posix(),
            "checkpoint_entry_count": checkpoint.entry_count,
            "checkpoint_chain_hash": checkpoint.chain_hash,
            "identity_mode": "attested",
            "authority_effect": "none",
            "decision_effect": "none",
            "membership_effect": "none",
            "action_execution_allowed": False,
        },
    )
