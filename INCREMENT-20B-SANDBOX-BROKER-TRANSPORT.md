# Increment 20B — Sandbox broker transport

## Status

**FROZEN BY ARTHUR ON 2026-08-26.** Arthur accepted decisions 1–14 from the
draft at commit `59e3cbb35595be59fecceb1ad62cb5931d9ef1f9`. This freeze fixes
the bounded 20B protocol and authorizes only its retention as the governing
implementation specification. It does not authorize runtime changes,
credential access, network I/O, a sandbox call, push, pull request, merge,
release, deployment, signing, key access, identity issuance, membership,
trust-domain operation, KOS change, or IDM change.

Implementation, publication, live sandbox use and merge each require separate
authorization.

## 0. Preflight basis

| Item | Value |
|---|---|
| CONCLAVE baseline | `main` at `101d491d8197e065b400d6375ba5fe3c3b323d5f` |
| Increment 20A implementation | PR #9, merged 2026-08-26 |
| Frozen evidence context | `conclave-evidence/1.0` |
| Existing request schema | `evidence-signing-request/0.1.0` |
| Existing binding schema | `signed-evidence-binding/0.1.0` |
| Existing broker profile | `broker-transport-profile/0.1.0` |
| Pinned IDM commit | `3769ce3943c87e6a5a72bf94b0efdaa2b11c3bd2` |
| Pinned IDM tree | `425f650696a798c10f2a553781fee45e0950dc2a` |
| Pre-20B suite | 920 passed, 2 platform-conditional skips on Windows |

Increment 20A stores a sandbox transport label and an `env:NAME` credential
selector, but deliberately refuses to resolve the selector or make a network
call. Increment 19 prepares immutable signing requests and imports exact COSE
envelopes through a pinned public verifier. 20B may connect those boundaries;
it may not weaken or reinterpret either one.

The provider `egress-decision/0.1.0` contract is not a broker authorization.
It binds provider prompts and context classifications and must not be silently
reused for evidence-broker traffic.

## 1. Objective and maximum scope

20B adds a single-attempt, authenticated, transport-neutral client boundary
for an explicitly configured **sandbox** evidence broker. It sends one exact,
already-sealed CONCLAVE signing request and the exact governed artifact bytes
bound by that request. It accepts one bounded binary response and submits
those unchanged bytes to the existing Increment 19 evidence-import verifier.

20B does not:

- discover or select a default profile, endpoint, request or trust input;
- prepare or revise a signing request;
- sign, parse private material, load a key, generate a key or expose a signing
  API;
- make a production broker call or accept production trust or credentials;
- retry automatically, recover an interrupted workflow or schedule work;
- infer verification PASS from HTTP or TLS success;
- approve, ratify, allocate, issue, activate membership or execute an action;
  or
- modify KOS, IDM, ADR-0009, ADR-0010 or the Constitution.

Automatic retry, operator recovery and migration workflow belong to 20C.
Security/conformance closeout belongs to 20D.

## 2. Governing order

Implementation shall conform, in descending order, to:

1. KOS ADR-0009 and ADR-0010;
2. the frozen Increment 19 protocol and 19A–19D closeouts;
3. `IDM-COMPATIBILITY-BASELINE-0001.md`;
4. the frozen Increment 20A protocol and merged implementation;
5. `policies/idm-reference-pin.json`; and
6. this frozen protocol, once approved.

20B may add transport records. It may not change an existing 19A/19B/20A
schema, IDM pin, evidence context, request hash, payload hash, envelope hash,
conflict rule, verification finding, identity mode or authority meaning.

## 3. New immutable records and storage

20B adds exactly four record types and four workspace areas:

```text
.conclave/signing/broker-endpoints/
.conclave/signing/broker-authorizations/
.conclave/signing/broker-attempts/
.conclave/signing/broker-receipts/
```

Every record is closed-schema, canonical JSON, content-hashed, immutable and
stored under a SHA-256-safe filename. Exact canonical workspace-relative
references are mandatory; there is no mutable current/default/active object.
The 20A containment rules apply unchanged, including rejection of absolute,
drive, UNC, backslash, ADS, traversal, symlink, reparse-point, directory,
non-regular-file and external references.

### 3.1 `sandbox-broker-endpoint/0.1.0`

Required fields:

- profile and schema version;
- endpoint ID using the 20A safe-label grammar;
- exact reference and hash of one 20A broker profile whose classification is
  `sandbox`;
