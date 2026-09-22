# Stage 21C Factual PR Assistant — correction record 0006

Date: 2026-09-21
Status: NARROW CORRECTIONS APPLIED / NOT REVIEWED / NOT FROZEN
Author: Claude (Claude Code session). Author-side record only.

Answers Council review 0005 (2/5 PASS; four NARROW findings R5-1..R5-4). Under
the agreed stopping rule — narrow items confined to changed text — fix and
confirm again.

## Identities

| Object | Predecessor | New SHA-256 | New blob | Bytes |
|---|---|---|---|---|
| Candidate | `ea8082e2…f4aee994` | `ed45fb9f2e1dfc8d8e9f542d71b8e67678aafe1d99120f209f5cb3b1891ab962` | `20c6b4d3f4101f0f5d974c888bdc94612f854823` | 36,123 |
| Adoption record draft | unchanged | `f3046039acded722999288e47c236a6c7f2ba60db05d8fbc0b9168b1a1eef623` | `fa412ff529d64212fb27b4a1aeafadab7571e061` | 10,593 |

Predecessor copied first to `…-PROTOCOL-SUPERSEDED-ea8082e2.md`. 8 hunks. No
tracked file changed. Valid UTF-8, zero CR, final LF.

## Corrections

- **R5-1** §4.4: the fourth condition requires at least one per-page record,
  each with a projection whose retry_after_present is false and remaining is
  non-null and greater than zero; zero records, an absent projection or a null
  remaining fails. Also adopts seat 2/3/5 hardening. The explanatory sentence now
  refers to the condition instead of restating it, so there is one definition.
- **R5-2** §4.5: "For report derivation, expected_base_sha is used only by
  section 5.3; section 3's request-equality check is unaffected."
- **R5-3** §3: base_ref and head_ref must be full refs in `refs/heads/<tail>`
  form, each tail validated as in 21A §7.1 (re-verified: §7.1 accepts only a
  `refs/heads/<tail>` allowed by the repository profile); any other form is
  rejected before collection. The §4.5 stripping rule is now defined on its whole
  input domain.
- **R5-4** §4.5: CHANGED from a verification slot requires status class 2xx and
  a valid retained projection showing an actual difference — repository `id` or
  `owner.id` against the bound repository and account IDs, or `hash_algorithm`
  against `git_object_format` (field names re-verified in 21A §8.1 and in
  `github_foundation.py`). identity_match false without such a projection is
  explicitly not evidence of change.

Non-blocking, folded: §4.6 preflight scope now names record validity under §3 and
the §6 budget (seats 1, 5).

§8: fixtures for zero records and null remaining; CHANGED from a differing 2xx
verification projection and UNKNOWN from a timed-out or 404 verification slot
(replacing the identity_match-false fixture); rejection of a non-`refs/heads/`
request ref.

## Author checks

Four stale phrases at zero; every use of identity_match, the fourth condition and
`refs/heads/` checked against the new text. Not independent evidence.

## Next gate

Council review 0006, confirmation round, all five seats.
