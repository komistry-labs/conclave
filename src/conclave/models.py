"""Task Packet models.

TASK PACKETS ARE IMMUTABLE.

A packet is written once and never edited. Revision produces a NEW packet at
the next version, linked to its predecessor:

    Task Packet v1 -> Handoff Packet -> Council Review -> Decision
                                                             |
                                                             v
                                                    Task Packet v2

`task_id` identifies the logical task and is stable across versions.
`version` identifies the immutable packet. Together they form the packet
reference `<task_id>@v<version>`, which is what everything downstream cites.

Object reference shape is deliberately identical across target_objects,
read_only_objects and prohibited_objects. Scope drift detection compares
these three sets, and a uniform shape keeps that comparison simple and
stable across schema versions.
"""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

SCHEMA_VERSION = "task-packet/0.1.0"

# Field names that must never appear in a packet, whatever a caller supplies.
# Unknown fields are otherwise preserved (requirement 5); these are the
# explicit exceptions, because each would assert an authority a Task Packet
# has no standing to grant.
FORBIDDEN_FIELDS: frozenset[str] = frozenset(
    {
        "approved",
        "approval",
        "merged",
        "merge_authorised",
        "authority_override",
        "constitutional_authority",
    }
)

TASK_ID_PATTERN = re.compile(r"^TP-[a-z0-9][a-z0-9-]{0,47}-[0-9a-f]{10}$")


class ObjectRef(BaseModel):
    """Reference to a KOS object.

    Identity-first: an object is named by its identifier, not its path.
    `path_hint` is advisory only and is never treated as authoritative -
    KOS paths may move, and CONCLAVE must not break when they do.

    STABLE STRUCTURE. Scope drift detection depends on this shape.
    """

    model_config = ConfigDict(extra="allow", frozen=True)

    object_id: str = Field(..., min_length=1, description="Working identifier, e.g. 'RA-001'.")
    canonical_id: str | None = Field(
        None, description="ADR-0005 canonical ID, e.g. 'kos:decision:000005'. May be unresolved."
    )
    object_type: str | None = Field(
        None, description="ADR-0002 type. Null where KOS has not assigned one."
    )
    section_id: str | None = Field(None, description="Optional section anchor.")
    expected_version: str | None = Field(None, description="Version expected at compile time.")
    path_hint: str | None = Field(
        None, description="ADVISORY ONLY. Never authoritative. Identity resolves the path."
    )

    def key(self) -> str:
        """Comparison key for scope detection.

        Section-level references are distinct from whole-object references:
        permission to edit RA-001-PART-IV is not permission to edit RA-001.
        """
        return f"{self.object_id}#{self.section_id}" if self.section_id else self.object_id


class EgressPolicy(BaseModel):
    """What content may leave the machine for a provider.

    Defaults are restrictive. A packet that says nothing about egress gets the
    most cautious policy, not the most permissive.
    """

    model_config = ConfigDict(extra="allow", frozen=True)

    policy: Literal["relay-only", "non-constitutional", "all"] = "relay-only"
    prohibited_classifications: list[str] = Field(default_factory=lambda: ["constitutional"])
    allowed_classifications: list[str] = Field(default_factory=list)
    notes: str | None = None


class ProviderAssignment(BaseModel):
    """A provider assigned to a role for this task.

    Roles belong to tasks, not vendors. `authority_level` is constrained to
    'advisory' at the type level - no AI agent holds decision authority, and
    a packet cannot grant it.
    """

    model_config = ConfigDict(extra="allow", frozen=True)

    provider: str = Field(..., min_length=1, description="Configured provider key.")
    role: str = Field(..., min_length=1, description="Role for this task, e.g. 'governance_critic'.")
    authority_level: Literal["advisory"] = "advisory"
    may_propose: bool = True
    may_merge: Literal[False] = False
    independent: bool = Field(
        True, description="If true, must not see other providers' responses before submitting."
    )


class TaskPacket(BaseModel):
    """An immutable instruction to coordinate work on KOS objects.

    Frozen. Attribute assignment raises. A revised packet is produced by
    `model_copy(update=...)`, which returns a NEW object whose content_hash is
    then stale until re-sealed — and `write_packet` refuses stale hashes. So
    the only path from "packet" to "packet on disk" runs through sealing.

    `content_hash` covers every field except itself, over a deterministically
    serialised form.
    """

    model_config = ConfigDict(extra="allow", frozen=True)

    schema_version: str = SCHEMA_VERSION
    task_id: str
    version: int = Field(1, ge=1)
    created_at: str
    created_by: str

    objective: str = Field(..., min_length=1)
    interpreted_objective: str | None = None

    target_objects: list[ObjectRef] = Field(default_factory=list)
    read_only_objects: list[ObjectRef] = Field(default_factory=list)
    prohibited_objects: list[ObjectRef] = Field(default_factory=list)

    assigned_providers: list[ProviderAssignment] = Field(default_factory=list)
    egress: EgressPolicy = Field(default_factory=EgressPolicy)

    constraints: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)

    supersedes: str | None = Field(
        None, description="Packet reference this revises, e.g. 'TP-foo-0123456789@v1'."
    )
    revision_reason: str | None = None

    content_hash: str | None = None

    @field_validator("task_id")
    @classmethod
    def _check_task_id(cls, v: str) -> str:
        if not TASK_ID_PATTERN.match(v):
            raise ValueError(
                f"task_id {v!r} does not match TP-<slug>-<10 hex digits>"
            )
        return v

    @property
    def ref(self) -> str:
        """Packet reference: the immutable citation for this exact packet."""
        return f"{self.task_id}@v{self.version}"

    def scope_keys(self) -> dict[str, set[str]]:
        """The three scope sets, as comparison keys.

        Sole input to scope drift detection. Keep stable.
        """
        return {
            "target": {o.key() for o in self.target_objects},
            "read_only": {o.key() for o in self.read_only_objects},
            "prohibited": {o.key() for o in self.prohibited_objects},
        }

    def to_serialisable(self) -> dict[str, Any]:
        """Plain dict, unknown fields preserved, for hashing and storage."""
        return self.model_dump(mode="json", exclude_none=False)
