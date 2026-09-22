# Stage 21C Factual PR Assistant — correction record 0002

Date: 2026-09-19
Status: BOUNDED CORRECTION APPLIED / NOT REVIEWED / NOT FROZEN
Author: Claude (Claude Code session), acting as author of this correction.

Closes Council technical review 0001's findings CR1, CR2 and CR3, and its two
actionable non-blocking notes. Author-side record, not a review and not an
approval. The corrected bytes have had **no** review of any kind.

---

## 1. Authority and boundary

Arthur directed five Council seats before freeze. Council technical review 0001
returned `2/5 PASS_EXACT_DRAFT / 3/5 FAIL_EXACT_DRAFT` and referred three bounded
findings back for remediation. This correction answers them and stops at the
review gate.

No implementation, commit, push, pull request, merge, credential use, live
provider call, live GitHub access, Stage 21D, production, KOS or IDM change was
performed. Files written: this record, the corrected candidate, the preserved
predecessor, and the updated Council review brief.

---

## 2. Object identities

| Object | SHA-256 | Git blob | Bytes | Lines |
|---|---|---|---|---|
| Predecessor (Council-reviewed) | `e939fe1e32ded72714db6da22823822fbd2b4eb4acc4a8dd9969eeae6b43a0d6` | `7428e43533235c71f80aa705d19766b9ffcbd98d` | 24,458 | 391 |
| **Corrected candidate** | `84c0b1e3c74370667583b14c8b0f4ebb3f1df63ad4126b3fc7f3cc5c4a12f26c` | `92d835bad36f4d9e51fe17cc8e196fa1be6e2b85` | 26,952 | 432 |

Delta: +2,494 bytes, +41 lines, nine hunks.

Encoding re-verified: valid UTF-8, no BOM, zero CR bytes, final LF present.
Local base `154394c570a9919fc00b7c00779f565f742508e2` unchanged.

### 2.1 Predecessor preservation

Applied in place at the established protocol path. The Council-reviewed bytes
were reconstructed by reversing the nine edits and verified to hash to
`e939fe1e…6b43a0d6` **byte-exactly**, then written to:

`INCREMENT-21C-FACTUAL-PR-ASSISTANT-PROTOCOL-SUPERSEDED-e939fe1e.md`

Because reversing exactly those nine substitutions reproduces the predecessor
hash, the reconstruction also proves those nine hunks are the **only**
differences. The earlier `b73676b1` predecessor remains preserved from
correction record 0001.

---

## 3. CR1 — null merge fields vs inherited completeness — CLOSED

**Finding (seat 3, G1).** §5's new `merged_by` is identity-bearing and nullable,
but Stage 21A §8.2 makes null identity-bearing objects incomplete or
identity-mismatched, and the candidate did not exempt it. An ordinary open PR
with `merged_by: null` could therefore make `pr_before` incomplete and stop all
later collection; another implementer might instead treat only the actor as
unavailable. Divergent readings were permitted.

**Correction, §5, exactly as specified.** Added explicit additive precedence over
Stage 21A §8.2: a null value in either new field does not make its observation
incomplete and does not clear target `identity_match`; only merge linkage and
actor availability change; an ordinary open PR reporting `merged_by` null is a
complete, identity-matched observation and never stops collection. Missing or
malformed fields still reject the projection, and the inherited repository, base
and head identity completeness rules are explicitly unchanged.

Scope held narrow: the exemption names only the two new informational fields and
does not touch any inherited completeness rule.

---

## 4. CR2 — attempted operation without an observation — CLOSED

**Finding (seats 4 S4-1 and 5 T1, independently).** Stage 21A §10 states that a
failure before the first transmission, where no lease-evidence record was
stored, creates **no** observation, emits only a sanitized local diagnostic, and
**leaves the pre-existing attempt claim retained**. No Step disposition could
honestly represent that: `FAILED` requires an observation, `OBSERVED` is false,
`NOT_APPLICABLE` is forbidden outside the conditional slots, and `NOT_ATTEMPTED`
misstates the attempted claim and credential work — yet §6 promises a prefix
report.

**Correction — option 1 of the minimum correction (closed branch, not a
reportless error).** Option 2 would have discarded the completed prefix, undoing
the B3 preservation fix, so the branch was added instead.

§3 changes:

- Step becomes `{slot, disposition, observation, reason}`.
- `disposition` gains `ATTEMPTED_NO_OBSERVATION`.
- `reason` is a Stage 21A §10 reason code or null, non-null exactly for that
  disposition.
- `FAILED` is clarified to include a stored `NOT_SENT` observation, which is
  Stage 21A's *other* pre-transmission branch — the one where lease evidence
  **was** stored and an observation therefore exists.