- one normalized HTTPS origin and fixed request path;
- authentication scheme, exactly `bearer-env-v1`;
- exact credential selector copied from the broker profile;
- TLS policy, exactly `system-ca-hostname-tls12-plus`;
- maximum request and response byte counts;
- connect and total timeout values within protocol caps;
- creation actor and UTC creation time;
- `environment: sandbox`;
- `authority_effect: none`, `decision_effect: none`,
  `membership_effect: none`, `action_execution_allowed: false`; and
- content hash.

Endpoint normalization must reject:

- plaintext HTTP or any scheme other than HTTPS;
- user information, query, fragment, noncanonical escaping or Unicode host;
- an IP-literal host, wildcard host, missing host or missing fixed path;
- loopback, link-local, multicast, unspecified, private or reserved addresses;
- redirects and cross-origin credential forwarding;
- proxy discovery from environment variables; and
- an origin or request path supplied only at call time.

The endpoint record stores no token, cookie, client certificate, private CA,
vault path or secret. System CA and hostname verification remain enabled.
TLS 1.0 and 1.1 are refused. 20B does not implement certificate pin rotation;
that requires a later separately governed design if system trust is
insufficient.

Immediately before connection, every resolved address must pass the public
address policy. The concrete transport must connect only to an address from
that vetted resolution while retaining the configured hostname for TLS SNI
and certificate verification. A redirect, resolver change, proxy or adapter
must not cause connection to a different address. This is the required DNS
rebinding/SSRF boundary, not a best-effort diagnostic.

Protocol caps:

- request body: 8 MiB maximum;
- response body: 1 MiB maximum, matching the existing envelope cap;
- connect timeout: 1–15 seconds;
- total timeout: 1–60 seconds; and
- zero automatic redirects.

### 3.2 `broker-egress-authorization/0.1.0`

This is a request-specific human authorization, not an identity, membership
or general network grant. It must be prepared outside the transport call and
confirmed by the configured workspace principal.

Required fields:

- profile and schema version;
- exact broker endpoint reference and hash;
- exact verifier-profile and trust-input references and hashes;
- exact signing-request reference and hash;
- exact artifact storage reference, schema, content hash and canonical payload
  hash copied from the signing request;
- allowed evidence context, exactly `conclave-evidence/1.0`;
- maximum transmitted classification from an allowlisted vocabulary;
- authorization purpose;
- authorized principal, issuance time and expiry time;
- `maximum_attempts: 1`;
- `environment: sandbox` and `production_use_allowed: false`;
- `authority_effect: broker_egress_only`;
- `decision_effect: none`, `membership_effect: none`,
  `action_execution_allowed: false`; and
- content hash.

The authorization is valid for one exact
request/endpoint/verifier/trust-input/artifact tuple. It cannot authorize
another profile, endpoint, trust set, artifact, request, purpose,
classification, context or retry. Its expiry is checked against local
operational time and does not become trusted IDM verification time.

The existing provider-egress decision cannot substitute for this record.
Conversely, this record cannot authorize provider API traffic.

The transmitted classification is an explicit assertion by the human
principal about the exact hash-bound artifact. CONCLAVE does not claim to
infer semantic sensitivity from arbitrary content. The authorization must
record that the principal reviewed the artifact for secret/private material;
schema and marker checks remain defense in depth, not a replacement for that
human classification.

### 3.3 `sandbox-broker-attempt/0.1.0`

This immutable intent is written under the request-scoped lock after every
pre-network validation passes but before credential resolution or network
I/O. It closes the crash window in which a request could be transmitted but
no receipt written.

Required fields:

- profile and schema version;
- deterministic attempt ID;
- exact endpoint, broker-profile, authorization and signing-request references
  and hashes;
- exact verifier-profile and trust-input references and hashes;
- artifact reference, schema, content hash and canonical payload hash;
- transmitted request-body hash and byte count;
- creation time with `time_source_classification: diagnostic-local`;
- `state: PREPARED`, `maximum_transmissions: 1`;
- `authority_effect: none`, `decision_effect: none`,
  `membership_effect: none`, `action_execution_allowed: false`; and
- content hash.

An existing valid attempt record blocks creation of another attempt for the
same authorization/request/endpoint/body tuple. If it has no corresponding
valid receipt, 20B reports `ATTEMPT_OUTCOME_UNKNOWN` and performs no credential
lookup or transmission. The attempt record does not prove that credential
resolution, transmission, signing or a response occurred. Recovery or retry
from this state belongs exclusively to 20C.

### 3.4 `sandbox-broker-transport-receipt/0.1.0`

