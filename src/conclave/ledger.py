"""Hash-chained CONCLAVE event ledger.

An audit chain of governed events, not a decision table. A decision-only
ledger would stay empty through the whole workflow and offer no integrity
trail for how the decision surface was produced. Here, a human decision will
later attach to a verifiable chain of evidence rather than starting a fresh
record at the end.

WHAT A LEDGER ENTRY MEANS

    An entry is a factual record that an event occurred and an artifact
    existed. It is not an endorsement.

      council_review_created   a review artifact was produced
                               NOT that its recommendations were accepted
      handoff_packet_imported  a response passed import validation
                               NOT that its findings are true
      scope_review_created     an evaluator produced a result under a named
                               schema
                               NOT that remediation is authorised

    No event may imply that an advisory agent approved, ratified,
    commissioned or merged anything. Provider-originated events name the
    provider but carry authority_level: advisory_agent.

The ledger references artifacts by id, path and hash. It never copies packet
bodies or provider prose into payloads: the artifact remains the source of
substantive content, and duplicating it would create a second copy that could
drift from the first.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator, Literal

from .errors import LedgerError
from .hashing import hash_bytes, hash_file
from .workspace import Workspace, utcnow

LEDGER_SCHEMA_VERSION = "conclave-ledger/0.1.0"
SUPPORTED_SCHEMA_VERSIONS = frozenset({LEDGER_SCHEMA_VERSION})
EVENT_ID_LEN = 16

AuthorityLevel = Literal["system", "advisory_agent", "human_principal"]
AUTHORITY_LEVELS = ("system", "advisory_agent", "human_principal")

GENESIS_EVENT = "workspace_genesis"

EVENT_TYPES = (
    GENESIS_EVENT,
    "workspace_snapshot_attested",
    "task_packet_created",
    "task_packet_revised",
    "relay_prompt_exported",
    "relay_prompt_replaced",
    "provider_response_preserved",
    "handoff_packet_imported",
    "provider_response_rejected",
    "scope_review_created",
    "council_review_created",
    "integrity_failure_detected",
    "operation_refused",
    "context_bundle_created",
    "route_plan_created",
    "provider_run_captured",
)

# Reserved for a later increment. Declared so the vocabulary is stable and so
# nothing else claims these names; not emitted by any current code path.
RESERVED_EVENT_TYPES = ("human_decision_recorded", "action_authorised")

ALL_EVENT_TYPES = frozenset(EVENT_TYPES) | frozenset(RESERVED_EVENT_TYPES)

# Event types an advisory agent may be the actor for. Anything implying
# approval is absent by construction.
ADVISORY_PERMITTED_EVENTS = frozenset({
    "provider_response_preserved",
    "handoff_packet_imported",
    "provider_response_rejected",
})

REQUIRED_FIELDS = (
    "schema_version", "sequence", "event_id", "event_type", "occurred_at",
    "recorded_at", "actor", "authority_level", "subject_refs",
    "artifact_hashes", "payload", "previous_entry_hash", "entry_hash",
)

LOCK_TIMEOUT_SECONDS = 10.0
STALE_LOCK_SECONDS = 60.0


# -- canonical form --------------------------------------------------------

def canonical_json(obj: Any) -> str:
    """Deterministic JSON. Sorted keys, no incidental whitespace."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def compute_entry_hash(event: dict[str, Any]) -> str:
    body = {k: v for k, v in event.items() if k != "entry_hash"}
    return "sha256:" + hashlib.sha256(canonical_json(body).encode("utf-8")).hexdigest()


