# CONCLAVE v0.5.0

## Bounded concurrent execution

- Added a real thread-based independent-review wave for lead, critic, and
  verifier stages.
- Added deterministic pre-dispatch input checks and per-stage output-token
  reservations.
- Added bounded provider-error retries, cooperative cancellation, and
  fail-fast handling.
- Added deterministic stage-ordered collection independent of completion
  order.
- Added sealed execution-batch evidence and ledger reconciliation.
- Added `conclave run concurrent-live` for the existing OpenAI, Claude, and
  Gemini live adapters under the existing principal-authored egress policy.
- Kept synthesizer execution sequential and provider submissions advisory.

## Verification

- Windows, Python 3.12: 720 tests passed.
- Debian/Linux, Python 3.13: 720 tests passed. Pytest emitted one cache-only
  warning because the mounted repository rejected `.pytest_cache` creation;
  no test failed or skipped.
