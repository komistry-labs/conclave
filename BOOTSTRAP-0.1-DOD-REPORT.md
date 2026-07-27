# CONCLAVE Bootstrap 0.1 — Definition of Done Report

| | |
|---|---|
| Date | 27 July 2026 |
| Tests | **517 passed**, 0 failed |
| Source | ~2,900 lines · Tests ~5,400 lines |
| KOS repository | `485f88f`, unmodified throughout |

Every requirement issued across increments 1–7 is listed. Nothing is omitted.

---

## 1. Mission and scope

| # | Requirement | Status | Evidence |
|---|---|---|---|
| 1.1 | Local CLI coordinating providers by manual relay | **PASS** | `cli.py`; live run in §7 |
| 1.2 | One instruction → independent responses → structured review → human decision | **PASS** | end-to-end test |
| 1.3 | Task Packet | **PASS** | `models.py`, `taskpacket.py` |
| 1.4 | Relay Prompt Generator | **PASS** | `relay.py` |
| 1.5 | Handoff Packet Import | **PASS** | `handoff.py` |
| 1.6 | Validation | **PASS** | `validation.py` |
| 1.7 | Scope Drift Detection | **PASS** | `scope.py` |
| 1.8 | Council Review Packet | **PASS** | `council.py` |
| 1.9 | Local hash-chained ledger | **PASS** | `ledger.py` |
| 1.10 | No web UI | **PASS** | none exists |
| 1.11 | No API integrations | **PASS** | no HTTP client anywhere |
| 1.12 | No provider automation | **PASS** | relay is file-based only |
| 1.13 | No GitHub PR automation | **PASS** | no git or GitHub code |
| 1.14 | No KOS modifications | **PASS** | verified after every increment |
| 1.15 | No further architecture documents | **PASS** | only README + this report |

## 2. Required CLI

| # | Command | Status |
|---|---|---|
| 2.1 | `conclave init` | **PASS** |
| 2.2 | `conclave task create` | **PASS** |
| 2.3 | `conclave relay export` | **PASS** |
| 2.4 | `conclave relay import` | **PASS** |
| 2.5 | `conclave validate` | **PASS** |
| 2.6 | `conclave council review` | **PASS** |
| 2.7 | `conclave ledger verify` | **PASS** |
| 2.8 | `conclave status` | **PASS** |
| 2.9 | Additional: `task revise/list/show`, `scope review`, `ledger init/reconcile/show`, `version` | **PASS** |

## 3. Canonical hashing

| # | Requirement | Status | Evidence |
|---|---|---|---|
| 3.1 | UTF-8, no BOM, LF, one trailing newline | **PASS** | `hashing.canonicalise` |
| 3.2 | Hash canonical bytes, not working-tree bytes | **PASS** | CRLF/LF hash equality test |
| 3.3 | Trailing whitespace preserved | **PASS** | hard-line-break test |
| 3.4 | BOM rejected, not stripped | **PASS** | raises `IntegrityError` |
| 3.5 | Invalid UTF-8 rejected | **PASS** | raises `IntegrityError` |
| 3.6 | Idempotent canonicalisation | **PASS** | 9 parametrised inputs |
| 3.7 | Binary content never canonicalised | **PASS** | PNG-header test |
| 3.8 | Single implementation module | **PASS** | all modules import `hashing` |

## 4. Task Packet

| # | Requirement | Status |
|---|---|---|
| 4.1 | Deterministic, collision-resistant IDs | **PASS** |
| 4.2 | All 10 required fields | **PASS** |
| 4.3 | Schema / semantic / governance separated | **PASS** |
| 4.4 | Validation never silently repairs | **PASS** — 4 tests |
| 4.5 | Unknown fields preserved | **PASS** |
| 4.6 | Forbidden fields rejected | **PASS** |
| 4.7 | Hashing uses the canonical module | **PASS** |
| 4.8 | Scope structures stable | **PASS** — `ObjectRef` frozen |
| 4.9 | Immutable; revision creates a new version | **PASS** |
| 4.10 | Frozen model | **PASS** |
| 4.11 | Write refuses stale `content_hash` | **PASS** |
| 4.12 | Schema errors short-circuit exactly | **PASS** |
| 4.13 | Explicit `--clear-*` for intentional emptying | **PASS** |

## 5. Relay export

