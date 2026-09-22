# Stage 21C Factual PR Assistant — Council technical review 0004

Date: 2026-09-21
Status: 0/5 PASS_EXACT_DRAFT; 5/5 FAIL_EXACT_DRAFT / ALL FINDINGS NARROW / NOT FREEZE-READY

## Provenance and authority

Five separate Claude subagent seats (Opus), read-only, under Arthur's
determination that five same-provider seats are acceptable. The coordinator
authored the round-4 rewrite and did not vote. Seats saw no other seat's
findings. All five ran. Each finding was classified BROAD (changes across
sections or to the method), NARROW (local edit of at most one paragraph affecting
no other section) or NON-BLOCKING / 21A RESIDUAL. The tally confers no approval.

```json
{"arthur_decision": {}}
```

## Exact objects

| Object | SHA-256 | Git blob |
|---|---|---|
| Candidate | `f5f2813f62a5383e67c04f5f9e2aeea865473335a427302e310cfc74ab0b932c` | `2f0854d895885d198d88d24f234b9c6fbce30207` |
| Adoption record draft (seat 1) | `c3089072fe5b8285f452383cc7f6e1bebe35dfab45d990981ae216871b1ced8a` | `2384d42a21398fe806a1f8548074641f992db24b` |

All seats matched both. Both objects byte-unchanged after review; no tracked
file changed.

## Seat returns and trend

| Seat | R1 | R2 | R3 | R4 |
|---|---|---|---|---|
| 1 Governance | PASS | FAIL | FAIL | FAIL (2 narrow) |
| 2 Security | PASS | PASS | FAIL | FAIL (1 narrow) |
| 3 GitHub/Git | FAIL | FAIL | FAIL | FAIL (2 narrow) |
| 4 Evidence/schema | FAIL | FAIL | FAIL | FAIL (2 narrow) |
| 5 Determinism/time | FAIL | FAIL | FAIL | FAIL (2 narrow) |
| Blocking findings | 3 | 11 | 12 | **7 (9 raised, 2 duplicated)** |
| BROAD findings | — | — | — | **0** |

The tally is unchanged at 0/5, but the kind of finding changed. No seat found a
remaining claim about Stage 21A's internals to disprove. Round-3 findings
CR15-CR26 and N1-N5 were all confirmed closed or reduced to the residues below.
Seats 4 and 5 each derived every section 8 fixture as constructible.

Two of the seven (R4-5, R4-6) are regressions the rewrite introduced by dropping
a qualifier its predecessor carried.

## Blocking findings — all NARROW

**R4-1 — Rule 4(b) omits two API-profile binding sites** (seat 1, G1). 21A §6.1
(resolution request binds `api_profile_hash`, rejected as `LEASE_BINDING_MISMATCH`)
and §6.4 (provider claims and lease evidence carry every non-secret receipt field)
are missing; correction record 0004 §1 dropped §6.4 without saying so. The
closing sentence "a site not listed here is governed by this rule all the same"
contradicts "exactly" and "No other Stage 21A clause is displaced", and the
adoption record §6. *Correction:* add §§6.1 and 6.4; delete the closing sentence.

**R4-2 — Rule 4 does not identify Stage 21A by hash** (seat 1, G2). Rules 1-3
bind by SHA-256; rule 4 cites "Stage 21A" by name. *Correction:* name
`INCREMENT-21A-READ-ONLY-GITHUB-FOUNDATION.md`, SHA-256
`4493237e46c72b3b3eed8150e4994580568831e55ffa24046b5058eb4a7b0b5f` (coordinator
re-verified).

**R4-3 — §4.4 relies on unstated 21A classification of ambiguous 403s** (seat 2,
F1). 21A has no code or status class for an ambiguous 403, and never says how a
secondary-rate-limit 403 is classified. A conforming 21A can store one as 4xx
with codes exactly [HTTP_RESPONSE_REJECTED], which is tolerated. The predecessor's
fail-safe ("If its safe outcome cannot establish the exception, stop") was
removed. *Correction:* either (a) additionally require that every per-page safe
rate-limit projection (21A §9) shows `retry_after_present` false and `remaining`
greater than zero, an absent projection stopping; or (b) delete "ambiguous" and
record correct rate-limit classification as an unverified 21A residual. Seat 2
prefers (a).

