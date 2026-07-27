"""Council Review — aggregate verified submissions for one Task Packet version.

Two artifacts. The YAML is canonical and immutable; the Markdown is a
projection for a human reader and carries the YAML's reference and full
content hash so the two cannot drift unnoticed.

What this does NOT do:

    No semantic comparison. Agreement and disagreement are detected from
    structured values only - identical enum values, identical explicit keys,
    identical scope classifications. Two findings are never called agreeing
    because their prose looks similar. No embeddings, no fuzzy matching, no
    model interpretation.

    No approval. The decision block is created empty and stays empty.
    CONCLAVE coordinates and summarises; it does not decide, and there is no
    code path by which it can populate a human decision field.

A NOTE ON FINDING KEYS
    `finding_id` is provider-local. Two providers both numbering their first
    finding F-001 have not agreed about anything. Cross-provider finding
    comparison therefore uses an explicit shared `key` field, and findings
    without one are not compared at all. Treating F-001 as a shared
    identifier would manufacture agreement out of a numbering convention.
"""

from __future__ import annotations

import hashlib
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

from .errors import ValidationError
from .handoff import HandoffPacket, verify_handoff_content_hash
from .hashing import hash_text, write_canonical
from .models import TaskPacket
from .scope import ScopeReview, read_review, verify_review_content_hash
from .taskpacket import read_packet, verify_content_hash
from .workspace import Workspace, utcnow

COUNCIL_SCHEMA_VERSION = "council-review/0.1.0"
ID_DIGEST_LEN = 10

ReviewStatus = Literal[
    "incomplete",
    "ready_for_human_review",
    "blocked_by_governance",
    "ambiguous_submissions",
]

# Most severe first. The first matching condition wins.
STATUS_PRECEDENCE = (
    "ambiguous_submissions",
    "blocked_by_governance",
    "incomplete",
    "ready_for_human_review",
)

SEVERITY_ORDER = ("high", "medium", "low", "unspecified")


# -- models ----------------------------------------------------------------

class DecisionBlock(BaseModel):
    """Reserved for the human principal. CONCLAVE never populates these.

    Types are pinned so an AI-generated council review cannot express a
    decision even by accident: `decision` admits only 'pending' at this
    schema version.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    decision: Literal["pending"] = "pending"
    decided_by: None = None
    decided_at: None = None
    rationale: None = None
    authorised_actions: list[Any] = Field(default_factory=list, max_length=0)


class Submission(BaseModel):
    model_config = ConfigDict(extra="allow", frozen=True)

    provider: str
    role: str
    submission_status: str
    recommended_next_action: str
    handoff_packet_hash: str
    raw_response_hash: str
    scope_status: str
    scope_violation_count: int
    summary: str | None = None
    findings: list[dict[str, Any]] = Field(default_factory=list)
    assumptions: list[Any] = Field(default_factory=list)
    abstentions: list[Any] = Field(default_factory=list)
    unresolved: list[Any] = Field(default_factory=list)
    evidence_used: list[Any] = Field(default_factory=list)


class CouncilReview(BaseModel):
    """Closed schema. Unknown top-level fields are rejected.

    A Council Review is the document a human reads before deciding. If it
    could carry undeclared fields, a manipulated review could smuggle in
    `approved: true` or `merge_authorised: true` and a reader — or a later
    tool — might act on it. The DecisionBlock forbids extras for the same
    reason; the enclosing document must too, or the protection is decorative.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = COUNCIL_SCHEMA_VERSION
    council_review_id: str
    task_packet_ref: str
    task_packet_hash: str
    created_at: str

    providers_expected: list[dict[str, str]] = Field(default_factory=list)
    submissions: list[Submission] = Field(default_factory=list)
    missing_providers: list[str] = Field(default_factory=list)
    provider_summaries: list[dict[str, Any]] = Field(default_factory=list)

    consolidated_findings: list[dict[str, Any]] = Field(default_factory=list)
    structural_agreements: list[dict[str, Any]] = Field(default_factory=list)
    structural_disagreements: list[dict[str, Any]] = Field(default_factory=list)
    unresolved_items: list[dict[str, Any]] = Field(default_factory=list)
    abstentions: list[dict[str, Any]] = Field(default_factory=list)

    scope_summary: dict[str, Any] = Field(default_factory=dict)
    governance_alerts: list[dict[str, Any]] = Field(default_factory=list)

    decision_block: DecisionBlock = Field(default_factory=DecisionBlock)
    review_status: ReviewStatus
    human_decision_required: bool

    source_handoff_hashes: list[str] = Field(default_factory=list)
    source_scope_review_hashes: list[str] = Field(default_factory=list)
    superseded_submissions: list[dict[str, Any]] = Field(default_factory=list)
    comparison_basis: str = (
        "structured values only; no semantic, lexical or model-based comparison of prose"
    )
    content_hash: str | None = None

    @property
    def task_id(self) -> str:
        return self.task_packet_ref.split("@", 1)[0]

    def to_serialisable(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude_none=False)