| # | Requirement | Status |
|---|---|---|
| 5.1 | One Markdown file per provider | **PASS** |
| 5.2 | No clipboard | **PASS** |
| 5.3 | No other provider's content | **PASS** — asserted per provider |
| 5.4 | Packet ref + short hash in filename | **PASS** |
| 5.5 | Windows-safe filename, hex only | **PASS** |
| 5.6 | Full `content_hash` inside the prompt | **PASS** |
| 5.7 | Refuse export on any validation error | **PASS** |
| 5.8 | Governance/egress warnings surfaced separately | **PASS** |
| 5.9 | Export never modifies the Task Packet | **PASS** |
| 5.10 | Idempotent; refuses differing overwrite | **PASS** |
| 5.11 | Provenance sufficient to bind a reply | **PASS** — `exports.jsonl` |
| 5.12 | Only the 11 specified prompt sections | **PASS** |
| 5.13 | Nulls omitted from the projection | **PASS** |
| 5.14 | Forced replacement requires `--reason` | **PASS** |
| 5.15 | `prompt_export_replaced` with all 10 fields | **PASS** |
| 5.16 | Replacement not recorded as ordinary export | **PASS** |
| 5.17 | Idempotent re-export records nothing | **PASS** |

## 6. Handoff import

| # | Requirement | Status |
|---|---|---|
| 6.1 | Raw preserved before parsing, immutably | **PASS** |
| 6.2 | `raw_response_hash` over exact bytes (binary) | **PASS** |
| 6.3 | Strict UTF-8 decode; no `errors="replace"` | **PASS** |
| 6.4 | Invalid encoding → defect + repair + preserved raw | **PASS** |
| 6.5 | Exactly one fenced YAML block | **PASS** |
| 6.6 | Zero blocks rejected | **PASS** |
| 6.7 | Multiple blocks rejected as ambiguous | **PASS** |
| 6.8 | Prose never read as fields | **PASS** |
| 6.9 | All 16 required fields | **PASS** |
| 6.10 | Provenance verified against `exports.jsonl` | **PASS** |
| 6.11 | Task Packet existence + integrity verified | **PASS** |
| 6.12 | Provider assignment verified | **PASS** |
| 6.13 | Plausible identifiers alone insufficient | **PASS** |
| 6.14 | Sealed, immutable storage | **PASS** |
| 6.15 | Duplicate raw idempotent | **PASS** |
| 6.16 | Distinct replies stored separately | **PASS** |
| 6.17 | Bounded repair request, no fabrication | **PASS** |
| 6.18 | `objects_touched` captured, not adjudicated | **PASS** |
| 6.19 | 18 required test cases | **PASS** |
| 6.20 | `verify_handoff_content_hash` at write | **PASS** |
| 6.21 | Submission vocabulary pinned | **PASS** |

## 7. Scope drift detection

| # | Requirement | Status |
|---|---|---|
| 7.1 | Reads both packets without modifying either | **PASS** |
| 7.2 | Five classifications | **PASS** |
| 7.3 | Whole-object grant covers sections | **PASS** |
| 7.4 | Section grant excludes whole object | **PASS** |
| 7.5 | Section grant excludes siblings | **PASS** |
| 7.6 | Whole-object prohibition covers sections | **PASS** |
| 7.7 | Section prohibition covers only that section | **PASS** |
| 7.8 | Action rules per grant class | **PASS** |
| 7.9 | Precedence prohibited > read-only > target > undeclared | **PASS** |
| 7.10 | All 10 sealed-review fields | **PASS** |
| 7.11 | `within_scope` / `expansion_detected` | **PASS** |
| 7.12 | Prose never mined | **PASS** — `evaluation_basis` field |
| 7.13 | 18 required test cases | **PASS** |
| 7.14 | Idempotent; no `--force` | **PASS** |
| 7.15 | Existing review verified on reuse | **PASS** |
| 7.16 | Failed integrity refuses | **PASS** |
| 7.17 | Schema version in path | **PASS** |

## 8. Council Review

| # | Requirement | Status |
|---|---|---|
| 8.1 | Canonical YAML + derived Markdown | **PASS** |
| 8.2 | Markdown carries ref + full hash | **PASS** |
| 8.3 | Only verified sources aggregated | **PASS** |
| 8.4 | All 22 required fields | **PASS** |
| 8.5 | All 14 submission-entry fields | **PASS** |
| 8.6 | No approval or merge authority | **PASS** |
| 8.7 | Decision block empty and pending | **PASS** |
| 8.8 | AI cannot populate decision fields | **PASS** — type-level, 5 tests |
| 8.9 | Structural agreement detection | **PASS** |
| 8.10 | Structural disagreement detection | **PASS** |
| 8.11 | No semantic contradiction detection | **PASS** |
| 8.12 | No lexical similarity matching | **PASS** |
| 8.13 | No embeddings / LLM / fuzzy matching | **PASS** |
| 8.14 | Missing providers reported | **PASS** |
| 8.15 | Latest submission by import order | **PASS** |
| 8.16 | Ambiguity flagged, never resolved | **PASS** |
| 8.17 | Scope violations prominent; human decision required | **PASS** |
| 8.18 | Four-value status vocabulary | **PASS** |
| 8.19 | Status precedence | **PASS** — 6 parametrised cases |
| 8.20 | All 12 Markdown sections | **PASS** |
| 8.21 | "has not approved…" disclaimer | **PASS** |
| 8.22 | Idempotent for unchanged sources | **PASS** |
| 8.23 | Changed sources → new version | **PASS** |
| 8.24 | Explicit shared `key`, never `finding_id` | **PASS** |
| 8.25 | `human_decision_required` always true | **PASS** |
| 8.26 | Closed schema (`extra="forbid"`) | **PASS** |
| 8.27 | Authority-bearing unknown fields rejected | **PASS** — 9 parametrised |

