"""Handoff import — raw provider response in, sealed Handoff Packet out.

Two distinct objects, deliberately:

    Raw Provider Response        what the provider actually returned
            |  parsed into
            v
    Handoff Packet               CONCLAVE's structured reading of it

The raw response is preserved before any parsing is attempted, and is never
overwritten or edited. When Council Review later evaluates omissions,
malformed submissions, scope drift or disputed evidence, it needs the
provider's actual words, not only the system's interpretation of them.

Nothing here repairs provider content. A response that fails extraction,
schema or provenance is preserved as-is, rejected, and answered with a
bounded repair request that contains no fabricated substance.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field
from pydantic import ValidationError as PydanticValidationError

from .errors import ValidationError
from .hashing import hash_bytes, hash_text, write_canonical
from .relay import HANDOFF_SCHEMA_VERSION, read_export_records
from .taskpacket import read_packet, verify_content_hash
from .workspace import Workspace, utcnow

RAW_HASH_LEN = 12

# Fenced blocks with these info strings are candidates. Anything else is not.
YAML_TAGS = {"yaml", "yml"}
_FENCE = re.compile(r"^[ \t]*```([^\n`]*)\n(.*?)^[ \t]*```[ \t]*$", re.S | re.M)

# Fields the PROVIDER must supply. The remaining required fields of a stored
# Handoff Packet (raw_response_hash, prompt_hash, imported_at) are supplied by
# CONCLAVE and must never be accepted from a provider.
PROVIDER_REQUIRED_FIELDS = (
    "packet_ref",
    "packet_content_hash",
    "provider",
    "role",
    "status",
    "objects_touched",
    "output",
    "findings",
    "assumptions",
    "abstentions",
    "unresolved",
    "evidence_used",
    "recommended_next_action",
)

CONCLAVE_SUPPLIED_FIELDS = ("raw_response_hash", "prompt_hash", "imported_at")

# Provider SUBMISSION states. Deliberately distinct from KOS object lifecycle
# states (ADR-0004) and from CONCLAVE task workflow states: this vocabulary
# describes what a provider did with one prompt, nothing more. The relay
# prompt declares exactly these, so they are pinned here to match.
SubmissionStatus = Literal["submitted", "abstained", "blocked"]
NextAction = Literal["revise", "accept", "escalate", "abstain"]

SUBMISSION_STATUSES = ("submitted", "abstained", "blocked")
NEXT_ACTIONS = ("revise", "accept", "escalate", "abstain")


# -- models ----------------------------------------------------------------

class ObjectTouched(BaseModel):
    """An object the provider says it read, cited or proposed a change to.

    Sole input to scope drift detection in the next increment. Adjudication
    is NOT performed here - this increment captures the claim only.
    """

    model_config = ConfigDict(extra="allow", frozen=True)

    object_id: str = Field(..., min_length=1)
    section_id: str | None = None
    action: Literal["read", "cited", "proposed_change"] = "read"

    def key(self) -> str:
        """Same keying as ObjectRef, so the two sets are directly comparable."""
        return f"{self.object_id}#{self.section_id}" if self.section_id else self.object_id


class HandoffPacket(BaseModel):
    """A provider's structured response, sealed and immutable once stored."""

    model_config = ConfigDict(extra="allow", frozen=True)

    schema_version: str = HANDOFF_SCHEMA_VERSION

    packet_ref: str
    packet_content_hash: str
    provider: str
    role: str
    status: SubmissionStatus

    objects_touched: list[ObjectTouched] = Field(default_factory=list)
    output: dict[str, Any] = Field(default_factory=dict)
    findings: list[dict[str, Any]] = Field(default_factory=list)
    assumptions: list[Any] = Field(default_factory=list)
    abstentions: list[Any] = Field(default_factory=list)
    unresolved: list[Any] = Field(default_factory=list)
    evidence_used: list[Any] = Field(default_factory=list)
    recommended_next_action: NextAction

    raw_response_hash: str
    prompt_hash: str
    imported_at: str
    content_hash: str | None = None

    @property
    def task_id(self) -> str:
        return self.packet_ref.split("@", 1)[0]

    @property
    def packet_version(self) -> int:
        return int(self.packet_ref.rsplit("@v", 1)[1])

    def touched_keys(self) -> set[str]:
        return {o.key() for o in self.objects_touched}

    def to_serialisable(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude_none=False)


