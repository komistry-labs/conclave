# Increment 20C — Operator invocation, recovery and bounded retry

## Status

**FROZEN BY ARTHUR ON 2026-08-27.** Arthur accepted decisions 1–14 from the
candidate at commit `026b2c1b2a76ecbf14d26d74fdd67b1f3150f1b3`.
This freeze fixes the bounded 20C protocol and authorizes only its retention
as the governing implementation specification. It does not authorize
implementation, credential access, network I/O, sandbox use, retry, push,
pull request, merge, release, deployment or production use.

Implementation, publication, live sandbox use and merge each require separate
Arthur authorization.

## 0. Preflight basis and dependency

| Item | Value |
|---|---|
| CONCLAVE dependency | Increment 20B PR #10 |
| Exact 20B head | `372df5b93ad57ea208c7916b55704f199c88dc52` |
| Evidence context | `conclave-evidence/1.0` |
| First-attempt record | `sandbox-broker-attempt/0.1.0` |
| First-attempt receipt | `sandbox-broker-transport-receipt/0.1.0` |
| Existing request | `evidence-signing-request/0.1.0` |
| Existing binding | `signed-evidence-binding/0.1.0` |

20C is strictly dependent on 20B. It must not be merged before 20B, and its
implementation PR must be rebased or retargeted to the protected `main` head
that contains the exact reviewed 20B implementation.

## 1. Objective and maximum scope

20C adds the dormant 20B library's explicit operator workflow:

1. create and inspect exact sandbox endpoint records;
2. create and inspect request-specific one-attempt egress authorizations;
3. invoke one initial sandbox submission;
4. inspect immutable attempt and receipt state;
5. abandon an ambiguous attempt without transmitting; or
6. perform one explicitly authorized idempotent recovery replay of the exact
   original request bytes under the exact original idempotency key.

20C remains sandbox-only. It does not add a background worker, queue,
scheduler, automatic retry, endpoint discovery, production broker, vault,
OAuth flow, browser connector, MCP credential source, key API, signing API,
identity allocation, approval, membership or action execution.

## 2. Governing invariants

20C shall not change or reinterpret any Increment 19, 20A or 20B record. In
particular:

- the original 20B attempt and receipt remain immutable;
- an attempt intent without a receipt remains `ATTEMPT_OUTCOME_UNKNOWN`;
- `SENT_NO_RESPONSE` remains ambiguous and never means not sent;
- HTTP/TLS success never means verification PASS;
- only the existing Increment 19 importer may establish evidence verification;
- a human may authorize a recovery operation but may not declare that a
  signature, broker action or verification occurred;
- ledger events remain factual system evidence without approval, authority,
  decision or membership semantics; and
- no operation changes `identity.mode` or creates an active/default profile.

## 3. New immutable records and storage

20C adds exactly three closed, canonical, content-hashed record types:

```text
.conclave/signing/broker-recovery-authorizations/
.conclave/signing/broker-recovery-attempts/
.conclave/signing/broker-recovery-dispositions/
```

Paths use hash-safe filenames. References are canonical workspace-relative
POSIX references and pass the existing containment, symlink/reparse,
regular-file, size and single-load rules.

### 3.1 `broker-recovery-authorization/0.1.0`

This is a human principal's authorization for exactly one recovery action.
Required fields include:

- profile, schema version and content hash;
- exact workspace genesis identity and principal;
- exact original endpoint, broker profile, verifier profile, trust input,
  signing request, artifact, authorization, attempt and optional receipt
  references and hashes;
- exact original canonical wire-body hash and byte count;
- exact original public 64-hex idempotency key (the deterministic 20B attempt
  digest), its hash and public algorithm label, never a credential or header
  dump;
- action, exactly `ABANDON` or `IDEMPOTENT_REPLAY`;
- principal confirmations that the original outcome is ambiguous, the exact
  artifact remains sandbox-eligible and secret-reviewed, and replay may cause
  the broker to return or complete the original signing operation;
- issuance and expiry with `time_source_classification: diagnostic-local`;
- `maximum_replays: 0` for `ABANDON`, exactly `1` for
  `IDEMPOTENT_REPLAY`;
- `environment: sandbox`, `production_use_allowed: false`;
- `authority_effect: broker_recovery_only`, `decision_effect: none`,
  `membership_effect: none`, `action_execution_allowed: false`; and
- content hash.

