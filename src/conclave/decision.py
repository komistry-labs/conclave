"""Authority-safe recording of a human decision on a Council Review.

The Council Review remains immutable and permanently carries ``pending`` in
its reserved decision block.  A human decision is a separate, write-once
artifact bound to the exact hashes of that review and its Task Packet.

The exact-principal entry used here is a local operator confirmation ceremony,
not cryptographic proof of identity.  The record says so explicitly.  Provider
adapters and reconciliation have no path that creates these artifacts.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Annotated, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .council import read_council, verify_council_content_hash
from .errors import ValidationError
from .hashing import hash_text, write_canonical
from .taskpacket import read_packet, verify_content_hash
from .workspace import Workspace, utcnow

INSTRUCTION_SCHEMA_VERSION = "authority-decision-instruction/0.1.0"
DECISION_SCHEMA_VERSION = "authority-decision/0.1.0"
DecisionValue = Literal["approve", "revise", "reject", "defer"]
COUNCIL_REVIEW_ID_PATTERN = (
    r"^CR-TP-[a-z0-9][a-z0-9-]{0,47}-[0-9a-f]{10}-v[1-9][0-9]*-[0-9a-f]{10}$"
)
BoundedAction = Annotated[str, Field(min_length=1, max_length=500)]


def _require_utc(value: str) -> str:
    if not value.endswith("Z"):
        raise ValueError("must be an ISO 8601 UTC timestamp ending in 'Z'")
    try:
        datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError("must be a valid ISO 8601 UTC timestamp") from exc
    return value


class DecisionInstruction(BaseModel):
    """Principal-authored input. Unknown fields are refused."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[INSTRUCTION_SCHEMA_VERSION] = INSTRUCTION_SCHEMA_VERSION
    council_review_id: str = Field(..., pattern=COUNCIL_REVIEW_ID_PATTERN)
    council_review_hash: str = Field(..., pattern=r"^sha256:[0-9a-f]{64}$")
    decision: DecisionValue
    decided_by: str = Field(..., min_length=1, max_length=200)
    decided_at: str
    rationale: str = Field(..., min_length=1, max_length=10_000)
    authorised_actions: list[BoundedAction] = Field(default_factory=list, max_length=64)
    authority_ref: str = Field(..., min_length=1, max_length=500)

    @field_validator("decided_at")
    @classmethod
    def _valid_time(cls, value: str) -> str:
        return _require_utc(value)

    @field_validator("authorised_actions")
    @classmethod
    def _nonempty_actions(cls, values: list[str]) -> list[str]:
        if any(not value.strip() for value in values):
            raise ValueError("authorised actions must not be empty")
        if len(set(values)) != len(values):
            raise ValueError("authorised actions must be unique")
        return values

    @model_validator(mode="after")
    def _actions_match_decision(self) -> "DecisionInstruction":
        if self.decision in ("reject", "defer") and self.authorised_actions:
            raise ValueError(f"decision {self.decision!r} cannot authorise actions")
        return self

    def to_serialisable(self) -> dict:
        return self.model_dump(mode="json")


