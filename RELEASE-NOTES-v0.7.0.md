# CONCLAVE v0.7.0

## Governed sequential synthesis

- Added `conclave orchestrate synthesize-fixture` and `synthesize-live`.
- Added fail-closed verification of the complete independent-wave evidence
  chain before the synthesizer is called.
- Added a deterministic synthesis prompt that preserves source provenance and
  explicit disagreement.
- Added crash-safe Run reuse and whole-continuation idempotency, preventing
  accidental duplicate provider calls.
- Added immutable `synthesis-continuation/0.1.0` records.
- Added post-synthesis Handoff, Scope, Council, ledger, and reconciliation
  integration.
- Kept human decision mandatory and action execution impossible by schema.

## Repository verification

- Added GitHub Actions coverage for Windows/Python 3.12 and
  Ubuntu/Python 3.13.
- Windows, Python 3.12: 743 tests passed.
- Debian/Linux, Python 3.13: 743 tests passed.
