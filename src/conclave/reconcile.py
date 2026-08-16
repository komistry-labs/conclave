"""Deterministic ledger reconciliation.

Closes the gap left when an artifact was written but its ledger event was not
appended — because the ledger was damaged, locked, or not yet initialised.

This is NOT a generic append interface. It reconstructs only the events that
can be established from immutable artifact metadata, and only for the
supported operational event types. It cannot and does not infer human
decisions or action authorisations.

TWO HONESTY CONSTRAINTS

    Timestamps. Where an artifact records when it was made — a Task Packet's
    created_at, an export record's exported_at, a Handoff Packet's
    imported_at — that value becomes occurred_at. Where no such record
    exists, reconciliation time is used and the payload says plainly that the
    original event time is unknown. A plausible-looking timestamp is worse
    than an admitted gap.

    Ordering. Reconciled events are appended in whatever order they are
    discovered. Their sequence numbers record when they were RECONCILED, not
    when the operations happened. No reconciled event claims an ordering that
    cannot be established from the artifacts themselves.

Anything that cannot be reconstructed unambiguously is reported as unresolved
rather than guessed at.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .council import CouncilReview, verify_council_content_hash
from .context import read_context_bundle
from .contextrelay import context_relay_dir, read_context_relay_export
from .concurrency import read_batch
from .errors import LedgerError
from .execution import read_run_record
from .handoff import HandoffPacket, verify_handoff_content_hash
from .hashing import hash_file
from .ledger import append_event, exists, read_events, verify
from .models import TaskPacket
from .orchestration import read_orchestration
from .routing import read_route_plan
from .scope import ScopeReview, verify_review_content_hash
from .synthesis import read_synthesis
from .taskpacket import list_tasks, list_versions, packet_path, read_packet, verify_content_hash
from .workspace import Workspace, utcnow

RECONCILIATION_REASON = "artifact existed without corresponding ledger event"

SUPPORTED_EVENTS = (
    "task_packet_created",
    "task_packet_revised",
    "relay_prompt_exported",
    "relay_prompt_replaced",
    "provider_response_preserved",
    "handoff_packet_imported",
    "provider_response_rejected",
    "scope_review_created",
    "council_review_created",
    "context_bundle_created",
    "route_plan_created",
    "provider_run_captured",
    "context_relay_prompt_exported",
    "execution_batch_recorded",
    "orchestration_recorded",
    "synthesis_continuation_recorded",
)


@dataclass(frozen=True)
class Candidate:
    """One event that would be appended, if it is not already recorded."""

    event_type: str
    actor: str
    authority_level: str
    subject_refs: list[str]
    artifact_hashes: dict[str, str]
    payload: dict[str, Any]
    occurred_at: str | None          # None => original time unknown
    identifying_hash: str            # the hash used to decide "already recorded"
    source: str


@dataclass(frozen=True)
class Unresolved:
    source: str
    reason: str


@dataclass
class ReconcileReport:
    created: list[dict[str, Any]] = field(default_factory=list)
    already_recorded: list[Candidate] = field(default_factory=list)
    unresolved: list[Unresolved] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.unresolved


# -- existing coverage -----------------------------------------------------

def _recorded_hashes(ws: Workspace) -> set[tuple[str, str]]:
    """(event_type, artifact_hash) pairs already present in the ledger.

    Matching is by artifact hash rather than event_id: a reconciled event
    carries `reconciled: true` in its payload and so can never share an id
    with the live event it stands in for.
    """
    out: set[tuple[str, str]] = set()
    for e in read_events(ws):
        etype = e.get("event_type")
        for value in (e.get("artifact_hashes") or {}).values():
            out.add((etype, value))
    return out


# -- candidate discovery ---------------------------------------------------

def _task_packets(ws: Workspace) -> tuple[list[Candidate], list[Unresolved]]:
    candidates, unresolved = [], []
    for task_id in list_tasks(ws):
        for version in list_versions(ws, task_id):
            path = packet_path(ws, task_id, version)
            try:
                packet: TaskPacket = read_packet(ws, task_id, version)
            except Exception as exc:
                unresolved.append(Unresolved(str(path.name), f"unreadable: {exc}"))
                continue
            if not verify_content_hash(packet):
                unresolved.append(Unresolved(
                    path.name, "content_hash does not verify; cannot attest to an "
                               "artifact whose integrity is in doubt"))
                continue
            candidates.append(Candidate(
                event_type="task_packet_created" if version == 1 else "task_packet_revised",
                actor="conclave", authority_level="system",
                subject_refs=[packet.ref],
                artifact_hashes={"task_packet": packet.content_hash or ""},
                payload={"task_id": packet.task_id, "version": packet.version,
                         "path": str(path.relative_to(ws.root)),
                         "created_by": packet.created_by,
                         **({"supersedes": packet.supersedes,
                             "revision_reason": packet.revision_reason}
                            if version > 1 else {})},
                occurred_at=packet.created_at,
                identifying_hash=packet.content_hash or "",
                source=path.name,
            ))
    return candidates, unresolved


def _context_bundles(ws: Workspace) -> tuple[list[Candidate], list[Unresolved]]:
    candidates, unresolved = [], []
    for path in sorted(ws.context_dir.glob("*.yaml")):
        try:
            bundle = read_context_bundle(path)
        except Exception as exc:
            unresolved.append(Unresolved(
                path.name, f"unreadable context bundle: {exc}"
            ))
            continue
        candidates.append(Candidate(
            event_type="context_bundle_created",
            actor="conclave", authority_level="system",
            subject_refs=[bundle.packet_ref],
            artifact_hashes={"context_bundle": bundle.content_hash},
            payload={"source_artifact": path.relative_to(ws.root).as_posix()},
            occurred_at=None,
            identifying_hash=bundle.content_hash,
            source=path.relative_to(ws.root).as_posix(),
        ))
    return candidates, unresolved


def _route_plans(ws: Workspace) -> tuple[list[Candidate], list[Unresolved]]:
    candidates, unresolved = [], []
    for path in sorted(ws.routes_dir.glob("*.yaml")):
        try:
            plan = read_route_plan(path)
        except Exception as exc:
            unresolved.append(Unresolved(
                path.name, f"unreadable route plan: {exc}"
            ))
            continue
        candidates.append(Candidate(
            event_type="route_plan_created",
            actor="conclave", authority_level="system",
            subject_refs=[plan.packet_ref],
            artifact_hashes={"route_plan": plan.content_hash},
            payload={"source_artifact": path.relative_to(ws.root).as_posix()},
            occurred_at=None,
            identifying_hash=plan.content_hash,
            source=path.relative_to(ws.root).as_posix(),
        ))
    return candidates, unresolved


def _context_relay_exports(
    ws: Workspace,
) -> tuple[list[Candidate], list[Unresolved]]:
    candidates, unresolved = [], []
    base = context_relay_dir(ws)
    if not base.exists():
        return candidates, unresolved
    for path in sorted(base.glob("*.yaml")):
        try:
            record = read_context_relay_export(path)
        except Exception as exc:
            unresolved.append(Unresolved(
                path.name, f"unreadable context relay export: {exc}"
            ))
            continue
        candidates.append(Candidate(
            event_type="context_relay_prompt_exported",
            actor="conclave",
            authority_level="system",
            subject_refs=[record.packet_ref],
            artifact_hashes={
                "task_packet": record.packet_content_hash,
                "context_bundle": record.context_bundle_hash,
                "route_plan": record.route_plan_hash,
                "prompt": record.prompt_hash,
                "context_relay_manifest": record.content_hash,
            },
            payload={
                "provider": record.provider,
                "role": record.role,
                "stage_index": record.stage_index,
                "prompt_file": record.prompt_file,
                "transport": "manual-relay",
            },
            occurred_at=record.exported_at,
            identifying_hash=record.content_hash,
            source=path.relative_to(ws.root).as_posix(),
        ))
    return candidates, unresolved


def _provider_runs(ws: Workspace) -> tuple[list[Candidate], list[Unresolved]]:
    candidates, unresolved = [], []
    for path in sorted(ws.runs_dir.glob("*.yaml")):
        try:
            record = read_run_record(path)
        except Exception as exc:
            unresolved.append(Unresolved(
                path.name, f"unreadable provider run: {exc}"
            ))
            continue
        candidates.append(Candidate(
            event_type="provider_run_captured",
            actor="conclave", authority_level="system",
            subject_refs=[record.packet_ref],
            artifact_hashes={"provider_run": record.content_hash},
            payload={
                "source_artifact": path.relative_to(ws.root).as_posix(),
                "provider": record.response.provider,
                "role": record.role,
                "status": record.status,
                "egress_authority": record.egress_authority,
                "egress_decision_ref": record.egress_decision_ref,
            },
            occurred_at=record.completed_at,
            identifying_hash=record.content_hash,
            source=path.relative_to(ws.root).as_posix(),
        ))
    return candidates, unresolved


def _execution_batches(ws: Workspace) -> tuple[list[Candidate], list[Unresolved]]:
    candidates, unresolved = [], []
    for path in sorted(ws.batches_dir.glob("*.yaml")):
        try:
            record = read_batch(path)
        except Exception as exc:
            unresolved.append(Unresolved(
                path.name, f"unreadable execution batch: {exc}"
            ))
            continue
        candidates.append(Candidate(
            event_type="execution_batch_recorded",
            actor="conclave", authority_level="system",
            subject_refs=[record.packet_ref],
            artifact_hashes={
                "execution_batch": record.content_hash,
                "route_plan": record.route_plan_hash,
                "context_bundle": record.context_bundle_hash,
                "task_packet": record.task_packet_hash,
            },
            payload={
                "batch_id": record.batch_id, "status": record.status,
                "stage_indices": list(record.stage_indices),
                "usage_complete": record.usage_complete,
            },
            occurred_at=record.started_at,
            identifying_hash=record.content_hash,
            source=path.relative_to(ws.root).as_posix(),
        ))
    return candidates, unresolved


def _orchestrations(ws: Workspace) -> tuple[list[Candidate], list[Unresolved]]:
    candidates, unresolved = [], []
    for path in sorted(ws.orchestrations_dir.glob("*.yaml")):
        try:
            record = read_orchestration(path)
        except Exception as exc:
            unresolved.append(Unresolved(
                path.name, f"unreadable orchestration record: {exc}"
            ))
            continue
        candidates.append(Candidate(
            event_type="orchestration_recorded",
            actor="conclave", authority_level="system",
            subject_refs=[record.packet_ref, record.council_review_id],
            artifact_hashes={
                "orchestration": record.content_hash,
                "execution_batch": record.execution_batch_hash,
                "council_review": record.council_review_hash,
                "route_plan": record.route_plan_hash,
                "task_packet": record.task_packet_hash,
            },
            payload={
                "orchestration_id": record.orchestration_id,
                "pause_state": record.pause_state,
                "action_execution_allowed": False,
            },
            occurred_at=record.completed_at,
            identifying_hash=record.content_hash,
            source=path.relative_to(ws.root).as_posix(),
        ))
    return candidates, unresolved


def _synthesis_continuations(
    ws: Workspace,
) -> tuple[list[Candidate], list[Unresolved]]:
    candidates, unresolved = [], []
    for path in sorted(ws.synthesis_dir.glob("*.yaml")):
        try:
            record = read_synthesis(path)
        except Exception as exc:
            unresolved.append(Unresolved(
                path.name, f"unreadable synthesis continuation: {exc}"
            ))
            continue
        candidates.append(Candidate(
            event_type="synthesis_continuation_recorded",
            actor="conclave", authority_level="system",
            subject_refs=[record.packet_ref, record.council_review_id],
            artifact_hashes={
                "synthesis_continuation": record.content_hash,
                "source_orchestration": record.source_orchestration_hash,
                "provider_run": record.synthesis_run_hash,
                "council_review": record.council_review_hash,
                "route_plan": record.route_plan_hash,
                "task_packet": record.task_packet_hash,
            },
            payload={
                "continuation_id": record.continuation_id,
                "pause_state": record.pause_state,
                "action_execution_allowed": False,
            },
            occurred_at=record.completed_at,
            identifying_hash=record.content_hash,
            source=path.relative_to(ws.root).as_posix(),
        ))
    return candidates, unresolved


def _relay_exports(ws: Workspace) -> tuple[list[Candidate], list[Unresolved]]:
    candidates, unresolved = [], []
    path = ws.outbox_dir / "exports.jsonl"
    if not path.exists():
        return candidates, unresolved

    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            unresolved.append(Unresolved(f"exports.jsonl:{i}", f"not valid JSON: {exc}"))
            continue

        kind = record.get("event_type", "prompt_exported")
        if kind == "prompt_export_replaced":
            # Only reconcilable because the record itself proves a replacement
            # occurred and names what was destroyed.
            candidates.append(Candidate(
                event_type="relay_prompt_replaced",
                actor="conclave", authority_level="system",
                subject_refs=[record.get("packet_ref", "")],
                artifact_hashes={"prompt": record.get("replacement_prompt_hash", ""),
                                 "task_packet": record.get("packet_content_hash", "")},
                payload={"provider": record.get("provider"), "role": record.get("role"),
                         "prompt_file": record.get("prompt_file"),
                         "replaced_prompt_hash": record.get("replaced_prompt_hash"),
                         "replacement_reason": record.get("replacement_reason"),
                         "replacement_authority": record.get("replacement_authority")},
                occurred_at=record.get("replaced_at"),
                identifying_hash=record.get("replacement_prompt_hash", ""),
                source=f"exports.jsonl:{i}",
            ))
        elif kind == "prompt_exported":
            candidates.append(Candidate(
                event_type="relay_prompt_exported",
                actor="conclave", authority_level="system",
                subject_refs=[record.get("packet_ref", "")],
                artifact_hashes={"prompt": record.get("prompt_hash", ""),
                                 "task_packet": record.get("packet_content_hash", "")},
                payload={"provider": record.get("provider"), "role": record.get("role"),
                         "prompt_file": record.get("prompt_file")},
                occurred_at=record.get("exported_at"),
                identifying_hash=record.get("prompt_hash", ""),
                source=f"exports.jsonl:{i}",
            ))
        else:
            unresolved.append(Unresolved(f"exports.jsonl:{i}",
                                         f"unrecognised export event_type {kind!r}"))
    return candidates, unresolved


def _raw_responses(ws: Workspace) -> tuple[list[Candidate], list[Unresolved], dict[str, Path]]:
    """Raw artifacts carry no timestamp, so occurred_at stays unknown."""
    from .handoff import raw_dir

    candidates: list[Candidate] = []
    by_prefix: dict[str, Path] = {}
    base = raw_dir(ws)
    if not base.exists():
        return candidates, [], by_prefix

    for p in sorted(base.glob("*")):
        if not p.is_file():
            continue
        raw_hash = hash_file(p, binary=True)
        by_prefix[raw_hash.split(":", 1)[-1][:12]] = p
        candidates.append(Candidate(
            event_type="provider_response_preserved",
            actor="unknown-provider", authority_level="advisory_agent",
            subject_refs=[],
            artifact_hashes={"raw_response": raw_hash},
            payload={"raw_file": p.name,
                     "note": "the exact bytes received, before parsing",
                     "actor_unknown": True,
                     "actor_note": "the raw artifact does not record which provider "
                                   "supplied it; a matching Handoff Packet may"},
            occurred_at=None,
            identifying_hash=raw_hash,
            source=p.name,
        ))
    return candidates, [], by_prefix


def _handoffs(ws: Workspace) -> tuple[list[Candidate], list[Unresolved]]:
    candidates, unresolved = [], []
    for p in sorted(ws.inbox_dir.glob("*.yaml")):
        try:
            h = HandoffPacket.model_validate(yaml.safe_load(p.read_text(encoding="utf-8")))
        except Exception as exc:
            unresolved.append(Unresolved(p.name, f"unreadable handoff packet: {exc}"))
            continue
        if not verify_handoff_content_hash(h):
            unresolved.append(Unresolved(p.name, "content_hash does not verify"))
            continue
        candidates.append(Candidate(
            event_type="handoff_packet_imported",
            actor=h.provider, authority_level="advisory_agent",
            subject_refs=[h.packet_ref],
            artifact_hashes={"handoff_packet": h.content_hash or "",
                             "raw_response": h.raw_response_hash,
                             "prompt": h.prompt_hash},
            payload={"provider": h.provider, "role": h.role,
                     "submission_status": h.status,
                     "recommended_next_action": h.recommended_next_action,
                     "declared_objects_touched": sorted(h.touched_keys()),
                     "handoff_file": p.name,
                     "note": "passed import validation; this asserts nothing about "
                             "whether its findings are correct"},
            occurred_at=h.imported_at,
            identifying_hash=h.content_hash or "",
            source=p.name,
        ))
    return candidates, unresolved


def _rejections(ws: Workspace, raw_by_prefix: dict[str, Path]) -> tuple[list[Candidate],
                                                                       list[Unresolved]]:
    """A repair artifact is what proves a rejection occurred."""
    from .handoff import repair_dir

    candidates, unresolved = [], []
    base = repair_dir(ws)
    if not base.exists():
        return candidates, unresolved

    for p in sorted(base.glob("*__repair.md")):
        prefix = p.name.split("__", 1)[0]
        raw = raw_by_prefix.get(prefix)
        if raw is None:
            unresolved.append(Unresolved(
                p.name, f"no raw response found for prefix {prefix!r}; the rejection "
                        "cannot be tied to the bytes that were rejected"))
            continue
        candidates.append(Candidate(
            event_type="provider_response_rejected",
            actor="conclave", authority_level="system",
            subject_refs=[],
            artifact_hashes={"raw_response": hash_file(raw, binary=True)},
            payload={"raw_file": raw.name, "repair_file": p.name,
                     "note": "rejected at import; no Handoff Packet was created",
                     "defect_codes_unknown": True,
                     "defect_note": "the repair artifact records the defects in prose; "
                                    "they are not reconstructed here as structured codes"},
            occurred_at=None,
            identifying_hash=hash_file(raw, binary=True),
            source=p.name,
        ))
    return candidates, unresolved


def _scope_reviews(ws: Workspace) -> tuple[list[Candidate], list[Unresolved]]:
    from .scope import scope_dir

    candidates, unresolved = [], []
    base = scope_dir(ws)
    if not base.exists():
        return candidates, unresolved

    for p in sorted(base.glob("*.yaml")):
        try:
            r = ScopeReview.model_validate(yaml.safe_load(p.read_text(encoding="utf-8")))
        except Exception as exc:
            unresolved.append(Unresolved(p.name, f"unreadable scope review: {exc}"))
            continue
        if not verify_review_content_hash(r):
            unresolved.append(Unresolved(p.name, "content_hash does not verify"))
            continue
        candidates.append(Candidate(
            event_type="scope_review_created",
            actor="conclave", authority_level="system",
            subject_refs=[r.task_packet_ref],
            artifact_hashes={"scope_review": r.content_hash or "",
                             "handoff_packet": r.handoff_packet_hash,
                             "task_packet": r.task_packet_hash},
            payload={"provider": r.provider, "evaluator_schema": r.schema_version,
                     "scope_status": r.scope_status,
                     "violation_count": r.violation_count,
                     "review_file": p.name,
                     "note": "an evaluator result under the named schema; it does not "
                             "itself authorise remediation"},
            occurred_at=r.evaluated_at,
            identifying_hash=r.content_hash or "",
            source=p.name,
        ))
    return candidates, unresolved


def _council_reviews(ws: Workspace) -> tuple[list[Candidate], list[Unresolved]]:
    candidates, unresolved = [], []
    for p in sorted(ws.council_dir.glob("*.yaml")):
        try:
            r = CouncilReview.model_validate(yaml.safe_load(p.read_text(encoding="utf-8")))
        except Exception as exc:
            unresolved.append(Unresolved(p.name, f"unreadable council review: {exc}"))
            continue
        if not verify_council_content_hash(r):
            unresolved.append(Unresolved(p.name, "content_hash does not verify"))
            continue
        candidates.append(Candidate(
            event_type="council_review_created",
            actor="conclave", authority_level="system",
            subject_refs=[r.task_packet_ref, r.council_review_id],
            artifact_hashes={"council_review": r.content_hash or "",
                             "task_packet": r.task_packet_hash,
                             **({"route_plan": r.route_plan_hash}
                                if r.route_plan_hash else {})},
            payload={"council_review_id": r.council_review_id,
                     "review_status": r.review_status,
                     "submission_count": len(r.submissions),
                     "missing_providers": r.missing_providers,
                     "governance_alert_count": len(r.governance_alerts),
                     "selection_basis": r.selection_basis,
                     "yaml_file": p.name,
                     "markdown_file": p.with_suffix(".md").name,
                     "note": "a review artifact was produced; this asserts nothing about "
                             "whether its recommendations were accepted"},
            occurred_at=r.created_at,
            identifying_hash=r.content_hash or "",
            source=p.name,
        ))
    return candidates, unresolved


def discover(ws: Workspace) -> tuple[list[Candidate], list[Unresolved]]:
    candidates: list[Candidate] = []
    unresolved: list[Unresolved] = []

    for fn in (
        _task_packets,
        _context_bundles,
        _route_plans,
        _context_relay_exports,
        _provider_runs,
        _execution_batches,
        _orchestrations,
        _synthesis_continuations,
        _relay_exports,
        _handoffs,
        _scope_reviews,
        _council_reviews,
    ):
        c, u = fn(ws)
        candidates += c
        unresolved += u

    raw_candidates, raw_unresolved, by_prefix = _raw_responses(ws)
    candidates += raw_candidates
    unresolved += raw_unresolved

    c, u = _rejections(ws, by_prefix)
    candidates += c
    unresolved += u

    return candidates, unresolved


# -- entry point -----------------------------------------------------------

def reconcile(ws: Workspace) -> ReconcileReport:
    """Append missing operational events. Idempotent. Refuses on a bad chain."""
    if not exists(ws):
        raise LedgerError("no ledger in this workspace; run 'conclave ledger init' first")

    report_before = verify(ws)
    if not report_before.ok:
        raise LedgerError(
            "refusing to reconcile: the ledger does not verify. Repair the chain first.\n  " +
            "\n  ".join(str(d) for d in report_before.defects[:5])
        )

    candidates, unresolved = discover(ws)
    recorded = _recorded_hashes(ws)
    report = ReconcileReport(unresolved=unresolved)

    for candidate in candidates:
        if (candidate.event_type, candidate.identifying_hash) in recorded:
            report.already_recorded.append(candidate)
            continue

        payload = dict(candidate.payload)
        payload["reconciled"] = True
        payload["reconciliation_reason"] = RECONCILIATION_REASON
        payload["source_artifact"] = candidate.source
        if candidate.occurred_at is None:
            payload["original_event_time_unknown"] = True
            payload["time_note"] = (
                "the artifact records no creation time; occurred_at is the "
                "reconciliation time and does not indicate when the operation happened"
            )

        event, created = append_event(
            ws,
            event_type=candidate.event_type,
            actor=candidate.actor,
            authority_level=candidate.authority_level,
            subject_refs=candidate.subject_refs,
            artifact_hashes=candidate.artifact_hashes,
            payload=payload,
            occurred_at=candidate.occurred_at or utcnow(),
        )
        if created:
            report.created.append(event)
            recorded.add((candidate.event_type, candidate.identifying_hash))
        else:
            report.already_recorded.append(candidate)

    return report
