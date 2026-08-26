# Increment 20A — Configuration and diagnostics

## Status

**REVISED DRAFT — NOT YET FROZEN FOR IMPLEMENTATION.** This revision replaces
the initial 2026-08-18 draft after an implementation-boundary review. It is a
protocol proposal only. It authorizes neither runtime changes nor a GitHub
push, pull request, merge, release, deployment, key operation, trust-domain
operation, KOS change, or IDM change.

Arthur must explicitly freeze this revised text before implementation can be
considered. A separate authorization is then required for 20A implementation.
Stages 20B–20D remain out of scope.

## 0. Preflight basis

This draft is based on the read-only CONCLAVE handoff and the committed
Increment 19 closeouts. Its repository baseline is:

| Item | Value |
|---|---|
| CONCLAVE baseline | `main` at `22d56a37ec12924afd464ac127a882a79a821d53` |
| Existing release tag | `v0.7.0` at `9c8682373ffbc3279c4bf660eeb147dc21fe60fa` |
| IDM commit | `3769ce3943c87e6a5a72bf94b0efdaa2b11c3bd2` |
| IDM tree | `425f650696a798c10f2a553781fee45e0950dc2a` |
| Machine-readable pin | `policies/idm-reference-pin.json` |
| Existing identity/evidence areas | `.conclave/identity/{trust-inputs,bindings,verifications}/`, `.conclave/signing/{requests,envelopes,bindings}/` |
| Existing identity default | `identity.mode: local` |

The pin file is a verification-dependency pin, not a trust anchor. B1/B2
rehearsal identities, trust bundles, registries, keys, passphrases,
revocations, custody records, and allocated objects remain excluded.

## 1. Objective and boundary

Increment 19 supplies the public verification/evidence library and fixture
conformance boundary. It does not provide workspace-facing configuration for a
specific pinned verifier or future broker profile.

20A closes only that configuration-and-diagnostics gap. It adds immutable
public profile records and a keyless **fixture diagnostics probe**. It does
not execute identity verification, prepare a signing request, import an
envelope, sign, load a key, connect to a sandbox or production broker, or
alter an existing Increment 19 record.

The fixture diagnostics probe establishes only that a source-checkout fixture
contract is callable and reports the expected public implementation pin. It
does not establish that a signing broker is healthy, that a key is available,
that an identity is valid, or that an action is authorized.

## 2. Governing baseline

Implementation shall conform, in descending order, to:

1. KOS ADR-0009 (§§2, 5, 6, 11) and ADR-0010 (§§5, 6, 9, 12);
2. `INCREMENT-19-IDM-BACKED-IDENTITY-AND-SIGNED-EVIDENCE.md` and the 19A–19D
   closeouts;
3. `IDM-COMPATIBILITY-BASELINE-0001.md`;
4. IDM v1 commit/tree stated in §0;
5. `policies/idm-reference-pin.json`; and
6. the CONCLAVE baseline stated in §0.

20A may clarify operational configuration but may not replace the IDM pin,
change the evidence context, weaken a 19A–19D failure rule, or change the
meaning of `audit.sign`.

## 3. Exact scope

20A adds **two immutable configuration record types** and **one immutable
diagnostic-result record type**:

```text
.conclave/identity/verifier-profiles/
.conclave/signing/broker-profiles/
.conclave/diagnostics/
```

The existing workspace layout may add only these three directories for 20A.
No profile is selected by default and no 20A command modifies `identity.mode`.

### 3.1 Canonical profile and reference rules

Every profile and diagnostics artifact is closed-schema, canonical JSON,
content-hashed, immutable, and stored under a SHA-256-safe filename. Raw
EID/MID/KID-like values must never become filenames.

Profile IDs are human labels only. They match:

```text
^[a-z][a-z0-9-]{0,63}$
```

They are not globally unique selectors and may not imply an active profile.
Every `show` or `broker-check` operation receives the exact canonical,
workspace-relative profile reference. There is no mutable “current”, “active”,
or default profile in 20A.

All file references must:

- use canonical workspace-relative POSIX syntax;
- be nonempty and contain no `.` or `..` segment;
- contain no backslash, colon, drive designator, UNC form, alternate data
  stream, or absolute path;
- resolve inside their exact allowlisted workspace area;
- traverse no symlink or Windows reparse point; and
- name a regular file only.

The implementation shall reuse or strengthen the containment protections
already used for Increment 19C stored-record references. A profile may not
name an external filesystem path, including `E:`, B1/B2 directories, vaults,
or a KOS/IDM checkout.

### 3.2 `idm-verifier-profile/0.1.0`

This profile is a public pointer to the one IDM implementation pin a workspace
expects to use later. It is not a trust-input set and does not verify any
identity or trust material.

Required fields:

- profile and schema version;
- profile ID;
- exact implementation identity copied from the existing pin: package,
  version, import name, commit, tree, wheel filename/hash, source archive
  hash, provisioning and classification;
- one canonical reference to an expected future
  `identity/trust-inputs/` record; this is syntactically validated only in
  20A and is not loaded as verification input;
