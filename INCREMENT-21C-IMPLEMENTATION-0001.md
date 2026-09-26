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
| `src/conclave/github_operation.py` | passes the profile's projection version to projection; status-class correction (§5) |
| `src/conclave/github_foundation.py` | cleanup-failure correction (`INCREMENT-21A-IMPLEMENTATION-CORRECTION-0002.md`) |
| `tests/test_github_factual.py` | new — 95 tests |
| `tests/test_github_foundation.py` | Stage 21A regression tests for the §5 correction, correction 0002, and the rule-4 projection guards |

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
| §7 limitations list | `LIMITATIONS` | initial report test |
| §7 rendering duties and §4.5's age warning | **not implemented** — no display surface exists in this increment; an open obligation before any CLI or renderer ships (review 0001 §3) | none |
| §8 fixture-only; no live or mutation path | `mode: live` refused; module imports no transport | `test_live_mode_is_refused`, `test_module_has_no_live_or_mutation_path` |

The coordinator loop is written one branch per protocol clause, in the protocol's
order, because rounds R4-5 and R4-6 of review were dropped-qualifier defects on
exactly these paths.

## 5. Finding: Stage 21A recorded HTTP rejections as `transport` — corrected

Found during implementation: `execute_github_read` sealed every failure
observation as `transport`, so a real GitHub 403/404 never carried status class
`4xx`, and profile §4.4's tolerated-rejection path (the round-1 B2 fix) could
not fire through the real path. Stage 21A §9 defines the class as that of the
response actually received, so the frozen text was correct and the
implementation was not.

Arthur authorized the fix ("fix it and keep going"). It is applied and recorded
in `INCREMENT-21A-IMPLEMENTATION-CORRECTION-0001.md`: the failure path now
derives the class from the last retained response, keeping `transport` for
failures with no usable response and `none` for nothing transmitted.

The profile needed no change. With the correction, §4.4 tolerance is now
reachable end to end — proven by
`test_real_http_rejection_is_its_own_status_class_and_is_tolerated`, with
`test_real_transport_failure_keeps_transport_class` confirming transport
failures are not relabelled, and a Stage 21A-owned regression test in
`tests/test_github_foundation.py`.

## 6. Council review 0006 residuals

| Residual | Disposition in this implementation |
|---|---|
| §4.5 raw field names vs normalized | Implemented against normalized `repository_id` / `account_id` / `hash_algorithm` |
| §4.5 "valid retained projection" | Implemented as: status 2xx, integer IDs present, or `hash_algorithm` in {sha1, sha256}; anything else is not evidence of change |
| §3 tail syntax only, not the allowlist | Implemented: `valid_branch` plus the 21A §7.1 character exclusions; `allowed_base_refs` stays 21A's check at dispatch |
| §4.6 lifetime bound as record validity | Record validity (pydantic) is checked; no time comparison at preflight |
| 401 shares class 4xx; secondary-rate-limit classification; `resolve_once()` unbounded; §6.5 two-gate | Stage 21A residuals; unchanged |
| Every 4xx gets a per-page record? | Answered: the real path retains the rejected response as one page with its rate-limit projection (§5 correction evidence) |

## 7. Evidence

Local, Windows / Python 3.12.10:

- full suite **1,405 passed, 2 skipped** after implementation reviews 0001 and
  0002 and their remediation (1,301 pre-existing unchanged, the rest new);
- mutation: the author's first check sampled only four rules and was not a
  mutation-adequacy result — review 0001 seat 4 ran 51 mutants and found 34
  survivors. Review 0002 found that two of the round-1 fixes were inert or
  half-enforced (review 0002 §3). After the round-2 remediation a 62-mutant
  battery across the decision rules, record closures, the rule-4 projection
  extension and both Stage 21A corrections kills all 62. Three findings proved
  untestable from conforming Stage 21A records because 21A rejects the input
  (duplicate attempt digest; wrong `maximum_network_requests`; any binding set
  overflowing the 95-transmission plan); all three are recorded as 21A-enforced
  and their 21C guards are tested against injected records;
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
   practice), including this record's claims and the two Stage 21A corrections
   (`INCREMENT-21A-IMPLEMENTATION-CORRECTION-0001.md`, `-0002.md`). Rounds 0001
   and 0002 are recorded; round 0002's remediation is not itself reviewed and
   its test-adequacy seat did not report.
2. Four-platform CI and installed-wheel probe on the PR.
3. Merge — Arthur's act, asked separately.
