# Increment 19 — IDM-backed identity and signed evidence

## Status

**Protocol frozen for implementation.** At the time of freeze, implementation
had not begun. Increments 19A and 19B were subsequently authorized and
implemented as separate bounded changes; see
`INCREMENT-19A-VERIFICATION-FOUNDATION.md` and
`INCREMENT-19B-EVIDENCE-IMPORT.md`. Stages 19C and 19D have not begun.

This increment changes CONCLAVE only. KOS and IDM remain external. The freeze
authorizes this protocol record and implementation preflight only. Runtime or
fixture implementation requires a separate authorization. The freeze does not
authorize an IDM trust-domain bootstrap, identity or K1 allocation, key
generation, manifest issuance, membership activation, constitutional
ratification, production use, or access to rehearsal or production secrets.

## 1. Governing baseline

Implementation shall conform to, in descending order:

1. KOS ADR-0009, especially Sections 2, 5, 6 and 11;
2. KOS ADR-0010, especially Sections 5, 6, 9 and 12;
3. `IDM-COMPATIBILITY-BASELINE-0001.md`;
4. IDM v1 merge commit
   `3769ce3943c87e6a5a72bf94b0efdaa2b11c3bd2`, tree
   `425f650696a798c10f2a553781fee45e0950dc2a`; and
5. CONCLAVE v0.7.0 at
   `9c8682373ffbc3279c4bf660eeb147dc21fe60fa`.

No floating IDM branch, unreviewed wheel, mutable URL, local rehearsal output,
or provider-generated schema may silently replace this baseline. The
implementation dependency shall be reproducibly built or hash-pinned to the
accepted tree and recorded in its validation evidence.

The B1/B2 artifacts are non-production rehearsal evidence. Their identities,
trust bundles, allocation registry, keys, passphrases, revocation state and
twenty allocated objects shall never become a CONCLAVE trust anchor or fixture
by convenience. Public fixture data for this increment must be newly generated
or explicitly classified for cross-project test reuse.

## 2. Frozen objective

Increment 19 adds a fail-closed identity-evidence layer that can:

1. bind a CONCLAVE logical actor to externally issued IDM EID, MID and VID
   evidence without changing the actor's authority level;
2. verify exact IDM artifacts against pinned public trust, revocation and time
   inputs;
3. bind an immutable CONCLAVE artifact to an IDM COSE_Sign1 evidence
   attestation produced by an external deterministic signing broker; and
4. preserve every verification and attestation result in the existing
   immutable artifact and ledger chain.

CONCLAVE remains a verifier and evidence coordinator. It is not an identity
authority, registrar, certificate authority, key custodian or signing oracle.

## 3. Identity separation

The following identities are distinct and shall never be collapsed:

| Layer | Meaning |
|---|---|
| CONCLAVE actor ID | Stable logical name used in Task Packets and ledger events |
| IDM EID | Enduring externally issued entity identity |
| IDM MID | Immutable manifest lineage for the EID |
| IDM VID | Exact finalized signed IDM artifact bytes |
| Execution identity | Provider, model, transport, adapter and run instance |
| Attester identity | EID/MID/KID whose scoped key attests exact evidence bytes |
| Human authority | Authority granted only by KOS and an Arthur-authored act |

An IDM verification `PASS` proves only the verified claims within its bounded
trust inputs. It does not make an actor a KOS member, approve a proposal,
activate a lifecycle transition, confer constitutional authority, allocate an
identifier, or authorize merge or execution.

Provider API authentication is transport evidence, not proof that a model
possesses an IDM private key. A provider name, model string, consumer-chat
account or API response must not be represented as a cryptographic signer
unless independently issued IDM evidence actually establishes that binding.

## 4. Artifact profiles

All CONCLAVE metadata artifacts below are strict, closed schemas, immutable,
canonically encoded using the existing CONCLAVE canonicalization rules, and
content-hashed before storage.

### 4.1 Trust input set

Schema: `idm-trust-input-set/0.1.0`

Required fields:

- profile and schema version;
- IDM implementation commit, tree and distribution hash;
- exact trust-bundle bytes hash and trust-domain identifier;
- one or more exact signed revocation-evidence hashes, including a signed
  current empty set when no revocations are effective;