- expected trust-domain identifier;
- creation actor, creation time, `authority_effect: none`,
  `decision_effect: none`, `membership_effect: none`,
  `action_execution_allowed: false`; and
- content hash.

At create and check time, every implementation field must exactly equal
`policies/idm-reference-pin.json`. No field may be inferred from an installed
package, a floating branch, a URL, or an external directory.

### 3.3 `broker-transport-profile/0.1.0`

This profile describes a future external evidence broker boundary. It neither
creates a network connection nor possesses a credential.

Required fields:

- profile and schema version;
- profile ID;
- classification: exactly `fixture-only` or `sandbox`;
- canonical verifier-profile reference and exact verifier-profile content
  hash;
- transport identifier, not a path or URL:
  - `fixture:conclave-19d-diagnostics` for the sole 20A fixture mode; or
  - `sandbox:<safe-label>` for a stored but unusable-in-20A sandbox profile;
- required IDM evidence context, exactly `conclave-evidence/1.0`;
- credential reference:
  - exactly `none` for `fixture-only`; or
  - an `env:<UPPERCASE_NAME>` syntactic selector for `sandbox`;
- creation actor, creation time, `authority_effect: none`,
  `decision_effect: none`, `membership_effect: none`,
  `action_execution_allowed: false`; and
- content hash.

A credential reference is a label, never a value. 20A shall never call
`os.getenv`, contact a credential manager, inspect a vault, open a file, or
otherwise dereference it. Inline credential values, paths, URIs, whitespace,
and any reference outside the grammar above are refused syntactically.

The `sandbox` classification is storable only to permit future explicit 20B
configuration work. `broker-check` must return `FAIL` with
`SANDBOX_TRANSPORT_NOT_AUTHORIZED` for it and must perform no network I/O.

### 3.4 `diagnostics-result/0.1.0`

`broker-check` is a mutating evidence operation because it writes this
immutable result. It is not a read-only command.

Required fields:

- profile and schema version;
- check kind, exactly `fixture_broker_diagnostics`;
- broker-profile and verifier-profile references and content hashes;
- checked implementation pin hash and public implementation identity;
- status, exactly `PASS` or `FAIL`;
- deterministic ordered reason codes;
- `checked_at` and `time_source_classification: diagnostic-local`;
- probe protocol/classification result, if the keyless probe returned one;
- `authority_effect: none`, `decision_effect: none`, `membership_effect: none`,
  `action_execution_allowed: false`; and
- content hash.

`checked_at` is a local operational timestamp only. It is not trusted time and
cannot support identity verification, signed-evidence verification, attested
mode, a decision, membership, authority, or any production eligibility claim.

Each invocation writes a content-addressed immutable result. An identical byte
retry is idempotent; a new local check normally produces a distinct record due
to `checked_at`. Results are retained rather than overwritten.

Each newly written diagnostics result creates one factual system ledger event
containing only the result reference/hash, profile hashes, status and reason
codes. The event must state authority, decision and membership effects as
`none`. Reconciliation may
restore that event only from the immutable diagnostics result; it may not infer
broker availability, verification PASS, signing, approval, authority, or
membership.

### 3.5 Fixture diagnostics probe

20A must not call the existing 19D fixture signing broker as a health check:
that harness correctly requires a signing request and a `.fixture-only.key`.

Instead, 20A may add one **test-only, non-packaged, keyless** fixture probe
under `tests/fixtures/`. It must:

- require both a dedicated command flag and an explicit fixture-only
  environment marker;
- accept no key path, passphrase, credential, signing request, envelope,
  workspace artifact, or network endpoint;
- create no `.cose` envelope and perform no signing operation;
- emit one bounded public canonical report containing only the fixture
  classification, fixed probe protocol, and the public IDM pin identity; and
- fail closed when run outside a source checkout or without its explicit
  fixture marker.

The 20A runtime invokes this probe only for
`fixture:conclave-19d-diagnostics`. In an installed distribution without the
test fixture, it returns `FAIL` with `FIXTURE_PROBE_UNAVAILABLE`; it must never
substitute a local success or fall back to a real broker.

This probe demonstrates a fixture subprocess contract, not broker health or
production readiness.

### 3.6 CLI surface

```text
conclave identity verifier-profile create
conclave identity verifier-profile show --profile <canonical-reference>
conclave evidence broker-profile create
conclave evidence broker-profile show --profile <canonical-reference>
conclave evidence broker-check --broker-profile <canonical-reference>
```

`create` never overwrites. A revised configuration is a new immutable profile
record with a new exact reference. `show` and `broker-check` never search by
label, choose a preferred profile, or create a profile as a side effect.

20A shall not add, modify, invoke, or rely on an identity-verification,
signing-request, envelope-import, signing, allocation, issuance, or
membership command. Existing Increment 19 library behavior remains unchanged.

## 4. Fail-closed rules

20A fails closed for at least:

- any pin field differing from `policies/idm-reference-pin.json`;
- an unknown field, unknown schema version, malformed content hash, unsafe
  profile ID, or invalid record reference;