The authorization is valid only for an original attempt with no receipt or a
receipt whose outcome is `SENT_NO_RESPONSE`. `NOT_SENT`,
`RESPONSE_REJECTED`, `RESPONSE_ACCEPTED_FOR_VERIFICATION`, an existing valid
recovery disposition or a changed record blocks recovery.

### 3.2 `sandbox-broker-recovery-attempt/0.1.0`

For `IDEMPOTENT_REPLAY`, this durable intent is written under the original
attempt-scoped lock before credential resolution or network I/O. It binds:

- the complete authorization bindings above;
- deterministic recovery-attempt ID;
- exact original wire-body hash and byte count;
- exact original idempotency key;
- `state: PREPARED`, `maximum_transmissions: 1`;
- diagnostic-local creation time;
- all authority-neutral fields; and
- content hash.

The replay must reconstruct the original canonical request bytes from the
same immutable records and prove that their hash and byte count match. It must
not copy a cached natural-language request, accept caller bytes, amend a
header, change an authorization-bound value or derive a new idempotency key.

### 3.3 `broker-recovery-disposition/0.1.0`

Every completed recovery action produces one immutable disposition:

- exact recovery authorization and original attempt/receipt bindings;
- action `ABANDON` or `IDEMPOTENT_REPLAY`;
- replay-attempt reference/hash when applicable;
- outcome:
  - `ABANDONED_WITHOUT_TRANSMISSION`,
  - `REPLAY_NOT_SENT`,
  - `REPLAY_SENT_NO_RESPONSE`,
  - `REPLAY_RESPONSE_REJECTED`, or
  - `REPLAY_RESPONSE_ACCEPTED_FOR_VERIFICATION`;
- stable ordered reason codes;
- request and response hashes/counts, status class, envelope and evidence
  binding references/hashes when established;
- verification status copied only from the existing importer;
- diagnostic-local start/finish times;
- credential selector label only;
- authority-neutral fields; and
- content hash.

`ABANDON` records that CONCLAVE will not transmit this attempt. It does not
prove the broker did nothing and does not revoke or delete any returned
evidence that may later be recovered independently.

## 4. Exact operator CLI

20C proposes only these commands:

```text
conclave evidence sandbox-endpoint create
conclave evidence sandbox-endpoint show --endpoint <reference>
conclave evidence broker-authorization create
conclave evidence broker-authorization show --authorization <reference>
conclave evidence broker-submit --endpoint <reference> --authorization <reference>
conclave evidence broker-attempt show --attempt <reference>
conclave evidence broker-receipt show --receipt <reference>
conclave evidence broker-recovery authorize
conclave evidence broker-recovery execute --authorization <reference>
conclave evidence broker-recovery show --disposition <reference>
```

Every mutating command requires explicit exact references. There is no
`--latest`, label search, active profile, default endpoint, inferred request,
raw URL, arbitrary header, raw payload, credential, token, passphrase, key
path or production flag. Secret values must never be command arguments.

Creation commands expose only the fields necessary to seal the governed
record. Human confirmation flags must be explicit and are recorded as facts;
an interactive yes/no default is insufficient. `show` commands emit only the
closed public record or a bounded public summary and never resolve credentials
or contact a network.

## 5. Initial submission

`broker-submit` is a thin operator entry point over the unchanged 20B
operation. Before credential resolution it must:

1. load and verify the initialized ledger/genesis identity;
2. load all exact records once and revalidate hashes and filenames;
3. reconstruct and hash the exact canonical body;
4. validate authorization, principal, expiry, artifact classification, trust
   and verifier bindings;
5. acquire the request/attempt lock; and
6. prove there is no prior attempt for the deterministic attempt ID.

It then uses the 20B environment-only resolver and HTTPS transport. CLI
output contains public references, hashes, outcome, verification status and
stable reason codes only. It never emits the endpoint origin redundantly,
credential, request body, response body or adapter exception text.

## 6. Recovery and retry rules

There is no automatic retry. Recovery is allowed only after a new exact human
authorization and only for a 20B unknown/ambiguous attempt.

### 6.1 Abandonment

`ABANDON` performs no credential lookup, DNS resolution or network I/O. It
writes the disposition and factual ledger event. An existing abandonment
permanently blocks CONCLAVE replay for that original attempt.

### 6.2 Idempotent replay

`IDEMPOTENT_REPLAY`:

