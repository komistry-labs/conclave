# Stage 21C Factual PR Assistant — Council technical review 0006 (confirmation)

Date: 2026-09-21
Status: 5/5 PASS_EXACT_DRAFT / NO BROAD OR NARROW FINDING / NOT FROZEN

## Provenance and authority

Five separate Claude subagent seats (Opus), read-only, under Arthur's
determination that five same-provider seats are acceptable
(`INCREMENT-21C-FACTUAL-PROFILE-ARTHUR-DECISION-0001.md`). The coordinator
authored the corrections under review and did not vote. Seats saw no other
seat's findings.

**Rerun disclosure.** Seats 1 and 2 returned verdicts in the first run. Seats 3,
4 and 5 were terminated by an account usage limit before returning any verdict or
finding; their partial runs produced no output bearing on the review. After the
limit reset, seats 3, 4 and 5 were rerun fresh with identical instructions on the
same exact bytes, which the coordinator verified unchanged before the reruns and
again after. No seat saw another seat's findings in either run.

The tally is arithmetic and confers no approval. The Council disposition, freeze
and adoption are Arthur's acts.

```json
{"arthur_decision": {}}
```

## Exact objects

| Object | SHA-256 | Git blob | Bytes |
|---|---|---|---|
| Candidate | `ed45fb9f2e1dfc8d8e9f542d71b8e67678aafe1d99120f209f5cb3b1891ab962` | `20c6b4d3f4101f0f5d974c888bdc94612f854823` | 36,123 |
| Adoption record draft (seat 1) | `f3046039acded722999288e47c236a6c7f2ba60db05d8fbc0b9168b1a1eef623` | `fa412ff529d64212fb27b4a1aeafadab7571e061` | 10,593 |

Every seat recomputed and matched both values. Both objects byte-unchanged after
review; no tracked file changed. Seat 1 also re-verified the Stage 21A, master,
erratum, three freeze-record and two unselected-profile hashes.

## Seat returns and full trend

| Seat | R1 | R2 | R3 | R4 | R5 | **R6** |
|---|---|---|---|---|---|---|
| 1 Governance | PASS | FAIL | FAIL | FAIL | FAIL | **PASS** |
| 2 Security | PASS | PASS | FAIL | FAIL | PASS | **PASS** |
| 3 GitHub/Git | FAIL | FAIL | FAIL | FAIL | FAIL | **PASS** |
| 4 Evidence/schema | FAIL | FAIL | FAIL | FAIL | FAIL | **PASS** |
| 5 Determinism/time | FAIL | FAIL | FAIL | FAIL | PASS | **PASS** |
| Blocking findings | 3 | 11 | 12 | 7 | 4 | **0** |

Rounds 1 and 2 reviewed with Codex and Claude seats respectively; rounds 3-6
with Claude seats. Round 4 introduced the method change (record what Stage 21A
returns; never restate how it works); rounds 5 and 6 were narrow confirmation
rounds.

## Findings confirmed closed

R5-1 (fourth condition non-vacuous), R5-2 (expected_base_sha scoped), R5-3
(request refs constrained to `refs/heads/<tail>`), R5-4 (CHANGED keyed on an
actual projection difference) — each confirmed by the seat that raised it and
cross-checked by others. No regression found in any of the 8 hunks or any
unchanged section.

Independently derived by seats, not accepted from the author: budget
79 + 16 = 95 = 7×11 + 9×2; target SAME/CHANGED/UNKNOWN exclusive and exhaustive;
rule 4 site list closed against all of Stage 21A; conditional-slot dispositions
single-valued on every path; no time, clock or platform dependency; every
stop_reason, disposition and target value reachable; every §8 fixture
constructible with a determinate output; prefix persisted on every stop path;
factual-only and no-mutation boundaries intact; adoption record §9 correct.

## Non-blocking and Stage 21A residuals recorded

Carried as implementation-review notes, not blockers:

- §4.5 names raw 21A fields (`id`, `owner.id`); stored projections use
  normalized `repository_id` / `account_id`. Mapping unambiguous (seats 3, 4, 5).
- §4.5 "valid retained projection" could cite 21A §9's "valid closed
  projection" to settle a doubly anomalous case; both readings are non-SAME and
  no fixture depends on it (seats 4, 5). Underlying 21A §8.2 retention scope is a
  21A residual.
- §3 "each tail validated as in Stage 21A section 7.1" is tail syntax only; it
  does not place head_ref in `allowed_base_refs` (seats 1, 2, 3, 5).
- Whether 21A's authorization lifetime bound is record validity or time validity
  under §4.6 (seat 5).
- 21A residuals: a 401 shares class 4xx; a secondary rate limit classified as
  plain rejection would violate 21A §7.3; 21A §7.1 "ambiguous ref forms"
  undefined in text; implementation stores a raw off-enum `hash_algorithm`; the
  21A §6.5 two-gate residual; unbounded `resolve_once()`; whether 21A emits a
  per-page record for every 4xx (if not, the cycle conservatively stops).

## Disposition

5/5 PASS_EXACT_DRAFT on the exact bytes above. This record makes the candidate
eligible for Arthur's freeze and adoption through the adoption record; it does
not itself freeze, adopt, publish or authorize implementation.

## Boundary

Read-only analysis, public documentation and repository-code reads, arithmetic.
No implementation, credential, live call, commit, push, PR, merge or KOS/IDM
change occurred.
