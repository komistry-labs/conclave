# Stage 21A implementation correction 0002 — responses dropped by a failing credential cleanup

Date: 2026-09-26
Status: CORRECTION APPLIED LOCALLY / NOT REVIEWED / NOT MERGED
Author: Claude (Claude Code session). Author-side record; not a review.

## 1. Authority

Seat 2 of Stage 21C implementation review 0001 reported this as a pre-existing
`main` behaviour and it was recorded, not fixed (review 0001 §3, "Recorded, not
fixed"). Seat 2 of review 0002 raised it again against the remediated bytes and
classified it NARROW. It was put to Arthur as one of six findings; he replied
verbatim:

```text
proceed next
```

Read as authority to carry out the remediation set out in that report, of which
this was item five. It authorizes no live operation, credential use, Stage 21D,
deployment, production, KOS or IDM change, and no merge.

This is the second correction to implemented Stage 21A in this increment. It is
separable from every Stage 21C change and can be reverted on its own.

## 2. Defect

`run_github_transport` releases the transport token and closes the credential
lease in a `finally` block, after the responses are already in hand. Both can
raise `GitHubFoundationFailure` — `CredentialEnvelope.close` raises
`CREDENTIAL_CLEANUP_FAILED` when zeroing the token or closing the pair validator
fails. That exception left the function un-wrapped, so it was not a
`GitHubOperationExecutionFailure` and carried no responses.

`execute_github_read` therefore saw no responses (its local `responses` was
still `()`, the assignment from `run_github_transport` never having completed)
and sealed the failure observation with `status_class="none"` and `pages=()`.

Stage 21A section 9 defines the status class as that of the response actually
received; section 10 reserves `none` for nothing transmitted. A completed 200
followed by a cleanup failure was recorded as if nothing had been sent.

Reproduced directly before the correction, with one 200 received and the pair
validator's `close` made to fail:

```text
status_class: none
pages: 0
reason_codes: ('CREDENTIAL_CLEANUP_FAILED',)
```

## 3. Correction

In `src/conclave/github_foundation.py`, `run_github_transport`'s `finally` now
catches a cleanup failure from either step and re-raises it as a
`GitHubOperationExecutionFailure` carrying `transmitted` and the retained
responses. The same reason code still wins over any in-flight failure, exactly
as before — only the evidence travelling with it changes.

After the correction, the same reproduction yields:

```text
status_class: 2xx
pages: 1
reason_codes: ('CREDENTIAL_CLEANUP_FAILED',)
```

The observation is still a failure observation (`complete` is false,
`visibility` is `not_observed`); no projection is admitted from it.

## 4. Why it mattered, and why it does not loosen anything

The observation now records the class of a response that really arrived, which
is what Stage 21A says it must. It does not widen Stage 21C's §4.4 tolerance:
tolerance requires `reason_codes == ("HTTP_RESPONSE_REJECTED",)` exactly, so an
observation carrying `CREDENTIAL_CLEANUP_FAILED` is refused whatever its status
class — asserted by `test_tolerance_requires_all_four_conditions`, unchanged.

The direction of the old defect was conservative in the same way as correction
0001: it understated what had been observed and never produced evidence that
was too strong. What it did lose was the record that a credential cleanup
failed *after* a real transmission, which is the case a reader most needs to
see.

## 5. Evidence

- `tests/test_github_foundation.py::test_cleanup_failure_retains_the_response_it_already_received`
  — a 200 through the real signed-lease coordinator followed by a failing pair
  validator now yields `status_class="2xx"`, one retained page, reason codes
  `("CREDENTIAL_CLEANUP_FAILED",)`, and `complete` false.
- Mutation: M19 (lease cleanup swallowed), M20 (cleanup drops responses) and
  M21 (cleanup reports `transmitted=False`) are all killed by that test.
- Full suite: 1,405 passed, 2 skipped (Windows / Python 3.12.10).

## 6. Scope and open items

This corrects implemented Stage 21A to match its own frozen text. It amends no
frozen document and changes no record schema, reason code, permission, endpoint
or gate.

Open: review of this correction; four-platform CI; Arthur's merge decision. A
reviewer should confirm, as for correction 0001, that no observation already
durable on `main` is reinterpreted — observations are immutable and none is
rewritten.