- trusted evaluation-time value, time-source classification and evidence
  reference;
- accepted roles and required scopes for the requested operation; and
- creation actor, creation time and content hash.

Omitting revocation input is not equivalent to an authoritative empty set.
Local system time is permitted only for a fixture explicitly classified
`rehearsal-local-time`; it cannot produce a production-eligible result.

Only public verification material may be copied into a workspace trust-input
set. A private key, vault, passphrase, recovery secret, bearer token, live
registry database or offline-root path is a governance error and is refused.

### 4.2 Actor identity binding

Schema: `idm-actor-binding/0.1.0`

Required fields:

- CONCLAVE actor ID and actor kind (`human`, `advisory_agent`, `system`);
- expected authority level from CONCLAVE policy;
- EID, MID, VID and exact `.idm` artifact hash;
- trust-input-set reference and hash;
- required identity role or claim, if any;
- binding purpose and bounded task/workspace scope; and
- content hash.

The binding is a claim awaiting verification. It cannot be used as a PASS
result and cannot increase the configured authority level.

### 4.3 Identity verification result

Schema: `idm-verification-result/0.1.0`

Status is exactly `NOT_RUN`, `PASS` or `FAIL`. A result records:

- actor-binding reference and hash;
- exact EID, MID, VID and artifact hash obtained by the verifier;
- trust, signature, lineage, delegation, role, scope, time and revocation
  findings;
- verifier implementation commit/tree/distribution hash;
- evaluation time and time-source classification;
- every trust/revocation input reference and hash;
- deterministic ordered reason codes;
- `authority_effect: none`;
- `membership_effect: none`;
- `action_execution_allowed: false`; and
- content hash.

Any mismatch, missing authoritative input, unknown field, unsupported version,
untrusted signer, expired delegation, future evidence, effective revocation,
wrong actor, wrong EID/MID/VID, or non-reproducible verifier identity is
`FAIL`, never a warning or partial PASS.

### 4.4 Evidence signing request

Schema: `evidence-signing-request/0.1.0`

The request contains no secret and grants no authority. It binds:

- one exact stored CONCLAVE artifact reference, schema and content hash;
- its exact canonical payload bytes hash;
- the Task Packet, Council Review or continuation chain that produced it;
- the requested IDM context `conclave-evidence/1.0`;
- required attester EID/MID, role, KID and `audit.sign` scope;
- purpose, expiry policy and replay domain;
- requester identity and requester authority level; and
- request content hash.

Only an artifact that already exists and verifies may be requested. CONCLAVE
does not accept an arbitrary byte string or natural-language signing target.

### 4.5 Signed evidence binding

The broker returns an attached-payload IDM COSE_Sign1 attestation with context
`conclave-evidence/1.0`. Detached payloads are forbidden by IDM v1.

Its canonical CBOR payload uses profile `conclave-signed-evidence/0.1.0` and
contains exactly:

- artifact reference, artifact schema and artifact content hash;
- canonical payload bytes hash;
- signing-request reference and hash;
- workspace ID and bounded task or ledger domain;
- attester EID, MID, role, KID and asserted scope;
- issued-at and optional expires-at timestamps;
- `authority_effect: none`;
- `decision_effect: none`;
- `membership_effect: none`; and
- profile version.

CONCLAVE stores the exact `.cose` bytes and a separate immutable
`signed-evidence-binding/0.1.0` record containing the derived evidence ID,
exact envelope hash, all verified cross-bindings and the verification result.
The envelope attests exact evidence bytes; it does not declare that the
artifact's claims are true or approved.

## 5. Verification algorithm

The verifier shall perform these steps in order and stop on failure:

1. load and verify the closed trust-input-set schema and content hash;
2. prove the IDM implementation/distribution matches the frozen baseline;
3. verify the trust bundle's domain and exact bytes;
4. parse and authorize every supplied revocation statement, or verify the
   signed current empty revocation set;
5. establish the evaluation time and its classification;
6. parse the exact `.idm` or COSE evidence bytes with the expected domain
   context;
7. verify canonical encoding, signature, recognized anchor or delegation,
   validity window, role and required scope;