## 9. Event ledger

| # | Requirement | Status |
|---|---|---|
| 9.1 | JSONL at `.conclave/ledger/ledger.jsonl` | **PASS** |
| 9.2 | All 13 required fields | **PASS** |
| 9.3 | Genesis: sequence 1, null previous, correct type | **PASS** |
| 9.4 | Genesis payload identifies workspace | **PASS** |
| 9.5 | `entry_hash` excludes itself | **PASS** |
| 9.6 | Chain linkage | **PASS** |
| 9.7 | Contiguous sequence from 1 | **PASS** |
| 9.8 | Never rewrite or truncate | **PASS** |
| 9.9 | Never silently repair | **PASS** |
| 9.10 | Verify entire chain before append | **PASS** |
| 9.11 | Refuse append on failure | **PASS** |
| 9.12 | Exclusive lock | **PASS** — portable `O_EXCL` |
| 9.13 | Flush + fsync before success | **PASS** — monkeypatched test |
| 9.14 | Deterministic `event_id`; idempotent | **PASS** |
| 9.15 | Materially different events append | **PASS** |
| 9.16 | Three-value authority vocabulary | **PASS** |
| 9.17 | Operational events are `system` | **PASS** |
| 9.18 | Provider events `advisory_agent` | **PASS** |
| 9.19 | No event implies advisory approval | **PASS** — enforced + verified |
| 9.20 | All 13 bootstrap event types | **PASS** |
| 9.21 | Human decision types reserved, not implemented | **PASS** |
| 9.22 | No fabricated chronology | **PASS** |
| 9.23 | Genesis + one snapshot on init | **PASS** |
| 9.24 | Deterministic snapshot manifest | **PASS** |
| 9.25 | Honest snapshot time | **PASS** |
| 9.26 | Payload states artifacts predate instrumentation | **PASS** |
| 9.27 | Snapshot covers six artifact classes | **PASS** |
| 9.28 | KOS excluded from snapshot | **PASS** |
| 9.29 | Reference artifacts, never duplicate | **PASS** |
| 9.30 | Verification reports 12 categories | **PASS** |
| 9.31 | Exit non-zero on defect | **PASS** |
| 9.32 | Verification never repairs | **PASS** |
| 9.33 | One internal `append_event` API | **PASS** |
| 9.34 | No generic user-facing append command | **PASS** |
| 9.35 | Partial failure preserves the artifact | **PASS** — demonstrated live |
| 9.36 | Events factual, not authoritative | **PASS** — `note` on each |
| 9.37 | 26 required test cases | **PASS** |
| 9.38 | `event_id` includes actor, authority, payload | **PASS** |
| 9.39 | Different reasons append separately | **PASS** |
| 9.40 | Payload key order irrelevant | **PASS** |
| 9.41 | Timestamps excluded from identity | **PASS** |

## 10. Reconciliation

| # | Requirement | Status |
|---|---|---|
| 10.1 | `conclave ledger reconcile` | **PASS** |
| 10.2 | Not a generic append interface | **PASS** |
| 10.3 | Verifies ledger first | **PASS** |
| 10.4 | Inventories verified artifacts | **PASS** |
| 10.5 | Compares against recorded hashes | **PASS** |
| 10.6 | Appends only what artifacts establish | **PASS** |
| 10.7 | `reconciled: true` + reason | **PASS** |
| 10.8 | Artifact timestamp where available | **PASS** |
| 10.9 | Otherwise states time unknown | **PASS** |
| 10.10 | No unestablishable ordering claims | **PASS** |
| 10.11 | Refuses ambiguous reconstruction | **PASS** |
| 10.12 | Idempotent | **PASS** |
| 10.13 | Created / recorded / unresolved separated | **PASS** |
| 10.14 | Nine supported event types | **PASS** |
| 10.15 | Replacement only when record proves it | **PASS** |
| 10.16 | Rejection only when repair artifact proves it | **PASS** |
| 10.17 | Never infers human decisions | **PASS** |
| 10.18 | CLI message directs to verify + reconcile | **PASS** |