@dataclass(frozen=True)
class CouncilOutcome:
    review: CouncilReview
    yaml_path: Path
    markdown_path: Path
    created: bool


# -- gathering -------------------------------------------------------------

def _verified_handoffs(ws: Workspace, packet: TaskPacket) -> list[HandoffPacket]:
    out: list[HandoffPacket] = []
    for path in sorted(ws.inbox_dir.glob("*.yaml")):
        try:
            h = HandoffPacket.model_validate(
                yaml.safe_load(path.read_text(encoding="utf-8")))
        except Exception:
            continue
        if h.packet_ref != packet.ref:
            continue
        if not verify_handoff_content_hash(h):
            raise ValidationError(
                f"handoff {path.name} does not verify against its own content_hash; "
                "it has been altered on disk"
            )
        if h.packet_content_hash != packet.content_hash:
            raise ValidationError(
                f"handoff {path.name} answers a different version of {packet.ref}"
            )
        out.append(h)
    return out


def _verified_scope_reviews(ws: Workspace, packet: TaskPacket) -> dict[str, ScopeReview]:
    """Keyed by handoff_packet_hash."""
    from .scope import scope_dir

    out: dict[str, ScopeReview] = {}
    for path in sorted(scope_dir(ws).glob("*.yaml")) if scope_dir(ws).exists() else []:
        try:
            r = read_review(path)
        except Exception:
            continue
        if r.task_packet_ref != packet.ref:
            continue
        if not verify_review_content_hash(r):
            raise ValidationError(
                f"scope review {path.name} does not verify against its own content_hash"
            )
        out[r.handoff_packet_hash] = r
    return out


def _select_submissions(
    handoffs: list[HandoffPacket],
) -> tuple[dict[str, HandoffPacket], list[dict[str, Any]], list[str]]:
    """One submission per provider, by explicit import order.

    Returns (selected, superseded, ambiguous_providers). Where the latest
    submission cannot be established unambiguously, the provider is flagged
    rather than resolved by an arbitrary rule.
    """
    by_provider: dict[str, list[HandoffPacket]] = defaultdict(list)
    for h in handoffs:
        by_provider[h.provider].append(h)

    selected: dict[str, HandoffPacket] = {}
    superseded: list[dict[str, Any]] = []
    ambiguous: list[str] = []

    for provider, items in by_provider.items():
        if len(items) == 1:
            selected[provider] = items[0]
            continue
        latest = max(i.imported_at for i in items)
        newest = [i for i in items if i.imported_at == latest]
        if len(newest) != 1:
            ambiguous.append(provider)
            continue
        selected[provider] = newest[0]
        for old in items:
            if old is not newest[0]:
                superseded.append({
                    "provider": provider,
                    "handoff_packet_hash": old.content_hash,
                    "raw_response_hash": old.raw_response_hash,
                    "imported_at": old.imported_at,
                    "reason": "a later submission from this provider was imported",
                })
    return selected, superseded, sorted(ambiguous)


# -- structural comparison -------------------------------------------------