8. apply entity, lineage, revision, key and delegation revocations;
9. cross-check EID, MID, VID, KID, actor, artifact and request bindings;
10. enforce the configured CONCLAVE authority ceiling; and
11. write one immutable deterministic PASS or FAIL result and ledger event.

Calling IDM `parse_attestation()` and `verify_attestation()` alone is
insufficient. The implementation must also authorize the signer through the
pinned trust bundle, check the `audit.sign` scope and validity window, apply
revocations and verify every payload cross-binding.

## 6. Signing boundary

CONCLAVE never imports, reads, derives, generates, decrypts or retains a private
key or passphrase. It never calls a signing primitive with private-key bytes.

Signing is performed by a separately configured deterministic broker outside
the AI/model process. The broker shall:

1. accept only the closed signing-request schema;
2. independently reload the referenced stored artifact;
3. recompute every hash and policy condition;
4. require a key delegated for the requested attester and `audit.sign` scope;
5. perform any human authentication at the key-unlock boundary;
6. return only the signed public evidence envelope and public receipt; and
7. log no secret or plaintext credential.

An AI may propose a signing request. It cannot approve the request, select an
unrestricted key, unlock a key, change the payload after approval or receive
private-key material.

The existing IDM v1 `audit.sign` scope authorizes evidence attestation only.
It does not authorize a constitutional decision. Increment 19 shall not invent
an `authority.decision` scope or reinterpret `audit.sign` as human approval.

## 7. CONCLAVE integration boundary

The first implementation may add only these workspace areas:

```text
.conclave/identity/trust-inputs/
.conclave/identity/bindings/
.conclave/identity/verifications/
.conclave/signing/requests/
.conclave/signing/envelopes/
.conclave/signing/bindings/
```

Planned CLI surface:

```text
conclave identity bind
conclave identity verify
conclave identity show
conclave evidence prepare-signing-request
conclave evidence import-envelope
conclave evidence verify
```

There is deliberately no `conclave key`, `conclave identity allocate`,
`conclave identity issue`, `conclave sign`, or `conclave membership` command.

Identity-backed mode is explicit per workspace:

- `local`: v0.7 behavior, clearly labelled non-cryptographic;
- `verify`: require identity PASS for configured gated operations; and
- `attested`: additionally require a valid signed evidence binding.

No command may silently downgrade from `verify` or `attested` to `local`.
Existing v0.7 workspaces remain readable and local unless the principal
explicitly enables a stronger mode.

The initial gated operations are limited to:

- importing an identity binding;
- accepting a principal-authored egress decision;
- recording an authority decision; and
- producing a signed ledger checkpoint or evidence receipt.

Even in `attested` mode, the existing interactive principal confirmation and
all KOS authority checks remain mandatory. Cryptography supplements those
controls; it does not replace them.

Provider Runs, Handoffs and Council Reviews remain advisory evidence. They may
be covered by an audit attestation, but a provider or synthesizer cannot sign
itself into authority or satisfy the human-principal gate.

## 8. Idempotency and ledger behavior

Artifact identity derives from substantive inputs, not timestamps. Repeating
verification with the same exact artifact, trust inputs and evaluation time
returns the existing result. A different evaluation time, revocation set,
trust bundle or source VID creates a new result linked to its predecessor; it
does not overwrite history.

Importing the same exact envelope is idempotent. Conflicting envelopes for one
request are retained as a conflict and block reliance until the principal
resolves the workflow; CONCLAVE does not choose one.

The ledger gains only evidence events. Reconciliation may reconstruct an event
from an existing verified immutable artifact, but it may not infer an identity
PASS, signature, decision, approval, membership or authorization.

## 9. Failure and security rules

The implementation fails closed for at least:

- absent, stale, malformed or untrusted revocation evidence;
- local or untrusted time in a mode requiring trusted time;
- trust-domain mismatch or unpinned trust bundle;
- wrong or revoked EID, MID, VID, KID, key or delegation;
- signature, role, scope, validity-window or canonical-encoding failure;
- actor/execution/attester identity substitution;
- wrong COSE context, detached payload or unknown payload field;
- artifact, canonical-payload, request or envelope hash mismatch;
- attempts to load private material or use a rehearsal trust domain;
- attempts to increase an actor's configured authority;
- attempts to claim independent custody where one operator controls all keys;
  and
