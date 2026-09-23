# Stage 21A implementation correction 0001 — status class of a rejected HTTP response

Date: 2026-09-23
Status: CORRECTION APPLIED LOCALLY / NOT REVIEWED / NOT MERGED
Author: Claude (Claude Code session). Author-side record; not a review.

## 1. Authority

Reported to Arthur with the Stage 21C fixture-only implementation
(`INCREMENT-21C-IMPLEMENTATION-0001.md` §5). Arthur replied verbatim:

```text
fix it and keep going
```

Read as authority to correct this defect in implemented Stage 21A and continue.
It authorizes no live operation, credential use, Stage 21D, deployment,
production, KOS or IDM change, and no merge.

## 2. Defect

`execute_github_read` sealed every failure observation with
`status_class="transport" if transmitted else "none"`. A rejected HTTP response
is a failure — `project_github_responses` raises `HTTP_RESPONSE_REJECTED` for
any non-2xx page — so a real GitHub 403 or 404 was recorded as `transport`.

Stage 21A section 9 defines the status class as the class of the response
actually received (`2xx`, `3xx`, `4xx`, `5xx`), with `transport` and `none` for
failures without one. `create_success_observation` already derives the class
from the response; only the failure path did not. The frozen 21A text is
correct; the implementation did not match it.

Nothing in the repository depended on the old value: the full suite passed
unchanged after the correction, and the only prior `status_class="4xx"`
assertion was a direct unit test of `create_failure_observation`.

## 3. Correction

In `src/conclave/github_operation.py`, the failure path now derives the class
from the last retained response when one exists and is in the 2xx-5xx range,
and otherwise keeps `transport` (a failure with no usable response) or `none`
(nothing transmitted). No other behaviour, record, reason code or gate changes.

## 4. Why it mattered

The adopted Stage 21C profile §4.4 lets collection continue past a rejected
response on a branch-protection slot — the round-1 finding B2 fix, so that a
repository governed by rulesets rather than classic branch protection does not
lose the rest of its report. That rule keys on status class `4xx`. Under the
defect it could never fire through the real path: every protection rejection
stopped the cycle. The direction was conservative, so no incorrect evidence was
ever produced; the B2 benefit was simply absent.

## 5. Evidence

- `tests/test_github_foundation.py::test_coordinator_records_rejected_http_response_with_its_own_status_class`
  — a real 404 through the real signed-lease coordinator now yields
  `status_class="4xx"`, `reason_codes=("HTTP_RESPONSE_REJECTED",)`,
  `visibility="not_observed"`, with the rejected response retained as one page.
- `tests/test_github_factual.py::test_real_http_rejection_is_its_own_status_class_and_is_tolerated`
  — the same read now satisfies profile §4.4 tolerance on a PROTECTIONS slot
  and still fails it on a non-PROTECTIONS slot.
- `tests/test_github_factual.py::test_real_transport_failure_keeps_transport_class`
  — a transport failure with no usable response is still `transport` and is
  never tolerated.
- Full suite: 1,350 passed, 2 skipped (Windows / Python 3.12.10).

## 6. Scope and open items

This corrects implemented Stage 21A to match its own frozen text. It does not
amend Stage 21A, the master protocol or any frozen document, and it changes no
Stage 21A record schema, reason code, permission, endpoint or gate.

Open: review of this correction with the Stage 21C implementation; four-platform
CI; Arthur's merge decision. A reviewer should confirm that no evidence already
recorded on `main` under the old behaviour is reinterpreted by this change —
observations are immutable and no stored observation is rewritten.
