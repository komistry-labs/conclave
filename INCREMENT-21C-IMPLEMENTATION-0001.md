# Stage 21C factual PR assistant — implementation record 0001

Date: 2026-09-23
Status: FIXTURE-ONLY IMPLEMENTATION COMPLETE LOCALLY / NOT REVIEWED / NOT MERGED
Author: Claude (Claude Code session). Author-side record; not a review.

## 1. Authority and scope

Adopted profile: `INCREMENT-21C-FACTUAL-PR-ASSISTANT-PROTOCOL.md`, SHA-256
`ed45fb9f2e1dfc8d8e9f542d71b8e67678aafe1d99120f209f5cb3b1891ab962`, merged via
PR #26 (`276b0f708f124e0a242b66db1167e4699ae84575`).

Authority: after the coordinator recommended fixture-only implementation as the
next step, Arthur replied verbatim:

```text
continue next
```

Read as authority for profile §8's initial implementation only: fixture-only,
no live transport, no credentials. This implementation authorizes and performs
no live GitHub operation, credential access, GitHub App change, signing, Stage
21D, deployment, production, KOS or IDM change. It is not merged; merge is
Arthur's act under his standing instruction to be asked each time.

Branch: `feat/increment-21c-factual-assistant`, based on `main` at `276b0f7`.

## 2. Files

| File | Change |
|---|---|
| `src/conclave/github_factual.py` | new — records, plan, decision rules, coordinator |
| `src/conclave/github_foundation.py` | additive — factual API profile and PR projection extension (rule 4) |
| `src/conclave/github_operation.py` | one line — passes the profile's projection version to projection |
| `tests/test_github_factual.py` | new — 47 tests |

## 3. Stage 21A changes — exactly profile §2 rule 4

| Rule 4 | Implementation |
|---|---|
| (a) §4.2 API-profile family and projection version | `GitHubFactualApiProfile(GitHubApiProfile)` renames only `profile`, `schema_version` and `response_projection_version`; every other §4.2 field and constant is inherited unchanged. Constants `FACTUAL_API_PROFILE_SCHEMA`, `FACTUAL_RESPONSE_PROJECTION_VERSION`. |
| (b) sites binding an API-profile reference or hash (§§5.1, 5.2, 5.3, 6.1, 6.3, 6.4, 9) | All bind by content hash, so they accept the factual record unchanged. `GitHubObservation.response_projection_version` admits the factual set; both observation builders record `api_profile.response_projection_version` instead of a hard-coded 21A value. Old validators still reject the record: `GitHubApiProfile.model_validate` fails on each renamed literal (tested). |
| (c) §8/§8.1 PR contract, bounded to two fields | `project_github_json(..., projection_version=...)`; under the factual set only, `pull_request.get` adds required-key `merge_commit_sha` and `merged_by`. Missing key rejects; login/email/URLs discarded by the existing `_actor`. |
| (d) §8.2 null-identity rule, bounded to those fields | Nullable `_oid` / `_actor` forms add no reason code and do not touch `identity` or `complete`. Repository/base/head rules untouched. |

Default arguments keep every existing caller on the 21A set. The full
pre-existing suite (1,301 tests) passes unchanged.

Design note for review: subclassing means a factual profile *instance* is
accepted where a `GitHubApiProfile` is typed. Those sites compare content
hashes and now record the profile's own projection version, so no observation
is ever labelled with the 21A set under a factual profile (tested end to end).

## 4. Clause-to-code map

