# Stage 21C Factual PR Assistant — correction record 0001

Date: 2026-09-19
Status: BOUNDED CORRECTION APPLIED / NOT REVIEWED / NOT FROZEN
Author: Claude (Claude Code session), acting as author of this correction.

This record closes review 0002's findings C1 and C2. It is an author-side
correction record, not a review and not an approval. The corrected bytes have
had **no** independent review: review 0002 covered the predecessor only.

---

## 1. Authority and boundary

Arthur directed: five Council seats must review before any freeze. This
correction was performed under that direction and stops at the review gate.

No implementation, commit, push, pull request, merge, credential use, live
provider call, live GitHub access, Stage 21D, production, KOS or IDM change was
performed. The only files written were this record, the Council review brief,
review 0002, the corrected candidate, and the preserved predecessor.

---

## 2. Object identities

| Object | SHA-256 | Git blob | Bytes | Lines |
|---|---|---|---|---|
| Predecessor (reviewed by 0002) | `b73676b1bdfd67ff9e8fed70c96c67320efed5bd9ff329e14e6e8439faac0d33` | `6c5dba3a789ad8edc9d0c67daec98bc659015fb9` | 24,152 | 386 |
| **Corrected candidate** | `e939fe1e32ded72714db6da22823822fbd2b4eb4acc4a8dd9969eeae6b43a0d6` | `7428e43533235c71f80aa705d19766b9ffcbd98d` | 24,458 | 391 |

Delta: +306 bytes, +5 lines, three hunks.

Corrected candidate encoding re-verified: valid UTF-8, no BOM, zero CR bytes,
final LF present.

Local base `154394c570a9919fc00b7c00779f565f742508e2` unchanged.

### 2.1 Predecessor preservation

The correction was applied in place at the established protocol path, following
the convention used for the readiness-protocol candidates 0001-0007. The
reviewed predecessor bytes were then reconstructed by reversing the three edits
and verified to hash to `b73676b1…faac0d33` **byte-exactly**, then written to:

`INCREMENT-21C-FACTUAL-PR-ASSISTANT-PROTOCOL-SUPERSEDED-b73676b1.md`

Because reversing exactly those three string substitutions reproduces the
predecessor hash, the reconstruction also proves that those three hunks are the
**only** differences between the two candidates. No other byte changed.

---

## 3. C1 — `PROFILE_EXPIRY` unreachable — CLOSED

**Defect.** §6 defined `D` = acquisition start + 300 s and `V` = Stage 21A
profile-verification expiry taken after the first two successful operations.
21A §7.2 fixes that expiry at five minutes, and §6 forbade any cached pair from
a prior cycle, so verification always ran fresh in-cycle and
`V` = t_slot2 + 300 s with t_slot2 > 0. Therefore `V` > `D` in every admissible
cycle and `min(D,V)` was always `D`. `PROFILE_EXPIRY` was a dead `stop_reason`
member, "expiry wins a tie" required the impossible `t_slot2 == 0`, and §8
mandated an acceptance fixture for a state the protocol made unreachable.

**Correction — option 1 of review 0002, three edits.**

1. §3: `PROFILE_EXPIRY` removed from the `stop_reason` enum, leaving
   `NONE/TIME_BUDGET/OPERATION_FAILURE/LINKAGE_CHANGED`.
2. §6: `V` and `min(D,V)` removed. The text now derives the result explicitly —
   because no cached pair is accepted, slots 1-2 always execute fresh in-cycle
   and the verification expiry falls strictly later than `D`, so `D` is the sole
   binding deadline and no admitted cycle can outlive its own profile
   verification. The stop record is `TIME_BUDGET` only.
3. §8: the impossible "profile expiry" fixture is replaced by a satisfiable
   invariant — "proof that no admitted cycle can outlive its own profile
   verification" — so the concern is retained as a positive test rather than
   deleted outright.

The reasoning that made `PROFILE_EXPIRY` unreachable is now stated in the
document as the justification for `D` being sole, rather than left implicit.

---

## 4. C2 — verification-pair reservation — CLOSED

**Defect.** §6 reserved a single 60-second deadline before the verification
pair, which is two distinct 60-second logical operations, and `V` — a term in
the later-slot check — was undefined until slot 2 succeeded, leaving slot 2 in a
gap between the two rules. Not reachable as a failure, but not closed.

**Correction.** §6 now requires `now+120 <= D` before the verification pair and
states explicitly that this single check governs slots 1 and 2. Removing `V`
under C1 also removes the undefined-term gap. §8's time fixture is widened to
"insufficient time before dispatch, both before the verification pair and before
a later slot."

---

## 5. Findings deliberately not actioned

**C3 — 21A cites no documentation source for `repository_hash_algorithm.get`.**
Non-blocking and located in frozen Stage 21A, not in this candidate. Correcting
it would require amending frozen 21A, which is out of scope here and not
justified on its own. Recorded for the next occasion 21A is amended.

The endpoint itself was verified during review 0002 against
`https://docs.github.com/en/rest/repos/repos` — `GET /repos/{owner}/{repo}/hash-algorithm`
is documented and returns `hash_algorithm` as a required string enum
`sha1`/`sha256`, matching both 21A §7.2's frozen path and the installed
implementation's expected key at `github_foundation.py:2149`. §8's live-preflight
gate is therefore satisfied as to the endpoint's existence.

The gate's **remaining** element is unchanged and still open: the documentation
does not state required permissions, so 21A §7.2's claim of "none beyond
mandatory metadata/read" is unconfirmed and must be settled by the separately
authorized fixture/live qualification §8 already requires. §8's gate text was
not narrowed in this correction; a reviewer may reasonably require that.

---

## 6. What this correction does not establish

B1-B4 closure was assessed against the predecessor by review 0002. The three
hunks here do not touch the B1, B2 or B4 corrections, and touch B3's algorithm
only to remove its unreachable branch — but that assessment was made by this
correction's own author and is not independent.

No verdict carries to `e939fe1e…6b43a0d6`. Review 0002 explicitly covers
`b73676b1…faac0d33` only, and its author is the author of this correction, so it
cannot serve as the independent review of these bytes.

**Next gate:** five distinct Council seats on the exact corrected bytes, per
`INCREMENT-21C-FACTUAL-PR-ASSISTANT-COUNCIL-REVIEW-BRIEF.md`. No freeze,
adoption, implementation or live operation is authorized until that review
returns and Arthur acts on it.