def _finding_key(finding: dict[str, Any]) -> str | None:
    """Explicit shared key only. NEVER finding_id, which is provider-local."""
    key = finding.get("key")
    return key if isinstance(key, str) and key.strip() else None


def _comparable_finding_values(finding: dict[str, Any]) -> dict[str, Any]:
    """Structured fields only. Prose fields are excluded from comparison."""
    return {k: finding.get(k) for k in ("severity", "dimension") if k in finding}


def _unresolved_id(item: Any) -> str | None:
    if isinstance(item, dict):
        for field_name in ("id", "identifier", "key"):
            value = item.get(field_name)
            if isinstance(value, str) and value.strip():
                return value
    return None


def detect_structural(
    submissions: dict[str, HandoffPacket], scopes: dict[str, ScopeReview]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    agreements: list[dict[str, Any]] = []
    disagreements: list[dict[str, Any]] = []
    providers = sorted(submissions)
    if len(providers) < 2:
        return agreements, disagreements

    # -- enum fields
    for field_name, attr in (("recommended_next_action", "recommended_next_action"),
                             ("submission_status", "status")):
        values = {p: getattr(submissions[p], attr) for p in providers}
        distinct = sorted(set(values.values()))
        entry = {"kind": field_name, "values": values}
        (agreements if len(distinct) == 1 else disagreements).append(
            {**entry, "value": distinct[0]} if len(distinct) == 1
            else {**entry, "distinct_values": distinct}
        )

    # -- accept vs anything else, called out explicitly
    accepting = [p for p in providers if submissions[p].recommended_next_action == "accept"]
    dissenting = [p for p in providers
                  if submissions[p].recommended_next_action in ("revise", "escalate", "abstain")]
    if accepting and dissenting:
        disagreements.append({
            "kind": "accept_versus_dissent",
            "accepting": accepting,
            "dissenting": {p: submissions[p].recommended_next_action for p in dissenting},
        })

    # -- findings, by explicit shared key only
    by_key: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for p in providers:
        for finding in submissions[p].findings:
            if not isinstance(finding, dict):
                continue
            key = _finding_key(finding)
            if key:
                by_key[key][p] = _comparable_finding_values(finding)
    for key, per_provider in sorted(by_key.items()):
        if len(per_provider) < 2:
            continue
        distinct = {yaml.safe_dump(v, sort_keys=True) for v in per_provider.values()}
        entry = {"kind": "finding", "finding_key": key, "values": per_provider}
        (agreements if len(distinct) == 1 else disagreements).append(entry)

    # -- scope classifications for the same object
    by_object: dict[str, dict[str, str]] = defaultdict(dict)
    for p in providers:
        review = scopes.get(submissions[p].content_hash or "")
        if not review:
            continue
        for r in review.object_results:
            by_object[r.key][p] = r.classification
    for obj, per_provider in sorted(by_object.items()):
        if len(per_provider) < 2:
            continue
        distinct = sorted(set(per_provider.values()))
        entry = {"kind": "scope_classification", "object": obj, "values": per_provider}
        (agreements if len(distinct) == 1 else disagreements).append(
            {**entry, "value": distinct[0]} if len(distinct) == 1
            else {**entry, "distinct_values": distinct}
        )

    # -- shared unresolved identifiers
    by_unresolved: dict[str, list[str]] = defaultdict(list)
    for p in providers:
        for item in submissions[p].unresolved:
            uid = _unresolved_id(item)
            if uid:
                by_unresolved[uid].append(p)
    for uid, ps in sorted(by_unresolved.items()):
        if len(ps) > 1:
            agreements.append({"kind": "unresolved_item", "identifier": uid,
                               "providers": sorted(ps)})

    return agreements, disagreements


# -- assembly --------------------------------------------------------------

def _severity(finding: dict[str, Any]) -> str:
    value = finding.get("severity")
    return value if value in SEVERITY_ORDER else "unspecified"


def derive_status(
    *, missing: list[str], ambiguous: list[str], governance_alerts: list[dict[str, Any]]
) -> ReviewStatus:
    if ambiguous:
        return "ambiguous_submissions"
    if governance_alerts:
        return "blocked_by_governance"
    if missing:
        return "incomplete"
    return "ready_for_human_review"


def council_review_id(packet: TaskPacket, handoff_hashes: list[str],
                      scope_hashes: list[str]) -> str:
    """Deterministic from the source set, so an unchanged set re-derives the
    same id and therefore the same path. A changed set is a new review."""
    payload = "\n".join([
        COUNCIL_SCHEMA_VERSION, packet.ref, packet.content_hash or "",
        *sorted(handoff_hashes), *sorted(scope_hashes),
    ])
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:ID_DIGEST_LEN]
    return f"CR-{packet.task_id}-v{packet.version}-{digest}"