# -- results ---------------------------------------------------------------

@dataclass(frozen=True)
class Defect:
    code: str
    message: str
    location: str | None = None

    def __str__(self) -> str:
        return f"{self.code}{f' ({self.location})' if self.location else ''}: {self.message}"


@dataclass
class ImportResult:
    status: Literal["imported", "duplicate", "rejected"]
    raw_path: Path
    raw_hash: str
    handoff_path: Path | None = None
    repair_path: Path | None = None
    packet: HandoffPacket | None = None
    defects: list[Defect] = field(default_factory=list)


# -- extraction ------------------------------------------------------------

def normalise_line_endings(text: str) -> str:
    """Convert CRLF and lone CR to LF for parsing purposes only.

    A provider's reply is saved by whatever editor the operator uses. On
    Windows that is almost always CRLF. Line endings carry no meaning in a
    fenced block or in YAML, so parsing must not depend on them.

    This does NOT weaken any preservation guarantee. It runs on an in-memory
    string, after the raw bytes have been stored verbatim and after strict
    UTF-8 decoding. The evidentiary artifact keeps its original bytes and its
    binary hash; only the working copy used for extraction is normalised.
    """
    return text.replace("\r\n", "\n").replace("\r", "\n")


def extract_yaml_block(text: str) -> tuple[str | None, list[Defect]]:
    """Return the single candidate fenced block, or defects explaining why not.

    Candidate selection is deterministic and stated, not a guess:
      - if any block is tagged yaml/yml, ONLY those are candidates;
      - otherwise, untagged blocks are candidates;
      - blocks tagged with any other language are never candidates.

    Zero candidates is a rejection. More than one is a rejection for
    ambiguity - CONCLAVE does not decide which of a provider's blocks was
    meant to be authoritative.

    Input is normalised to LF first. The closing-fence pattern anchors with
    `$` under re.MULTILINE, which matches immediately before a newline; in a
    CRLF file a carriage return sits in that position and the fence is never
    found. Normalising is preferred over making the pattern CR-tolerant
    because it also keeps carriage returns out of the extracted block, so a
    Windows-authored reply and a Linux-authored one produce byte-identical
    Handoff Packets.
    """
    text = normalise_line_endings(text)
    blocks = [(m.group(1).strip().lower(), m.group(2)) for m in _FENCE.finditer(text)]
    tagged = [body for tag, body in blocks if tag in YAML_TAGS]
    untagged = [body for tag, body in blocks if tag == ""]
    candidates = tagged or untagged

    if not candidates:
        return None, [Defect(
            "no-yaml-block",
            "no fenced YAML block found. The response must contain exactly one "
            "```yaml block and nothing else.",
        )]
    if len(candidates) > 1:
        return None, [Defect(
            "ambiguous-yaml-blocks",
            f"found {len(candidates)} candidate fenced blocks. Exactly one is required; "
            "CONCLAVE will not guess which is authoritative.",
        )]
    return candidates[0], []


def parse_block(block: str) -> tuple[dict[str, Any] | None, list[Defect]]:
    try:
        data = yaml.safe_load(block)
    except yaml.YAMLError as exc:
        return None, [Defect("malformed-yaml", f"block is not valid YAML: {exc}")]
    if not isinstance(data, dict):
        return None, [Defect("not-a-mapping",
                             f"block parsed as {type(data).__name__}, expected a mapping")]
    return data, []


# -- schema ----------------------------------------------------------------

