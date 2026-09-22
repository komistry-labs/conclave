# Stage 21C Factual PR Assistant — correction record 0005

Date: 2026-09-21
Status: NARROW CORRECTIONS APPLIED / NOT REVIEWED / NOT FROZEN
Author: Claude (Claude Code session). Author-side record only.

Answers Council review 0004 (0/5; seven NARROW findings R4-1..R4-7; no BROAD).
Arthur directed: apply the seven, then a confirmation round.

## Identities

| Object | Predecessor | New SHA-256 | New blob | Bytes |
|---|---|---|---|---|
| Candidate | `f5f2813f…ab0b932c` | `ea8082e2846e6c4d75559999b89631f4769975999f11a27127012291f4aee994` | `2ee4e195c148b237d2ec7bed7f6edb110caaee4b` | 35,109 |
| Adoption record draft | `c3089072…1b1ced8a` | `f3046039acded722999288e47c236a6c7f2ba60db05d8fbc0b9168b1a1eef623` | `fa412ff529d64212fb27b4a1aeafadab7571e061` | 10,593 |

Predecessors copied before editing to `…-PROTOCOL-SUPERSEDED-f5f2813f.md` and
`…-ADOPTION-RECORD-SUPERSEDED-c3089072.md`. Candidate: 15 hunks. Record: 1 hunk.
No tracked file changed. Valid UTF-8, zero CR, final LF.

## Corrections — each the seat-specified minimum

- **R4-1** rule 4(b): adds 21A §6.1 (credential-resolution request) and §6.4
  (provider claims and lease evidence), both re-verified against 21A text;
  deletes "a site not listed here is governed by this rule all the same", so
  "exactly" and "No other Stage 21A clause is displaced" now hold. Record §6
  ("clauses named in rule 4") is consistent without edit.
- **R4-2** rule 4 opening names `INCREMENT-21A-READ-ONLY-GITHUB-FOUNDATION.md`,
  SHA-256 `4493237e…a0b7b0b5f` (re-verified).
- **R4-3** §4.4: seat 2's option (a). A fourth tolerance condition over data 21A
  already stores (§9 per-page safe rate-limit projection, fields per §7.3):
  retry_after_present false and remaining greater than zero on every page; an
  absent projection fails. The unfounded "ambiguous … fails" claim is removed and
  replaced by what is actually checked, plus an explicit statement that the
  profile does not otherwise verify 21A's rate-limit classification. Also folds
  seat 2's non-blocking rendering note: a tolerated FAILED is rendered as
  "rejected by GitHub (4xx), cause not recorded".
- **R4-4** §4.5: defines matching. A PR read matches on base.ref, head.ref (request
  full refs stripped of `refs/heads/`, per 21A §8.1's short PR refs versus
  ref.get's full `ref`) and head.sha = expected_head_sha; the base_ref observation
  matches on its returned ref. SAME / CHANGED / UNKNOWN restated as an exclusive
  rule. States that neither base_ref's object SHA nor PR base.sha is compared with
  expected_base_sha, so base movement — including by the merge — never changes
  target; expected_base_sha is used only by §5.3. Folds seat 3's non-blocking
  ref-normalization note. One dependent sentence ("changed head/base") is
  re-pointed to the definition.
- **R4-5** §5.3: "In an initial report parents_comparison is UNKNOWN." Restores
  what the round-4 rewrite dropped.
- **R4-6** §5.2: the sentence now begins "In post_action, …", and adds that in an
  initial report the conditional slots are NOT_APPLICABLE on every path,
  including after a stop. Restores the qualifier the rewrite dropped.
- **R4-7** §4.6 (seat 5 option A): preflight checks presence, bindings and
  attempt-digest non-use only and evaluates no time validity; 21A evaluates it at
  dispatch and §4.3 records the result. Keeps the profile time-free.

Also folded, both non-blocking in review 0004: §6 names the scope of "storage
failure" (the profile's own records or a §4.3 store code) — seat 4; adoption
record §9 says "the JSON values in this §9" — seat 1.

§8 gains a fixture for each correction.

## Author checks

Seven stale phrases confirmed at zero. Every use of "match" in the document
checked against the new §4.5 definition. SAME and CHANGED shown mutually
exclusive (SAME requires both PR reads matching and all verification slots
OBSERVED, hence identity-matched). Budget and plan unchanged (95). Not
independent evidence.

## Next gate

Confirmation round (Council review 0005): all five seats, focused on the changed
hunks with a whole-document regression check, since R4-5 and R4-6 were
regressions introduced by the previous rewrite.