def build_council_review(
    packet: TaskPacket,
    handoffs: list[HandoffPacket],
    scopes: dict[str, ScopeReview],
) -> CouncilReview:
    selected, superseded, ambiguous = _select_submissions(handoffs)

    expected = [{"provider": a.provider, "role": a.role} for a in packet.assigned_providers]
    missing = sorted({a.provider for a in packet.assigned_providers} - set(selected))

    submissions: list[Submission] = []
    provider_summaries: list[dict[str, Any]] = []
    consolidated: list[dict[str, Any]] = []
    unresolved_items: list[dict[str, Any]] = []
    abstentions: list[dict[str, Any]] = []
    governance_alerts: list[dict[str, Any]] = []
    scope_rows: list[dict[str, Any]] = []

    for provider in sorted(selected):
        h = selected[provider]
        review = scopes.get(h.content_hash or "")
        violations = review.violation_count if review else 0
        status = review.scope_status if review else "not_evaluated"

        submissions.append(Submission(
            provider=provider, role=h.role,
            submission_status=h.status,
            recommended_next_action=h.recommended_next_action,
            handoff_packet_hash=h.content_hash or "",
            raw_response_hash=h.raw_response_hash,
            scope_status=status, scope_violation_count=violations,
            summary=(h.output or {}).get("summary"),
            findings=list(h.findings), assumptions=list(h.assumptions),
            abstentions=list(h.abstentions), unresolved=list(h.unresolved),
            evidence_used=list(h.evidence_used),
        ))

        provider_summaries.append({
            "provider": provider, "role": h.role,
            "submission_status": h.status,
            "recommended_next_action": h.recommended_next_action,
            "summary": (h.output or {}).get("summary"),
            "finding_count": len(h.findings),
            "unresolved_count": len(h.unresolved),
            "abstention_count": len(h.abstentions),
            "scope_status": status,
        })

        for finding in h.findings:
            if isinstance(finding, dict):
                consolidated.append({"provider": provider, "severity": _severity(finding),
                                     **finding})
        for item in h.unresolved:
            unresolved_items.append({"provider": provider, "item": item,
                                     "identifier": _unresolved_id(item)})
        for item in h.abstentions:
            abstentions.append({"provider": provider, "item": item})

        scope_rows.append({"provider": provider, "scope_status": status,
                           "violation_count": violations,
                           "evaluated": review is not None})

        if review and review.scope_status == "expansion_detected":
            for r in review.violations():
                governance_alerts.append({
                    "kind": "scope_violation", "provider": provider,
                    "classification": r.classification, "object": r.key,
                    "action": r.action, "matched_grant": r.matched_grant,
                    "detail": r.reason,
                })
        if review is None:
            governance_alerts.append({
                "kind": "scope_not_evaluated", "provider": provider,
                "detail": "no verified Scope Review exists for this submission; "
                          "scope compliance is unknown, not confirmed",
            })

    for provider in ambiguous:
        governance_alerts.append({
            "kind": "provider_submission_ambiguous", "provider": provider,
            "detail": "multiple submissions from this provider and no unambiguous "
                      "latest one; CONCLAVE will not choose between them",
        })

    consolidated.sort(key=lambda f: (SEVERITY_ORDER.index(f["severity"]), f["provider"]))
    agreements, disagreements = detect_structural(selected, scopes)

    handoff_hashes = sorted(h.content_hash or "" for h in handoffs)
    scope_hashes = sorted(r.content_hash or "" for r in scopes.values())

    return seal(CouncilReview(
        council_review_id=council_review_id(packet, handoff_hashes, scope_hashes),
        task_packet_ref=packet.ref,
        task_packet_hash=packet.content_hash or "",
        created_at=utcnow(),
        providers_expected=expected,
        submissions=submissions,
        missing_providers=missing,
        provider_summaries=provider_summaries,
        consolidated_findings=consolidated,
        structural_agreements=agreements,
        structural_disagreements=disagreements,
        unresolved_items=unresolved_items,
        abstentions=abstentions,
        scope_summary={
            "providers": scope_rows,
            "total_violations": sum(r["violation_count"] for r in scope_rows),
            "any_expansion": any(r["scope_status"] == "expansion_detected" for r in scope_rows),
        },
        governance_alerts=governance_alerts,
        review_status=derive_status(missing=missing, ambiguous=ambiguous,
                                    governance_alerts=governance_alerts),
        # Always true. The decision block is pending and only the principal may
        # fill it, so every council review awaits a human. Governance alerts do
        # not raise this flag - nothing could, because it is never false.
        human_decision_required=True,
        source_handoff_hashes=handoff_hashes,
        source_scope_review_hashes=scope_hashes,
        superseded_submissions=superseded,
    ))


