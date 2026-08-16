# CONCLAVE v0.4.0

## Authority-safe decision recording

- Added a strict principal-authored decision instruction schema.
- Added separate write-once YAML and Markdown Authority Decision Records bound
  to verified Council Review and Task Packet hashes.
- Added `conclave council record-decision` with mandatory exact-principal
  interactive confirmation and no unattended bypass.
- Added `human_decision_recorded` ledger events restricted to the configured
  human principal.
- Kept Council Review decision blocks immutable and permanently pending.
- Kept human decisions outside automatic ledger reconciliation.
- Added negative tests for wrong principals, altered or mismatched evidence,
  premature approval, conflicting decisions, invalid actions, missing ledgers,
  and provider/system authority claims.
- Windows verification: 704 tests pass on Python 3.12.

## Explicitly not included

- No execution of authorised actions.
- No KOS mutation.
- No concurrent provider orchestration.
- No provider browser login, MCP connector, or GitHub automation.
- No claim of cryptographic identity, trusted time, or multi-custodian control.
