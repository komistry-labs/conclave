# CONCLAVE v0.6.0

## Batch-to-Council orchestration

- Added `conclave orchestrate batch`.
- Added whole-batch Handoff preflight before downstream writes.
- Added idempotent Run → Handoff → Scope → Council projection.
- Added immutable orchestration checkpoint records with derived pause states.
- Added an explicit canonical-route pause for sequential synthesis.
- Added literal schema constraints that require human decision and forbid
  action execution.
- Added orchestration ledger events, snapshot coverage, and reconciliation.
- Added tests for readiness, governance blocks, malformed evidence, external
  batch injection, tampering, idempotency, synthesis gating, authority
  boundaries, CLI behavior, and ledger recovery.

## Verification

- Windows, Python 3.12: 731 tests passed.
- Debian/Linux, Python 3.13: 731 tests passed.