# -- sealing and storage ---------------------------------------------------

def compute_content_hash(review: CouncilReview) -> str:
    payload = {k: v for k, v in review.to_serialisable().items() if k != "content_hash"}
    return hash_text(yaml.safe_dump(payload, sort_keys=True, allow_unicode=True))


def seal(review: CouncilReview) -> CouncilReview:
    return review.model_copy(update={"content_hash": compute_content_hash(review)})


def verify_council_content_hash(review: CouncilReview) -> bool:
    if not review.content_hash:
        return False
    return review.content_hash == compute_content_hash(review)


def yaml_path(ws: Workspace, review_id: str) -> Path:
    return ws.council_dir / f"{review_id}.yaml"


def markdown_path(ws: Workspace, review_id: str) -> Path:
    return ws.council_dir / f"{review_id}.md"


def read_council(path: Path) -> CouncilReview:
    return CouncilReview.model_validate(yaml.safe_load(Path(path).read_text(encoding="utf-8")))


def write_council(ws: Workspace, review: CouncilReview) -> tuple[Path, Path]:
    if not review.content_hash:
        raise ValidationError("council review is not sealed")
    if not verify_council_content_hash(review):
        raise ValidationError("council review content_hash is stale")

    ypath = yaml_path(ws, review.council_review_id)
    if ypath.exists():
        raise ValidationError(f"{ypath.name} already exists; Council Reviews are immutable")
    ypath.parent.mkdir(parents=True, exist_ok=True)
    text = yaml.safe_dump(review.to_serialisable(), sort_keys=False, allow_unicode=True)
    ypath.write_bytes(text.replace("\r\n", "\n").encode("utf-8"))

    mpath = markdown_path(ws, review.council_review_id)
    write_canonical(mpath, render_markdown(review))
    return ypath, mpath


# -- markdown projection ---------------------------------------------------

DISCLAIMER = (
    "CONCLAVE has coordinated and summarised advisory submissions. "
    "It has not approved, ratified, commissioned or merged anything."
)

STATUS_BANNER = {
    "ready_for_human_review": "READY FOR HUMAN REVIEW",
    "incomplete": "INCOMPLETE — not all assigned providers have submitted",
    "blocked_by_governance": "BLOCKED BY GOVERNANCE — authority boundaries were crossed",
    "ambiguous_submissions": "AMBIGUOUS SUBMISSIONS — cannot establish which response counts",
}