def validate_submission(data: dict[str, Any]) -> list[Defect]:
    """Check provider-supplied fields. Never fills anything in."""
    defects: list[Defect] = []

    for name in PROVIDER_REQUIRED_FIELDS:
        if name not in data:
            defects.append(Defect("missing-required-field",
                                  f"required field '{name}' is absent", location=name))

    for name in CONCLAVE_SUPPLIED_FIELDS:
        if name in data:
            defects.append(Defect(
                "provider-supplied-system-field",
                f"field '{name}' is set by CONCLAVE and must not appear in a response",
                location=name))

    declared = data.get("schema_version") or data.get("handoff_packet")
    if declared and declared != HANDOFF_SCHEMA_VERSION:
        defects.append(Defect("schema-version-mismatch",
                              f"response declares {declared!r}; expected "
                              f"{HANDOFF_SCHEMA_VERSION!r}", location="schema_version"))

    for name in ("objects_touched", "findings", "assumptions", "abstentions",
                 "unresolved", "evidence_used"):
        if name in data and not isinstance(data[name], list):
            defects.append(Defect("wrong-type",
                                  f"'{name}' must be a list, got "
                                  f"{type(data[name]).__name__}", location=name))

    if "output" in data and not isinstance(data["output"], dict):
        defects.append(Defect("wrong-type", "'output' must be a mapping", location="output"))

    if "status" in data and data["status"] not in SUBMISSION_STATUSES:
        defects.append(Defect("invalid-status",
                              f"status must be one of {list(SUBMISSION_STATUSES)}, "
                              f"got {data['status']!r}", location="status"))

    if "recommended_next_action" in data and data["recommended_next_action"] not in NEXT_ACTIONS:
        defects.append(Defect("invalid-next-action",
                              f"recommended_next_action must be one of {list(NEXT_ACTIONS)}, "
                              f"got {data['recommended_next_action']!r}",
                              location="recommended_next_action"))

    return defects


# -- provenance ------------------------------------------------------------

def find_export_record(
    ws: Workspace, submission: dict[str, Any] | None
) -> dict[str, Any] | None:
    """Best-effort lookup of the export a rejected submission was answering.

    Used only to quote authoritative identifiers back in a repair request.
    Never used to accept a response - acceptance goes through
    verify_provenance, which checks every field rather than one.
    """
    if not submission:
        return None
    ref = submission.get("packet_ref")
    provider = submission.get("provider")
    matches = [r for r in read_export_records(ws)
               if r.get("packet_ref") == ref and r.get("provider") == provider]
    if not matches and ref:
        matches = [r for r in read_export_records(ws) if r.get("packet_ref") == ref]
    return matches[-1] if matches else None


def effective_prompt_hash(record: dict[str, Any]) -> str | None:
    """The hash of the prompt this record left in place."""
    return record.get("replacement_prompt_hash") or record.get("prompt_hash")