- any request to infer KOS validation PASS, membership or ratification.

Logs and error reports contain identifiers, hashes and stable reason codes,
never passphrases, private keys, bearer tokens or decrypted protected fields.

## 10. Required acceptance evidence

Implementation is not complete until all of the following pass on Windows,
Linux and macOS where IDM's adopted baseline supports them:

1. exact baseline and distribution pinning;
2. valid fixture identity PASS;
3. tampered artifact, trust bundle and envelope rejection;
4. missing and malformed revocation evidence rejection;
5. effective entity, lineage, revision, key and delegation revocation rejection;
6. future, expired and untrusted-time rejection;
7. wrong EID/MID/VID/KID, actor and trust-domain rejection;
8. wrong context, detached payload and unknown-field rejection;
9. missing role or `audit.sign` scope rejection;
10. artifact/request/envelope cross-binding rejection;
11. replay across workspace or task domain rejection;
12. identity PASS cannot increase authority or confer membership;
13. advisory provider cannot satisfy the human-principal gate;
14. no model-accessible path can read or invoke a private key;
15. verification and envelope import are idempotent;
16. conflicting evidence is preserved and blocks reliance;
17. ledger verification and reconciliation preserve the no-inference rule;
18. v0.7 local workspaces remain compatible and cannot be silently upgraded;
19. deterministic canonical bytes and results match across platforms; and
20. the complete existing CONCLAVE suite remains green.

Tests use newly generated public fixture identities and fixture-only keys.
Fixture keys are visibly non-production and must not be accepted by any
non-fixture trust bundle.

## 11. Implementation sequence

1. **19A — Verification foundation:** dependency pin, closed schemas, public
   trust inputs, identity bindings, verification results and negative tests.
2. **19B — Evidence import:** signing requests, externally produced envelope
   import, full authorization/revocation verification and ledger events.
3. **19C — Gated workflows:** opt-in `verify` and `attested` enforcement for
   egress decisions, authority decisions and signed checkpoints.
4. **19D — Broker conformance fixture:** a fixture-only external broker and
   cross-platform end-to-end tests. No production key integration.

Each stage requires a separate reviewed PR and exact-head/post-merge CI. A
stage may not weaken a preceding failure rule to keep working.

## 12. Frozen decisions and change rule

The following are frozen:

- IDM v1 is reused; CONCLAVE creates no competing identity or signature format.
- Accepted IDM commit/tree identity is pinned; local B2 trust is not adopted.
- EID/MID/VID, execution identity, attester identity and human authority remain
  separate.
- Verification requires trust, scope, time and revocation, not signature alone.
- Evidence uses attached-payload COSE_Sign1 with context
  `conclave-evidence/1.0` and scope `audit.sign`.
- `audit.sign` attests exact evidence and never represents constitutional
  approval.
- Private keys and signing primitives remain outside CONCLAVE and every AI
  process.
- Stronger identity modes are explicit and cannot silently downgrade.
- Every result is immutable, idempotent, hash-bound and ledger-visible.
- No identity PASS or signature changes KOS authority, lifecycle or membership.

A change to these decisions, IDM baseline, evidence context, signature meaning,
required scope, trust model, authority effect or KOS effect requires a new
governed protocol decision before implementation. Editorial clarification and
additional fail-closed tests may be added without reopening the freeze.

## 13. Explicit non-authorization

This protocol freeze does not authorize:

- runtime or public-fixture implementation of Stages 19A through 19D;
- access to `E:` offline custody or any IDM authority directory;
- deletion, movement or reuse of B1/B2 evidence;
- production or rehearsal trust-domain bootstrap;
- key or passphrase generation, entry, storage or transmission;
- UUIDv7, K1, EID, MID, RID or VID allocation or issuance;
- provider possession of a signing key;
- identity-backed constitutional membership or ratification;
- changes to KOS, IDM, ADR-0009, ADR-0010 or the Constitution; or
- deployment, release or production reliance.