def render_markdown(review: CouncilReview) -> str:
    out: list[str] = [
        f"# Council Review — {review.task_packet_ref}",
        "",
        f"> **{STATUS_BANNER[review.review_status]}**",
        "",
        f"> {DISCLAIMER}",
        "",
        "## Identity",
        "",
        "```",
        f"council_review_id : {review.council_review_id}",
        f"content_hash      : {review.content_hash}",
        f"task_packet_ref   : {review.task_packet_ref}",
        f"task_packet_hash  : {review.task_packet_hash}",
        f"schema_version    : {review.schema_version}",
        f"created_at        : {review.created_at}",
        f"review_status     : {review.review_status}",
        f"human_decision_required : {str(review.human_decision_required).lower()}",
        "```",
        "",
        "This document is a projection. The YAML packet above is authoritative.",
        "",
        "## Participation",
        "",
        "| Provider | Role | Submitted | Status | Recommends | Scope |",
        "|---|---|---|---|---|---|",
    ]
    submitted = {s.provider for s in review.submissions}
    for e in review.providers_expected:
        s = next((x for x in review.submissions if x.provider == e["provider"]), None)
        if s:
            out.append(f"| {s.provider} | {s.role} | yes | {s.submission_status} | "
                       f"{s.recommended_next_action} | {s.scope_status} |")
        else:
            out.append(f"| {e['provider']} | {e['role']} | **NO** | — | — | — |")
    out.append("")

    if review.missing_providers:
        out += [f"**Missing submissions:** {', '.join(review.missing_providers)}", ""]

    out += ["## Executive summaries", ""]
    if review.provider_summaries:
        for p in review.provider_summaries:
            out += [f"### {p['provider']} — {p['role']}", "",
                    p.get("summary") or "_no summary supplied_", "",
                    f"`{p['finding_count']} finding(s) · {p['unresolved_count']} unresolved "
                    f"· {p['abstention_count']} abstention(s)`", ""]
    else:
        out += ["_no submissions_", ""]

    out += ["## Structural agreements", ""]
    out += _render_structural(review.structural_agreements) or ["_none detected_", ""]

    out += ["## Structural disagreements", ""]
    out += _render_structural(review.structural_disagreements) or ["_none detected_", ""]

    out += ["", f"_{review.comparison_basis}._", "", "## Findings by severity", ""]
    if review.consolidated_findings:
        for sev in SEVERITY_ORDER:
            group = [f for f in review.consolidated_findings if f["severity"] == sev]
            if not group:
                continue
            out += [f"### {sev}", ""]
            for f in group:
                ident = f.get("key") or f.get("finding_id") or "—"
                out.append(f"- **{f['provider']}** `{ident}` — {f.get('claim', '_no claim_')}")
                if f.get("proposed_resolution"):
                    out.append(f"  - proposed: {f['proposed_resolution']}")
            out.append("")
    else:
        out += ["_none_", ""]

    out += ["## Unresolved items", ""]
    if review.unresolved_items:
        for u in review.unresolved_items:
            out.append(f"- **{u['provider']}** — {u['item']}")
        out.append("")
    else:
        out += ["_none_", ""]

    out += ["## Abstentions", ""]
    if review.abstentions:
        for a in review.abstentions:
            out.append(f"- **{a['provider']}** — {a['item']}")
        out.append("")
    else:
        out += ["_none_", ""]

    out += ["## Scope and governance alerts", ""]
    if review.governance_alerts:
        for a in review.governance_alerts:
            out.append(f"- **{a['kind']}** — {a.get('provider', '')} "
                       f"{a.get('object', '')} {a.get('detail', '')}".rstrip())
        out.append("")
    else:
        out += ["_none_", ""]
    out += [f"Total scope violations: **{review.scope_summary.get('total_violations', 0)}**", ""]

    out += ["## Source provenance", "", "```",
            *[f"handoff : {h}" for h in review.source_handoff_hashes],
            *[f"scope   : {s}" for s in review.source_scope_review_hashes]]
    for s in review.superseded_submissions:
        out.append(f"superseded: {s['provider']} {s['handoff_packet_hash']}")
    out += ["```", ""]

    out += [
        "## Human decision",
        "",
        "_Reserved for the constitutional authority. CONCLAVE cannot populate this._",
        "",
        "```yaml",
        "decision: pending",
        "decided_by: null",
        "decided_at: null",
        "rationale: null",
        "authorised_actions: []",
        "```",
        "",
        "---",
        "",
        DISCLAIMER,
        "",
    ]
    return "\n".join(out)