class AuthorityDecisionRecord(BaseModel):
    """Sealed, immutable record written by CONCLAVE after confirmation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[DECISION_SCHEMA_VERSION] = DECISION_SCHEMA_VERSION
    decision_id: str
    council_review_id: str = Field(..., pattern=COUNCIL_REVIEW_ID_PATTERN)
    council_review_hash: str = Field(..., pattern=r"^sha256:[0-9a-f]{64}$")
    council_review_status: str
    task_packet_ref: str
    task_packet_hash: str = Field(..., pattern=r"^sha256:[0-9a-f]{64}$")
    decision: DecisionValue
    decided_by: str
    decided_at: str
    rationale: str
    authorised_actions: list[BoundedAction] = Field(default_factory=list, max_length=64)
    authority_ref: str
    instruction_hash: str = Field(..., pattern=r"^sha256:[0-9a-f]{64}$")
    recorded_at: str
    confirmation_method: Literal["exact-workspace-principal-entry"] = (
        "exact-workspace-principal-entry"
    )
    identity_assurance: Literal["local-operator-confirmation-not-cryptographic"] = (
        "local-operator-confirmation-not-cryptographic"
    )
    content_hash: str | None = Field(None, pattern=r"^sha256:[0-9a-f]{64}$")

    def to_serialisable(self) -> dict:
        return self.model_dump(mode="json", exclude_none=False)


@dataclass(frozen=True)
class DecisionOutcome:
    record: AuthorityDecisionRecord
    yaml_path: Path
    markdown_path: Path
    created: bool


def instruction_hash(instruction: DecisionInstruction) -> str:
    return hash_text(yaml.safe_dump(
        instruction.to_serialisable(), sort_keys=True, allow_unicode=True
    ))


def compute_content_hash(record: AuthorityDecisionRecord) -> str:
    payload = {k: v for k, v in record.to_serialisable().items() if k != "content_hash"}
    return hash_text(yaml.safe_dump(payload, sort_keys=True, allow_unicode=True))


def seal(record: AuthorityDecisionRecord) -> AuthorityDecisionRecord:
    return record.model_copy(update={"content_hash": compute_content_hash(record)})


def verify_decision_content_hash(record: AuthorityDecisionRecord) -> bool:
    return bool(record.content_hash) and record.content_hash == compute_content_hash(record)


def read_instruction(path: Path) -> DecisionInstruction:
    try:
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        return DecisionInstruction.model_validate(data)
    except OSError as exc:
        raise ValidationError(f"cannot read decision instruction {path}: {exc}") from exc
    except Exception as exc:
        raise ValidationError(f"invalid decision instruction {path}: {exc}") from exc


def read_decision(path: Path) -> AuthorityDecisionRecord:
    try:
        return AuthorityDecisionRecord.model_validate(
            yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        )
    except OSError as exc:
        raise ValidationError(f"cannot read authority decision {path}: {exc}") from exc
    except Exception as exc:
        raise ValidationError(f"invalid authority decision {path}: {exc}") from exc


def prepare_decision(ws: Workspace, instruction: DecisionInstruction) -> AuthorityDecisionRecord:
    config = ws.load_config()
    principal = config.get("principal")
    constitutional = (config.get("authority") or {}).get("constitutional_authority")
    if not principal or principal != constitutional:
        raise ValidationError(
            "workspace principal and constitutional authority are absent or inconsistent"
        )
    if instruction.decided_by != principal:
        raise ValidationError(
            f"decided_by {instruction.decided_by!r} is not the workspace principal "
            f"{principal!r}"
        )

    review_path = ws.council_dir / f"{instruction.council_review_id}.yaml"
    if not review_path.exists():
        raise ValidationError(f"no Council Review at {review_path}")
    review = read_council(review_path)
    if not verify_council_content_hash(review):
        raise ValidationError("Council Review content_hash does not verify")
    if review.council_review_id != instruction.council_review_id:
        raise ValidationError("Council Review id does not match its filename/instruction")
    if review.content_hash != instruction.council_review_hash:
        raise ValidationError("decision instruction cites a different Council Review hash")
    if review.decision_block.decision != "pending":
        raise ValidationError("Council Review decision block is not pending")
    if instruction.decision == "approve" and review.review_status != "ready_for_human_review":
        raise ValidationError(
            "approve is permitted only for a Council Review that is ready_for_human_review"
        )

    try:
        task_id, version_text = review.task_packet_ref.rsplit("@v", 1)
        packet = read_packet(ws, task_id, int(version_text))
    except Exception as exc:
        raise ValidationError(f"cannot resolve cited Task Packet: {exc}") from exc
    if not verify_content_hash(packet):
        raise ValidationError("cited Task Packet content_hash does not verify")
    if packet.ref != review.task_packet_ref or packet.content_hash != review.task_packet_hash:
        raise ValidationError("Council Review does not bind to the stored Task Packet")

    ihash = instruction_hash(instruction)
    digest = hashlib.sha256(
        f"{review.content_hash}\n{ihash}".encode("utf-8")
    ).hexdigest()[:12]
    return seal(AuthorityDecisionRecord(
        decision_id=f"DR-{review.council_review_id}-{digest}",
        council_review_id=review.council_review_id,
        council_review_hash=review.content_hash or "",
        council_review_status=review.review_status,
        task_packet_ref=review.task_packet_ref,
        task_packet_hash=review.task_packet_hash,
        decision=instruction.decision,
        decided_by=instruction.decided_by,
        decided_at=instruction.decided_at,
        rationale=instruction.rationale,
        authorised_actions=list(instruction.authorised_actions),
        authority_ref=instruction.authority_ref,
        instruction_hash=ihash,
        recorded_at=utcnow(),
    ))


def yaml_path(ws: Workspace, decision_id: str) -> Path:
    return ws.decisions_dir / f"{decision_id}.yaml"


def markdown_path(ws: Workspace, decision_id: str) -> Path:
    return ws.decisions_dir / f"{decision_id}.md"


def _existing_for_review(ws: Workspace, review_id: str) -> list[Path]:
    if not ws.decisions_dir.exists():
        return []
    matches: list[Path] = []
    for path in sorted(ws.decisions_dir.glob("*.yaml")):
        record = read_decision(path)
        if not verify_decision_content_hash(record):
            raise ValidationError(f"existing authority decision {path.name} does not verify")
        if record.council_review_id == review_id:
            matches.append(path)
    return matches


def record_decision(
    ws: Workspace,
    instruction: DecisionInstruction,
    *,
    confirmed_principal: str,
    prepared: AuthorityDecisionRecord | None = None,
) -> DecisionOutcome:
    # Human decisions require an already-initialised, healthy audit chain.
    # This check occurs before any artifact write.
    from . import ledger

    if not ledger.exists(ws):
        raise ValidationError(
            "authority decisions require an initialised ledger; run 'conclave ledger init'"
        )
    ledger_report = ledger.verify(ws)
    if not ledger_report.ok:
        raise ValidationError("authority decision refused because the ledger does not verify")

    principal = ws.load_config().get("principal")
    if confirmed_principal != principal:
        raise ValidationError("exact workspace-principal confirmation did not match")

    record = prepared or prepare_decision(ws, instruction)
    # Rebuild after confirmation unless the caller supplied the exact candidate.
    if prepared is not None:
        check = prepare_decision(ws, instruction)
        stable_fields = {"recorded_at", "content_hash"}
        if prepared.model_dump(exclude=stable_fields) != check.model_dump(exclude=stable_fields):
            raise ValidationError("prepared decision no longer matches verified sources")

    existing = _existing_for_review(ws, record.council_review_id)
    if existing:
        if len(existing) != 1:
            raise ValidationError(
                f"Council Review {record.council_review_id} has multiple authority "
                "decision artifacts; refusing to choose between them"
            )
        current = read_decision(existing[0])
        # A retry of the exact instruction is permitted so a failed ledger append can
        # be retried after the human reconfirms. The immutable artifact is unchanged.
        if current.instruction_hash == record.instruction_hash:
            projection = existing[0].with_suffix(".md")
            if not projection.exists():
                write_canonical(projection, render_markdown(current))
            outcome = DecisionOutcome(
                current, existing[0], projection, False
            )
            _record_ledger_event(ws, outcome)
            return outcome
        raise ValidationError(
            f"Council Review {record.council_review_id} already has an immutable "
            f"authority decision: {existing[0].name}"
        )

    ypath = yaml_path(ws, record.decision_id)
    mpath = markdown_path(ws, record.decision_id)
    ypath.parent.mkdir(parents=True, exist_ok=True)
    text = yaml.safe_dump(record.to_serialisable(), sort_keys=False, allow_unicode=True)
    ypath.write_bytes(text.replace("\r\n", "\n").encode("utf-8"))
    write_canonical(mpath, render_markdown(record))
    outcome = DecisionOutcome(record, ypath, mpath, True)
    _record_ledger_event(ws, outcome)
    return outcome


def _record_ledger_event(ws: Workspace, outcome: DecisionOutcome) -> None:
    """Append the bounded audit event; exact retries are idempotent."""
    from .ledger import append_event

    record = outcome.record
    append_event(
        ws,
        event_type="human_decision_recorded",
        actor=record.decided_by,
        authority_level="human_principal",
        subject_refs=[record.task_packet_ref, record.council_review_id, record.decision_id],
        artifact_hashes={
            "authority_decision": record.content_hash or "",
            "council_review": record.council_review_hash,
            "task_packet": record.task_packet_hash,
        },
        payload={
            "decision": record.decision,
            "authority_ref": record.authority_ref,
            "authorised_action_count": len(record.authorised_actions),
            "decision_file": outcome.yaml_path.name,
            "confirmation_method": record.confirmation_method,
            "identity_assurance": record.identity_assurance,
            "note": "records the named human principal's bounded decision; provider "
                    "submissions remain advisory",
        },
        occurred_at=record.decided_at,
    )


def render_markdown(record: AuthorityDecisionRecord) -> str:
    actions = [f"- {action}" for action in record.authorised_actions] or ["_none_"]
    return "\n".join([
        f"# Authority Decision — {record.council_review_id}", "",
        f"> **{record.decision.upper()}** — recorded for `{record.decided_by}`", "",
        "## Binding", "", "```",
        f"decision_id        : {record.decision_id}",
        f"content_hash       : {record.content_hash}",
        f"council_review_id  : {record.council_review_id}",
        f"council_review_hash: {record.council_review_hash}",
        f"task_packet_ref    : {record.task_packet_ref}",
        f"task_packet_hash   : {record.task_packet_hash}", "```", "",
        "The YAML artifact is authoritative. The Council Review remains immutable and",
        "continues to display its reserved `decision: pending` block.", "",
        "## Decision", "", f"**Decision:** {record.decision}", "",
        f"**Decided by:** {record.decided_by}", "",
        f"**Decided at:** {record.decided_at}", "",
        f"**Authority reference:** {record.authority_ref}", "",
        record.rationale, "", "## Authorised actions", "", *actions, "",
        "## Identity assurance", "",
        "Recorded after exact workspace-principal entry. This is local operator",
        "confirmation, not cryptographic identity proof or multi-custodian approval.", "",
    ])
