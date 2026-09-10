# CONCLAVE Stage 21B Implementation Review Findings 0001

## Status

FROZEN LOCAL REVIEW FINDINGS — corrections required before Council review.

Recorded: 2026-09-10

## Scope

This review evaluates the uncommitted corrected Stage 21B implementation on
`feature/increment-21b-bounded-publication`, based on protected `main` commit
`c3804e2077bfe38f66623404da51d1bd0478846b`, against the frozen Stage 21B
protocol and merged Erratum 0001. Passing implementation tests do not replace
the protocol comparison.

## Frozen findings

### P0-1 — Governing authorization chain absent

The coordinator does not require or verify the proposal manifest, publication
authorization, publication plan, generic operation intent 0.2.0, publication
intent, exclusive attempt claim, Task Packet, Handoff, scope review, base
observation, base-tree closure, provider-key evidence, credential-lease
evidence, branch-rules observation, or ruleset observation.

### P0-2 — Results compare descriptive labels, not exact GitHub identities

The rehearsal accepts caller-supplied labels such as `proposal-tree` and
`proposal-commit`. It does not prove returned blob, tree, commit, ref, or pull
request identity against the locally calculated and authorized values.

### P0-3 — Admission-without-result evidence omitted

When dispatch fails after durable admission, the terminal receipt does not
retain that admission. The required four-variant closed step-state union is
absent, breaking conservative ambiguity and crash reconciliation.

### P0-4 — Reconciliation is not governed

Reconciliation lacks its separate human authorization, intent, exclusive
claim, lease evidence, original-chain validation, terminal-artifact inventory
proof, rate admission, and durable read admission/result chain.

### P1-1 — Source observation completeness is overstated

The recursive-tree observation can carry `complete:true` without proving that
its entries reconstruct the stated root tree OID.

### P1-2 — Base-tree closure bindings are incomplete

The closure does not directly bind every source-operation authorization,
intent, claim, and lease reference/hash and does not enforce full source/base
identity equality, the 15-minute preparation window, repository-extension
identity, or source-response byte bounds.

### P1-3 — Rate evidence is insufficiently cross-bound

Rate admission checks freshness and a numeric remainder but not the repository,
API profile, account, App, installation, provider, provider key, API version,
or resource bucket against the publication chain. Per-response rate evidence
is similarly under-specified.

### P1-4 — Ambiguous ref and PR states are inaccurate

A dispatched ambiguous ref or pull-request mutation is recorded as
`NOT_ATTEMPTED` rather than `AMBIGUOUS`.

### P1-5 — Exact mutation request construction is absent

The coordinator hashes descriptive labels instead of closed canonical request
bodies for blobs, tree, commit, ref, and pull request.

### P1-6 — Acceptance evidence is incomplete

Missing evidence includes independent nested SHA-1/SHA-256 Git vectors;
executable, symlink, and submodule base entries; prefix and non-ASCII ordering;
unaffected subtree preservation; indispensable binding substitution; exact
request bodies; credential cleanup; transport attacks; terminal-failure
fallback; all receipt variants; platform path controls; and actual CI evidence
on Windows, Ubuntu, and macOS.

## Positive foundations retained

- canonical Git blob, tree, and commit hashing;
- correct API-tree-mode to Git-tree-mode serialization;
- bottom-up subtree verification;
- regular-file-only proposal overlay;
- canonical path, collision, and prohibited-path controls;
- deterministic `2F + 14` local ceiling and ten-request reserve;
- immutable exclusive record writes;
- no mutation retry in the rehearsal coordinator;
- preservation of the frozen Stage 21A endpoint table; and
- explicit refusal of a non-loopback transport.

## Disposition

`CHANGES_REQUIRED`. The implementation must not be represented as frozen,
Council-ready, push-ready, or Stage 21B-conformant until every finding above is
closed with deterministic evidence. This record grants no operational or
publication authority.
