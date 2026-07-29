# CONCLAVE v0.3.0 — Governed Context Relay

Status: **RELEASE VERIFIED**

v0.3.0 closes the Phase 1B manual-relay context gap without weakening the D7
live-egress boundary.

## Added

- `conclave relay export-context`
- sealed `context-relay-export/0.1.0` manifests
- complete Context Bundle projection into stage-bound manual prompts
- Task Packet, Context Bundle, Route Plan, stage, provider, and role binding
- Handoff provenance discovery from sealed context-relay manifests
- `context_relay_prompt_exported` ledger evidence
- deterministic ledger reconciliation for missed context-relay appends

## Preserved

- no provider call occurs during export
- D7 still excludes constitutional context from live APIs
- KOS remains external and read-only
- provider outputs are never included in another provider's prompt
- all agents remain advisory
- Arthur remains the sole constitutional authority
- pricing is not embedded; provider-reported token usage remains preserved

## Compatibility

Existing Task Packets, relay prompts, Handoff Packets, Context Bundles, Route
Plans, Run Records, Council Reviews, and ledgers retain their schema versions.
The workspace bootstrap version advances to `0.3.0`; existing workspaces remain
readable.

## Verification

- Windows, Python 3.12: **689 passed**
- Debian 13 under WSL2, Python 3.13: **689 passed**
- no live provider request was made
