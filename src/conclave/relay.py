"""Relay export — render a Task Packet into per-provider prompt files.

Manual relay: CONCLAVE writes a Markdown file per assigned provider. The
operator opens it, pastes it into that provider's interface, and saves the
response for import. No clipboard, no automation, no provider API.

Independence is structural. Each prompt is rendered from the Task Packet
alone and contains no other provider's prompt or response. There is no code
path by which one provider's output can reach another's prompt, because
nothing but the packet is read during rendering.

The prompt is a COMPACT PROJECTION of the packet. Null and empty fields are
omitted because they carry no operational information and consume provider
context. The stored packet remains the source of truth and keeps its explicit
nulls; the projection is derived, never authoritative. The packet reference
and full content hash appear in every prompt so any response can be tied back
to the exact immutable packet it answers.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from .errors import ValidationError, WorkspaceError
from .hashing import hash_text, write_canonical
from .models import ObjectRef, ProviderAssignment, TaskPacket
from .workspace import Workspace, utcnow

PROMPT_SCHEMA_VERSION = "relay-prompt/0.1.0"
HANDOFF_SCHEMA_VERSION = "handoff-packet/0.1.0"
HASH_SUFFIX_LEN = 12

ExportStatus = Literal["created", "unchanged", "refused", "replaced"]


@dataclass(frozen=True)
class ExportResult:
    provider: str
    role: str
    path: Path
    prompt_hash: str
    status: ExportStatus
    detail: str | None = None


# -- filenames -------------------------------------------------------------

def hash_suffix(content_hash: str) -> str:
    """First 12 hex digits, without the 'sha256:' prefix.

    A colon is invalid in Windows filenames, so the algorithm prefix is
    stripped rather than escaped.
    """
    return content_hash.split(":", 1)[-1][:HASH_SUFFIX_LEN]


def export_filename(packet: TaskPacket, provider: str) -> str:
    return (
        f"{packet.task_id}__v{packet.version}__{provider}"
        f"__{hash_suffix(packet.content_hash or '')}.md"
    )


# -- projection helpers ----------------------------------------------------

def render_object_ref(ref: ObjectRef) -> str:
    """One line per object. Null fields omitted."""
    parts = [ref.object_id]
    if ref.section_id:
        parts.append(f"§ {ref.section_id}")
    if ref.expected_version:
        parts.append(f"(expected version {ref.expected_version})")
    if ref.canonical_id:
        parts.append(f"[{ref.canonical_id}]")
    if ref.object_type:
        parts.append(f"<{ref.object_type}>")
    return " ".join(parts)


def _section(title: str, lines: list[str], *, empty: str | None = None) -> list[str]:
    if not lines:
        return [f"### {title}", "", empty or "_none_", ""] if empty else []
    return [f"### {title}", "", *lines, ""]


HANDOFF_TEMPLATE = """```yaml
handoff_packet: "%(handoff_version)s"

# Echo these three verbatim. They prove which packet you answered.
packet_ref: "%(packet_ref)s"
packet_content_hash: "%(content_hash)s"
provider: "%(provider)s"

role: "%(role)s"
status: submitted        # submitted | abstained | blocked

# EVERY object you read, cited or proposed a change to. Omitting one is a
# governance failure, not a formatting slip: this list is compared against
# the scope you were granted.
objects_touched:
  - object_id: ""
    section_id: null     # omit or null if whole object
    action: read         # read | cited | proposed_change

output:
  type: %(output_type)s
  summary: ""
  body: |
    <your substantive work here>

findings:
  - finding_id: F-001
    severity: medium     # high | medium | low
    dimension: ""
    claim: ""
    evidence:
      - ""
    proposed_resolution: ""
    confidence:
      self_reported: 0.0

assumptions: []          # what you assumed because it was not established
abstentions: []          # what you declined to answer, and why
unresolved: []           # disagreements or gaps you could not close
evidence_used: []        # external sources, with enough detail to verify
recommended_next_action: revise   # revise | accept | escalate | abstain
```"""

ROLE_OUTPUT_TYPE = {
    "lead": "draft",
    "critic": "critique",
    "verifier": "verification",
    "institutional_architect": "draft",
    "governance_critic": "critique",
    "external_verifier": "verification",
    "synthesiser": "synthesis",
    "synthesizer": "synthesis",
}


def build_prompt(
    packet: TaskPacket, assignment: ProviderAssignment, config: dict[str, Any]
) -> str:
    """Render the compact provider-facing projection of a Task Packet."""
    spec = (config.get("providers") or {}).get(assignment.provider, {})
    display = spec.get("display_name", assignment.provider)
    principal = config.get("principal", "the principal")

    out: list[str] = [
        f"# CONCLAVE task — {assignment.role} — {display}",
        "",
        "You are one participant in a governed multi-agent task for Komistry OS (KOS).",
        "Work independently. You have not been shown, and must not assume, what any",
        "other participant will say.",
        "",
        "## Packet reference",
        "",
        "```",
        f"packet_ref   : {packet.ref}",
        f"content_hash : {packet.content_hash}",
        "```",
        "",
        "Quote both verbatim in your response.",
        "",
        "## Your assignment",
        "",
        "```",
        f"provider  : {assignment.provider}",
        f"identity  : {display}",
        f"role      : {assignment.role}",
        f"authority : advisory",
        "```",
        "",
        "## Objective",
        "",
        packet.objective.strip(),
        "",
    ]

    if packet.interpreted_objective:
        out += ["**Interpreted objective**", "", packet.interpreted_objective.strip(), ""]

    out += ["## Scope", ""]
    out += _section(
        "Target objects — you may propose changes to these",
        [f"- {render_object_ref(r)}" for r in packet.target_objects],
        empty="_no target objects declared_",
    )
    out += _section(
        "Read-only objects — you may read and cite these; do not propose changes",
        [f"- {render_object_ref(r)}" for r in packet.read_only_objects],
        empty="_none_",
    )
    out += _section(
        "Prohibited objects — do not read, quote, cite or modify",
        [f"- {render_object_ref(r)}" for r in packet.prohibited_objects],
        empty="_none_",
    )

    out += [
        "Anything not listed above is out of scope. If your work appears to require",
        "an out-of-scope object, do not proceed with that part — record it under",
        "`unresolved` and say why. Declare every object you actually touched in",
        "`objects_touched`.",
        "",
    ]

    if packet.constraints:
        out += ["## Constraints", "", *[f"- {c}" for c in packet.constraints], ""]

    if packet.acceptance_criteria:
        out += ["## Acceptance criteria", "",
                *[f"- {c}" for c in packet.acceptance_criteria], ""]

    out += [
        "## Authority boundary",
        "",
        f"- {principal} is the sole constitutional authority for Komistry OS.",
        "- You are advisory. You may propose, critique, verify, draft and cite.",
        "- You may not approve, ratify, commission or merge anything.",
        "- If you detect a governance conflict, report it. Do not resolve it.",
        "- If a governing object you need is missing, that is not permission to",
        "  proceed without it. Record it under `unresolved` and stop that line of work.",
        "- Do not invent sources, identifiers, versions or approval records.",
        "- If you are uncertain, say so and record it. Confident-sounding filler is",
        "  worse than a declared gap.",
        "",
        "## Required response format",
        "",
        "Reply with a single fenced YAML block and nothing before or after it.",
        "Delete example entries you do not use; leave lists empty rather than",
        "inventing content to fill them.",
        "",
        HANDOFF_TEMPLATE % {
            "handoff_version": HANDOFF_SCHEMA_VERSION,
            "packet_ref": packet.ref,
            "content_hash": packet.content_hash,
            "provider": assignment.provider,
            "role": assignment.role,
            "output_type": ROLE_OUTPUT_TYPE.get(assignment.role, "draft"),
        },
        "",
    ]
    return "\n".join(out)


# -- export ----------------------------------------------------------------

def export_record(
    packet: TaskPacket, assignment: ProviderAssignment, path: Path, prompt_hash: str
) -> dict[str, Any]:
    """Metadata proving which packet version and prompt a response answers."""
    return {
        "event_type": "prompt_exported",
        "export_id": path.stem,
        "exported_at": utcnow(),
        "prompt_schema_version": PROMPT_SCHEMA_VERSION,
        "handoff_schema_version": HANDOFF_SCHEMA_VERSION,
        "task_id": packet.task_id,
        "version": packet.version,
        "packet_ref": packet.ref,
        "packet_content_hash": packet.content_hash,
        "provider": assignment.provider,
        "role": assignment.role,
        "prompt_file": path.name,
        "prompt_hash": prompt_hash,
    }


def replacement_record(
    packet: TaskPacket,
    assignment: ProviderAssignment,
    path: Path,
    *,
    replaced_prompt_hash: str,
    replacement_prompt_hash: str,
    reason: str,
    authority: str,
) -> dict[str, Any]:
    """Audit event for a forced replacement.

    A forced replacement destroys a prompt that may already have been pasted
    into a provider. It is a distinct event from an initial export and is
    never recorded as one.
    """
    return {
        "event_type": "prompt_export_replaced",
        "export_id": path.stem,
        "task_id": packet.task_id,
        "version": packet.version,
        "packet_ref": packet.ref,
        "packet_content_hash": packet.content_hash,
        "provider": assignment.provider,
        "role": assignment.role,
        "prompt_file": path.name,
        "replaced_prompt_hash": replaced_prompt_hash,
        "replacement_prompt_hash": replacement_prompt_hash,
        "replaced_at": utcnow(),
        "replacement_reason": reason,
        "replacement_authority": authority,
    }


def append_export_record(ws: Workspace, record: dict[str, Any]) -> None:
    path = ws.outbox_dir / "exports.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(record, sort_keys=True) + "\n")


def read_export_records(ws: Workspace) -> list[dict[str, Any]]:
    path = ws.outbox_dir / "exports.jsonl"
    records = [
        json.loads(line)
        for line in (path.read_text(encoding="utf-8").splitlines() if path.exists() else [])
        if line.strip()
    ]
    # Imported lazily to avoid a module cycle: contextrelay reuses the frozen
    # Task Packet prompt renderer above. Its sealed manifests are authoritative
    # export records and do not need a second mutable JSONL representation.
    from .contextrelay import read_context_relay_records

    return records + read_context_relay_records(ws)


def export_prompts(
    ws: Workspace,
    packet: TaskPacket,
    config: dict[str, Any],
    *,
    providers: list[str] | None = None,
    force: bool = False,
    reason: str | None = None,
    authority: str | None = None,
) -> list[ExportResult]:
    """Write one prompt per assigned provider. Never touches the Task Packet.

    Re-exporting identical content is idempotent: the existing file is left
    alone, reported as unchanged, and NO record is appended. Differing content
    is refused unless `force` is set with a reason, which appends a distinct
    `prompt_export_replaced` audit event.
    """
    if not packet.content_hash:
        raise ValidationError("cannot export an unsealed packet")

    if force and not (reason or "").strip():
        raise ValidationError(
            "forced replacement requires a reason. A forced export destroys a prompt "
            "that may already have been given to a provider; the reason is recorded "
            "in the export log."
        )

    assignments = packet.assigned_providers
    if providers:
        wanted = set(providers)
        unknown = wanted - {a.provider for a in assignments}
        if unknown:
            raise ValidationError(
                f"not assigned to this packet: {sorted(unknown)}. "
                f"Assigned: {sorted(a.provider for a in assignments)}"
            )
        assignments = [a for a in assignments if a.provider in wanted]

    if not assignments:
        raise ValidationError("packet has no assigned providers to export")

    ws.outbox_dir.mkdir(parents=True, exist_ok=True)
    results: list[ExportResult] = []

    for assignment in assignments:
        prompt = build_prompt(packet, assignment, config)
        prompt_hash = hash_text(prompt)
        path = ws.outbox_dir / export_filename(packet, assignment.provider)

        replaced_hash: str | None = None

        if path.exists():
            existing = hash_text(path.read_text(encoding="utf-8"))
            if existing == prompt_hash:
                results.append(ExportResult(assignment.provider, assignment.role, path,
                                            prompt_hash, "unchanged",
                                            "identical prompt already exported"))
                continue
            if not force:
                results.append(ExportResult(assignment.provider, assignment.role, path,
                                            prompt_hash, "refused",
                                            "a different prompt exists at this path; "
                                            "re-run with --force --reason to replace"))
                continue
            replaced_hash = existing

        write_canonical(path, prompt)

        if replaced_hash is not None:
            append_export_record(ws, replacement_record(
                packet, assignment, path,
                replaced_prompt_hash=replaced_hash,
                replacement_prompt_hash=prompt_hash,
                reason=reason or "",
                authority=authority or "unknown",
            ))
            results.append(ExportResult(assignment.provider, assignment.role, path,
                                        prompt_hash, "replaced",
                                        f"replaced {replaced_hash[:19]}…"))
        else:
            append_export_record(ws, export_record(packet, assignment, path, prompt_hash))
            results.append(ExportResult(assignment.provider, assignment.role, path,
                                        prompt_hash, "created"))

    return results
