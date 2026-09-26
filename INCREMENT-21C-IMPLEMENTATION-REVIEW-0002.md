# Stage 21C fixture-only implementation — review 0002 and remediation

Date: 2026-09-26
Status: 0/5 PASS AT REVIEW (4 SEATS RETURNED, 1 INTERRUPTED) / FINDINGS REMEDIATED / NOT RE-REVIEWED
Recorded by: Claude (Claude Code session), coordinator and author of the code
under review. Seats were five Claude subagents (Opus), read-only, same
provider — the standard Arthur accepted on 2026-09-21.

## 1. Reviewed object

Branch `feat/increment-21c-factual-assistant` at
`0cee756fbd1706e1eed023616d30c3c8d0fe515a` (PR #27), the bytes produced by
review 0001's remediation. `main` unmoved at `276b0f70`. Every returning seat
verified HEAD; no seat modified the worktree.

## 2. Verdicts

| Seat | Verdict |
|---|---|
| 1 Protocol conformance | FAIL_EXACT_IMPLEMENTATION (2 narrow, 3 non-blocking) |
| 2 Stage 21A extension and corrections | FAIL_EXACT_IMPLEMENTATION (2 narrow, 2 non-blocking) |
| 3 Fixture-only scope, security, authority | FAIL_EXACT_IMPLEMENTATION (2 narrow, 1 non-blocking) |
| 4 Test adequacy and acceptance coverage | **INTERRUPTED — returned nothing** |
| 5 Robustness, determinism, packaging | FAIL_EXACT_IMPLEMENTATION (2 narrow, 3 non-blocking) |

No finding was BROAD. No seat found the implementation wrong against the
adopted profile in a way requiring redesign.

**Seat 4 did not report.** Its remit was to re-run an independent mutation
battery of at least 40 mutants and to check review 0001's specific claims —
the 26-of-26 figure, the suite count, and the two "untestable because Stage 21A
rejects it" claims. That seat's work was not done by a reviewer. The
coordinator ran a 62-mutant battery during remediation (§5), which is
author-side evidence and not an independent adequacy verdict.

## 3. Two claims in review 0001 were false

Both were the coordinator's own descriptions of round-1 remediation. They are
corrected here and in a correction block appended to review 0001 itself; the
original text of that record is not rewritten.

**(a) "`preflight` reserves the whole plan, as §6 requires" — false.** The
added guard read

```python
reserved = sum(slot.maximum_pages + 1 for slot in SLOTS)
if budget > MAXIMUM_TRANSMISSIONS or reserved > MAXIMUM_TRANSMISSIONS:
```

`SLOTS` is a frozen module constant and that sum is character-for-character
`MAXIMUM_TRANSMISSIONS`, so the second test was `95 > 95` and the first still
saw only the supplied bindings (71 for an initial request). The clause seat 4
raised in round 1 was therefore never fixed; an inert line was added.
Seats 1, 3 and 5.

**(b) "`FactualReport.closed_report` recomputes both" `Section.sources` and
`Merge.commit_source` — half true.** Sources were recomputed. `commit_source`
was guarded by `if self.merge.commit_source is not None and ...`, which
enforces only one direction of §5.2's biconditional. Seats 1 and 5.

## 4. Findings and disposition

### Fixed in code

| Finding | Seats | Fix |
|---|---|---|
| §5.2 `commit_source` biconditional enforced in one direction only: a FAILED merge_commit with a `commit_source`, and an OBSERVED one without, both sealed | 1, 5 | closure keys on the merge_commit **Step's disposition**, not on the presence of an observation; §5.3's "null commit_source → UNKNOWN parents" is now enforced too |
| §6 plan reservation was a tautology; `BUDGET_OVERFLOW` unreachable | 1, 3, 5 | the supplied bindings' declared ceilings plus the plan allowance of every unsupplied slot, checked **before** the binding chain so a cap enlargement is reported as overflow rather than as a malformed chain |
| Malformed projections escaped as uncaught `TypeError`/`KeyError` instead of a closed code | 3 | `merged_by` missing `id`/`type`, a non-integer actor id, a non-string `merge_commit_sha` and a malformed `parents` array each raise `FactualCollectionError("RESULT_INVALID")` |
| Stage 21A: a cleanup failure after a received response sealed `status_class="none"` with `pages=()` | 2 | `INCREMENT-21A-IMPLEMENTATION-CORRECTION-0002.md` — the cleanup failure now carries the retained responses out of `run_github_transport` |

### Fixed in tests

| Finding | Seats | Fix |
|---|---|---|
| The projection-version closed-set guard and the envelope/projection invariant had **no test**; both mutants survived | 2, 5 | two tests in `tests/test_github_foundation.py`; mutants M16, M17, M18 killed |
| The §8 reachability test was defeatable — seat 3 added a live `HTTPSGitHubTransport` and a lazy publication-engine import inside a function body and all 79 tests still passed | 3 | replaced by an **AST** analysis that descends into function and class bodies, split into a per-module name check and a transitive import-closure check, plus a guard test that feeds the detectors seat 3's exact shape and asserts they fire |

The old test walked module namespaces with `vars()`, which cannot see an import
inside a function. Its docstring also claimed that "nothing this module can
reach builds a live transport", which was **false**: `github_factual` imports
`github_operation` for the `GitHubReadResult` shape, and `github_operation`
does build a live path. The replacement asserts only what is true — that
`github_factual` itself references no transport, lease or dispatch machinery at
any depth, and that no mutation module is reachable at any depth — and says so.

### Recorded, not fixed

- **§7 rendering and the §4.5 age warning still have no implementation.**
  Unchanged from review 0001: no display surface exists in this increment, and
  this remains an open obligation before any CLI or renderer ships.
- `BUDGET_OVERFLOW` **cannot fire on conforming records.** Stage 21A pins every
  authorization's `maximum_network_requests` to its endpoint's page ceiling
  plus one, and the 16-slot plan is frozen at exactly 95, so no valid binding
  set can overflow. The guard is defence against an injected binding Stage 21A
  would refuse to seal, and is tested as exactly that — the same class as the
  two findings review 0001 recorded as 21A-enforced. The code comment now says
  this instead of implying a live runtime check.
- Non-blocking, carried: an out-of-range status yielding `transport` with a
  retained page; observation sort order not enforced by the record closure;
  `ProjectionResult.projection_version`'s default failing open;
  `tools/installed_wheel_probe.py` omitting the new module (a 21B publication
  member list, extended with a 21C release); the `_HTTPS_SENTINEL` construction
  bypass (a 21A residual needing a code edit); frozenset iteration in
  `derive_target` (determinism already proven across `PYTHONHASHSEED`).
- Stage 21A residuals carried unchanged: 401 shares class 4xx; secondary
  rate-limit classification unverified by this profile; `resolve_once()`
  unbounded; the §6.5 two-gate ordering; `revalidate_instances` hardening for
  subclassed profiles.

## 5. Evidence after remediation

Local, Windows / Python 3.12.10:

- full suite **1,405 passed, 2 skipped** (1,386 before this round);
- mutation: **62 mutants, 62 killed, 0 survivors**, across the §3 coverage
  algorithm, §4.4 tolerance, §4.5 source binding and merge-SHA binding, §4.6
  preflight, §5.1/§5.2/§5.3 merge derivation, the §6 budget, the record
  closures, the rule-4 projection extension and both Stage 21A corrections. One
  further mutant was discarded for a non-unique anchor and re-run in a form
  that applied cleanly.
- The fixture-only detectors were re-checked against seat 3's demonstrated
  defeat: with the live transport and lazy publication import planted in
  `github_factual`, both new tests fail. With them removed, all pass.

Not run locally: the CI installed-wheel probe and conformance evidence (they
need the pinned `wheelhouse`) and macOS/Linux. CI on PR #27 provides them.

## 6. Provenance limits

The seats were same-provider subagents and the coordinator authored both the
code and this record. This is not independent cross-provider assurance.
**Seat 4 did not report, so test adequacy was not independently reviewed this
round**; the 62-mutant figure above is the author's own. This remediation has
not itself been reviewed. A fresh review of the remediated bytes — with the
test-adequacy seat actually completing — is the next gate, alongside
four-platform CI on PR #27.
