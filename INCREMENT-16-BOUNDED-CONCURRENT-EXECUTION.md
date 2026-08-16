# Increment 16 — Bounded concurrent execution

## Status

Implemented for CONCLAVE v0.5.0. This increment changes CONCLAVE only. KOS
remains external and read-only.

## Frozen execution policy

1. Only a contiguous independent wave may execute concurrently.
2. Every earlier route stage must already have exactly one completed,
   hash-bound Provider Run.
3. Lead, critic, and verifier may enter a concurrent wave when the Route Plan
   marks them independent.
4. A synthesizer is categorically excluded from concurrent execution and must
   run sequentially after all predecessors.
5. Each stage receives only its own prompt plus the sealed Context Bundle.
   Provider responses are never relayed across concurrent workers.
6. Estimated input for the whole wave is checked before any provider call.
7. Remaining output capacity is deterministically reserved across stages
   before dispatch. Explicit per-role limits take precedence; the remainder is
   divided by ascending stage index.
8. Results are collected and persisted in ascending stage order regardless of
   completion order.
9. Retries apply only to provider-boundary failures, are capped at three
   attempts, and default to one. Validation failures are never retried.
10. Cancellation is cooperative: queued work and retries stop, while an
    already in-flight HTTP call may finish and its evidence is preserved.
11. Raw exception text is never written to the batch record. Only bounded
    error codes are retained.
12. Failed provider attempts may have consumed tokens without returning usage.
    The record sets `usage_complete: false` instead of understating certainty.

## Artifacts and ledger

Each successful provider response remains an immutable `provider-run/0.2.0`
artifact. The wave adds a sealed `execution-batch/0.1.0` manifest containing
the ordered stage outcomes, attempts, token reservations, normalized usage,
budget defects, and cancellation semantics.

The ledger records each captured Provider Run and one
`execution_batch_recorded` event. Reconciliation may reconstruct these
operational events from sealed artifacts; it still never infers a human
decision.

## Explicit limits

- No hard cancellation of an in-flight stdlib HTTP request.
- No retry cost estimate when a failed provider call returns no usage.
- No concurrency for synthesis or authority decisions.
- No cross-machine scheduler, queue service, provider login, or GitHub action.
