# CONCLAVE Stage 21C Factual PR Assistant — Exact-Draft Council Review Brief

Date: 2026-09-21
Status: REVIEW PACKAGE READY — ROUND 4 / NO COUNCIL VERDICT ASSERTED

> **Round 4 supersedes the object identities below.** Review:
> candidate `INCREMENT-21C-FACTUAL-PR-ASSISTANT-PROTOCOL.md`
> SHA-256 `f5f2813f62a5383e67c04f5f9e2aeea865473335a427302e310cfc74ab0b932c`,
> blob `2f0854d895885d198d88d24f234b9c6fbce30207`; and adoption record draft
> SHA-256 `c3089072fe5b8285f452383cc7f6e1bebe35dfab45d990981ae216871b1ced8a`,
> blob `2384d42a21398fe806a1f8548074641f992db24b`.
> Round 4 is a **method change**, not a patch: read
> `INCREMENT-21C-FACTUAL-PR-ASSISTANT-CORRECTION-RECORD-0004.md` §1 and
> `INCREMENT-21C-FACTUAL-PR-ASSISTANT-COUNCIL-REVIEW-0003.md`. Diff against
> `…-PROTOCOL-SUPERSEDED-d0718db3.md` and
> `…-ADOPTION-RECORD-SUPERSEDED-7ce3e3b9.md`. The round-3 focus below is
> historical; each seat's round-4 prompt states its focus.

## Review objects

Primary — the candidate:

- File: `INCREMENT-21C-FACTUAL-PR-ASSISTANT-PROTOCOL.md`
- SHA-256: `d0718db30a80325177c569f01e18614f11c84fd7ace80c17f700b66e2003bcdd`
- Git blob: `d8bacbabca5fad53841ecea4356fdad4320e5979`
- Size: `32,408` bytes; `517` LF-terminated lines; zero CR; final LF; no BOM
- Local base: `154394c570a9919fc00b7c00779f565f742508e2` (merge of PR #25)

Secondary — seat 1 only, for scope and consistency:

- File: `INCREMENT-21C-FACTUAL-PROFILE-ADOPTION-RECORD.md` (draft, no effect)
- SHA-256: `7ce3e3b9590bcd8d8484a2450909b15ee660d65fe0e324e01c99486da4f47033`
- Git blob: `347d5eca9b331a622cea6b40c8544f4a0b4e3224`

All verdicts apply only to these exact bytes. Any byte change invalidates every
verdict. The candidate names the adoption record by path only, so a later change
to the draft record does not change the candidate's bytes; it does invalidate
seat 1's assessment of the record.

## Round history

| Round | Object | Seats | Result | Findings |
|---|---|---|---|---|
| Council 0001 | `e939fe1e…` | 5 Codex | 2/5 PASS | CR1-CR3 |
| Council 0002 | `84c0b1e3…` | 5 Claude | 1/5 PASS | CR4-CR14 |
| Council 0003 | `d0718db3…` | — | pending | — |

Four round-2 findings were introduced by the round-1 remediation itself. No
PASS from any round carries to these bytes. All five seats run.

## Required reading

1. This brief.
2. The complete candidate.
3. Frozen Increment 21 master protocol `INCREMENT-21-GITHUB-REPOSITORY-AND-PR-ADAPTER.md`
   (`89a05211…`).
4. Frozen Erratum 0001 `INCREMENT-21-ERRATUM-0001-STAGE-21C-HUMAN-MERGE-SPLIT.md`
   (`a0fa6388…`).
5. `INCREMENT-21A-READ-ONLY-GITHUB-FOUNDATION.md` — §§3, 4.2, 5.1-5.3, 6.4, 7.2,
   8.1, 8.2, 9, 10 are load-bearing.
6. Merged freeze records, now named in the candidate's §2:
   `INCREMENT-21C-PROTOCOL-FREEZE-RECORD.md`,
   `INCREMENT-21-ERRATUM-0001-FREEZE-RECORD.md`,
   `INCREMENT-21C-CONTROL-ATTESTATION-COLLECTION-PROTOCOL-FREEZE-RECORD.md`.
7. `INCREMENT-21C-FACTUAL-PR-ASSISTANT-COUNCIL-REVIEW-0001.md` and `-0002.md`.
8. `INCREMENT-21C-FACTUAL-PR-ASSISTANT-CORRECTION-RECORD-0003.md` — author-side.
9. Predecessor preserved byte-exactly: `…-PROTOCOL-SUPERSEDED-84c0b1e3.md`.
   Diffing against it shows exactly the 14 remediation hunks.

## Provenance the Council must weigh

Every earlier finding was assessed against a different object, and every
correction since review 0002 was authored by the coordinator who convenes this
Council. Correction record 0003 states its own reasoning and its own checks;
treat both as claims to test, not as evidence.

Rounds 1 and 2 used five subagent seats of a single provider each (Codex, then
Claude). Both records state this is not five distinct providers or independent
cross-provider assurance. Whether that satisfies the five-seat requirement for
freeze is Arthur's determination and is a field in the adoption record's §9.

## Common reviewer requirements

Each reviewer must:

1. independently recompute and verify the SHA-256 and Git blob;
2. read the required documents and the complete candidate;
3. identify any contradiction, under-bound authority, unsafe ambiguity,
   untestable requirement, unreachable state, or undocumented dependency;
4. treat GitHub documentation as factual input without granting authority;
5. return exactly `PASS_EXACT_DRAFT` or `FAIL_EXACT_DRAFT`; and
6. if failing, name the exact section, defect, consequence, and minimum
   correction.

No conditional pass is accepted.

### Defect classes this lineage has repeatedly produced

- **Unreachable or dead states** — an enum member, terminal arm, or acceptance
  fixture no admissible execution can produce. Rounds C1 and CR11.
- **Two-implementer divergence** — rounds B1, B4, CR4, CR7, CR8, CR12, CR13.
- **Assertions presented as derivations** — rounds CR9, CR14.
- **Repairs that introduce new coupling** — CR7, CR9, CR10, CR11 were all
  created by the preceding remediation.

### Round 3 focus — the 14 changed hunks

Seats must test the remediation, not only the sections they own.

- **§2 preamble and adoption-record split (CR4).** Is the one-way binding sound —
  candidate names record by path, record binds candidate by hash? Is anything
  now governed by neither instrument, or by both?
- **§2 rules 3 and 4 (CR5, CR6).** Does rule 4's list of exactly three Stage 21A
  displacements match every precedence clause actually present in §5, and is
  each located at the right 21A section?
- **§5 actor rule and `commit_source` (CR7, CR8).** Is the actor rule exhaustive
  and exclusive across all Merge states? Does deriving `parents_comparison` from
  `commit_source` change any outcome relative to the predecessor?
- **§6 T0, time check, and failure order (CR11-CR14).** Is T0 a single
  determinable instant? Does removing the pre-pair check leave any gap? Is
  Stage 21A's claim-before-credential ordering correctly cited and applied, and
  is every per-slot failure given exactly one disposition? Is "E is no earlier
  than D" derived, and is the E = D case coherent?
- **§8 fixtures (CR9, CR11, CR13, CR14).** Is every fixture constructible by an
  admissible execution? Is anything the remediation made reachable left without
  a fixture?
- **Growth.** The candidate grew 20% this round. Look for coupling the author did
  not trace.

## Seat 1 — Governance, authority and supersession

Confirm the profile is factual-only, with no readiness verdict, recommendation,
approval or overall green indicator derivable, including by composition. Confirm
§2's rules name every clause of the frozen documents they displace and nothing
else, and that the retained no-mutation boundary is intact. **Also review the
adoption-record draft:** does its §4 supersede exactly the baseline-selection
effect of the three freeze records and nothing more; do its retained clauses
match what the candidate relies on; is the split between the two instruments
free of gaps and overlap; and does its §9 decision block bind what it needs to?

## Seat 2 — Security, credentials and permission semantics

Credential isolation; no mutation or review-submission path; §4's
tolerated-failure exception limited to PROTECTIONS slots with a received,
definitively non-rate-limited rejected HTTP response; no "404 means
unprotected"; §7's "permission failure means unavailable" at every coverage
value; untrusted-text handling. Confirm §6's new per-slot failure order creates
no path where a lease or authority failure is tolerated, retried, or handled
with broader credentials, and that claim consumption matches Stage 21A replay
protection.

## Seat 3 — GitHub and Git correctness

Every §4 slot against Stage 21A §7.2 row by row. Merge semantics: test-merge SHA
never treated as a merge; Merge solely from identity-matched `pr_after`; parents
arms; contradictory flags; conditional-slot branches. Verify the new actor rule
and `commit_source` rule against every Merge state, including merged with null
actor and null SHA. Verify GitHub claims against official documentation.

## Seat 4 — Evidence, schema and record algebra

Schema closure; step/section/coverage algebra total and exclusive; recompute the
budget independently. Verify the §6 failure order maps each Stage 21A §10
outcome class to exactly one Step disposition, including the new NOT_ATTEMPTED
cause for pre-claim validation failure. Verify §8's four-branch coverage
enumeration against the §3 algorithm yourself.

## Seat 5 — Determinism, time and cross-platform testability

§6's time algorithm: is T0 well-defined; do slots 1-2 (no check) and slots 3-14
(`now+60 <= D`) jointly cover all fourteen slots; is every `stop_reason` member
reachable; is "E is no earlier than D" derived rather than asserted; is the
E = D case coherent under a frozen fixture clock. Confirm the prefix is
persisted on every stop path. Confirm every §8 fixture is constructible.

## Required response form

```text
Role: <one exact reviewer role>
Object SHA-256: d0718db30a80325177c569f01e18614f11c84fd7ace80c17f700b66e2003bcdd
Git blob: d8bacbabca5fad53841ecea4356fdad4320e5979
[Seat 1 only] Adoption record SHA-256: 7ce3e3b9590bcd8d8484a2450909b15ee660d65fe0e324e01c99486da4f47033
Verdict: PASS_EXACT_DRAFT | FAIL_EXACT_DRAFT
Findings: <none, or exact section/defect/consequence/minimum correction>
Boundary confirmation: No implementation, credential, live operation, GitHub
mutation, commit, push, PR, merge, protection change, KOS/IDM change, signing,
identity, membership, deployment, or production use is authorized.
```

## Aggregation

Record verdicts in `INCREMENT-21C-FACTUAL-PR-ASSISTANT-COUNCIL-REVIEW-0003.md`.
The coordinator authored the corrections and does not vote. The tally is
arithmetic; the Council disposition is Arthur's act. Record any cross-seat
disagreement as a disagreement, not resolved by the coordinator.

## Current disposition

Package ready. Nothing committed or pushed. No verdict asserted. No freeze
authorized.
