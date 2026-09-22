# Stage 21C Factual PR Assistant — correction record 0004

Date: 2026-09-21
Status: METHOD CHANGE APPLIED / NOT REVIEWED / NOT FROZEN
Author: Claude (Claude Code session), author of this rewrite.

Answers Council review 0003 (0/5, CR15-CR26, N1-N5). Author-side record only.

## 1. Method change

Review 0003 showed the lineage diverging (2/5 → 1/5 → 0/5) and that most
findings concerned the candidate **restating Stage 21A's behaviour** and either
misstating it or exposing a point 21A leaves open. Two such misstatements were
the author's (CR24, CR26).

The rewrite applies one rule: **record what Stage 21A returns; never restate how
it works.** Every Step, stop and coverage value is now a function of results 21A
stores or emits, so a validator can recompute them from the report and the
observations it references.

Verified against 21A text and code before writing, rather than assumed:

- a 21A observation has **no top-level outcome field**; it stores `complete`, a
  status class, and **sorted unique reason codes** (§9);
- implemented 21A (`github_foundation.py`) **does not enforce** the §7.2
  five-minute profile-verification expiry, and §7.2 gives no anchor or clock —
  so delegating freshness to 21A would delegate it to nothing;
- 21A §7.3 contains the complete retry rule;
- 21A's PR projection already carries `state`, `merged`, `merged_at`,
  `closed_at` (§8.1);
- API-profile references are bound at §§5.1, 5.2 (incl. preimage), 5.3, 6.3, 9.

## 2. Identities

| Object | SHA-256 | Git blob | Bytes |
|---|---|---|---|
| Predecessor candidate (review 0003) | `d0718db3…2003bcdd` | `d8bacbab…` | 32,408 |
| **Candidate** | `f5f2813f62a5383e67c04f5f9e2aeea865473335a427302e310cfc74ab0b932c` | `2f0854d895885d198d88d24f234b9c6fbce30207` | 32,584 |
| Predecessor adoption draft | `7ce3e3b9…4f47033` | `347d5eca…` | — |
| **Adoption record draft** | `c3089072fe5b8285f452383cc7f6e1bebe35dfab45d990981ae216871b1ced8a` | `2384d42a21398fe806a1f8548074641f992db24b` | 10,580 |

Both predecessors were copied to `…-SUPERSEDED-d0718db3.md` and
`…-ADOPTION-RECORD-SUPERSEDED-7ce3e3b9.md` before editing. No tracked file
changed.

**Size did not shrink.** The author forecast a smaller document; it is flat
(+176 bytes). Removed: T0/D/E, the 300 s cycle limit, the 32 MiB aggregate, the
clock rules, restated retry. Added: the recording table, the Merge.state table,
the bracketing verification pair, the complete rule 4 list, and a structured §8.
What shrank is the number of claims about 21A's internals.

## 3. Structural changes

- **Recording table (§4.3)** keyed on returned observation / `complete` /
  emitted code. Replaces the ordered 21A-internal failure sequence. Closes
  CR21 (reason domain is 21A §10's closed set; exactly three named store codes
  go to error), CR22 (NO_OBSERVATION carries its code; `stop_slot` names the
  stopping slot), CR26 (no claim about 21A's internal order; the Step records
  what the implementation produced). ATTEMPTED_NO_OBSERVATION is renamed
  NO_OBSERVATION because it now covers any no-observation result.
- **Continuation rule (§4.4)** keyed on stored fields: tolerated iff PROTECTIONS
  slot, status class 4xx, reason codes exactly [HTTP_RESPONSE_REJECTED]; a
  tolerated FAILED does not change stop_reason. Closes CR17.
- **Bracketing verification (§4.2)**: new slots repository_after and
  object_format_after. The profile no longer depends on 21A's unanchored cache or
  any cycle deadline; the report shows repository identity before and after.
  Closes CR23, CR24, CR25 by removing the machinery they concerned. Plan: 16
  slots, 79 pages + 16 retries = 95 = 7 × 11 + 9 × 2 (recomputed from the table).
- **No cycle limits (§6)**: CR20 closed by removing the 32 MiB aggregate;
  started_at/completed_at are informational and nothing depends on them.
- **Merge.state table (§5.1)** over `state`, `merged`, `merged_at`, `merged_by`,
  every other combination UNKNOWN. Closes CR18.
- **Wrong-SHA commit (§5.2)**: a source-binding validation error returning an
  error. Closes CR19. merge_commit's parameter is now expected_merge_sha, which
  equals the dispatched SHA and matches the pre-issued authorizations.
- **LINKAGE_CHANGED** now skips only the conditional slots; dispatch continues to
  the closing verification pair.
- **Rule 4 (§2)** lists four displacement groups including §8/§8.1 (bounded to
  the two fields) and every API-profile binding site, with a closing rule for
  unlisted sites. Closes CR15.
- **Rules 2 and 3 (§2)**: rule 2 states it governs master text beyond the
  erratum's list (CR16, candidate side); rule 3 classifies Erratum §2 item 2 and
  the closing paragraph (N1) and says no method is declared conforming (N2).

## 4. Adoption record

- §1 adds Stage 21A to the documents the candidate governs, and subjects retained
  freeze-record descriptions to the candidate's §2 (CR16).
- §4.2 retains Erratum freeze record §4 items 4-5 only as statements of what the
  erratum did, not as caps (CR16).
- §6 restates Stage 21A as byte-identical with rule 4's named precedence (CR16).
- §4.1 supersedes item 5 with stated reasoning and maps items 1 and 6 to named
  candidate clauses (N5); §4.3 lists its unaffected sections (N5).
- §9: effect requires ISSUE with every field bound; DECLINE or an unbound field
  gives no effect; issued bytes may differ from the reviewed draft only in the
  Status line, §2 values and §9, bound by a new `reviewed_draft_sha256` (N3, N4).
  Records Arthur's council-standard determination.

## 5. Author checks

Removed-term sweep: 16 phrases at zero. Budget and section partition recomputed
programmatically from the table. Every new §8 fixture checked for an admissible
execution; recording-table fixtures inject 21A result shapes directly, which
tests this profile's mapping rather than 21A. A `claim_retained` field was
drafted and dropped because one of its values may be unreachable under a
conforming 21A. These checks are the author's and are not independent evidence.

## 6. Next gate

Council review 0004 on both objects above. Per the stopping rule stated to
Arthur: a pass goes to issuance; narrow residual findings go to Arthur for a
freeze-with-residuals decision; a broad failure switches the method to
fixture-first.
