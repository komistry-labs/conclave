# Stage 21C Factual PR Assistant — Council technical review 0003

Date: 2026-09-21
Status: 0/5 PASS_EXACT_DRAFT; 5/5 FAIL_EXACT_DRAFT / NOT FREEZE-READY

## Provenance and authority

Five separate Claude subagent seats (Opus), read-only, convened by the
coordinator under Arthur's determination that five same-provider seats are
acceptable (`INCREMENT-21C-FACTUAL-PROFILE-ARTHUR-DECISION-0001.md`). The
coordinator authored every correction under review and did not vote. Seats saw
no other seat's findings. All five ran. The tally is arithmetic and confers no
approval.

```json
{"arthur_decision": {}}
```

Arthur's recorded ISSUE intent for the adoption record has no effect: no
candidate has passed.

## Exact objects

| Object | SHA-256 | Git blob |
|---|---|---|
| Candidate | `d0718db30a80325177c569f01e18614f11c84fd7ace80c17f700b66e2003bcdd` | `d8bacbabca5fad53841ecea4356fdad4320e5979` |
| Adoption record draft (seat 1) | `7ce3e3b9590bcd8d8484a2450909b15ee660d65fe0e324e01c99486da4f47033` | `347d5eca9b331a622cea6b40c8544f4a0b4e3224` |

Every seat recomputed and matched. Both objects byte-unchanged after review;
`git diff --stat HEAD` empty.

## Seat returns

| Seat | R1 (Codex) | R2 (Claude) | R3 (Claude) |
|---|---|---|---|
| 1 Governance | PASS | FAIL | **FAIL** |
| 2 Security | PASS | PASS | **FAIL** |
| 3 GitHub/Git | FAIL | FAIL | **FAIL** |
| 4 Evidence/schema | FAIL | FAIL | **FAIL** |
| 5 Determinism/time | FAIL | FAIL | **FAIL** |
| Blocking findings | 3 | 11 | **12** |

## Trend finding

Three consecutive rounds have not converged: 2/5 → 1/5 → 0/5, with blocking
findings 3 → 11 → 12. Seat 2, which passed twice, now fails on text introduced
by this round's remediation.

The round-3 findings also shift in kind. Most no longer concern the factual
profile's own logic; they concern places where the candidate **restates Stage
21A's behaviour** and either misstates it or exposes a point Stage 21A leaves
open — time anchoring (CR23-CR25), where expiry is checked (CR26), the operation
window's extent (CR23), aggregate byte limits (CR20), reason-code classes
(CR21). Each time the candidate paraphrases 21A precisely, a seat correctly
demands the paraphrase be proven or closed.

### Coordinator attribution errors

Two claims in correction record 0003 attributed to Stage 21A rules it does not
contain. Seat 5 found both; the coordinator re-verified them:

- CR13's closure cited 21A §5.2 as placing authorization/intent validation
  before claim creation. §5.2 says only that malformed attempt-preimage input
  "fails before claim creation." 21A checks authorization expiry at the
  evidence-commit gate (§6.5, line 505), after the claim.
- §6's profile-verification expiry E was presented as "frozen Stage 21A". 21A
  §7.2 says only "expires after five minutes", with no anchor instant or clock.

Correction record 0003 described CR13 as "derived from Stage 21A rather than
chosen." That description was wrong.

## Blocking findings

### CR15 — Rule 4's "exactly three" Stage 21A displacements is incomplete (seat 1, G1; CR6 not closed)

The §5 PR extension also displaces 21A §8's retained-facts rule for
`pull_request.get`, the §8.1 raw contract, and §8.1's "additive raw fields not
named below are discarded" rule; and the API-profile hash is bound at 21A §§5.3,
6.3, 6.4 and 9, not only §§5.1-5.2. A literal §8.1 reader discards the new
fields and §5 then rejects every PR read. Minimum correction: name those clauses
(bounded to the two fields) and every API-profile binding site, then derive "no
other clause."

### CR16 — Adoption record and candidate govern Stage 21A and master supersession in conflicting terms (seat 1, G2)

Record §1 omits Stage 21A from the candidate's governed documents; record §6
says Stage 21A "remain[s] unchanged" without carve-out; record §4.2 retains
Erratum freeze record §4 items 4-5 "in full", capping master supersession at the
erratum's list — while candidate rule 2 goes beyond that list (master §10 item 9
attestation, §6 readiness/no-bypass reservations, §12 decision 7). Minimum
correction: add Stage 21A to record §1; retain items 4-5 only as descriptions of
what the erratum did, subject to candidate rules 2 and 4; restate record §6 as
"byte-identical; named clauses receive rule 4's precedence for this profile
only."

### CR17 — §6's blanket "every such failure records OPERATION_FAILURE" overrides §4's tolerated exception (seat 2)

Item 3 routes post-transmission failures through the lead-in, including §4's
tolerated PROTECTIONS rejection, for which §4 says stop_reason is unchanged
(NONE if the plan finishes). Implementers diverge on stop_reason and possibly on
dispatch; a later LINKAGE_CHANGED or TIME_BUDGET can be masked. Introduced by
this round. Minimum correction: limit the lead-in to items 1-2; state the
tolerated case leaves stop_reason unchanged; add a fixture with a tolerated
rejection followed by a later terminating condition.

### CR18 — Merge.state mapping is open-ended (seat 3, F1)

"Contradictory PR flags (merged with open state, for example)" is not a closed
rule. Combinations such as closed/merged/null `merged_at`, or closed/unmerged
with non-null `merged_by`, map to MERGED/CLOSED_UNMERGED for one implementer and
UNKNOWN for another, changing dispatch, stop_reason and Merge. Minimum
correction: a closed decision table over `state`, `merged`, `merged_at`,
`merged_by`, with every other combination UNKNOWN; state that non-null
`merge_commit_sha` with `merged=false` is the test merge; add a fixture.

