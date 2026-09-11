# CONCLAVE Stage 21C Council Review 0001

Status: `5/5 FAIL_EXACT_DRAFT / REMEDIATION REQUIRED`

Review date: 2026-09-10

## 1. Exact reviewed object

- File:
  `INCREMENT-21C-EXACT-HEAD-REVIEW-AND-HUMAN-AUTHORIZED-MERGE.md`
- SHA-256:
  `5cce5525659cccea9be2d0c8ee180a3609c17cf72fa7f1bcde120b2173ccd6e1`
- Git blob: `bbec3ba2f7b6a9f50c88ad61f0192584e3c3c1e6`
- Size: `39,240` bytes
- Length: `822` LF-terminated lines
- Governing baseline:
  `HEAD == origin/main == dda5961fa4aa0c67acafac2de230e9ce9313a03e`

All five seats independently recomputed the exact draft identifiers. The
frozen Increment 21 master protocol also independently recomputed to SHA-256
`89a05211a4323db2e79d2854952b24ce033c71f357430c7ac839457ff0878d75`
and Git blob `83d8fb2cabb9d343b6a8d089d920d25dcd8c5728`.

This review records the rejected byte sequence without modifying it. Any
corrected draft is a different object and requires a new five-seat review.

## 2. Council verdicts

### Seat 1 — Governance and authority

Verdict: `FAIL_EXACT_DRAFT`

Blocking findings:

1. `github-merge-readiness/0.1.0` omits the frozen master literals
   `authority_effect: "none"` and `merge_authorized: false`.
2. The proposed mutation refers to the frozen Stage 21A generic intent even
   though that intent is Stage-21A-bound, GET-only, and read-only.
3. One immutable attempt record is incorrectly described as changing through
   multiple lifecycle states and referring to evidence that does not yet exist.
4. The executable gates do not require an explicitly authorized dedicated
   disposable target or reject KOS, IDM, CONCLAVE `main`, client, and
   production targets.
5. The merge endpoint conditionally binds only the head SHA. Exact-base and
   continuing-control races need an enforceable admission policy rather than
   an unsupported atomicity claim.

### Seat 2 — Security and abuse resistance

Verdict: `FAIL_EXACT_DRAFT`

Blocking findings:

1. The attempt/lease/result chain is causally impossible while all records are
   immutable.
2. Concurrency is scoped to an authorization tuple rather than a durable
   repository-and-PR target lock, allowing two distinct authorizations to race.
3. The no-bypass evidence does not close legacy branch-protection bypass
   allowances, disabled administrator enforcement, or other effective legacy
   bypass paths.
4. The three signature profiles are self-contained but are not pinned by a
   pre-existing governed trust-policy object; profile substitution could
   introduce a new trusted signer.
5. Fresh state is read before credential resolution, leaving avoidable work
   and a race window before transmission.
6. GraphQL pagination is name-bound and has no immutable repository/PR identity
   on every page or stable-enumeration proof.
7. The readiness non-authority literals required by the master are absent.

### Seat 3 — GitHub API and implementation feasibility

Verdict: `FAIL_EXACT_DRAFT`

Blocking findings:

1. The `160`-transmission ceiling cannot fund two maximum observation cycles,
   the merge, and mandatory proof under inherited read-retry ceilings. The
   minimum computed success-path ceiling is at least `169` before any added
   profile or ancestry read.
2. `review_requests.get` and `review_threads.graphql` cannot use the frozen
   Stage 21A authorization, operation-key, intent, attempt, lease, endpoint,
   or projection schemas. Additive Stage 21C versions are required.
3. The frozen Stage 21A PR projection discards `merge_commit_sha`, making the
   proposed success proof impossible without a Stage 21C post-merge projection.
4. Reusing the Stage 21B `core` rate mechanism does not govern GitHub's
   separate point-based GraphQL bucket. Exact `core` and `graphql` observations
   and reserves are required.
5. Latest-head-pusher independence has no closed, authenticated evidence
   source.
6. The selected synchronous merge endpoint has a head-SHA precondition but no
   expected-base precondition. The protocol must not claim otherwise.
7. The GraphQL operation lacks a complete normative HTTP, header,
   content-type, nullability, raw-type, bounded-reader, and retry contract.