One completed in-process call attempt produces one immutable receipt whether
it succeeds, fails before transmission, fails after transmission or receives
a response. A hard process or machine failure may leave only the immutable
attempt record; that is an explicit blocked recovery state, not permission to
resend.

Required fields:

- profile and schema version;
- exact attempt reference and hash;
- exact endpoint, broker-profile, authorization and signing-request references
  and hashes;
- exact verifier-profile and trust-input references and hashes;
- artifact reference, schema, content hash and canonical payload hash;
- deterministic transport attempt ID;
- start and finish timestamps with
  `time_source_classification: diagnostic-local`;
- outcome: `NOT_SENT`, `SENT_NO_RESPONSE`, `RESPONSE_REJECTED` or
  `RESPONSE_ACCEPTED_FOR_VERIFICATION`;
- ordered stable reason codes;
- transmitted request-body hash and byte count, if sent;
- response-body hash and byte count, if received;
- HTTP status class only, never raw status text;
- returned envelope storage reference/hash and existing evidence-binding
  reference/hash when available;
- `verification_status` copied only from the existing evidence-import result,
  otherwise `NOT_RUN`;
- credential selector label, never its value;
- `authority_effect: none`, `decision_effect: none`,
  `membership_effect: none`, `action_execution_allowed: false`; and
- content hash.

A transport receipt records what the client attempted and observed. TLS
success, HTTP 2xx, a matching content type or receipt creation is not evidence
verification, broker approval, signer identity, authority or membership.

### 3.5 Runtime and CLI surface

20B adds a verification-independent `SandboxBrokerTransport` protocol and one
bounded HTTPS implementation. The protocol accepts already validated canonical
request bytes plus public endpoint metadata and returns only a normalized
status class, media type and exact bounded response bytes. It exposes no key,
signing, identity-allocation or credential-return method. Tests inject the
local fixture implementation through this same boundary.

20B adds no operator CLI command. Endpoint/authorization creation, transport
invocation, recovery and retry CLI workflow remain 20C work. Consequently, a
merged 20B library is dormant by default and cannot turn a legacy or 20A
workspace into a network-calling workspace. Any exceptional pre-20C live
sandbox exercise requires a separately authorized bounded harness and exact
records; it is not production use.

## 4. Exact wire contract

### 4.1 Request body

The request uses HTTPS `POST`, fixed content type
`application/vnd.conclave.evidence-request+json;version=1`, and canonical JSON
with exactly:

- the complete sealed `evidence-signing-request/0.1.0` record;
- the artifact schema;
- the exact artifact bytes encoded as canonical unpadded base64url; and
- the SHA-256 hash and byte count of those exact bytes.

Before credential resolution or network I/O, CONCLAVE must:

1. require a valid initialized ledger and verified genesis workspace identity;
2. load all referenced immutable records once under their size caps;
3. revalidate closed schemas, content hashes, content-addressed filenames,
   reference containment and cross-hashes;
4. load the exact public trust input and prove its reference matches the 20A
   verifier profile, its implementation matches the frozen IDM pin and its
   hash matches the authorization;
5. resolve the artifact through the existing 19B governed-artifact resolver;
6. prove the loaded artifact bytes match both request hashes;
7. validate the unexpired authorization and all exact bindings;
8. canonicalize the bounded wire body once and hash those exact bytes; and
9. refuse before credential access if any earlier check fails.

No natural-language prompt, arbitrary file, KOS path, IDM checkout, B1/B2
material, trust input, private key, passphrase or extra metadata may enter the
wire body.

### 4.2 Headers and idempotency

Allowed outbound headers are fixed to:

- `Content-Type` and `Accept` from this protocol;
- `Authorization: Bearer <resolved value>`;
- `Idempotency-Key`, derived from the endpoint hash, authorization hash,
  signing-request hash and wire-body hash; and
- a bounded public CONCLAVE client version.

No caller-supplied header is accepted. Cookies are disabled. Redirects are
disabled. The token never enters the idempotency key.

The idempotency key protects the broker against duplicate submissions, but
20B performs exactly one attempt and has no automatic retry. A later manual
call requires a new authorization because `maximum_attempts` is one. 20C may
define governed retry/recovery without changing this first-attempt evidence.

### 4.3 Response body

The only success response is HTTP 2xx with content type
`application/cose; cose-type="cose-sign1"` and a nonempty body within the
existing 1 MiB envelope limit. The exact response bytes are never decoded as
text, normalized, reserialized or logged.

