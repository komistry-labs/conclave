# Increment 10 — Provider Execution and Response Capture

Status: **FROZEN FOR IMPLEMENTATION**

Depends on: Increment 9 context, routing, provider, and accounting contracts

## 1. Purpose

Execute one authorized route stage through a provider adapter and preserve the
normalized result as a sealed, write-once Run Record.

This increment provides fixture execution only. It makes no live provider call,
stores no credential, reads no KOS object, and grants no authority.

## 2. Frozen workflow

1. Load and verify a Context Bundle and Route Plan.
2. Require both artifacts to cite the same immutable Task Packet.
3. Select an existing route stage by index.
4. Verify provider, role, adapter identity, and context classifications.
5. Enforce estimated input tokens before execution.
6. Execute exactly one adapter call.
7. Preserve the normalized response even if actual usage exceeds a ceiling.
8. Mark the run `completed` or `budget_exceeded`.
9. Seal and write the Run Record once.
10. Record the artifact in the ledger when the ledger is enabled.

No later stage may treat `budget_exceeded` as a successful predecessor.

## 3. Integrity

The Run Record binds:

- Task Packet reference;
- Context Bundle hash;
- Route Plan hash and stage index;
- provider, model, transport, and role;
- prompt hash and requested output ceiling;
- normalized response and provider-reported usage;
- start and completion timestamps;
- final run status and content hash.

Provider text is evidence, not fact and not approval.

## 4. Acceptance criteria

1. Mismatched packet, provider, role, transport, or adapter identity is refused.
2. Estimated input above the route ceiling prevents adapter execution.
3. Actual usage above a ceiling is preserved and marked `budget_exceeded`.
4. Completed responses round-trip from write-once storage.
5. Identical Run Records are idempotent; existing files are never overwritten.
6. The fixture CLI creates a run without network access.
7. Ledger and snapshot vocabulary include Run Records.
8. All prior tests continue to pass.

## 5. Deferred

- live provider SDK adapters and credentials;
- retry, rate-limit, timeout, cancellation, and concurrency engine;
- automatic Handoff Packet conversion;
- multi-stage run orchestration;
- live egress authorization.