def derive_event_id(
    event_type: str,
    actor: str,
    authority_level: str,
    subject_refs: list[str],
    artifact_hashes: dict[str, str],
    payload: dict[str, Any] | None = None,
) -> str:
    """Deterministic from substantive identity, excluding timestamps.

    Includes the payload. Without it, events that carry their substance in the
    payload rather than in an artifact hash would collapse: two
    `operation_refused` events about the same subject for entirely different
    reasons, or two `integrity_failure_detected` events reporting different
    defects, would share an id and the second would be silently swallowed as a
    duplicate.

    Excluded: sequence, occurred_at, recorded_at, previous_entry_hash,
    entry_hash. Those describe when and where the event was recorded, not what
    it is. Retrying the same substantive event later must stay idempotent.

    Payload is canonicalised, so key insertion order cannot affect identity.
    """
    material = canonical_json({
        "event_type": event_type,
        "actor": actor,
        "authority_level": authority_level,
        "subject_refs": sorted(subject_refs),
        "artifact_hashes": dict(sorted(artifact_hashes.items())),
        "payload": payload or {},
    })
    return "EV-" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:EVENT_ID_LEN]


# -- locking ---------------------------------------------------------------

@contextmanager
def exclusive_lock(path: Path, timeout: float = LOCK_TIMEOUT_SECONDS) -> Iterator[None]:
    """Portable exclusive lock via O_EXCL. Works on Windows and POSIX.

    Two writers must not compute the same next sequence number from the same
    chain state. The lock is held across read-verify-append, not merely across
    the write.
    """
    lock = path.with_name(path.name + ".lock")
    lock.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + timeout
    fd = None
    while True:
        try:
            fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            break
        except FileExistsError:
            try:
                age = time.time() - lock.stat().st_mtime
                if age > STALE_LOCK_SECONDS:
                    lock.unlink(missing_ok=True)
                    continue
            except OSError:
                pass
            if time.monotonic() > deadline:
                raise LedgerError(
                    f"could not acquire ledger lock at {lock} within {timeout}s. "
                    "Another CONCLAVE process may be appending."
                ) from None
            time.sleep(0.02)
    try:
        os.write(fd, str(os.getpid()).encode("ascii"))
        os.close(fd)
        fd = None
        yield
    finally:
        if fd is not None:
            os.close(fd)
        try:
            lock.unlink(missing_ok=True)
        except OSError:
            pass


# -- reading ---------------------------------------------------------------

def ledger_path(ws: Workspace) -> Path:
    return ws.ledger_path


def exists(ws: Workspace) -> bool:
    return ledger_path(ws).exists()