Those bytes are passed unchanged to the existing Increment 19 evidence-import
operation with an explicitly supplied trust-input reference and pinned public
verifier. Existing import behavior remains authoritative:

- exact envelope bytes are content-addressed and retained;
- all payload/request/artifact/workspace/identity/KID/context/time/revocation
  bindings must pass;
- conflicting verified envelopes are retained separately and reliance is
  blocked; and
- no HTTP result can override a verification failure.

Non-2xx bodies, malformed content types, oversized bodies and transport errors
produce stable reason codes. Raw bodies and adapter exception text are not
written to logs or receipts. A bounded response hash may be recorded only for
bytes actually received.

## 5. Credential boundary

Credential resolution is allowed only after every pre-network check in §4.1
passes and immediately before constructing the single request.

For 20B, the sole supported selector is the exact `env:UPPERCASE_NAME` already
sealed into the sandbox broker profile and endpoint. The implementation:

- reads exactly that one variable once;
- rejects missing, empty, whitespace-bearing, control-character, newline,
  non-UTF-8 or over-8-KiB values;
- never accepts an inline value, CLI token, file path, URI or different
  selector;
- never enumerates the environment;
- never passes the ambient environment to a subprocess;
- never stores, hashes, compares, returns, prints or logs the token;
- never includes it in an exception, receipt, ledger event, test snapshot or
  crash diagnostic; and
- drops the in-process reference as soon as the request completes.

20B does not add vault, keychain, browser-session, OAuth refresh, MCP or
connector credential support. Those require separate protocols.

## 6. Transport lifecycle and failure states

The bounded lifecycle is:

```text
validate records and ledger
  -> load and bind exact artifact bytes
  -> validate one-attempt authorization
  -> write immutable PREPARED attempt intent
  -> resolve one credential
  -> send one HTTPS request
  -> retain bounded response bytes if any
  -> invoke existing evidence import
  -> write immutable transport receipt
  -> append factual system ledger event
  -> stop
```

Stable fail-closed reason codes must cover at least:

- invalid/missing/stale endpoint, profile, request or authorization;
- invalid/missing/stale trust input or frozen IDM implementation mismatch;
- wrong endpoint/request/artifact/profile/trust/context/classification binding;
- uninitialized or invalid ledger/workspace identity;
- unsafe artifact or record reference;
- artifact schema/hash/payload/size mismatch;
- authorization not yet valid, expired or already consumed;
- credential missing or malformed;
- DNS/address policy failure, TLS failure, timeout or connection failure;
- redirect attempted;
- unsupported response status/content type, oversized or empty response;
- evidence importer unavailable or failed; and
- receipt or ledger append failure.

Errors exposed to the operator contain only stable codes and public canonical
references/hashes. Endpoint origins may appear only in the immutable public
endpoint profile; errors use its reference/hash rather than repeating it.

If transmission may have occurred but no response was established, the
receipt must say `SENT_NO_RESPONSE`. 20B must not guess whether the broker
signed or whether a retry is safe. That state is handed to 20C recovery.

## 7. Concurrency, immutability and ledger rules

- A request-scoped portable lock covers authorization-consumption check,
  attempt-intent creation, credential resolution, transmission and receipt
  creation.
- The attempt ID is deterministic from the endpoint, authorization, request
  and wire-body hashes.
- An existing valid attempt intent prevents a second transmission, whether or
  not a receipt exists.
- An intent without a receipt is an explicit unknown-outcome recovery blocker.
  A partial state never permits an unrecorded automatic resend.
- Exact response bytes and existing evidence bindings remain hash-keyed; no
  request-keyed overwrite is introduced.
- Receipt creation precedes the ledger event. A ledger failure preserves the
  receipt for reconciliation.
- The factual system event is
  `sandbox_broker_transport_attempt_recorded` and carries hashes/references,
  outcome and reason codes only.
- Reconciliation may restore that event only from a valid immutable receipt.
  It may not infer that a request was sent, a response was authentic, evidence
  passed, the broker was healthy, signing occurred, or authority/membership
  exists beyond what the receipt itself proves.

## 8. Test-only sandbox fixture

CI must not call a real external service or use a real credential. 20B may add
one test-only, non-packaged local TLS sandbox fixture that:

- requires an explicit fixture marker;
- uses a newly generated disposable certificate and token;
- accepts only the exact frozen request media type and idempotency header;
- verifies request hashes before returning a prebuilt fixture envelope;
- records no token or request body outside the test temporary directory; and
- supports deterministic negative modes for redirects, timeouts, oversized
  bodies, wrong media types, disconnects and malformed responses.

