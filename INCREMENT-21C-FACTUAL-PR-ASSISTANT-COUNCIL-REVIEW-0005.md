# Stage 21C Factual PR Assistant — Council technical review 0005 (confirmation)

Date: 2026-09-21
Status: 2/5 PASS_EXACT_DRAFT; 3/5 FAIL_EXACT_DRAFT / ALL FINDINGS NARROW / NOT FREEZE-READY

## Provenance and authority

Five separate Claude subagent seats (Opus), read-only, confirmation round
focused on the round-5 hunks with a whole-document regression check, under
Arthur's five-same-provider-seat determination. The coordinator authored the
corrections and did not vote. Seats saw no other seat's findings. All five ran.
The tally confers no approval.

```json
{"arthur_decision": {}}
```

## Exact objects

| Object | SHA-256 | Git blob |
|---|---|---|
| Candidate | `ea8082e2846e6c4d75559999b89631f4769975999f11a27127012291f4aee994` | `2ee4e195c148b237d2ec7bed7f6edb110caaee4b` |
| Adoption record draft (seat 1) | `f3046039acded722999288e47c236a6c7f2ba60db05d8fbc0b9168b1a1eef623` | `fa412ff529d64212fb27b4a1aeafadab7571e061` |

All seats matched. Both objects byte-unchanged after review.

## Seat returns and trend

| Seat | R3 | R4 | R5 |
|---|---|---|---|
| 1 Governance | FAIL | FAIL | FAIL (2 narrow) |
| 2 Security | FAIL | FAIL | **PASS** |
| 3 GitHub/Git | FAIL | FAIL | FAIL (1 narrow) |
| 4 Evidence/schema | FAIL | FAIL | FAIL (1 narrow) |
| 5 Determinism/time | FAIL | FAIL | **PASS** |
| Blocking | 12 | 7 | **4 (all narrow)** |

All seven round-4 findings R4-1..R4-7 were confirmed closed by the seats owning
them. No regression was found in any unchanged section. The adoption record
draft raised no finding. The four new findings all lie in text changed this
round or in its input domain.

## Blocking findings — all NARROW

**R5-1 — Fourth tolerance condition vacuous over zero page records** (seat 1;
noted non-blocking by seats 2, 3, 5). "Every per-page record carries…" is true
for an observation with no per-page record, and "an absent projection" does not
clearly cover that case; a null `remaining` is also unaddressed. *Correction:*
require at least one per-page record; state that zero records, an absent
projection or a null remaining fails.

**R5-2 — "expected_base_sha is used only by section 5.3" contradicts §3** (seat
1). §3's prior-report equality check also uses it. *Correction:* "For report
derivation, … only by section 5.3; section 3's request-equality check is
unaffected."

**R5-3 — Request refs not constrained to `refs/heads/`** (seat 3). §4.5 strips
`refs/heads/`, but §3 allows any "Stage 21A full ref"; head_ref is never sent to
21A and is unconstrained, so a `refs/tags/x` request diverges between rejection
and a CHANGED (or even SAME) report — the ref/tag confusion 21A §12.2 guards.
*Correction:* §3 requires `refs/heads/<tail>` form validated as in 21A §7.1;
any other form is rejected before collection.

**R5-4 — CHANGED keyed on identity_match false for FAILED verification
observations** (seat 4). 21A §8.2 sets identity_match false when identity is
merely absent, and §9 leaves its value on NOT_SENT, timeout, 404 or invalid
projection unstated; a timed-out repository_after could yield CHANGED. The
profile relied on an unstated 21A resolution. *Correction:* key CHANGED on status
class 2xx and a valid retained projection showing an actual difference from the
bound repository profile.

## Non-blocking

- §6 overflow check vs §4.6 "only" preflight scope — say "and the section 6
  budget" (seat 1).
- §4.6 "no time validity" should not be read as skipping schema validation;
  21A's authorization lifetime bound is record validity (seat 5).
- Secondary rate limit with no Retry-After and remaining > 0, if classified as
  plain rejection, violates 21A §7.3 itself — 21A residual (seat 2).
- 401 shares class 4xx — 21A residual; rendering now prevents a permission claim
  (seat 2).
- Fork head repo ID not compared; deleted-fork null head.repo stops the cycle —
  21A residual (seat 3).
- 21A §6.5 two-gate residual and unbounded resolve_once() carried (seat 5).

## Verified sound

Rule 4(b) site list closed (seat 1 searched all of 21A independently); 21A hash
correct; record §9 correct; tolerance now narrower; rendering consistent with §7;
R4-7 no security defect; ref semantics checked against GitHub (short PR refs,
full ref.get ref, head.sha unchanged by any merge method); target exclusive and
exhaustive (135,000-case enumeration, overlap 0); R4-6 single-valued on every
path; no time or clock dependency; every fixture determinate; budget 95.

## Boundary

Read-only. No implementation, credential, live call, commit, push, PR, merge or
KOS/IDM change. No freeze requested; no authority inferred from the tally.
