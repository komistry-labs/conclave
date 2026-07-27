"""Task Packet validation.

Three categories, kept strictly distinct because they have different owners:

  SCHEMA      structural. Wrong shape, wrong type, missing required field.
              Fixed by whoever wrote the packet.

  SEMANTIC    structurally valid but internally inconsistent or unusable.
              Unknown provider, empty objective, duplicate references.
              Fixed by whoever authored the task.

  GOVERNANCE  a violation of an authority boundary. An agent instructed to
              modify something it is forbidden to touch; a packet asserting
              merge authority; egress exceeding the configured policy.
              NOT fixed by an agent. Escalates to the principal.

VALIDATION NEVER REPAIRS. It reports and refuses. A validator that quietly
normalises its input produces packets nobody wrote and whose hashes nobody
can reproduce.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import yaml
from pydantic import ValidationError as PydanticValidationError

from .models import FORBIDDEN_FIELDS, SCHEMA_VERSION, TaskPacket
from .taskpacket import verify_content_hash


class Category(str, Enum):
    SCHEMA = "schema"
    SEMANTIC = "semantic"
    GOVERNANCE = "governance"


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True)
class Finding:
    category: Category
    severity: Severity
    code: str
    message: str
    location: str | None = None

    def __str__(self) -> str:
        where = f" [{self.location}]" if self.location else ""
        return f"{self.category.value}/{self.severity.value}: {self.code}{where} — {self.message}"


@dataclass
class ValidationReport:
    findings: list[Finding] = field(default_factory=list)
    packet: TaskPacket | None = None

    def add(self, *args: Any, **kwargs: Any) -> None:
        self.findings.append(Finding(*args, **kwargs))

    def by_category(self, category: Category) -> list[Finding]:
        return [f for f in self.findings if f.category is category]

    @property
    def errors(self) -> list[Finding]:
        return [f for f in self.findings if f.severity is Severity.ERROR]

    @property
    def warnings(self) -> list[Finding]:
        return [f for f in self.findings if f.severity is Severity.WARNING]

    @property
    def ok(self) -> bool:
        return not self.errors

    @property
    def has_governance_violation(self) -> bool:
        return any(
            f.category is Category.GOVERNANCE and f.severity is Severity.ERROR
            for f in self.findings
        )


# -- schema ----------------------------------------------------------------

REQUIRED_FIELDS = (
    "task_id",
    "created_at",
    "objective",
    "target_objects",
    "read_only_objects",
    "prohibited_objects",
    "assigned_providers",
    "egress",
    "content_hash",
    "schema_version",
)


def validate_schema(raw: dict[str, Any]) -> tuple[ValidationReport, TaskPacket | None]:
    report = ValidationReport()

    if not isinstance(raw, dict):
        report.add(Category.SCHEMA, Severity.ERROR, "not-a-mapping",
                   "packet must be a YAML mapping")
        return report, None

    for name in REQUIRED_FIELDS:
        if name not in raw:
            report.add(Category.SCHEMA, Severity.ERROR, "missing-required-field",
                       f"required field '{name}' is absent", location=name)

    declared = raw.get("schema_version")
    if declared and declared != SCHEMA_VERSION:
        report.add(Category.SCHEMA, Severity.WARNING, "schema-version-mismatch",
                   f"packet declares {declared!r}; this build expects {SCHEMA_VERSION!r}",
                   location="schema_version")

    for name in sorted(FORBIDDEN_FIELDS & set(raw)):
        report.add(Category.SCHEMA, Severity.ERROR, "forbidden-field",
                   f"field '{name}' is forbidden by {SCHEMA_VERSION}; a Task Packet "
                   "cannot assert approval or merge authority",
                   location=name)

    try:
        packet = TaskPacket.model_validate(raw)
    except PydanticValidationError as exc:
        for err in exc.errors():
            loc = ".".join(str(p) for p in err["loc"]) or None
            report.add(Category.SCHEMA, Severity.ERROR, "invalid-value", err["msg"], location=loc)
        return report, None

    # Construction succeeding is NOT the same as the schema being satisfied.
    # Extra fields are preserved by design, so a forbidden field parses
    # cleanly while still being a schema error. Short-circuit on any schema
    # error, not merely on a parse failure: downstream semantic and
    # governance findings about a structurally invalid packet would be noise.
    if report.errors:
        return report, None

    return report, packet


# -- semantic --------------------------------------------------------------

def validate_semantics(packet: TaskPacket, config: dict[str, Any]) -> ValidationReport:
    report = ValidationReport(packet=packet)

    if not packet.objective.strip():
        report.add(Category.SEMANTIC, Severity.ERROR, "empty-objective",
                   "objective is blank", location="objective")

    if not packet.target_objects:
        report.add(Category.SEMANTIC, Severity.WARNING, "no-target-objects",
                   "no target objects declared; scope drift detection will flag any "
                   "output as expansion", location="target_objects")

    if not packet.assigned_providers:
        report.add(Category.SEMANTIC, Severity.ERROR, "no-providers",
                   "no providers assigned", location="assigned_providers")

    for name in ("target_objects", "read_only_objects", "prohibited_objects"):
        refs = getattr(packet, name)
        seen: set[str] = set()
        for ref in refs:
            if ref.key() in seen:
                report.add(Category.SEMANTIC, Severity.ERROR, "duplicate-object-reference",
                           f"{ref.key()!r} appears more than once", location=name)
            seen.add(ref.key())

    configured = set(config.get("providers", {}))
    assigned: set[str] = set()
    for a in packet.assigned_providers:
        if a.provider not in configured:
            report.add(Category.SEMANTIC, Severity.ERROR, "unknown-provider",
                       f"provider {a.provider!r} is not configured in this workspace "
                       f"(known: {sorted(configured) or 'none'})",
                       location="assigned_providers")
        if a.provider in assigned:
            report.add(Category.SEMANTIC, Severity.ERROR, "duplicate-provider",
                       f"provider {a.provider!r} assigned more than once",
                       location="assigned_providers")
        assigned.add(a.provider)

    if not verify_content_hash(packet):
        report.add(Category.SEMANTIC, Severity.ERROR, "content-hash-mismatch",
                   "content_hash does not match the packet body; the packet has been "
                   "altered after sealing, or was never sealed correctly",
                   location="content_hash")

    if packet.version > 1 and not packet.supersedes:
        report.add(Category.SEMANTIC, Severity.ERROR, "missing-supersedes",
                   f"version {packet.version} must reference the packet it supersedes",
                   location="supersedes")

    if packet.supersedes and packet.version == 1:
        report.add(Category.SEMANTIC, Severity.ERROR, "v1-supersedes",
                   "a version-1 packet cannot supersede anything", location="supersedes")

    return report


# -- governance ------------------------------------------------------------

def validate_governance(packet: TaskPacket, config: dict[str, Any]) -> ValidationReport:
    report = ValidationReport(packet=packet)
    scope = packet.scope_keys()

    overlap = scope["target"] & scope["prohibited"]
    if overlap:
        report.add(Category.GOVERNANCE, Severity.ERROR, "target-is-prohibited",
                   f"objects are both targeted and prohibited: {sorted(overlap)}. "
                   "A packet cannot instruct an agent to modify what it forbids.",
                   location="target_objects")

    overlap = scope["target"] & scope["read_only"]
    if overlap:
        report.add(Category.GOVERNANCE, Severity.ERROR, "target-is-read-only",
                   f"objects are both targeted and read-only: {sorted(overlap)}",
                   location="target_objects")

    overlap = scope["read_only"] & scope["prohibited"]
    if overlap:
        report.add(Category.GOVERNANCE, Severity.ERROR, "read-only-is-prohibited",
                   f"objects are both readable and prohibited: {sorted(overlap)}",
                   location="read_only_objects")

    authority = config.get("authority", {})
    if authority.get("agents_may_merge") is True:
        report.add(Category.GOVERNANCE, Severity.ERROR, "workspace-permits-merge",
                   "workspace config sets agents_may_merge: true. No AI agent may merge.",
                   location="config.authority")

    for a in packet.assigned_providers:
        if a.may_merge:
            report.add(Category.GOVERNANCE, Severity.ERROR, "provider-may-merge",
                       f"provider {a.provider!r} is assigned merge authority",
                       location="assigned_providers")
        if a.authority_level != "advisory":
            report.add(Category.GOVERNANCE, Severity.ERROR, "non-advisory-authority",
                       f"provider {a.provider!r} has authority_level {a.authority_level!r}; "
                       "AI agents are advisory",
                       location="assigned_providers")

    ws_policy = (config.get("egress") or {}).get("policy")
    rank = {"relay-only": 0, "non-constitutional": 1, "all": 2}
    if ws_policy in rank and rank.get(packet.egress.policy, 99) > rank[ws_policy]:
        report.add(Category.GOVERNANCE, Severity.ERROR, "egress-exceeds-policy",
                   f"packet egress {packet.egress.policy!r} exceeds workspace policy "
                   f"{ws_policy!r}",
                   location="egress")

    if "constitutional" not in packet.egress.prohibited_classifications and \
            packet.egress.policy != "all":
        report.add(Category.GOVERNANCE, Severity.WARNING, "constitutional-egress-permitted",
                   "constitutional material is not excluded from egress. Confirm this is "
                   "intended before any provider call.",
                   location="egress.prohibited_classifications")

    independent = [a for a in packet.assigned_providers if a.independent]
    if len(packet.assigned_providers) > 1 and not independent:
        report.add(Category.GOVERNANCE, Severity.WARNING, "no-independent-providers",
                   "multiple providers assigned, none marked independent; responses may "
                   "anchor on one another",
                   location="assigned_providers")

    return report


# -- entry point -----------------------------------------------------------

def validate_packet_data(raw: dict[str, Any], config: dict[str, Any]) -> ValidationReport:
    """Validate a raw packet mapping. Never mutates `raw`."""
    report, packet = validate_schema(raw)
    if packet is None:
        return report

    report.packet = packet
    report.findings.extend(validate_semantics(packet, config).findings)
    report.findings.extend(validate_governance(packet, config).findings)
    return report


def validate_packet_file(path, config: dict[str, Any]) -> ValidationReport:
    from pathlib import Path

    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return validate_packet_data(raw, config)
