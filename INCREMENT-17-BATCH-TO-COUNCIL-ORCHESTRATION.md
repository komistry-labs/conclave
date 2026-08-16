# Increment 17 — Batch-to-Council orchestration

## Status

Implemented for CONCLAVE v0.6.0. The orchestration changes only the CONCLAVE
workspace. KOS remains external and read-only.

## Frozen protocol

1. Only a sealed `execution-batch/0.1.0` stored inside the current workspace
   may be orchestrated.
2. The batch must have status `completed`; partial, failed, cancelled, or
   budget-exceeded batches are refused.
3. The exact Task Packet, Route Plan, batch, and every cited Provider Run are
   verified and cross-bound before any downstream write.
4. Every provider response is validated as a complete Handoff submission
   before the first response is converted. A malformed later response cannot
   leave an apparently completed partial orchestration.
5. Provider Runs project idempotently into raw-response evidence and immutable
   Handoff Packets, then into immutable Scope Reviews.
6. The verified Handoff and Scope set projects into the existing immutable,
   stage-aware Council Review.
7. The orchestration emits one of five derived pause states:
   `awaiting_human_decision`, `awaiting_sequential_synthesizer`,
   `blocked_by_governance`, `ambiguous_submissions`, or
   `awaiting_provider_submissions`.
8. Canonical independent waves pause for the sequential synthesizer. They are
   not presented as decision-ready.
9. The checkpoint carries `human_decision_required: true` and
   `action_execution_allowed: false` as literal schema constraints.
10. Re-running unchanged evidence verifies and returns the existing artifacts;
    it does not create new timestamps or duplicate records.
11. Operational ledger gaps may be reconciled from sealed artifacts. Human
    decisions remain excluded from reconciliation.

## Command

```powershell
conclave orchestrate batch .conclave/batches/<batch>.yaml
```

The command displays the pause state and authoritative Council Review path.
It never invokes an authority decision command and never executes an action.

## Explicit limits

- A canonical route still requires a separately executed synthesizer stage.
- The orchestrator does not invent structured Handoff data from prose.
- It does not resolve scope violations, missing providers, or ambiguity.
- It does not modify KOS, Git, pull requests, or external systems.