- reuses the exact original endpoint, request bytes and idempotency key;
- permits exactly one replay transmission;
- writes durable intent before credential resolution;
- uses the same credential selector but resolves the current value once;
- applies all 20B DNS, TLS, redirect, proxy, header, timeout and size rules;
- passes any accepted COSE bytes unchanged to the existing importer; and
- creates a disposition before its ledger event.

A second recovery authorization, a second replay intent or any completed
disposition blocks transmission. Another ambiguous failure ends as
`REPLAY_SENT_NO_RESPONSE`; 20C provides no further resend. Later recovery may
only import independently obtained exact envelope bytes through the existing
19B importer or record non-transmitting administrative follow-up outside this
runtime protocol.

## 7. Concurrency, crash safety and reconciliation

- Lock identity is derived from the original deterministic attempt ID.
- The lock covers prior-state scan, recovery intent, credential resolution,
  replay and disposition creation.
- Invalid or unreadable recovery stores fail closed.
- Intent without disposition blocks all future replay.
- Exact duplicate command invocation is observationally idempotent and
  returns the existing reference; it never sends again.
- Disposition is written before ledger append.
- Factual system events are
  `sandbox_broker_recovery_abandoned` and
  `sandbox_broker_recovery_attempt_recorded`.
- Reconciliation may restore only the event proved by a valid immutable
  disposition. It may not infer transmission, broker state, signing,
  verification, approval, authority or membership.

## 8. Error and secret policy

Stable codes must cover invalid bindings, stale/expired authorization,
ineligible original outcome, already disposed/replayed, invalid stores,
wire-body or idempotency mismatch, missing/malformed credential, transport
failures, response rejection, importer failure, immutable-write failure and
ledger failure.

Credential values, tokens, private material, command environment, raw bodies,
full external paths, endpoint origins in errors and adapter exception text are
forbidden from stdout, stderr, exceptions, logs, records, ledger events and
test reports.

## 9. Required acceptance evidence

At the exact PR head and protected `main`, Windows/Python 3.12,
Ubuntu/Python 3.13 and macOS/Python 3.12 must prove:

1. all closed records, exact-reference commands and installed-wheel CLI help;
2. initial submission is an exact wrapper over 20B with no alternate path;
3. all preflight failures occur before credential resolution;
4. no retry for `NOT_SENT`, rejected, accepted, verified or disposed states;
5. abandonment performs no credential, DNS or network operation;
6. replay uses byte-identical body and the exact original idempotency key;
7. one replay maximum under serial, concurrent and crash-window tests;
8. exact COSE preservation and unchanged Increment 19 import behavior;
9. secret sentinel scans over outputs, errors, records, ledger and temp data;
10. factual ledger/reconciliation and authority-neutral assertions;
11. installed-wheel proof that test TLS fixtures are absent;
12. local disposable TLS fixture success and negative response modes only;
13. no external network or real credential in CI; and
14. the complete suite remains green.

## 10. Frozen decisions

By freezing this protocol on 2026-08-27, Arthur accepted and confirmed:

1. 20C is sandbox-only operator workflow; production remains prohibited.
2. Add only the stated CLI commands; require exact references everywhere.
3. Preserve 20B first-attempt records and semantics unchanged.
4. Permit recovery only for missing-receipt or `SENT_NO_RESPONSE` ambiguity.
5. Require a new exact human recovery authorization.
6. Allow `ABANDON` with no credential or network access.
7. Allow at most one idempotent replay of the exact original bytes under the
   exact original idempotency key.
8. Never derive a new idempotency key or accept caller-supplied retry bytes.
9. A second ambiguous replay failure is terminal for CONCLAVE transmission.
10. Preserve all attempts, responses, dispositions and conflicts immutably.
11. Keep verification exclusively within the existing Increment 19 importer.
12. Keep ledger and CLI language factual and authority-neutral.
13. Require Windows, Linux and macOS CI with no real service or credential.
14. Require separate authorizations for implementation, PR, merge and any
    live sandbox execution.

## 11. Explicit non-authorization

This protocol freeze does not authorize implementation, credential lookup,
network I/O, live sandbox use, retry, push, PR, merge, release or deployment.
It does not authorize production use, background work, keys/signing, trust or
identity bootstrap, allocation, issuance, membership, approval,
constitutional action, KOS/IDM changes, or Increment 20D implementation.