| Profile clause | Code in `github_factual.py` | Tests |
|---|---|---|
| §3 request record, refs `refs/heads/<tail>` validated as 21A §7.1 | `FactualRequest`, `_validate_request_ref` (reuses 21A `valid_branch`) | `test_request_rejects_non_branch_refs`, `..._purpose_fields...` |
| §3 Step / Section / Merge / report closure, nullity, stop_slot | `Step`, `Section`, `Merge`, `FactualReport` validators | every coordinator test; `test_report_persists_immutably_and_revalidates` |
| §3 coverage ordered algorithm | `derive_coverage` | branch 1-4 tests |
| §4.1 16-slot plan, 79 + 16 = 95 | `SLOTS`, `MAXIMUM_TRANSMISSIONS` (asserted at import) | `test_plan_and_budget_are_the_adopted_table` |
| §4.2 bracketing verification | slots 15-16; `derive_target` | `test_changed_and_unknown_targets` |
| §4.3 recording table | `record_result` | `test_recording_table_maps_every_result_shape` |
| §4.4 continuation and tolerance | `is_tolerated`, coordinator loop | `test_tolerance_requires_all_four_conditions`, `test_tolerated_protection_then_later_linkage_is_recorded`, `test_rate_limited_protection_stops_everything` |
| §4.5 target, matching, source binding | `pr_matches`, `verification_shows_difference`, `derive_target`, `_check_source_binding` | target tests; `test_wrong_repository_observation_is_an_error` |
| §4.6 preflight — no time validity | `preflight` | `test_preflight_*` (4 tests) |
| §5 projection extension | 21A `project_github_json` | `test_factual_pr_projection_adds_two_nullable_fields`, `test_real_21a_read_records_factual_projection_set` |
| §5.1 Merge.state table | `merge_state`, `derive_merge` | `test_merge_state_table` (8 cases) |
| §5.2 linkage and conditional slots | coordinator loop (`linkage_skip`) | post-action null/differing linkage, R4-6 initial and post-action stop tests, wrong-SHA error |
| §5.3 parents and actor comparisons | `derive_merge` | `test_actor_comparison_is_exhaustive` (5 cases), happy path, R4-5 |
| §6 storage error, no overwrite | `persist_factual_report` | persistence test; store-code test |
| §7 limitations | `LIMITATIONS` | initial report test |
| §8 fixture-only; no live or mutation path | `mode: live` refused; module imports no transport | `test_live_mode_is_refused`, `test_module_has_no_live_or_mutation_path` |

The coordinator loop is written one branch per protocol clause, in the protocol's
order, because rounds R4-5 and R4-6 of review were dropped-qualifier defects on
exactly these paths.

## 5. Finding: implemented Stage 21A records HTTP rejections as `transport`

`project_github_responses` raises `HTTP_RESPONSE_REJECTED` for any non-2xx page;
`execute_github_read` then seals the failure observation with
`status_class="transport"`. Stage 21A §9 describes status class `4xx`/`5xx` for
HTTP responses. Proven end to end by
`test_characterize_21a_records_http_rejection_as_transport_class` (a real 404
through the real signed-lease path).

Consequence: profile §4.4's tolerated-rejection path — the round-1 B2 fix that
lets a report continue past a protection 404/403 — never fires through the real
21A path today. Every protection rejection stops the cycle. That is the
conservative direction, not a hazard, but B2's intended benefit is absent.

Not changed here: correcting it is a change to merged Stage 21A code and needs
Arthur's separate authority. The fix is small (derive the status class from the
last response in the failure path) and would make the characterization test
change deliberately. The profile's §4.4 text needs no change; its fixtures
already inject the 4xx shape directly as §8 permits.

## 6. Council review 0006 residuals

| Residual | Disposition in this implementation |
|---|---|
| §4.5 raw field names vs normalized | Implemented against normalized `repository_id` / `account_id` / `hash_algorithm` |
| §4.5 "valid retained projection" | Implemented as: status 2xx, integer IDs present, or `hash_algorithm` in {sha1, sha256}; anything else is not evidence of change |
| §3 tail syntax only, not the allowlist | Implemented: `valid_branch` plus the 21A §7.1 character exclusions; `allowed_base_refs` stays 21A's check at dispatch |
| §4.6 lifetime bound as record validity | Record validity (pydantic) is checked; no time comparison at preflight |
| 401 shares class 4xx; secondary-rate-limit classification; `resolve_once()` unbounded; §6.5 two-gate | Stage 21A residuals; unchanged |
| Every 4xx gets a per-page record? | Answered by §5: the real path records `transport`, see finding |

## 7. Evidence

Local, Windows / Python 3.12.10:

- full suite **1,348 passed, 2 skipped** (1,301 pre-existing + 47 new); the
  pre-existing 1,301 also pass alone after the 21A change;
- mutation checks on four critical rules: three killed (R4-6 initial
  NOT_APPLICABLE — 20 failures; tolerate `transport` — 1; null `remaining` — 1);
  the fourth (`actor_id is not None` guard) is an equivalent mutation because a
  null `merged_by` already fails the `User` type check;
- wheel builds offline (48 members = 47 + `github_factual.py`, no test files);
  the module imports from the unpacked wheel in isolation.

Environment notes, not code defects: this worktree is owned by another Windows
account, so tests were run with pytest `--basetemp` under a directory this
account owns, and with `safe.directory` passed via process-scoped
`GIT_CONFIG_*` variables. No global configuration was changed.

Not run locally: the CI installed-wheel probe and conformance evidence (they
need the pinned `wheelhouse` from PyPI) and macOS/Linux. CI on the PR provides
them.

## 8. Open before implementation acceptance

1. Implementation review against the adopted profile (the lineage's Council
   practice), including this record's claims.
2. Arthur's decision on the §5 Stage 21A status-class finding.
3. Four-platform CI and installed-wheel probe on the PR.
4. Merge — Arthur's act, asked separately.