- any external, absolute, drive, UNC, traversal, backslash, ADS, symlink,
  reparse-point, directory, or non-regular-file reference;
- a broker classification other than `fixture-only` or `sandbox`;
- a fixture profile not using `fixture:conclave-19d-diagnostics` and
  credential reference `none`;
- a sandbox profile with a malformed credential-reference selector;
- an attempt to resolve or display a credential value;
- no explicitly supplied profile, a missing profile, a profile-hash mismatch,
  or a broker profile pointing at a different verifier-profile hash;
- a fixture probe that is unavailable, malformed, unmarked, returns unknown
  fields, reports the wrong classification, or reports a pin mismatch;
- any sandbox `broker-check` invocation;
- any network socket, HTTP client, subprocess argument, or error output that
  would expose a credential, external custody path, unredacted response body,
  or secret; and
- any attempt to use the diagnostic result as an identity PASS or evidence
  binding.

20A profiles contain no trust bytes, identity artifact, key, registry,
revocation statement, or offline-custody reference. Because external paths
are refused, 20A cannot import B1/B2 material. It does not claim to recognize
arbitrarily copied historical bytes inside a later workspace artifact; that is
outside this configuration-only stage.

## 5. Logging and error policy

Allowed output and artifact fields are limited to profile ID, canonical
workspace-relative reference, public pin values, classification, status,
reason codes, public content hashes, and `diagnostic-local` timestamp.

Forbidden everywhere—CLI stdout/stderr, exceptions, logs, records and
ledger payloads—are private keys, passphrases, credential values, bearer
tokens, vault data, external full paths, raw broker responses, and decrypted
or protected fields. Adapter/probe exceptions must be converted to stable
reason codes before output or storage.

## 6. Compatibility and migration

- Existing `local`, `verify`, and `attested` workspaces behave exactly as
  before when no 20A profile is created.
- 20A creates no profile by default and does not alter `identity.mode`.
- No profile changes, re-hashes, or reinterprets a 19A trust input, actor
  binding, verification result, signing request, envelope, binding, gate,
  receipt, or checkpoint.
- Profile creation has no gate, decision, membership, or authority effect.
- A pre-20A workspace without any new directory must remain readable and
  behaviorally identical.

## 7. Required acceptance evidence

At the exact 20A PR head and again after merge on protected `main`, all of the
following must pass on Windows/Python 3.12, Ubuntu/Python 3.13 and
macOS/Python 3.12:

1. verifier and broker profile creation, exact-reference show, reload, closed
   schema validation, immutable write behavior and no-overwrite conflict;
2. deterministic pin mismatch rejection for commit, tree, wheel filename,
   wheel hash, source hash, provisioning, and classification;
3. reference safety rejection for absolute, drive, UNC, backslash, ADS,
   traversal, symlink, reparse point, directory, and non-regular-file cases;
4. no implicit/default/active profile behavior and no `identity.mode` change;
5. keyless fixture probe success in a source checkout, including exact public
   pin comparison and no key, request, envelope, signing, or network use;
6. deterministic failure when the probe is unavailable, unmarked, malformed,
   mismatched, or invoked with a sandbox profile;
7. a secret-non-dereference test with a sentinel environment value proving
   20A never reads or emits it, plus stdout/stderr/artifact/ledger redaction
   scans;
8. diagnostics-result content-addressing, retry behavior, factual ledger
   event and no-inference reconciliation behavior;
9. regression coverage proving no existing Increment 19 verification,
   evidence, gating, provider, routing, concurrency, synthesis, or legacy
   workspace behavior changes; and
10. the complete existing suite remains green. The pre-implementation
    baseline is 892 passed with one platform-conditional symlink skip.

## 8. Explicit non-authorization

This revised draft does not authorize:

- implementation, push, pull request, merge, release, tag, deployment, or
  production reliance;
- identity verification execution, signing-request preparation, envelope
  import, signing, key loading, key generation, credential lookup, vault
  lookup, or passphrase entry;
- sandbox or production broker transport, network I/O, or a real broker
  health claim;
- access to `E:`, any offline custody, B1/B2 material, a private key,
  passphrase, bearer token, or vault;
- trust-domain bootstrap; EID, MID, RID, VID, UUIDv7, or K1 allocation;
  identity issuance; membership; constitutional action; or ratification;
- changes to KOS, IDM, ADR-0009, ADR-0010, or the Constitution; or
- any change to the authority-neutral meaning of Increment 19 evidence.

## 9. Freeze decision required

Before this protocol becomes frozen, Arthur must confirm that:

1. 20A is limited to the three record types, the keyless fixture diagnostics
   probe, the five stated CLI commands, tests and documentation;
2. sandbox is storable but not callable until 20B;
3. no credential value may be dereferenced in 20A;
4. no keyless fixture result will be described as broker health, signing
   readiness, identity PASS, authority, membership, or production readiness;
5. implementation remains a separately authorized next stage; and
6. no push or PR occurs until separately authorized.