def verify_provenance(
    ws: Workspace, data: dict[str, Any], *, prompt_hash: str | None = None
) -> tuple[dict[str, Any] | None, list[Defect]]:
    """Match the submission against a recorded export and a live Task Packet.

    A response is not accepted merely because it echoes plausible identifiers.
    Every identifier is checked against what CONCLAVE actually exported and
    against the Task Packet as it currently stands on disk.
    """
    defects: list[Defect] = []
    ref = data.get("packet_ref")
    provider = data.get("provider")
    role = data.get("role")

    records = [
        r for r in read_export_records(ws)
        if r.get("event_type", "prompt_exported") in ("prompt_exported",
                                                      "prompt_export_replaced")
    ]

    matching = [r for r in records if r.get("packet_ref") == ref and r.get("provider") == provider]
    if not matching:
        defects.append(Defect(
            "no-matching-export",
            f"no export record for packet_ref={ref!r} provider={provider!r}. "
            "A response can only be imported against a prompt CONCLAVE actually issued.",
            location="packet_ref"))
        return None, defects

    if prompt_hash:
        matching = [r for r in matching if effective_prompt_hash(r) == prompt_hash]
        if not matching:
            defects.append(Defect("prompt-hash-mismatch",
                                  f"no export for this packet and provider has prompt_hash "
                                  f"{prompt_hash!r}", location="prompt_hash"))
            return None, defects

    # Several records can describe the SAME prompt - a forced replacement that
    # regenerates identical content, for instance. That is not ambiguity: the
    # response answers that prompt whichever record is consulted. Only
    # genuinely different prompt content is ambiguous.
    distinct = {effective_prompt_hash(r) for r in matching}
    if len(distinct) > 1:
        defects.append(Defect(
            "ambiguous-export",
            f"{len(distinct)} materially different prompts were exported for this packet "
            f"and provider. Disambiguate with --prompt-hash. Candidates: {sorted(distinct)}",
            location="prompt_hash"))
        return None, defects

    record = matching[-1]  # most recent record for this prompt content

    if data.get("packet_content_hash") != record.get("packet_content_hash"):
        defects.append(Defect("packet-hash-mismatch",
                              "packet_content_hash does not match the exported packet",
                              location="packet_content_hash"))

    if role != record.get("role"):
        defects.append(Defect("role-mismatch",
                              f"role {role!r} does not match the assigned role "
                              f"{record.get('role')!r}", location="role"))

    # The Task Packet must still exist and still be what it was when exported.
    try:
        packet = read_packet(ws, record["task_id"], record["version"])
    except Exception:
        defects.append(Defect("task-packet-missing",
                              f"Task Packet {ref} is no longer present in this workspace",
                              location="packet_ref"))
        return None, defects

    if not verify_content_hash(packet):
        defects.append(Defect("task-packet-integrity-failure",
                              f"Task Packet {ref} no longer verifies against its own "
                              "content_hash; it has been altered on disk",
                              location="packet_ref"))
    elif packet.content_hash != record.get("packet_content_hash"):
        defects.append(Defect("task-packet-altered",
                              f"Task Packet {ref} has changed since export",
                              location="packet_ref"))

    if provider not in {a.provider for a in packet.assigned_providers}:
        defects.append(Defect("provider-not-assigned",
                              f"provider {provider!r} is not assigned to {ref}",
                              location="provider"))

    return (record if not defects else None), defects


# -- storage ---------------------------------------------------------------

def raw_dir(ws: Workspace) -> Path:
    return ws.inbox_dir / "raw"


def repair_dir(ws: Workspace) -> Path:
    return ws.inbox_dir / "repair"


def raw_filename(raw_hash: str) -> str:
    return f"{raw_hash.split(':', 1)[-1][:RAW_HASH_LEN]}.raw.md"


def handoff_filename(packet: HandoffPacket) -> str:
    return (
        f"{packet.task_id}__v{packet.packet_version}__{packet.provider}"
        f"__{packet.raw_response_hash.split(':', 1)[-1][:RAW_HASH_LEN]}.yaml"
    )


def preserve_raw(ws: Workspace, source: Path) -> tuple[Path, str, bool]:
    """Store the raw response verbatim BEFORE parsing. Never overwrites.

    Hashed as BINARY, not canonical text. The raw artifact is evidentiary:
    it must record exactly what arrived, so a CRLF/LF difference, a BOM, or a
    trailing-whitespace change is a different artifact. Canonicalising here
    would erase precisely the differences an audit might need to see.

    Content-addressed, so re-importing byte-identical content is idempotent
    and a genuinely different response from the same provider lands beside
    the first rather than replacing it.
    """
    body = Path(source).read_bytes()
    raw_hash = hash_bytes(body, binary=True)
    path = raw_dir(ws) / raw_filename(raw_hash)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return path, raw_hash, True
    path.write_bytes(body)
    return path, raw_hash, False


