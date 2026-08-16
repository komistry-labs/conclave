# Increment 18 — Governed sequential synthesis

## Status

Implemented for CONCLAVE v0.7.0. The increment changes only CONCLAVE. KOS
remains external and read-only.

## Frozen protocol

1. The source must be an immutable orchestration stored in the current
   workspace and paused at `awaiting_sequential_synthesizer`.
2. The source Task Packet, Context Bundle, Route Plan, Execution Batch,
   independent Runs, Handoffs, Scope Reviews, and incomplete Council Review
   must all verify and cross-bind before a provider call.
3. The route must end in exactly one synthesizer stage. Every earlier stage
   must be present once in the completed independent batch.
4. The synthesis prompt is deterministic and carries every independent
   Handoff, its Run and Handoff hashes, and an explicit instruction to preserve
   disagreement and never claim approval.
5. Only the final route provider may synthesize. The stage executes
   sequentially through the existing fail-closed egress and cumulative token
   budget controls.
6. A malformed synthesizer response is rejected before its Run is stored or
   any downstream artifact is created.
7. A valid response becomes a new immutable Run, raw response, Handoff, Scope
   Review, Council Review, and synthesis-continuation record. No source
   artifact is edited or superseded in place.
8. Re-running the same continuation verifies and returns existing artifacts;
   it never calls the provider again. A retained Run can resume downstream
   projection after an interrupted write sequence.
9. The continuation ends only at `awaiting_human_decision`,
   `blocked_by_governance`, or `ambiguous_submissions`.
10. `human_decision_required: true` and `action_execution_allowed: false` are
    literal schema constraints. CONCLAVE cannot decide or act.
11. Ledger reconciliation may reconstruct the operational continuation event.
    It cannot infer a decision or action authorization.

## Commands

```powershell
conclave orchestrate synthesize-fixture <orchestration> `
  --instruction instruction.md --response response.md `
  --estimated-input-tokens 100

conclave orchestrate synthesize-live <orchestration> `
  --instruction instruction.md --egress-decision D7-egress.yaml `
  --model <provider-model> --estimated-input-tokens 3200
```

## Explicit limits

- Sequential synthesis is structural coordination, not semantic truth.
- The synthesizer receives governed evidence only after the independent wave
  is sealed; it never participates in that wave.
- Provider output is advisory. A completed synthesis does not approve,
  ratify, merge, write to KOS, or execute an action.
- Live execution still requires provider credentials and an exact
  principal-authored egress decision.
