"""Scope drift detection.

Compares what a provider DECLARED it touched against what the Task Packet
granted, and produces an immutable sealed Scope Review.

What this does not do, deliberately:

    It reads `objects_touched` and nothing else. It does not parse the
    provider's prose, output body or findings looking for objects the
    provider failed to declare. A detector that guessed at undeclared
    objects would report findings nobody could verify and would create the
    impression that undeclared work is reliably caught. It is not.

    Missing declarations are a Council Review concern, where a human is
    looking. Scope drift reports only what was declared, and says so.

Neither packet is modified. Both are verified before evaluation: a Scope
Review computed against an altered packet would attest to something that no
longer exists.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

from .errors import ValidationError
from .handoff import HandoffPacket, ObjectTouched, verify_handoff_content_hash
from .hashing import hash_text
from .models import ObjectRef, TaskPacket
from .taskpacket import read_packet, verify_content_hash
from .workspace import Workspace, utcnow

SCOPE_SCHEMA_VERSION = "scope-review/0.1.0"
HASH_LEN = 12

Classification = Literal[
    "in_target",
    "in_read_only",
    "read_only_modified",
    "prohibited_touched",
    "undeclared_expansion",
]

VIOLATIONS: frozenset[str] = frozenset(
    {"read_only_modified", "prohibited_touched", "undeclared_expansion"}
)

# Ordering used when the same object is declared touched more than once.
ACTION_SEVERITY = {"read": 0, "cited": 1, "proposed_change": 2}


# -- containment -----------------------------------------------------------

def grant_covers(grant: ObjectRef, touch: ObjectTouched) -> bool:
    """Does `grant` cover `touch`?

    A whole-object grant covers the object and every section of it.
    A section grant covers ONLY that section — not the whole object, and not
    a sibling section. Permission to edit RA-001-PART-IV is not permission to
    edit RA-001, and a reviewer who granted the narrower thing should not
    find the broader thing has been done under it.
    """
    if grant.object_id != touch.object_id:
        return False
    if grant.section_id is None:
        return True
    return grant.section_id == touch.section_id


def _first_covering(grants: list[ObjectRef], touch: ObjectTouched) -> ObjectRef | None:
    for g in grants:
        if grant_covers(g, touch):
            return g
    return None


# -- models ----------------------------------------------------------------

class ObjectResult(BaseModel):
    model_config = ConfigDict(extra="allow", frozen=True)

    object_id: str
    section_id: str | None = None
    key: str
    actions: list[str] = Field(default_factory=list)
    action: str
    classification: Classification
    allowed: bool
    matched_grant: str | None = Field(
        None, description="Scope entry that decided this result, or null if undeclared."
    )
    reason: str


class ScopeReview(BaseModel):
    """Immutable sealed record of one scope evaluation."""

    model_config = ConfigDict(extra="allow", frozen=True)

    schema_version: str = SCOPE_SCHEMA_VERSION
    task_packet_ref: str
    task_packet_hash: str
    handoff_packet_hash: str
    provider: str
    role: str
    evaluated_at: str
    object_results: list[ObjectResult] = Field(default_factory=list)
    scope_status: Literal["within_scope", "expansion_detected"]
    human_review_required: bool
    declared_touch_count: int = 0
    violation_count: int = 0
    evaluation_basis: str = (
        "declared objects_touched only; provider prose was not parsed"
    )
    content_hash: str | None = None

    @property
    def task_id(self) -> str:
        return self.task_packet_ref.split("@", 1)[0]

    @property
    def packet_version(self) -> int:
        return int(self.task_packet_ref.rsplit("@v", 1)[1])

    def violations(self) -> list[ObjectResult]:
        return [r for r in self.object_results if not r.allowed]

    def to_serialisable(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude_none=False)


# -- evaluation ------------------------------------------------------------

def classify(
    touch: ObjectTouched, packet: TaskPacket
) -> tuple[Classification, bool, str | None, str]:
    """Classify one touch. Returns (classification, allowed, matched_grant, reason).

    Precedence is prohibited > read-only > target > undeclared. It only bites
    when scope sets overlap, which packet validation already rejects as a
    governance violation — but if a malformed packet reaches here, the most
    restrictive grant must win. A precedence that resolved toward permission
    would turn a validation gap into an authorisation.
    """
    prohibited = _first_covering(packet.prohibited_objects, touch)
    if prohibited is not None:
        return ("prohibited_touched", False, prohibited.key(),
                f"{touch.action} of an object prohibited by {prohibited.key()}")

    read_only = _first_covering(packet.read_only_objects, touch)
    if read_only is not None:
        if touch.action == "proposed_change":
            return ("read_only_modified", False, read_only.key(),
                    f"proposed_change to {read_only.key()}, which was granted read-only")
        return ("in_read_only", True, read_only.key(),
                f"{touch.action} permitted under read-only grant {read_only.key()}")

    target = _first_covering(packet.target_objects, touch)
    if target is not None:
        return ("in_target", True, target.key(),
                f"{touch.action} permitted under target grant {target.key()}")

    return ("undeclared_expansion", False, None,
            f"{touch.action} of an object not present in any scope set")


def evaluate(packet: TaskPacket, handoff: HandoffPacket) -> ScopeReview:
    """Evaluate declared touches against granted scope. Modifies nothing."""
    grouped: dict[str, list[ObjectTouched]] = {}
    for touch in handoff.objects_touched:
        grouped.setdefault(touch.key(), []).append(touch)

    results: list[ObjectResult] = []
    for key, touches in grouped.items():
        # Where an object is declared more than once, the most severe action
        # governs: a later `read` does not excuse an earlier `proposed_change`.
        governing = max(touches, key=lambda t: ACTION_SEVERITY.get(t.action, 0))
        classification, allowed, matched, reason = classify(governing, packet)
        results.append(ObjectResult(
            object_id=governing.object_id,
            section_id=governing.section_id,
            key=key,
            actions=sorted({t.action for t in touches}),
            action=governing.action,
            classification=classification,
            allowed=allowed,
            matched_grant=matched,
            reason=reason,
        ))

    results.sort(key=lambda r: (r.allowed, r.key))
    violations = [r for r in results if not r.allowed]

    return seal(ScopeReview(
        task_packet_ref=packet.ref,
        task_packet_hash=packet.content_hash or "",
        handoff_packet_hash=handoff.content_hash or "",
        provider=handoff.provider,
        role=handoff.role,
        evaluated_at=utcnow(),
        object_results=results,
        scope_status="expansion_detected" if violations else "within_scope",
        human_review_required=bool(violations),
        declared_touch_count=len(handoff.objects_touched),
        violation_count=len(violations),
    ))


# -- sealing and storage ---------------------------------------------------

def compute_content_hash(review: ScopeReview) -> str:
    payload = {k: v for k, v in review.to_serialisable().items() if k != "content_hash"}
    return hash_text(yaml.safe_dump(payload, sort_keys=True, allow_unicode=True))


def seal(review: ScopeReview) -> ScopeReview:
    return review.model_copy(update={"content_hash": compute_content_hash(review)})


def verify_review_content_hash(review: ScopeReview) -> bool:
    if not review.content_hash:
        return False
    return review.content_hash == compute_content_hash(review)


def scope_dir(ws: Workspace) -> Path:
    return ws.root / "scope"


def schema_slug(schema_version: str = SCOPE_SCHEMA_VERSION) -> str:
    return schema_version.rsplit("/", 1)[-1]


def review_filename(review: ScopeReview) -> str:
    """Path includes the schema version.

    A change in evaluation logic must ship a new schema version, which lands
    at a new path. An existing attestation is therefore never replaced by a
    later evaluator disagreeing with it.
    """
    return (
        f"{review.task_id}__v{review.packet_version}__{review.provider}"
        f"__{review.handoff_packet_hash.split(':', 1)[-1][:HASH_LEN]}"
        f"__scope-{schema_slug(review.schema_version)}.yaml"
    )


def read_review(path: Path) -> ScopeReview:
    return ScopeReview.model_validate(yaml.safe_load(Path(path).read_text(encoding="utf-8")))


def write_review(ws: Workspace, review: ScopeReview) -> Path:
    if not review.content_hash:
        raise ValidationError("scope review is not sealed")
    if not verify_review_content_hash(review):
        raise ValidationError(
            "scope review content_hash is stale: it does not match the review body"
        )
    path = scope_dir(ws) / review_filename(review)
    if path.exists():
        raise ValidationError(f"{path.name} already exists; Scope Reviews are immutable")
    path.parent.mkdir(parents=True, exist_ok=True)
    text = yaml.safe_dump(review.to_serialisable(), sort_keys=False, allow_unicode=True)
    path.write_bytes(text.replace("\r\n", "\n").encode("utf-8"))
    return path


def read_handoff(path: Path) -> HandoffPacket:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return HandoffPacket.model_validate(data)


# -- entry point -----------------------------------------------------------

@dataclass(frozen=True)
class ReviewOutcome:
    review: ScopeReview
    path: Path
    created: bool


def _expected_review_path(ws: Workspace, packet: TaskPacket, handoff: HandoffPacket) -> Path:
    return scope_dir(ws) / (
        f"{packet.task_id}__v{packet.version}__{handoff.provider}"
        f"__{(handoff.content_hash or '').split(':', 1)[-1][:HASH_LEN]}"
        f"__scope-{schema_slug()}.yaml"
    )


def _load_existing(path: Path, packet: TaskPacket, handoff: HandoffPacket) -> ScopeReview:
    """Load and fully verify an existing attestation. Refuses on any mismatch."""
    try:
        existing = read_review(path)
    except Exception as exc:
        raise ValidationError(f"existing scope review {path.name} is unreadable: {exc}") from None

    if not verify_review_content_hash(existing):
        raise ValidationError(
            f"existing scope review {path.name} does not verify against its own "
            "content_hash; it has been altered on disk"
        )

    for field_name, expected, actual in (
        ("schema_version", SCOPE_SCHEMA_VERSION, existing.schema_version),
        ("task_packet_ref", packet.ref, existing.task_packet_ref),
        ("task_packet_hash", packet.content_hash, existing.task_packet_hash),
        ("handoff_packet_hash", handoff.content_hash, existing.handoff_packet_hash),
        ("provider", handoff.provider, existing.provider),
    ):
        if expected != actual:
            raise ValidationError(
                f"existing scope review {path.name} does not match its sources: "
                f"{field_name} is {actual!r}, expected {expected!r}"
            )
    return existing


def review_handoff(ws: Workspace, handoff_path: Path) -> ReviewOutcome:
    """Evaluate a stored Handoff Packet against its Task Packet.

    IDEMPOTENT. A Scope Review is an attestation about a specific pair of
    immutable objects under a specific schema. Re-running does not produce a
    second opinion: the existing attestation is loaded, fully verified, and
    returned unchanged, with its original `evaluated_at` intact.

    There is deliberately no --force. Replacing an attestation would let a
    later run quietly overwrite what an earlier one found. A change in
    evaluation logic ships a new schema version instead, which lands at a
    different path and leaves the prior finding standing.

    Both packets are verified first. Evaluating against an altered packet
    would produce a review attesting to a grant that no longer exists.
    """
    handoff_path = Path(handoff_path)
    if not handoff_path.exists():
        raise ValidationError(f"no such handoff packet: {handoff_path}")

    handoff = read_handoff(handoff_path)

    if not verify_handoff_content_hash(handoff):
        raise ValidationError(
            f"handoff packet {handoff_path.name} does not verify against its own "
            "content_hash; it has been altered on disk"
        )

    try:
        packet = read_packet(ws, handoff.task_id, handoff.packet_version)
    except Exception:
        raise ValidationError(
            f"Task Packet {handoff.packet_ref} is not present in this workspace; "
            "scope cannot be evaluated against a grant that cannot be read"
        ) from None

    if not verify_content_hash(packet):
        raise ValidationError(
            f"Task Packet {handoff.packet_ref} does not verify against its own "
            "content_hash; it has been altered on disk"
        )

    if packet.content_hash != handoff.packet_content_hash:
        raise ValidationError(
            f"Task Packet {handoff.packet_ref} has changed since this response was "
            f"produced (response answered {handoff.packet_content_hash}, packet is "
            f"now {packet.content_hash})"
        )

    expected = _expected_review_path(ws, packet, handoff)
    if expected.exists():
        return ReviewOutcome(_load_existing(expected, packet, handoff), expected, created=False)

    review = evaluate(packet, handoff)
    return ReviewOutcome(review, write_review(ws, review), created=True)