def decode_raw(raw_path: Path) -> tuple[str | None, list[Defect]]:
    """Decode preserved bytes as strict UTF-8.

    Never lossy. A response that is not valid UTF-8 is rejected rather than
    silently mangled into replacement characters — which would produce a
    "parsed" document nobody wrote.
    """
    try:
        return raw_path.read_bytes().decode("utf-8"), []
    except UnicodeDecodeError as exc:
        return None, [Defect(
            "invalid-response-encoding",
            f"response is not valid UTF-8 ({exc.reason} at byte {exc.start}). "
            "Re-send it as UTF-8 without a byte-order mark.",
        )]


def compute_handoff_content_hash(packet: HandoffPacket) -> str:
    payload = {k: v for k, v in packet.to_serialisable().items() if k != "content_hash"}
    return hash_text(yaml.safe_dump(payload, sort_keys=True, allow_unicode=True))


def seal_handoff(packet: HandoffPacket) -> HandoffPacket:
    return packet.model_copy(update={"content_hash": compute_handoff_content_hash(packet)})


def verify_handoff_content_hash(packet: HandoffPacket) -> bool:
    if not packet.content_hash:
        return False
    return packet.content_hash == compute_handoff_content_hash(packet)


def write_handoff(ws: Workspace, packet: HandoffPacket) -> Path:
    if not packet.content_hash:
        raise ValidationError("handoff packet is not sealed; call seal_handoff() first")
    if not verify_handoff_content_hash(packet):
        raise ValidationError(
            "handoff content_hash is stale: it does not match the packet body. "
            "The packet was modified after sealing."
        )
    path = ws.inbox_dir / handoff_filename(packet)
    if path.exists():
        raise ValidationError(f"{path.name} already exists; Handoff Packets are immutable")
    path.parent.mkdir(parents=True, exist_ok=True)
    text = yaml.safe_dump(packet.to_serialisable(), sort_keys=False, allow_unicode=True)
    path.write_bytes(text.replace("\r\n", "\n").encode("utf-8"))
    return path


# -- repair request --------------------------------------------------------

def build_repair_request(
    defects: list[Defect],
    raw_path: Path,
    raw_hash: str,
    submission: dict[str, Any] | None,
    record: dict[str, Any] | None = None,
) -> str:
    """A bounded correction request. Contains no substantive answer.

    Only the defects and the identifiers needed to resubmit. CONCLAVE does
    not suggest what the provider should have said - doing so would put words
    in the provider's mouth and then evaluate them as if independently given.

    Identifiers are taken from CONCLAVE's own export record where one can be
    found, NOT from the rejected submission. Echoing back a value the provider
    got wrong would invite them to repeat it.
    """
    sub = submission or {}
    if record:
        ref = record.get("packet_ref")
        content_hash = record.get("packet_content_hash")
        provider = record.get("provider")
        role = record.get("role")
    else:
        unknown = "<not supplied or unreadable>"
        ref = sub.get("packet_ref", unknown)
        content_hash = sub.get("packet_content_hash", unknown)
        provider = sub.get("provider", unknown)
        role = sub.get("role", unknown)

    lines = [
        "# CONCLAVE — response rejected, correction requested",
        "",
        "Your previous response could not be accepted. It has been preserved unaltered",
        "and has NOT been recorded as a submission.",
        "",
        "Return a corrected response. Send the whole thing again as a single fenced",
        "YAML block — do not send a patch or a description of the changes.",
        "",
        "## Defects found",
        "",
    ]
    for d in defects:
        lines.append(f"- **{d.code}**{f' — `{d.location}`' if d.location else ''}")
        lines.append(f"  {d.message}")
    lines += [
        "",
        "## Identifiers to quote verbatim",
        "",
        ("These come from CONCLAVE's record of the prompt it issued to you — not from"
         if record else
         "No export record could be matched, so these are as you supplied them —"),
        ("your rejected reply. Use them exactly, even if your reply said otherwise."
         if record else
         "they may themselves be wrong. Take them from the original prompt."),
        "",
        "```",
        f"packet_ref          : {ref}",
        f"packet_content_hash : {content_hash}",
        f"provider            : {provider}",
        f"role                : {role}",
        "```",
        "",
        "## Requirements",
        "",
        "- Exactly one fenced ```yaml block. Nothing before or after it.",
        "- Every required field present. Leave lists empty rather than inventing entries.",
        "- Do not set `raw_response_hash`, `prompt_hash` or `imported_at` — CONCLAVE sets those.",
        "- Declare every object you touched in `objects_touched`.",
        "",
        "## Rejected response",
        "",
        "```",
        f"file : {raw_path.name}",
        f"hash : {raw_hash}",
        "```",
        "",
        "Preserved for audit. It has not been altered, repaired or interpreted.",
        "",
    ]
    return "\n".join(lines)