**R4-4 — "base_ref is OBSERVED and matching" is undefined** (seat 3, F1; seat 4,
F2 independently). It is unclear whether the ref name or the object SHA must
match `expected_base_sha`, and a base_ref SHA mismatch is in neither the CHANGED
list nor otherwise assigned. After any merge the base moves, so every post-merge
report is affected. *Correction:* define matching; state whether the object SHA is
compared, where a mismatch goes, and that a base moved by the merge does not by
itself change the target; add a post_action fixture.

**R4-5 — parents_comparison unspecified for an initial MERGED report** (seat 3,
F2). The predecessor's "Initial reports leave comparisons UNKNOWN" was removed;
§5.3's parents rule is post_action-only. *Correction:* "In an initial report
parents_comparison is UNKNOWN," plus a fixture.

**R4-6 — §5.2's last sentence is not limited to post_action** (seat 4, F1; seat
5, F1 independently). In an initial report stopping at or before pr_after, the
conditional slots are both NOT_APPLICABLE (§5.2 paragraph 1) and NOT_ATTEMPTED
(the last sentence). Coverage is unaffected; Steps and report bytes differ.
*Correction:* begin the sentence "In post_action, if pr_after is not OBSERVED,…".

**R4-7 — Preflight time validity is unspecified** (seat 5, F2). An authorization
already expired at preflight yields an error in one implementation and a partial
report with consumed authority in another. This is the profile's own step, not
21A's. *Correction:* state that preflight checks presence, bindings and
attempt-digest non-use only, evaluating no time validity (which Stage 21A
evaluates at dispatch and §4.3 records); or the reverse with a named clock; plus a
fixture.

## Non-blocking and Stage 21A residuals

- Adoption record §9: say "the JSON values in §9" rather than "this §9 block"
  (seat 1).
- A 401 shares status class 4xx with 403/404 and meets the tolerance rule; 21A
  stores only the class. Render a tolerated FAILED as "rejected by GitHub (4xx),
  cause not recorded" (seat 2; 21A residual).
- §7's lowercase "unavailable" is rendering language, not the coverage literal
  (seat 2).
- Full request refs versus short PR-projection refs: state the normalization
  (seat 3).
- A merged PR whose fork was deleted returns `head.repo` null and stops the cycle
  under 21A §8.2 (seat 3; 21A residual).
- A no-observation result with two or more codes is unmapped; unreachable under
  21A (seat 4; optional hardening).
- A lease-evidence store failure masked by a cleanup failure is recorded as
  NO_OBSERVATION, consistent with the method; §6 "storage failure" could name
  its scope (seat 4).
- `resolve_once()` is unbounded in 21A, so cycle termination is not guaranteed
  (seat 5; liveness, 21A residual). §6 overflow can never trigger with a fixed
  plan (seat 5).
- 21A's two §6.5 gates can yield NO_OBSERVATION in one implementation and FAILED
  with NOT_SENT in another (seat 5; 21A residual).

## Verified sound

Budget 79 + 16 = 95 = 7×11 + 9×2 (four seats). 16-slot table matches 21A §7.2.
CR17 closed; CR18 closed (16-combination enumeration, no ordinary PR falls into
UNKNOWN); CR19 closed (21A retains commit `sha`); CR20-CR22 closed; CR23-CR25
closed by removal; bracketing accepted as a sound, honestly labelled weaker
claim; recording table total over conforming 21A result shapes; continuation a
pure function of stored fields; `stop_slot` nullity holds on every path; every
`stop_reason` and disposition reachable; every §8 fixture constructible;
factual-only boundary holds; rules 2 and 3 exact; adoption record CR16 and N1-N5
closed; no-mutation boundary intact.

## Boundary

Read-only analysis, arithmetic, repository-code reads. No implementation,
credential, live call, commit, push, PR, merge or KOS/IDM change. No freeze or
adoption requested; no authority decision inferred from the tally.
