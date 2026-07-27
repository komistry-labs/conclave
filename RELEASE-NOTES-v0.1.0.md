# CONCLAVE v0.1.0 — Bootstrap 0.1

Feature-complete advisory coordination runtime.

---

## Release facts

| | |
|---|---|
| Tag | `v0.1.0` (annotated) |
| Release commit | recorded in the annotated tag message — see note below |
| Date | 27 July 2026 |
| Tests | **517 passed, 0 failed** |
| Python (tested) | **3.10.12** |
| Python (untested) | 3.11, 3.12 and later — see *Verification gaps* |
| KOS reference | **`485f88f`**, unmodified throughout development |
| Source | ~5,100 lines · Tests ~4,500 lines |

**On the commit hash.** A commit cannot contain its own hash. The release commit
hash is recorded in the annotated `v0.1.0` tag message, created immediately
after the commit, and reported to the principal. Retrieve it with:

```
git rev-list -n 1 v0.1.0
git show v0.1.0
```

---

## What this release contains

An operator issues one instruction. CONCLAVE turns it into an immutable Task
Packet, generates one independent prompt per provider for manual relay,
preserves each reply exactly as received, validates it into a sealed Handoff
Packet, evaluates declared scope against what was granted, aggregates
everything into a Council Review that preserves disagreement, and records every
step in a hash-chained event ledger.

| Component | State |
|---|---|
| Immutable Task Packets, versioned with lineage | complete |
| Three-category validation (schema / semantic / governance) | complete |
| Independent per-provider relay prompts | complete |
| Raw response preservation + Handoff import with provenance | complete |
| Scope drift detection with containment and precedence rules | complete |
| Council Review — canonical YAML + Markdown projection | complete |
| Hash-chained event ledger, snapshot bridge, reconciliation | complete |
| Human decision recording | **deferred by design** |

Full requirement-by-requirement status: `BOOTSTRAP-0.1-DOD-REPORT.md`.

---

## Deferred items

Seven, deferred by explicit instruction rather than omission.

| # | Item | Reason |
|---|---|---|
| 1 | **Human decision recording** | Changes the authority model; reserved for its own reviewed increment against this fixed baseline |
| 2 | `human_decision_recorded`, `action_authorised` ledger events | Names reserved so nothing else claims them; deliberately unimplemented |
| 3 | Provider API adapters | Bootstrap 0.1 is manual relay only |
| 4 | GitHub / pull-request automation | Out of scope |
| 5 | Trust and calibration tracking | Requires operating history that does not yet exist |
| 6 | Semantic comparison of provider prose | Deliberately excluded; structural comparison only |
| 7 | Web UI | Out of scope |

---

## Known limitations

Boundaries, not defects. Stated so they are not mistaken for coverage.

**Undeclared object use is undetectable.** Scope drift reads `objects_touched`
and nothing else. A provider that touches an object without declaring it passes
clean. Council Review, read by a human, is the compensating control. Every
Scope Review states this in its `evaluation_basis` field.

**Ledger events are wired at the CLI boundary.** Calling the library directly
records nothing. `conclave ledger reconcile` closes such gaps deterministically.

**Reconciliation cannot recover rejection defect codes.** The repair artifact
records them as prose; they are not reconstructed as structured data.

**Submission recency is import order.** Equal `imported_at` timestamps are
reported as ambiguous rather than resolved by an arbitrary rule.

**Single operator.** The ledger lock guards concurrent writers on one machine.
Nothing coordinates multiple machines.

**`conclave validate` covers Task Packets only.** Other artifacts are verified
at read time by their own hash checks.

**Cross-provider finding comparison requires an explicit shared `key`.**
`finding_id` is provider-local — two providers both writing `F-001` have agreed
about nothing — so findings without a shared key are not compared at all.

---

## Verification gaps

Stated plainly rather than left for a user to discover.

**Only Python 3.10.12 was exercised.** The full suite passes there. It has not
been run on 3.11, 3.12 or later. `requires-python` is `>=3.10` because that is
the version actually verified. Nothing in the code targets a version-specific
feature, but untested is not verified. Run `python -m pytest` on your own
interpreter before relying on this.

**No Windows execution.** Development and testing ran on Linux. Windows
specifics — the `O_EXCL` ledger lock, path handling, CRLF checkout behaviour —
are implemented deliberately for Windows and covered by tests, but have not
been executed there.

**No real provider has been through the loop.** Every response used in testing
was constructed by the test suite. The relay prompt format has not been given
to ChatGPT, Claude or Gemini in anger, and no real provider reply has been
imported. The first genuine multi-provider run is Phase 1A's purpose.

---

## Invariants verified at release

Checked on a clean workspace via the CLI, and asserted by the end-to-end test.

- KOS untouched and read-only
- No agent holds merge or approval authority
- All canonical packets immutable
- All stored hashes verify
- Relay prompts independent — no provider sees another's content
- Raw provider bytes preserved exactly
- Rejected responses remain auditable
- Scope reviews evaluate declarations only
- Council Review remains advisory and pending
- Ledger chain verifies from genesis to head
- Repeated commands idempotent where specified

---

## Authority position

CONCLAVE proposes, coordinates and records. It does not approve, ratify,
commission or merge. The Council Review decision block admits only
`decision: pending`, with the human-decision fields typed such that no code
path in this release can populate them.

Komistry OS is external, read-only, and was not modified at any point.

---

## Next increment

Human decision recording, as Bootstrap 0.2 / Increment 8, from a branch based
on `v0.1.0`. The separation must be preserved:

```
Council Review            advisory, immutable, pending
        │
        ▼
Human Decision Record     separate principal-authored artifact,
        │                 referencing the exact Council Review hash
        ▼
Authorised Action Record  only where expressly authorised
```

The Council Review must remain unchanged. A decision is a new authority-bearing
object and a new ledger event — never written into, patched into, or re-sealed
over the review it responds to.