# -- entry point -----------------------------------------------------------

def import_response(
    ws: Workspace, source: Path, *, prompt_hash: str | None = None
) -> ImportResult:
    """Import one provider response. Preserves the raw artifact regardless of outcome."""
    source = Path(source)
    if not source.exists():
        raise ValidationError(f"no such file: {source}")

    raw_path, raw_hash, already_present = preserve_raw(ws, source)

    if already_present:
        short = raw_hash.split(":", 1)[-1][:RAW_HASH_LEN]
        existing = [p for p in ws.inbox_dir.glob("*.yaml") if short in p.name]
        prior_repair = repair_dir(ws) / f"{short}__repair.md"
        if existing:
            detail = "this exact response has already been imported"
        elif prior_repair.exists():
            detail = ("this exact response was already submitted and rejected; "
                      f"see {prior_repair.name}")
        else:
            detail = "this exact response has already been submitted"
        return ImportResult("duplicate", raw_path, raw_hash,
                            handoff_path=existing[0] if existing else None,
                            repair_path=prior_repair if prior_repair.exists() else None,
                            defects=[Defect("duplicate-response", detail)])

    text, defects = decode_raw(raw_path)

    submission: dict[str, Any] | None = None
    if text is not None:
        block, extract_defects = extract_yaml_block(text)
        defects += extract_defects
        if block is not None:
            submission, parse_defects = parse_block(block)
            defects += parse_defects
            if submission is not None:
                defects += validate_submission(submission)

    record = None
    if submission is not None and not defects:
        record, prov_defects = verify_provenance(ws, submission, prompt_hash=prompt_hash)
        defects += prov_defects

    if defects or submission is None or record is None:
        # Best-effort lookup so the repair request can quote authoritative
        # identifiers rather than the provider's own rejected values.
        authoritative = record or find_export_record(ws, submission)
        repair = build_repair_request(defects, raw_path, raw_hash, submission, authoritative)
        repair_path = repair_dir(ws) / f"{raw_hash.split(':', 1)[-1][:RAW_HASH_LEN]}__repair.md"
        write_canonical(repair_path, repair)
        return ImportResult("rejected", raw_path, raw_hash,
                            repair_path=repair_path, defects=defects)

    data = dict(submission)
    data.pop("handoff_packet", None)
    data["schema_version"] = HANDOFF_SCHEMA_VERSION
    data["raw_response_hash"] = raw_hash
    data["prompt_hash"] = effective_prompt_hash(record)
    data["imported_at"] = utcnow()

    try:
        packet = seal_handoff(HandoffPacket.model_validate(data))
    except PydanticValidationError as exc:
        defects = [Defect("invalid-value", e["msg"],
                          location=".".join(str(p) for p in e["loc"]) or None)
                   for e in exc.errors()]
        repair_path = repair_dir(ws) / f"{raw_hash.split(':', 1)[-1][:RAW_HASH_LEN]}__repair.md"
        write_canonical(repair_path,
                        build_repair_request(defects, raw_path, raw_hash, submission, record))
        return ImportResult("rejected", raw_path, raw_hash,
                            repair_path=repair_path, defects=defects)

    handoff_path = write_handoff(ws, packet)
    return ImportResult("imported", raw_path, raw_hash,
                        handoff_path=handoff_path, packet=packet)