### CR19 — A `merge_commit` observation with a different SHA has no defined outcome (seat 3, F2)

21A's identity_match does not cover commit SHA (no repository ID in the
response), so an OBSERVED, complete, identity-matched commit can carry a
different SHA. CR8's wording nulls `commit_source` for it but no rule gives its
disposition or stop_reason, or says whether it is §4's "wrong source binding …
validation error". The §8 "wrong commit linkage" fixture has no determinate
output. Minimum correction: one sentence assigning it — e.g. a source-binding
validation error returning an error, not a report.

### CR20 — The 32 MiB aggregate limit has no place in the failure order (seat 4, F1)

It is not a 21A failure, cannot be pre-checked without stopping every cycle after
four operations, and must be enforced mid- or post-operation, which the
candidate does not specify. Mid-operation abort has no lawful Step disposition.
Minimum correction: state when it is checked, its disposition, nullity and
stop_reason — or remove the limit.

### CR21 — ATTEMPTED_NO_OBSERVATION's reason set is not closed; codes fall in two branches (seat 4, F2)

"Any 21A §10 code that can arise in that class" is asserted, not enumerated.
`LEASE_EVIDENCE_STORE_FAILED` is in §3's class but §6 routes storage failures to
an error; `ATTEMPT_CLAIM_CONFLICT` / `ATTEMPT_ALREADY_CLAIMED` fall under both;
`AUTHORIZATION_EXPIRED` can arise at three points. Minimum correction: enumerate
the closed subset; assign each of those four codes to exactly one of Step or
error.

### CR22 — The new pre-claim NOT_ATTEMPTED loses its reason and the stopping slot (seat 4, F3)

A mid-cycle pre-claim failure produces a Step identical to every following
NOT_ATTEMPTED slot, with null reason. Distinct histories (ambiguous-403 stop vs
tolerated rejection then pre-claim failure) produce identical records, so §4's
stop rule cannot be validated from the report. Minimum correction: a non-null
reason restricted to pre-claim codes for the stopping slot, or a closed report
member naming the stopping slot and its code.

### CR23 — The 60 s Stage 21A deadline does not bound a whole slot (seat 5, F1; CR11/CR14 not closed)

21A's 60 s window bounds the HTTP exchange (§7.1, §6.5), not claim write,
`resolve_once()`, pair validation, lease-evidence write, cleanup or observation
write; `resolve_once()` has no 21A bound. "Slots 1-2 end by T0+120" and "every
operation ends no later than E" are asserted. A slow provider can transmit after
E. §8's proof fixture is unsatisfiable. Minimum correction: either define this
profile's per-slot window from its time check through the sealed observation
with a stated overrun disposition, or add a D/E check at 21A's pre-transmission
gate for every slot with a fixed FAILED/NOT_SENT disposition.

### CR24 — E's anchor and clock are the candidate's own rule, presented as 21A (seat 5, F2)

21A gives neither. Anchoring E to second-precision UTC `created_at` can place E
before D. Minimum correction: state for this profile that the five-minute window
is measured on D's monotonic clock from slot 2's completion reading, and list it
as a narrowing in rule 4.

### CR25 — started_at / completed_at clock and rounding undefined (seat 5, F3; CR12 not fully closed)

A monotonic reading has no UTC instant. Clock, rounding, and whether the 300 s
check runs on monotonic or serialized UTC fields are open; a wall-clock step
yields a report under one implementation and an error under another. Minimum
correction: define both as wall-clock readings paired with the monotonic ones,
fix rounding, enforce 300 s on the monotonic clock only, and state the
disposition when the intervals disagree.

### CR26 — Pre-claim authorization-expiry check misattributed to 21A §5.2 (seat 5, F4; CR13 residue)

See "Coordinator attribution errors." A conforming 21A implementer creates the
claim and fails at the evidence gate (ATTEMPTED_NO_OBSERVATION, consumed claim);
another records NOT_ATTEMPTED. Minimum correction: state as this profile's own
additive rule a pre-claim validity check with disposition NOT_ATTEMPTED, and
give the disposition for expiry between claim creation and the evidence gate.

## Non-blocking (seat 1)

- N1 — rule 3 leaves Erratum §2 item 2 and the closing second sentence
  unclassified.
- N2 — "other methods … are not declared conforming" implies normal merges are;
  say no method is declared conforming.
- N3 — record §9: effect should require decision = ISSUE with all fields bound;
  a completed DECLINE is not stated.
- N4 — the issued record will differ from the reviewed draft; bind the reviewed
  draft hash and allow placeholder-only differences.
- N5 — record §4.1 retains freeze-record §5 item 5 ("complete stop before the
  external human action") asserting the candidate satisfies it, which the
  candidate does not show; map or supersede it. §4.3 omits its unaffected
  sections list.

## Verified sound

Budget (77 + 14 = 91 = 7×11 + 7×2), independently by four seats. §4 slot table
matches 21A §7.2 row by row. CR7 closed (seat 3 enumerated every Merge state ×
actor × `expected_human_id`). CR8 closed; deriving parents from `commit_source`
changes no outcome except rejecting partial parents, which is stricter. CR9
closed (seat 4 derived all four branches). CR10 closed. Factual-only boundary
holds. All freeze-record quotations in the adoption draft match source text; its
baseline-selection supersession is correctly located; the one-way binding is
sound. No-mutation boundary intact. GitHub facts re-verified.

## Boundary

Read-only analysis, public documentation reads, arithmetic only. No
implementation, credential, live call, commit, push, PR, merge or KOS/IDM change.
No freeze or adoption requested. No authority decision inferred from the tally.
