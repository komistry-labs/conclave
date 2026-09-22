# Stage 21C Factual PR Assistant — correction record 0003

Date: 2026-09-21
Status: BOUNDED CORRECTION APPLIED / NOT REVIEWED / NOT FROZEN
Author: Claude (Claude Code session), acting as author of this correction.

Closes Council technical review 0002's findings CR4-CR14. Author-side record,
not a review and not an approval. The corrected bytes have had no review.

## 1. Authority and boundary

Arthur selected CR4 option A: a separate Arthur-issued record supersedes the
baseline-selection effect of the three merged freeze records. Arthur directed a
draft of that record, then remediation of the remaining findings.

No implementation, commit, push, PR, merge, credential use, live provider or
GitHub call, Stage 21D, production, KOS or IDM change was performed. No tracked
file changed: `git diff --stat HEAD` is empty. Files written: this record, the
corrected candidate, the preserved predecessor, the adoption-record draft, and
the updated Council brief.

## 2. Object identities

| Object | SHA-256 | Git blob | Bytes | Lines |
|---|---|---|---|---|
| Predecessor (Council review 0002) | `84c0b1e3c74370667583b14c8b0f4ebb3f1df63ad4126b3fc7f3cc5c4a12f26c` | `92d835bad36f4d9e51fe17cc8e196fa1be6e2b85` | 26,952 | 432 |
| **Corrected candidate** | `d0718db30a80325177c569f01e18614f11c84fd7ace80c17f700b66e2003bcdd` | `d8bacbabca5fad53841ecea4356fdad4320e5979` | 32,408 | 517 |
| Adoption record (draft, no effect) | `7ce3e3b9590bcd8d8484a2450909b15ee660d65fe0e324e01c99486da4f47033` | `347d5eca9b331a622cea6b40c8544f4a0b4e3224` | — | — |

Delta: +5,456 bytes, +85 lines, 14 hunks. Encoding re-verified: valid UTF-8, no
BOM, zero CR, final LF.

The predecessor was copied to `…-PROTOCOL-SUPERSEDED-84c0b1e3.md` **before**
editing and hash-verified, rather than reconstructed afterward.

## 3. Governance findings — CR4, CR5, CR6

**Division of instruments.** The candidate's §2 governs the frozen protocol
*documents*; the adoption record governs Arthur's merged *freeze records*.
Neither restates the other. The record binds the candidate by exact hash; the
candidate names the record by path. That is the only hash binding and it runs
one way, so neither document's hash depends on the other's.

- **CR4 — CLOSED by option A.** New §2 preamble: adoption is effective only
  through the Arthur-issued adoption record, which must bind these exact bytes;
  that record, not the candidate, supersedes the baseline-selection effect of
  the three freeze records, each named by file and SHA-256; without it no §2
  rule takes effect. Rule 1's "historical" is replaced: both profiles remain
  frozen, merged and preserved, and adoption leaves them unselected, not
  rescinded. The adoption record's §4 supersedes clause by clause —
  21C protocol freeze record §5 first sentence and items 2, 3, 4, 7 (items 1, 5,
  6 and the no-mutation paragraph retained); Erratum freeze record §4 item 1
  (items 2-5 retained) with §6's conformance clause read against the erratum as
  amended by rule 3 and its fresh-review requirement retained; collection freeze
  record §5 first sentence.
- **CR5 — CLOSED.** Rule 3 now states Erratum §2 items 1 and 4 are descriptive
  of the replaced sections and carry no independent normative force; item 3 and
  the closing no-send/queue/retry/schedule statement are retained. Item 2 is
  left untouched: it is permissive to the human and requires nothing of
  CONCLAVE.
- **CR6 — CLOSED.** Rule 4 now enumerates exactly three Stage 21A clauses
  receiving additive precedence, each located by verified section: (a) §4.2's
  fixed API-profile family and `response_projection_version`; (b) the API-profile
  reference validation in §§5.1-5.2; (c) §8.2's null-identity rule, only for
  `merge_commit_sha` and `merged_by`. "No other Stage 21A clause is displaced."
  The false "only Stage 21A extension" sentence is removed.

## 4. Mechanical findings — CR7-CR14

- **CR7 — CLOSED.** One exhaustive rule: `actor_comparison` is UNKNOWN when the
  report is initial, state is not MERGED, `actor_id` is null, actor type is not
  User, or `expected_human_id` is null; otherwise SAME_ACCOUNT / DIFFERENT_ACCOUNT
  on equality. "A null or unavailable actor never yields DIFFERENT_ACCOUNT." The
  separate "Non-User actor yields UNKNOWN" sentence was folded in, so exactly one
  clause decides the value.
