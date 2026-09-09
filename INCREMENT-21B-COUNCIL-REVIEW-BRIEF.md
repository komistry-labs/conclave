# CONCLAVE Stage 21B — Exact-Draft Council Review Brief

## Review object

- File: `INCREMENT-21B-BOUNDED-BRANCH-AND-PR-PUBLICATION.md`
- SHA-256: `b90c97284afec9ac7cef44fd9186b38f9e2a86630e283c593dc2ed95e88384c4`
- Git blob: `ad1adbae80847ee9d7114e49a8a3cee15143777d`
- Length: 817 lines
- State: local, uncommitted, unpushed, unfrozen

Review exactly those bytes. Do not infer implementation, credentials, live
GitHub access, publication authority, or permission to alter the draft.

Stage 21A remains outside this review. Its implementation branch is published
but has not yet completed PR review and merge. The Council may review the 21B
candidate now; Stage 21B freeze and implementation remain gated on Stage 21A
completion and separate Arthur authority.

## Common reviewer requirements

Each reviewer must:

1. independently verify the SHA-256 and Git blob;
2. read the frozen Increment 21 master protocol and this complete candidate;
3. identify any contradiction, under-bound authority, unsafe ambiguity,
   untestable requirement, or undocumented dependency;
4. treat GitHub documentation as factual input without granting authority;
5. return exactly `PASS_EXACT_DRAFT` or `BLOCK`; and
6. if blocking, name the exact section, defect, consequence, and minimum
   correction.

No conditional pass is accepted. Any byte change invalidates every pass.

## Reviewer 1 — Governance and authority

Confirm that publication is proposal-only; the configured human principal is
the sole publication authority; all Task Packet, Handoff, scope, base,
proposal, and authorization bindings are exact; and no clause implies approval,
merge, protection bypass, KOS/IDM authority, deployment, or production use.

## Reviewer 2 — Security and credentials

Review the GitHub App permission envelope, provider-authenticated lease,
credential lifetime and erasure, absence of ambient credentials and Git
helpers, fixed-origin transport, path controls, zero mutation retry, ambiguity
handling, rate-budget admission/exhaustion, prohibited endpoints, and
sentinel-secret evidence.

## Reviewer 3 — Git and GitHub correctness

Review the selected REST Git-database mechanism, local blob/tree/commit OID
reproduction, base-tree and sole-parent construction, positive branch-absence
proof, new-ref-only rule, exact response identity checks, duplicate-PR refusal,
and post-create PR verification. Confirm that no update/delete/merge path is
available.

## Reviewer 4 — Evidence and schema integrity

Review schema closure, immutable storage, content hashing, references,
exclusive claims, exact request-body hashes, lease and receipt binding, minimal
ledger payload, conflict/replay retention, ambiguous outcome evidence, and
read-only reconciliation classifications.

## Reviewer 5 — Cross-platform testability

Review Windows/Linux/macOS path and durability behavior, race/crash injection,
deterministic fixtures, TLS isolation, installed-wheel execution, archive
inventory, network denial, request ceilings, and whether every normative claim
can be proven without live GitHub access or shipped fixtures.

## Required response form

```text
Role: <one exact reviewer role>
Object SHA-256: b90c97284afec9ac7cef44fd9186b38f9e2a86630e283c593dc2ed95e88384c4
Git blob: ad1adbae80847ee9d7114e49a8a3cee15143777d
Verdict: PASS_EXACT_DRAFT | BLOCK
Findings: <none, or exact section/defect/consequence/minimum correction>
Boundary confirmation: No implementation, credential, live operation, GitHub
mutation, commit, push, PR, merge, protection change, KOS/IDM change, signing,
identity, membership, deployment, or production use is authorized.
```

## Current disposition

The review package is ready for the Council of five. Neither file is committed
or pushed. No Council verdict is asserted by this brief.