- The new disposition is scoped to exactly Stage 21A §10's no-lease-evidence,
  no-observation class; the retained claim stays consumed so later cycles cannot
  reuse it; the slot contributes no section source and always stops dispatch.

§4 change: the PROTECTIONS tolerated-failure exception is stated to require an
actual received HTTP response, so a pre-transmission failure never qualifies for
it. This prevents the new disposition from silently inheriting B2's exception.

**No new vocabulary was invented.** `reason` draws from Stage 21A §10's existing
closed reason-code set, and no Stage 21A observation is fabricated — both
explicit prohibitions in the finding.

---

## 5. CR3 — POST_MERGE_CHECKS coverage not single-valued — CLOSED

**Finding (seat 4, S4-2).** §3 required PARTIAL when a section had any source but
was incomplete, while §5 said linkage failure was "otherwise UNAVAILABLE." A
failed `merge_commit` read with a valid incomplete observation satisfied both.
Initial reports collided with §3's NOT_REQUESTED the same way.

**Correction, exactly the ordered algorithm specified.** §3 now carries one
algorithm, first match wins, explicitly stated to override nothing elsewhere and
to be overridden by nothing elsewhere:

1. POST_MERGE_CHECKS in an initial report → NOT_REQUESTED
2. otherwise, no sources → UNAVAILABLE
3. otherwise, every slot OBSERVED, identity-matched and pagination-complete →
   COMPLETE_WITHIN_ENDPOINT
4. otherwise → PARTIAL

§5's "Otherwise UNAVAILABLE" is replaced by "That constrains dispatch only; the
section's coverage value follows section 3's ordered algorithm."

**Verification.** The algorithm was executed against every branch. All are
single-valued, including the exact collision the finding names:

| Case | Coverage |
|---|---|
| Failed `merge_commit` with valid incomplete observation (CR3's case) | PARTIAL only |
| Initial report post-merge section | NOT_REQUESTED |
| Null linkage, all conditional slots inapplicable | UNAVAILABLE |
| Partial checks (one slot FAILED) | PARTIAL |
| All three slots OBSERVED | COMPLETE_WITHIN_ENDPOINT |
| PROTECTIONS with B2 tolerated rejection | PARTIAL |
| CR2 pre-transmission failure, no observation | UNAVAILABLE |

---

## 6. Non-blocking notes actioned

Both are the Council's own notes, actioned to avoid the next round re-raising
them. Neither was required for freeze-readiness.

- **Stale documentary uncertainty.** Seat 3 and the coordinator confirmed
  official GitHub documentation for `repository_hash_algorithm.get`, including
  that it accepts GitHub App installation tokens and requires **Metadata
  repository permission (read)** — consistent with Stage 21A §7.2's claim of no
  permission beyond mandatory metadata/read, which correction record 0001 had
  left open. §8 now records the documentary question as closed while keeping the
  live-preflight gate intact for the separately authorized fixture/live
  qualification. That distinction is the Council's, and it is preserved.
- **Signing deferral must not imply no cryptographic boundary.** §1 now states
  that the deferral is confined to Stage 21C human-approval signing, that Stage
  21A's signed credential-provider lease verification and key pinning are
  retained in full, and that no eventual live operation under this profile is
  credential-free.

Not actioned: the note that older frozen readiness summaries should remain
historical rather than be edited retroactively. That is guidance for
current-state records, not a change to this candidate; no frozen document was
edited.

---

## 7. What this correction does not establish

Seats 1 and 2 passed the **predecessor**. Their passes do not carry to these
bytes. The nine hunks touch §§1, 3, 4, 5 and 8 — including the supersession-
adjacent §5 precedence clause and §1's boundary statement, both within seat 1's
remit, and §4's stop rule within seat 2's remit. A fresh five-seat review is
required on the exact new bytes, not a re-run of only the three failing seats.

The verification in §5 above was performed by this correction's author against
the author's own algorithm and is not independent evidence.

One provenance caveat carried forward from the Council record itself, unchanged
and not resolved here: review 0001's seats were five Codex subagent seats of the
same provider, which that record explicitly states are "not five distinct
providers, human Council votes or independent cross-provider assurance." Whether
that satisfies the five-seat requirement for freeze is Arthur's determination,
not this record's.

**Next gate:** fresh exact-draft review of
`84c0b1e3c74370667583b14c8b0f4ebb3f1df63ad4126b3fc7f3cc5c4a12f26c` per the
updated brief. No freeze, adoption, implementation or live operation is
authorized until that review returns and Arthur acts on it.