- **CR8 — CLOSED.** `commit_source` is the `merge_commit` reference only when
  that slot is OBSERVED, complete, identity-matched and its SHA equals
  `Merge.merge_sha`; null otherwise, including FAILED and
  ATTEMPTED_NO_OBSERVATION. `parents_comparison` now explicitly derives from
  `commit_source`, UNKNOWN when it is null.
- **CR9 — CLOSED.** §8 enumerates all four coverage branches with transmission
  state explicit; branch 3 (COMPLETE_WITHIN_ENDPOINT) now has a fixture, and
  "failed merge-commit read" is split into its pre-transmission (branch 2) and
  post-transmission (branch 4) cases.
- **CR10 — CLOSED.** "That slot remains FAILED" → "The tolerated PROTECTIONS
  slot remains FAILED". Seats 2 and 4 disagreed on whether this was a defect; the
  wording is now unambiguous under both readings.
- **CR11 — CLOSED.** The pre-pair check that could never fail is removed rather
  than restated. §6 now derives why slots 1-2 need no check — each is bounded by
  its 60 s Stage 21A deadline including retry, so both end by T0 + 120 s, inside
  D. The unconstructible "before the verification pair" fixture is removed from
  §8.
- **CR12 — CLOSED.** T0 is defined as one instant: the monotonic reading taken
  immediately after request, profile, fixed-slot-attempt validation and budget
  pre-admission succeed, and immediately before slot 1 dispatch; `started_at`
  is the UTC instant of that reading; no claim, credential resolution or network
  operation precedes it. §3 points to that definition.
- **CR13 — CLOSED, derived from Stage 21A rather than chosen.** The §6
  reservation is now a time check only. After it passes, Stage 21A's frozen
  order fixes each failure's disposition, all with OPERATION_FAILURE:
  validation failure is before claim creation per 21A §5.2 ("fails before claim
  creation") → NOT_ATTEMPTED, no claim; claim creation precedes credential
  resolution per 21A §5.3 → failure before stored lease evidence is
  ATTEMPTED_NO_OBSERVATION, after stored lease evidence is FAILED with NOT_SENT;
  storage failures return an error. The implementer-A / implementer-B split
  seat 5 described cannot arise, because the ordering is 21A's, not the
  implementer's.
- **CR14 — CLOSED.** "Strictly later than D" replaced by a derivable claim: E is
  no earlier than D; every later slot starts no later than D − 60 and ends no
  later than D; so every operation starts before E and ends no later than E; the
  E = D case, reachable only under a frozen fixture clock, is admitted. §8's
  proof requirement is restated to match, including that boundary.

## 5. Checks performed before submission

Per the method committed to after round 2:

- **Blast radius.** Every normative term the edits touched — actor comparison,
  `commit_source`, `parents_comparison`, T0, `started_at`, D, E,
  OPERATION_FAILURE, TIME_BUDGET, NOT_SENT, verification — was enumerated at
  every use in the document and checked against its new definition. Nine removed
  phrases were confirmed at zero occurrences.
- **New coupling found and traced.** `parents_comparison` now depends on
  `commit_source`. Its three affected branches — differing final SHA, failed
  linkage, FAILED read — each already yielded UNKNOWN under the predecessor's
  "Missing linkage leaves comparisons UNKNOWN"; the coupling makes that explicit
  without changing any outcome.
- **Fixture constructibility.** Each new or changed §8 fixture was checked for
  an admissible execution producing it: mid-cycle authorization expiry (an
  authorization issued with expiry inside the window); E = D (frozen fixture
  clock); insufficient time before a later slot (slow earlier slots); each actor
  arm; each coverage branch. No slot number is asserted for the earliest
  time-check failure, since that would be an unverified arithmetic claim.
- **Dead states.** No enum member was added. NOT_ATTEMPTED gains a reachable
  cause (pre-claim validation failure mid-cycle).

These checks were performed by the author and are not independent evidence.

## 6. Size, and a caution

The candidate grew 20% (26,952 → 32,408 bytes), mostly in §8's fixture list and
§6's time and failure-order text. Growth is how the offline ceremony plan
failed. Here most added text replaces implicit behaviour with an explicit rule a
seat had shown was ambiguous, but the next Council should weigh whether any of it
created coupling the author did not see.

## 7. Next gate

1. Arthur reviews the adoption-record draft. Because the candidate names the
   record by path only, changes to the draft do not change the candidate's bytes.
2. A fresh five-seat review of `d0718db3…`, with seat 1 also reviewing the
   adoption-record draft for scope and consistency.

No freeze, adoption, implementation or live operation is authorized.
