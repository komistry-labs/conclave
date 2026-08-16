# Increment 15 — Authority-safe human decision recording

## Status

Implemented for CONCLAVE v0.4.0. This increment changes CONCLAVE only. It does
not modify KOS, execute an authorised action, merge code, or grant authority to
an AI provider.

## Frozen protocol

1. A Council Review is immutable and always retains its closed
   `decision: pending` block.
2. The constitutional authority supplies a strict, closed-schema decision
   instruction.
3. CONCLAVE verifies the exact Council Review hash, its own content hash, and
   the exact stored Task Packet reference and hash.
4. `approve` is accepted only when the review status is
   `ready_for_human_review`. `reject` and `defer` cannot authorise actions.
5. The configured workspace principal must equal the configured constitutional
   authority and the instruction's `decided_by` value.
6. The operator must interactively type the exact workspace principal. There
   is no non-interactive bypass.
7. The decision is written separately as sealed canonical YAML with a Markdown
   projection. Only one materially distinct decision may exist for a Council
   Review.
8. A `human_decision_recorded` event is appended with
   `authority_level: human_principal`. The ledger independently refuses the
   event for any other authority level or actor.
9. Reconciliation never discovers or infers human decisions. An exact retry
   requires another principal confirmation and only retries the idempotent
   ledger append.

## Instruction schema

```yaml
schema_version: authority-decision-instruction/0.1.0
council_review_id: CR-...
council_review_hash: sha256:...
decision: approve # approve | revise | reject | defer
decided_by: Arthur
decided_at: 2026-08-16T10:10:00Z
rationale: The bounded evidence satisfies the acceptance criteria.
authorised_actions:
  - Create the approved bounded implementation commit.
authority_ref: Arthur approval recorded in the governing session.
```

Record it with:

```powershell
conclave council record-decision decision.yaml
```

## Security meaning

The interactive ceremony prevents accidental or provider-originated decision
recording through normal CONCLAVE paths and binds the event to the configured
principal. It is not cryptographic identity proof, authentication of the person
at the keyboard, trusted time, or multi-custodian control. The artifact records
that limitation explicitly so it cannot later be mistaken for IDM-backed
assurance.

Authorised actions are data, not execution. This increment contains no action
runner and does not treat a decision record as permission to mutate KOS.