The production endpoint policy remains public-address HTTPS only. The local
fixture exception is dependency-injected in tests and cannot be selected by a
stored sandbox endpoint or packaged CLI.

Tests may use only newly generated fixture identities, trust and keys. B1/B2
material and offline custody remain prohibited.

## 9. Required acceptance evidence

At the exact 20B PR head and again on protected `main`, Windows/Python 3.12,
Ubuntu/Python 3.13 and macOS/Python 3.12 must pass:

1. closed-schema, immutable, content-addressed endpoint, authorization,
   attempt-intent and receipt records;
2. exact endpoint/profile/request/authorization/artifact/context cross-binding;
   including the verifier profile, public trust input and frozen IDM pin;
3. URL, TLS, DNS/address, redirect, proxy and reference-containment negatives;
4. proof that all validation failures occur before credential resolution;
5. one-variable-only credential resolution and sentinel secret-leak scans of
   stdout, stderr, exceptions, records, ledger, temp files and test reports;
6. exact canonical request bytes, body hash, media type and idempotency key on
   Windows, Linux and macOS;
7. exact binary response preservation and unchanged handoff to the Increment
   19 verifier/importer;
8. non-2xx, empty, oversized, malformed, redirect, timeout, TLS and ambiguous
   `SENT_NO_RESPONSE` failures;
9. pre-network durable attempt intent, single-attempt locking, crash-window
   blocking, concurrent-call refusal and no automatic retry;
10. success, verification-failure and verified-envelope-conflict receipts;
11. factual ledger events, reconciliation and no-inference assertions;
12. installed-wheel proof that test fixture code is absent;
13. no regression in identity modes, evidence import, gating, providers,
    routing, concurrency, synthesis, 20A diagnostics or legacy workspaces; and
14. the complete existing suite remains green.

Actual live sandbox execution is not part of CI and requires a separate
Arthur authorization naming the exact endpoint profile, authorization record,
request, artifact classification and credential selector.

## 10. Frozen decisions

By freezing this protocol on 2026-08-26, Arthur accepted and confirmed:

1. **20B scope:** sandbox HTTPS transport only; production remains prohibited.
2. **Endpoint model:** add an immutable endpoint record rather than placing a
   URL on the CLI or revising the 20A broker-profile schema.
3. **Wire content:** transmit the complete sealed signing request plus the
   exact governed artifact bytes so the sandbox signer can attest what it saw.
4. **Authorization:** require a new request-specific, one-attempt human broker
   egress authorization; do not reuse provider D7 egress.
5. **Credential mechanism:** permit only one sealed `env:NAME` bearer selector
   in 20B; defer vault/OAuth/MCP/browser connectors.
6. **Network policy:** HTTPS, system CA/hostname verification, TLS 1.2+, no
   redirects, proxies, IP literals or non-public destinations.
7. **Attempt policy:** exactly one attempt and no automatic retry; ambiguous
   delivery stops as `SENT_NO_RESPONSE` for 20C recovery.
8. **Response contract:** exact bounded `application/cose` bytes only, with
   verification performed exclusively by the unchanged Increment 19 importer.
9. **Crash safety:** write a durable immutable attempt intent before credential
   resolution; an intent without a receipt blocks resend pending 20C recovery.
10. **Evidence:** write one immutable secret-free transport receipt and factual
   ledger event for every completed attempt outcome.
11. **Testing:** local dependency-injected TLS sandbox fixture only; no CI
    external service or real credential.
12. **Live-use boundary:** implementation and live sandbox execution require
    separate authorizations after the protocol freeze.
13. **Downstream boundary:** 20C retry/operator recovery and 20D security
    closeout remain unauthorized and may not be folded into 20B.
14. **Dormant library boundary:** 20B adds the injectable transport library and
    records but no operator CLI; CLI invocation and recovery remain 20C.

## 11. Explicit non-authorization

This protocol freeze does not authorize:

- implementation, credential resolution, network I/O or sandbox execution;
- push, PR, merge, release, tag or deployment;
- production endpoint, credential, trust, identity, key or broker activation;
- signing, key loading, key generation, embedded signer or private-key API;
- automatic retry, background worker, queue, recovery or scheduling;
- identity allocation/issuance, membership, constitutional action, authority
  decision, merge authority or production reliance;
- changes to KOS, IDM, ADR-0009, ADR-0010 or the Constitution; or
- any 20C or 20D implementation.

This disposition freezes the protocol only. It does not constitute any of the
separate implementation, publication, live-use or merge authorizations above.