def read_raw_lines(ws: Workspace) -> list[str]:
    path = ledger_path(ws)
    if not path.exists():
        return []
    return [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


def read_events(ws: Workspace) -> list[dict[str, Any]]:
    """Parse all entries. Raises on malformed JSON rather than skipping."""
    events = []
    for i, line in enumerate(read_raw_lines(ws), start=1):
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise LedgerError(f"ledger line {i} is not valid JSON: {exc}") from None
    return events


def head(ws: Workspace) -> dict[str, Any] | None:
    events = read_events(ws)
    return events[-1] if events else None


def chain_hash(ws: Workspace) -> str | None:
    last = head(ws)
    return last.get("entry_hash") if last else None


# -- verification ----------------------------------------------------------

@dataclass(frozen=True)
class Defect:
    code: str
    message: str
    line: int | None = None

    def __str__(self) -> str:
        where = f" [line {self.line}]" if self.line else ""
        return f"{self.code}{where}: {self.message}"


@dataclass
class VerificationReport:
    defects: list[Defect] = field(default_factory=list)
    entry_count: int = 0
    final_chain_hash: str | None = None

    @property
    def ok(self) -> bool:
        return not self.defects

    def add(self, code: str, message: str, line: int | None = None) -> None:
        self.defects.append(Defect(code, message, line))


def verify(ws: Workspace) -> VerificationReport:
    """Verify the whole chain. NEVER repairs anything."""
    report = VerificationReport()
    lines = read_raw_lines(ws)
    report.entry_count = len(lines)

    if not lines:
        report.add("empty-ledger", "ledger is absent or empty; run 'conclave ledger init'")
        return report

    events: list[dict[str, Any]] = []
    for i, line in enumerate(lines, start=1):
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            report.add("malformed-json", f"line is not valid JSON: {exc}", i)
            continue
        if not isinstance(event, dict):
            report.add("not-an-object", f"line parsed as {type(event).__name__}", i)
            continue
        events.append(event)

        for name in REQUIRED_FIELDS:
            if name not in event:
                report.add("missing-required-field", f"field {name!r} is absent", i)

        schema = event.get("schema_version")
        if schema not in SUPPORTED_SCHEMA_VERSIONS:
            report.add("unsupported-schema-version",
                       f"schema_version {schema!r} is not supported by this build", i)

        if event.get("event_type") not in ALL_EVENT_TYPES:
            report.add("unknown-event-type",
                       f"event_type {event.get('event_type')!r} is not recognised", i)

        authority = event.get("authority_level")
        if authority not in AUTHORITY_LEVELS:
            report.add("invalid-authority-level",
                       f"authority_level {authority!r} is not one of {list(AUTHORITY_LEVELS)}", i)
        elif authority == "advisory_agent" and \
                event.get("event_type") not in ADVISORY_PERMITTED_EVENTS:
            report.add("forbidden-advisory-authority",
                       f"an advisory agent cannot be the actor for "
                       f"{event.get('event_type')!r}; no advisory agent approves, ratifies, "
                       "commissions or merges anything", i)

    # -- genesis
    genesis_positions = [i for i, e in enumerate(events, start=1)
                         if e.get("event_type") == GENESIS_EVENT]
    if not genesis_positions:
        report.add("missing-genesis", f"no {GENESIS_EVENT} entry found")
    else:
        if len(genesis_positions) > 1:
            report.add("multiple-genesis",
                       f"{len(genesis_positions)} genesis entries at lines "
                       f"{genesis_positions}; exactly one is permitted")
        if genesis_positions[0] != 1:
            report.add("genesis-not-first",
                       f"genesis appears at line {genesis_positions[0]}, not line 1")
        first = events[0]
        if first.get("event_type") == GENESIS_EVENT:
            if first.get("sequence") != 1:
                report.add("genesis-bad-sequence",
                           f"genesis sequence is {first.get('sequence')!r}, expected 1", 1)
            if first.get("previous_entry_hash") is not None:
                report.add("genesis-has-previous",
                           "genesis previous_entry_hash must be null", 1)

    # -- sequence, linkage, hashes
    seen_ids: dict[str, int] = {}
    seen_sequences: dict[int, int] = {}
    previous: dict[str, Any] | None = None

    for i, event in enumerate(events, start=1):
        seq = event.get("sequence")
        if isinstance(seq, int):
            if seq in seen_sequences:
                report.add("duplicate-sequence",
                           f"sequence {seq} already used at line {seen_sequences[seq]}", i)
            seen_sequences[seq] = i
            if seq != i:
                report.add("sequence-gap",
                           f"expected sequence {i}, found {seq}; sequences must be "
                           "contiguous from 1", i)
        else:
            report.add("invalid-sequence", f"sequence {seq!r} is not an integer", i)

        eid = event.get("event_id")
        if isinstance(eid, str):
            if eid in seen_ids:
                report.add("duplicate-event-id",
                           f"event_id {eid} already used at line {seen_ids[eid]}", i)
            seen_ids[eid] = i

        expected_hash = compute_entry_hash(event)
        if event.get("entry_hash") != expected_hash:
            report.add("entry-hash-mismatch",
                       f"entry_hash does not match the entry body "
                       f"(recorded {event.get('entry_hash')}, computed {expected_hash}); "
                       "the entry has been altered", i)

        if previous is not None:
            if event.get("previous_entry_hash") != previous.get("entry_hash"):
                report.add("broken-chain",
                           f"previous_entry_hash does not match the preceding entry "
                           f"(expected {previous.get('entry_hash')}, "
                           f"found {event.get('previous_entry_hash')})", i)
        previous = event

    report.final_chain_hash = events[-1].get("entry_hash") if events else None
    return report


# -- appending -------------------------------------------------------------

def _write_line(path: Path, event: dict[str, Any]) -> None:
    """Append one line and force it to disk before reporting success."""
    path.parent.mkdir(parents=True, exist_ok=True)
    line = canonical_json(event) + "\n"
    with path.open("a", encoding="utf-8", newline="\n") as fh:
        fh.write(line)
        fh.flush()
        os.fsync(fh.fileno())


def append_event(
    ws: Workspace,
    *,
    event_type: str,
    actor: str = "conclave",
    authority_level: AuthorityLevel = "system",
    subject_refs: list[str] | None = None,
    artifact_hashes: dict[str, str] | None = None,
    payload: dict[str, Any] | None = None,
    occurred_at: str | None = None,
    allow_genesis: bool = False,
) -> tuple[dict[str, Any], bool]:
    """Append one event. Returns (event, created).

    Verifies the entire existing chain before appending. A ledger that is
    already broken must not be extended: a later entry chained onto a corrupt
    one would give the corruption the appearance of continuity.

    Idempotent by event_id. Appending the same substantive event twice
    returns the existing entry unchanged.
    """
    if event_type not in ALL_EVENT_TYPES:
        raise LedgerError(f"unknown event_type {event_type!r}")
    if authority_level not in AUTHORITY_LEVELS:
        raise LedgerError(f"invalid authority_level {authority_level!r}")
    if authority_level == "advisory_agent" and event_type not in ADVISORY_PERMITTED_EVENTS:
        raise LedgerError(
            f"an advisory agent cannot be the actor for {event_type!r}. "
            "No advisory agent approves, ratifies, commissions or merges anything."
        )
    if event_type == GENESIS_EVENT and not allow_genesis:
        raise LedgerError("genesis is created by initialise(), not by append_event()")

    subject_refs = sorted(subject_refs or [])
    artifact_hashes = dict(sorted((artifact_hashes or {}).items()))
    payload = payload or {}
    event_id = derive_event_id(event_type, actor, authority_level,
                               subject_refs, artifact_hashes, payload)

    path = ledger_path(ws)
    with exclusive_lock(path):
        existing = read_events(ws)

        if existing:
            report = verify(ws)
            if not report.ok:
                raise LedgerError(
                    "refusing to append: the existing ledger does not verify.\n  " +
                    "\n  ".join(str(d) for d in report.defects[:5])
                )
            for e in existing:
                if e.get("event_id") == event_id:
                    return e, False
        elif event_type != GENESIS_EVENT:
            raise LedgerError(
                "ledger has no genesis entry; run 'conclave ledger init' first"
            )

        previous_hash = existing[-1]["entry_hash"] if existing else None
        now = utcnow()
        event = {
            "schema_version": LEDGER_SCHEMA_VERSION,
            "sequence": len(existing) + 1,
            "event_id": event_id,
            "event_type": event_type,
            "occurred_at": occurred_at or now,
            "recorded_at": now,
            "actor": actor,
            "authority_level": authority_level,
            "subject_refs": subject_refs,
            "artifact_hashes": artifact_hashes,
            "payload": payload,
            "previous_entry_hash": previous_hash,
        }
        event["entry_hash"] = compute_entry_hash(event)
        _write_line(path, event)
        return event, True


def record_event(ws: Workspace, **kwargs: Any) -> tuple[dict[str, Any] | None, bool]:
    """Append if a ledger exists; otherwise do nothing.

    Operations call this so that workspaces created before ledger integration
    keep working. Once `ledger init` has run, events accrue from that point
    forward — the snapshot is the bridge to everything earlier.
    """
    if not exists(ws):
        return None, False
    return append_event(ws, **kwargs)


# -- snapshot bridge -------------------------------------------------------

# Governed artifact classes. KOS is deliberately absent: it is external,
# read-only, and not CONCLAVE's to attest to.
SNAPSHOT_CLASSES: tuple[tuple[str, str, str, bool], ...] = (
    # (class name, subdirectory, glob, hash as binary)
    ("task_packets", "tasks", "*/v*.yaml", False),
    ("relay_prompts", "relay/outbox", "*.md", False),
    ("relay_export_records", "relay/outbox", "exports.jsonl", False),
    ("raw_provider_responses", "relay/inbox/raw", "*", True),
    ("handoff_packets", "relay/inbox", "*.yaml", False),
    ("repair_requests", "relay/inbox/repair", "*.md", False),
    ("scope_reviews", "scope", "*.yaml", False),
    ("council_reviews", "council", "*.yaml", False),
    ("council_markdown", "council", "*.md", False),
    ("context_bundles", "context", "*.yaml", False),
    ("route_plans", "routes", "*.yaml", False),
    ("provider_runs", "runs", "*.yaml", False),
)


def build_snapshot_manifest(ws: Workspace) -> dict[str, Any]:
    """Deterministic manifest of existing governed artifacts.

    Sorted by relative path, so the same workspace always produces the same
    manifest and therefore the same event_id.

    Raw provider responses are hashed as binary: they are evidentiary, and
    canonicalising them would erase byte-level differences the audit may need.
    """
    classes: dict[str, list[dict[str, str]]] = {}
    total = 0
    for name, subdir, pattern, binary in SNAPSHOT_CLASSES:
        base = ws.root / subdir
        if not base.exists():
            continue
        entries = []
        for p in sorted(base.glob(pattern)):
            if not p.is_file():
                continue
            entries.append({
                "path": p.relative_to(ws.root).as_posix(),
                "content_hash": hash_file(p, binary=binary),
                "hashing": "binary" if binary else "kos-canonical-text-v1",
            })
        if entries:
            classes[name] = entries
            total += len(entries)
    return {"classes": classes, "artifact_count": total}


def initialise(ws: Workspace, config: dict[str, Any]) -> list[dict[str, Any]]:
    """Create genesis and the snapshot bridge. Idempotent."""
    if exists(ws) and read_raw_lines(ws):
        report = verify(ws)
        if not report.ok:
            raise LedgerError(
                "ledger already exists but does not verify; refusing to initialise over it"
            )
        return read_events(ws)

    genesis_payload = {
        "bootstrap_version": config.get("bootstrap_version"),
        "principal": config.get("principal"),
        "authority_policy": config.get("authority", {}),
        "hashing_algorithm": (config.get("hashing") or {}).get("algorithm", "sha256"),
        "canonicalisation": (config.get("hashing") or {}).get(
            "canonicalisation", "kos-canonical-text-v1"),
        "kos_access": config.get("kos_access", "read-only"),
        "kos_repository": config.get("kos_repository"),
        "ledger_schema_version": LEDGER_SCHEMA_VERSION,
    }
    genesis, _ = append_event(
        ws, event_type=GENESIS_EVENT, actor="conclave", authority_level="system",
        subject_refs=[str(ws.root)], payload=genesis_payload, allow_genesis=True,
    )

    manifest = build_snapshot_manifest(ws)
    snapshot, _ = append_event(
        ws,
        event_type="workspace_snapshot_attested",
        actor="conclave",
        authority_level="system",
        subject_refs=[str(ws.root)],
        artifact_hashes={
            "manifest": hash_bytes(canonical_json(manifest).encode("utf-8")),
        },
        payload={
            **manifest,
            "snapshot_taken_at": utcnow(),
            "chronology_note": (
                "These artifacts predate ledger instrumentation. This entry attests "
                "only that they existed with these hashes at the snapshot time above. "
                "It does NOT assert when they were created, in what order, or by whom. "
                "No historical events have been fabricated."
            ),
            "excludes": [
                "the KOS repository, which is external, read-only and not CONCLAVE's "
                "to attest to"
            ],
        },
    )
    return [genesis, snapshot]