def _render_structural(items: list[dict[str, Any]]) -> list[str]:
    if not items:
        return []
    out: list[str] = []
    for i in items:
        kind = i["kind"]
        if kind in ("recommended_next_action", "submission_status"):
            if "value" in i:
                out.append(f"- **{kind}** — all providers: `{i['value']}`")
            else:
                pairs = ", ".join(f"{p}=`{v}`" for p, v in sorted(i["values"].items()))
                out.append(f"- **{kind}** — {pairs}")
        elif kind == "accept_versus_dissent":
            out.append(f"- **accept vs dissent** — accepting: {', '.join(i['accepting'])}; "
                       f"dissenting: " +
                       ", ".join(f"{p}=`{v}`" for p, v in sorted(i["dissenting"].items())))
        elif kind == "scope_classification":
            pairs = ", ".join(f"{p}=`{v}`" for p, v in sorted(i["values"].items()))
            out.append(f"- **scope** `{i['object']}` — {pairs}")
        elif kind == "finding":
            out.append(f"- **finding** `{i['finding_key']}` — " +
                       ", ".join(f"{p}={v}" for p, v in sorted(i["values"].items())))
        elif kind == "unresolved_item":
            out.append(f"- **unresolved** `{i['identifier']}` — "
                       f"raised by {', '.join(i['providers'])}")
    out.append("")
    return out


# -- entry point -----------------------------------------------------------

def _load_existing(path: Path, expected_id: str, packet: TaskPacket) -> CouncilReview:
    try:
        existing = read_council(path)
    except Exception as exc:
        raise ValidationError(f"existing council review {path.name} is unreadable: {exc}") from None
    if not verify_council_content_hash(existing):
        raise ValidationError(
            f"existing council review {path.name} does not verify against its own content_hash"
        )
    for name, expected, actual in (
        ("council_review_id", expected_id, existing.council_review_id),
        ("schema_version", COUNCIL_SCHEMA_VERSION, existing.schema_version),
        ("task_packet_ref", packet.ref, existing.task_packet_ref),
        ("task_packet_hash", packet.content_hash, existing.task_packet_hash),
    ):
        if expected != actual:
            raise ValidationError(
                f"existing council review {path.name} does not match its sources: "
                f"{name} is {actual!r}, expected {expected!r}"
            )
    return existing


def review_task(ws: Workspace, task_id: str, version: int) -> CouncilOutcome:
    """Aggregate verified submissions for one immutable Task Packet version.

    IDEMPOTENT for an unchanged source set: the review id is derived from the
    source hashes, so re-running finds and verifies the existing review rather
    than recomputing `created_at`. A changed source set yields a different id
    and therefore a new immutable review beside the old one.
    """
    try:
        packet = read_packet(ws, task_id, version)
    except Exception:
        raise ValidationError(f"no Task Packet {task_id}@v{version} in this workspace") from None
    if not verify_content_hash(packet):
        raise ValidationError(f"Task Packet {task_id}@v{version} has been altered on disk")

    handoffs = _verified_handoffs(ws, packet)
    scopes = _verified_scope_reviews(ws, packet)

    review = build_council_review(packet, handoffs, scopes)
    ypath = yaml_path(ws, review.council_review_id)

    if ypath.exists():
        existing = _load_existing(ypath, review.council_review_id, packet)
        mpath = markdown_path(ws, review.council_review_id)
        if not mpath.exists():
            write_canonical(mpath, render_markdown(existing))
        return CouncilOutcome(existing, ypath, mpath, created=False)

    ypath, mpath = write_council(ws, review)
    return CouncilOutcome(review, ypath, mpath, created=True)