Verified compatible facts include the requested-reviewers endpoint and
permission, the synchronous merge method/path/body, Contents-write permission,
and repository-object-format-aware 40/64-character OIDs.

### Seat 4 — Evidence, schema, and immutability

Verdict: `FAIL_EXACT_DRAFT`

Blocking findings:

1. “With at least” is not a closed schema. Every family needs exact
   discriminators, fields, types, bounds, nullability, ordering, enums, and
   mandatory authority/decision/membership/production effects.
2. A separately governed trust-policy must pin all three signer profiles,
   hashes, key IDs, 32-byte-key fingerprints, roles, scopes, and validity.
3. The lifecycle must be an append-only predecessor chain:
   plan → deterministic attempt ID → generic intent → merge intent → exclusive
   claim → lease evidence → transmission admission/result → terminal artifact
   → ledger event.
4. Pre-transmission blocks, transmitted rejections, ambiguous outcomes,
   reconciliation results, receipt-storage failures, terminal inventory, and
   ledger reconstruction lack exact immutable contracts.

The signature preimage ordering was independently verified as non-circular.

### Seat 5 — Cross-platform, conformance, and operations

Verdict: `FAIL_EXACT_DRAFT`

Blocking findings:

1. Frozen Stage 21A fixes `live_use_allowed` to false. Stage 21C needs an
   additive, exact, disposable-live-exercise capability overlay rather than
   weakening Stage 21A.
2. Mixed REST/GraphQL rate admission, query cost, boundary pagination, and
   separate reserves are not fully defined.
3. The attempt state machine lacks append-only crash/restart reconstruction,
   deterministic storage paths, exclusive-create behavior, and durable
   readback rules for Windows and POSIX.
4. Requiring the base ref to remain equal to the merge commit makes later
   recovery inconclusive after a benign subsequent base advance. A bounded
   compare/ancestry proof is required.
5. Acceptance evidence can be vacuous: it does not require the production
   encoder, TLS validation, bounded reader, parser, and mutation state machine
   to run through loopback; isolated installed-wheel conformance; exact-head
   and protected-main evidence; Stage 21C skip policy; complete Ed25519 vectors;
   or updated module inventories in the evidence tools.

The four-platform matrix and current locked cryptography dependency were
verified compatible.

## 3. Consolidated mandatory remediation

Before re-review, a corrected exact draft must:

1. define additive Stage 21C profiles, operation records, endpoint tables,
   projections, and live-exercise overlay without changing frozen Stage 21A;
2. provide exact closed schemas and mandatory no-authority fields;
3. introduce a pre-governed signer trust-policy anchor;
4. replace the mutable attempt with an acyclic append-only lifecycle and a
   target-wide atomic lock;
5. close legacy and ruleset bypass evidence;
6. define stable identity-bound GraphQL enumeration, exact transport/parsing,
   head-push provenance, and a post-merge PR projection;
7. publish complete REST/core and GraphQL rate arithmetic and sufficient
   request ceilings;
8. state the head-only atomic merge limitation and add a bounded exact-base
   race/control policy;
9. add bounded ancestry proof for later base advancement;
10. define complete terminal, failure, reconciliation, inventory, and ledger
    records; and
11. make cross-platform, installed-package, negative-control, network-denial,
    signature-vector, and evidence-producer tests non-vacuous.

## 4. Verified non-blocking properties

All seats agreed that the candidate has strong direction in these areas:

- readiness is distinct from authority;
- the merge request is limited to one synchronous normal merge with an exact
  head SHA and zero automatic mutation retries;
- no administrator exception or protection-lowering path is intended;
- fixed GraphQL query text prevents caller-selected query expansion;
- the embedded GraphQL query is exactly 390 UTF-8 bytes and hashes to
  `79dd4a99e5784cee3b88a1b6f63522d837102ca9ccacfd545c0a8a71b3cd1826`;
- KOS, IDM, identity, membership, deployment, and production authority remain
  outside the draft.

## 5. Review boundary

This record rejects only the exact draft identified in §1. It grants no
authority to freeze, implement, access credentials, create or install a GitHub
App, call a live GitHub endpoint, change a repository, commit, push, create a
pull request, merge, alter protection, deploy, use production, change KOS or
IDM, sign, allocate identity, or activate membership.

The next permitted action is bounded local protocol remediation followed by a
new exact-hash five-seat Council review. No rejected finding is silently
discarded.