## 11. Bootstrap invariants — verified on a clean workspace

| # | Invariant | Status |
|---|---|---|
| 11.1 | KOS untouched and read-only | **PASS** |
| 11.2 | No agent merge or approval authority | **PASS** |
| 11.3 | All canonical packets immutable | **PASS** |
| 11.4 | All stored hashes verify | **PASS** |
| 11.5 | Relay prompts independent | **PASS** |
| 11.6 | Raw provider bytes preserved exactly | **PASS** |
| 11.7 | Rejected responses auditable | **PASS** |
| 11.8 | Scope evaluates declarations only | **PASS** |
| 11.9 | Council advisory and pending | **PASS** |
| 11.10 | Ledger verifies genesis → head | **PASS** |
| 11.11 | Idempotency where specified | **PASS** |

## 12. Documentation and closure

| # | Requirement | Status |
|---|---|---|
| 12.1 | Ledger help says event/audit, not decision | **PASS** |
| 12.2 | No command described as unimplemented | **PASS** — asserted by test |
| 12.3 | Each command states what it does | **PASS** — CREATE/VERIFY/PROJECT/RECONCILE/DISPLAY |
| 12.4 | README with all 13 required sections | **PASS** |
| 12.5 | End-to-end test in a temporary workspace | **PASS** |
| 12.6 | This DoD report | **PASS** |

---

## DEFERRED

Deferred by explicit instruction, not oversight:

| Item | Reason |
|---|---|
| Human decision recording | Reserved for its own increment; changes the authority model |
| `human_decision_recorded`, `action_authorised` | Types reserved, unimplemented |
| Provider API adapters | Bootstrap 0.1 is manual relay only |
| GitHub / PR automation | Out of scope |
| Trust and calibration tracking | Requires history that does not yet exist |
| Semantic comparison | Deliberately excluded |
| Web UI | Out of scope |

## FAIL

**None.**

---

## Defects found and fixed during the DoD pass

Recorded because a DoD pass that finds nothing usually means it was not really run.

**Ledger events lost to SIGPIPE.** `council review` appended its event *after*
printing its summary. Piping into `head` terminated the process before the
append, silently losing the event. Ledger recording now happens immediately
after the artifact exists, before any display output. Fixed for both council
and scope review.

**Ambiguity logic wrong (increment 4).** Forced replacement was assumed always
to create two competing prompts. Replacing a tampered file regenerates
*identical* content, so both records describe the same prompt. Now collapsed by
effective prompt hash.

**Repair request echoed the provider's own error.** Identifiers were taken from
the rejected submission, so a provider with the wrong role was told to quote
that wrong role back. Now taken from CONCLAVE's export record.

**Duplicate detection misreported rejections.** A previously *rejected*
response re-imported was reported as "already imported". Now distinguished.

**Snapshot test asserted the wrong hash.** Written expecting the packet's own
`content_hash`; the snapshot records the *file* hash, which is correct because
it must also detect tampering with the recorded hash line itself.

**Two crude test assertions.** A raw-hash test passed by coincidence on
already-canonical input; a "the string KOS never appears" invariant matched the
snapshot's own exclusion note. Both replaced with assertions that test the
actual property.

---

## Known limitations at Bootstrap 0.1

Not defects — boundaries, stated so they are not mistaken for coverage.

- **Undeclared object use is undetectable.** Scope drift reads declarations. A
  provider that touches an object and does not say so passes clean. Council
  Review, with a human reading, is the compensating control.
- **Ledger events are wired at the CLI boundary.** Calling the library directly
  records nothing. `ledger reconcile` closes such gaps.
- **Reconciliation cannot recover defect codes** for rejections; the repair
  artifact holds them as prose and they are not reconstructed as structured
  data.
- **Import order determines submission recency**, and equal timestamps are
  ambiguous by design rather than resolved by an arbitrary rule.
- **Single-operator.** The lock guards concurrent local writers; nothing
  coordinates multiple machines.
- **`conclave validate` covers Task Packets only.** Other artifacts are
  verified at read time by their own hash checks.

---

## Conclusion

All Bootstrap 0.1 requirements are **PASS**. No requirement is FAIL. Deferred
items were deferred by instruction.

The success criterion — *one instruction from Arthur becomes a traceable,
independently reviewed proposal without any model silently taking control* —
is met for the advisory half. The decision half is deliberately absent: the
decision block exists, stays pending, and cannot be populated by anything in
this codebase.

Recommended next step is to tag Bootstrap 0.1 before designing human decision
recording, so the advisory runtime has a fixed, verified baseline to attach to.
