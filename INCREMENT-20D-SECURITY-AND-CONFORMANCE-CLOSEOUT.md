# Increment 20D — Sandbox transport security and conformance closeout

## Status

**CANDIDATE — NOT FROZEN OR AUTHORIZED.** This document defines a proposed
security/conformance closeout after reviewed Increments 20A–20C. It authorizes
nothing by itself. Freeze, implementation, publication and merge each require
separate Arthur authorization.

20D is not a production-readiness approval and does not authorize a live
sandbox call, production broker, production credential or production trust.

## 0. Dependency and objective

20D may begin implementation only after the exact reviewed 20B and 20C heads
are present on protected `main`. Its objective is to demonstrate that the
configuration, transport, operator and recovery surfaces fail closed under
adversarial conditions, preserve secrets and exact evidence bytes, package
only the intended runtime, and retain authority-neutral semantics.

20D adds conformance evidence, tests and closeout documentation. It does not
add another transport, retry route, credential resolver, signer, key API,
trust bootstrap or production mode.

## 1. Frozen surfaces under review

The closeout must bind and review:

- the exact protected-main commit and source tree;
- the frozen 20A–20D protocol documents;
- `policies/idm-reference-pin.json` and the pinned public IDM verifier;
- all 20A profiles/diagnostics records;
- all 20B endpoint/authorization/attempt/receipt records;
- all 20C recovery authorization/attempt/disposition records;
- CLI command/help surface and installed wheel contents;
- ledger events, snapshots and reconciliation;
- dependency and workflow definitions; and
- the complete Windows/Linux/macOS test evidence.

The report shall identify 20B/20C as sandbox-only even if every check passes.

## 2. New immutable conformance record

20D adds one record type and workspace area:

```text
.conclave/signing/conformance-reports/
```

`sandbox-broker-conformance-report/0.1.0` is closed-schema, canonical JSON,
content-hashed, immutable and hash-filename-addressed. It contains only public,
secret-free evidence:

- exact CONCLAVE commit/tree and protocol document hashes;
- exact IDM pin values;
- Python/OS matrix and normalized test-suite identifiers;
- installed sdist/wheel hashes and inventories;
- dependency-lock/workflow hashes;
- named control findings with status `PASS`, `FAIL` or `NOT_RUN` and stable
  reason codes;
- hashes of machine-readable test, package and scan reports;
- explicit `live_sandbox_exercised: false` unless a separately authorized
  external exercise was performed and independently recorded;
- explicit `production_ready: false`, `production_use_allowed: false`;
- `authority_effect: none`, `decision_effect: none`,
  `membership_effect: none`, `action_execution_allowed: false`;
- diagnostic-local creation time; and
- content hash.

No report may claim PASS from missing evidence. Any unavailable required check
is `NOT_RUN` and prevents closeout PASS. The report is factual evidence, not a
self-approval or signature.

## 3. Threat and abuse matrix

Required adversarial coverage includes:

1. absolute, drive, UNC, ADS, traversal, backslash, symlink/reparse,
   directory, device and non-regular-file references;
2. DNS rebinding-style multiple answers, mixed public/private answers,
   loopback, link-local, multicast, reserved, unspecified, IPv4-mapped and
   malformed addresses;
3. proxy environment variables, redirects, alternate schemes, user-info,
   fragments, non-canonical ports and hostname/SNI/certificate mismatch;
4. TLS downgrade, untrusted CA, expired/not-yet-valid certificate, timeout,
   truncation and connection reset before/during/after send;
5. header injection, credential whitespace/control/oversize, multiple
   credential sources, bearer leakage and adapter error leakage;
6. malformed/unknown/oversized JSON records and responses, duplicate keys,
   noncanonical JSON, Unicode/order/line-ending differences and binary COSE
   preservation;
7. request, artifact, workspace, identity, MID/EID/KID, trust, verifier,
   context, time and revocation substitution;
8. stale, missing or malformed trust/revocation evidence and frozen IDM pin
   mismatch;
9. duplicate, concurrent and crash-window initial sends and recovery replays;
10. attempt/receipt/disposition deletion, corruption, orphaning, hash swap and
    ledger-before-record or record-before-ledger partial state;
11. unknown-outcome abandonment and replay semantics, including proof that a
    second ambiguous replay cannot transmit;
12. stdout, stderr, exception, log, record, ledger, temporary-directory,
    package and test-report secret sentinel scans;
13. legacy workspace compatibility and absence of silent mode/profile
    activation; and
14. absence of signing, private-key, identity-allocation, membership,
    decision-execution or production code paths in the Increment 20 surface.

No test may read B1/B2 custody material, `E:`, a real credential or a real
external sandbox endpoint. Cryptographic fixture material is disposable and
created within the test temporary directory.

## 4. Verification layers

### 4.1 Static/source inspection

The closeout records bounded scans for forbidden imports/APIs, accidental
credential output, broad exception interpolation, unbounded reads, dynamic
execution, subprocess/shell use in transport, packaged test fixtures and
unexpected CLI commands. A scan match is reviewed, not automatically waived.

### 4.2 Unit, property and mutation-oriented tests

Tests cover closed schemas, canonical serialization, cross-binding, state
machines, path normalization, URL/address classification, concurrency and
failure phase classification. Bounded property/generated cases must be
deterministic from a recorded public seed. The project need not add an
unbounded fuzzer or network crawler.

### 4.3 Disposable integration conformance

The existing dependency-injected local TLS fixture exercises exact request,
credential, idempotency, response and importer behavior. It remains local,
test-only and excluded from installed artifacts. Test certificates, tokens,
keys and identities are newly generated and destroyed with the temporary
workspace.

### 4.4 Package and clean-environment proof

Build sdist and wheel from the exact source head, inventory both, install the
wheel into a clean temporary environment and prove:

- expected public modules and CLI commands exist;
- test fixtures, certificates, tokens and temporary evidence do not ship;
- the installed CLI fails closed without explicit records;
- no import or help command reads a credential or opens a socket; and
- the complete package-focused conformance suite passes.

### 4.5 Cross-platform evidence

Required GitHub Actions jobs are Windows/Python 3.12, Ubuntu/Python 3.13 and
macOS/Python 3.12. They publish machine-readable, secret-free reports whose
hashes can be included in the final conformance record. Platform differences
must be explicit; skipped required security tests prevent PASS.

## 5. Review and closeout procedure

1. Pin the exact candidate commit and verify a clean tracked tree.
2. Run the full threat/abuse, regression and package matrix.
3. Produce machine-readable reports and hashes without secrets.
4. Perform an independent code/security review of the exact head.
5. Resolve every blocker through a new commit and rerun the entire matrix.
6. Create the immutable conformance report only from completed evidence.
7. Review the report against the exact head and artifacts.
8. Merge only through protected-main policy after separate authorization.
9. Rerun required CI on protected `main` and record the final result.

A report from a superseded commit cannot be carried forward. Passing 20D does
not authorize any endpoint call or production use.

## 6. Required PASS criteria

All of the following are mandatory for 20D closeout PASS:

1. every threat/abuse matrix control has retained reproducible evidence;
2. no secret appears in outputs, errors, records, ledger, packages or reports;
3. exact request and COSE bytes/hashes are identical across platforms;
4. DNS/TLS/redirect/proxy/path controls fail closed;
5. initial-send and recovery state machines prevent duplicate transmission;
6. ambiguous outcomes remain ambiguous and bounded;
7. evidence PASS comes only from the pinned existing importer;
8. ledger/reconciliation remain factual and no-inference;
9. installed artifacts contain no test broker, token, certificate or key;
10. all CLI commands are explicit, exact-reference and dormant by default;
11. legacy and non-attested workspaces remain behaviorally compatible;
12. no Increment 20 production, signing/key, allocation, membership,
    approval or decision-execution capability exists;
13. the complete test suite passes on all required platforms with no required
    security skip; and
14. independent review approves the exact head.

Any blocker yields overall `FAIL`. `NOT_RUN` yields incomplete, never PASS.

## 7. Live sandbox evidence boundary

20D does not require a live external sandbox call. A separately authorized
live exercise may be attached later as supplemental evidence only if the
authorization names the exact endpoint/profile/request/artifact/trust/
credential-selector references, sets a time window and transmission ceiling,
and confirms the artifact contains no secret/private material.

Such an exercise must never place a credential in GitHub Actions, the
repository, a report or chat. Its success does not alter
`production_ready: false` and is not required to close fixture-level 20D.

## 8. Candidate decisions requiring Arthur freeze

1. 20D is security/conformance closeout only; it adds no transport capability.
2. Add exactly one immutable conformance-report schema and storage area.
3. Treat unavailable required evidence as `NOT_RUN`, preventing PASS.
4. Require the complete named threat/abuse matrix.
5. Use only disposable local TLS/crypto fixtures in automated tests.
6. Build and inspect sdist/wheel and prove fixtures/secrets are absent.
7. Require clean-environment installed-wheel CLI/conformance proof.
8. Require Windows 3.12, Ubuntu 3.13 and macOS 3.12 with no required skip.
9. Require independent review of the exact head and full rerun after changes.
10. Keep all evidence and language factual, secret-free and authority-neutral.
11. Keep `production_ready` and `production_use_allowed` false regardless of
    fixture conformance PASS.
12. Make live external sandbox evidence optional and separately authorized.
13. Prohibit B1/B2/offline custody, real credentials and real keys from tests.
14. Require separate authorization for implementation, PR, merge, release or
    any live sandbox exercise.

## 9. Explicit non-authorization

This candidate authorizes no implementation, push, PR, merge, release, tag,
deployment, credential access, network I/O or external exercise. It does not
authorize production use, production trust, keys/signing, identity or trust
bootstrap, allocation, issuance, membership, approval, constitutional action,
KOS/IDM change or reliance on a conformance report as authority.
