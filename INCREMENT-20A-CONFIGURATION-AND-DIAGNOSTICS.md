# Increment 20A — Configuration and diagnostics

## Status

**Protocol frozen for implementation.** Content confirmed by Arthur,
2026-08-18. §11's sandbox-scope question is resolved: 20A's availability
check is fixture-only end to end; `sandbox` is a storable classification
value but `broker-check` refuses to run against it in this stage (deferred
to 20B).

At the time of freeze, implementation has not begun. This freeze authorizes
this protocol record and implementation preflight only; runtime
implementation of 20A requires a separate, subsequent authorization, exactly
as 19A required its own authorization after the overall Increment 19
protocol was frozen. 20B–20D remain out of scope and are not authorized by
this document even in outline.

## 0. Preflight performed for this proposal (read-only)

Re-checked immediately before drafting, against the handoff document and
current `main`:

| Item | Value |
|---|---|
| `origin/main` | `22d56a37ec12924afd464ac127a882a79a821d53` (unchanged since the earlier session preflight; no drift) |
| Local `main` HEAD | same — up to date, `git status --short` empty |
| `v0.7.0` tag | unchanged, `9c8682373ffbc3279c4bf660eeb147dc21fe60fa` |
| Existing pin file | `policies/idm-reference-pin.json` confirmed present, fields: `package`, `version`, `import_name`, `commit`, `tree`, `wheel.{filename,sha256}`, `source_archive_sha256`, `provisioning`, `classification` |
| Existing workspace layout | `.conclave/identity/{trust-inputs,bindings,verifications}/`, `.conclave/signing/{requests,envelopes,bindings}/` confirmed present from 19A/19B (`src/conclave/workspace.py`) |
| Existing config key | `identity.mode` confirmed present in workspace config, default `local`, monotonic via `set_identity_mode` (`src/conclave/gating.py`) |

No code was changed. No new commit, branch, or file was added to the
repository.

## 1. Why 20A, narrowly

The v0.8.0 release-readiness review (2026-08-17) found that Increment 19
shipped a verification/evidence *library* with no CLI path to configure which
public IDM verifier or broker a workspace should actually address. 20A closes
only that configuration/diagnostics gap. It does not run a verification, does
not prepare a signing request, and does not import an envelope — those
remain later stages and are explicitly not authorized here.

## 2. Governing baseline

Same descending order as Increment 19 protocol §1, with Increment 19's
frozen protocol and its four closeouts added above IDM/CONCLAVE baseline
identity, since 20A extends that layer and may not reopen or weaken any of
its frozen decisions (Increment 19 protocol §12):

1. KOS ADR-0009 (§§2, 5, 6, 11) and ADR-0010 (§§5, 6, 9, 12);
2. `INCREMENT-19-IDM-BACKED-IDENTITY-AND-SIGNED-EVIDENCE.md` (frozen) and
   `INCREMENT-19A` through `INCREMENT-19D` closeouts;
3. `IDM-COMPATIBILITY-BASELINE-0001.md`;
4. IDM v1 commit `3769ce3943c87e6a5a72bf94b0efdaa2b11c3bd2`, tree
   `425f650696a798c10f2a553781fee45e0950dc2a` — unchanged from Increment 19;
5. `policies/idm-reference-pin.json` — the existing machine-readable
   implementation pin 20A must validate against, not replace; and
6. CONCLAVE `main` at `22d56a37ec12924afd464ac127a882a79a821d53`.

## 3. Exact scope

20A adds exactly two new closed, immutable, workspace-scoped configuration
record types, plus CLI commands to create, show, and diagnose them. Nothing
else.

### 3.1 `idm-verifier-profile/0.1.0`

A named pointer describing which public IDM verifier a workspace is
configured to use. It is **not** a verification-ready trust-input-set — it
does not itself embed the revocation/time evidence bytes 19A's
`idm-trust-input-set/0.1.0` requires. It records:

- profile id/label and schema version;
- implementation identity: commit, tree, wheel filename+SHA-256, source
  archive SHA-256 — required to match `policies/idm-reference-pin.json`
  exactly at validation time;
- workspace-relative references (not inline bytes) to where trust-bundle
  bytes, revocation evidence, and time-source configuration are *expected*
  to be loaded from when an actual verification is later requested (20B/C);
- accepted trust-domain identifier;
- creation actor, creation time, content hash.

### 3.2 `broker-transport-profile/0.1.0`

A named pointer describing which external evidence-signing broker a
workspace is configured to address for future signing-request flows
(20B/C). It records:

- profile id/label and schema version;
- classification: exactly `fixture-only` or `sandbox` — no other value is
  accepted by this stage (see §5);
- transport reference (workspace-relative path or profile-scoped
  identifier — never a bare network URL with embedded credentials);
- required IDM context (`conclave-evidence/1.0`, fixed, matching 19B/19D);
- a *credential reference* (a pointer to where a provider/broker credential
  is expected to be supplied at call time, e.g. an environment variable
  name) — never the credential value itself;
- creation actor, creation time, content hash.

### 3.3 Availability/diagnostics operation

A read-only, non-mutating operation that:

- loads a named verifier and/or broker profile;
- checks the verifier profile's implementation identity against
  `policies/idm-reference-pin.json` (fails closed on any mismatch);
- for `fixture-only` broker profiles, checks that the fixture harness
  (`tests/fixtures/idm_fixture_broker.py`, gated by the existing 19D flags
  `--fixture-only` and `CONCLAVE_FIXTURE_BROKER=1`) is reachable and reports
  a matching implementation identity;
- for `sandbox` broker profiles: refused per §11 — not authorized in 20A;
- produces one closed `diagnostics-result/0.1.0` record (see §6) — never a
  verification result, never a signing result.

### 3.4 CLI surface (proposed names, subject to review)

```text
conclave identity verifier-profile set
conclave identity verifier-profile show
conclave evidence broker-profile set
conclave evidence broker-profile show
conclave evidence broker-check
```

No other command is added. In particular, this stage adds **no**
`identity verify`, **no** `evidence prepare-signing-request`, and **no**
`evidence import-envelope` — those remain out of scope for 20A specifically
(proposed for 20B/20C).

## 4. Fail-closed rules

20A fails closed for at least:

- a verifier profile whose commit, tree, wheel hash, or source-archive hash
  does not exactly match `policies/idm-reference-pin.json`;
- a verifier or broker profile containing an unknown/extra field (closed
  schema, `extra="forbid"`, matching every existing Increment 19 record);
- a broker-transport profile with a classification other than `fixture-only`
  or `sandbox` — `production` or any unrecognized value is refused, not
  downgraded or warned;
- a broker-transport profile whose credential reference is, or resolves at
  validation time to, an inline secret, private key, passphrase, or vault
  path (mirrors Increment 19 §4.1's existing refusal rule verbatim);
- an availability check against a profile that does not exist — no implicit
  default profile is ever assumed;
- an availability check whose broker reports an implementation identity
  that does not match the configured verifier profile's pin;
- an availability check against an unreachable or timed-out broker — this
  reports `FAIL` with a stable reason code, never a silent skip or
  "unknown" status;
- any attempt to construct a profile from a B1/B2 rehearsal trust bundle,
  identity, or key path (mirrors Increment 19 §1's existing refusal rule).

## 5. Authority effects

Every 20A record — both profile types and every diagnostics result — fixes:

- `authority_effect: none`;
- `membership_effect: none`; and
- `action_execution_allowed: false`.

A `diagnostics-result/0.1.0` record is explicitly a **new, distinct**
closed schema, not a reuse or relabeling of `idm-verification-result/0.1.0`.
A broker reporting "reachable" or "healthy," or a verifier profile passing
its hash check, must never be representable as, confused with, or silently
promoted to an identity PASS or a signed-evidence binding. No 20A command
may create, mutate, reference, or count toward an
`idm-verification-result` or `signed-evidence-binding` record.

## 6. `diagnostics-result/0.1.0` (new schema)

- profile reference(s) and hash(es) checked;
- status: exactly `PASS` or `FAIL` (same two-value discipline as Increment
  19's verification result — no partial/warning state);
- deterministic ordered reason codes (reusing Increment 19's reason-code
  vocabulary style);
- evaluation time and time-source classification;
- `authority_effect: none`, `membership_effect: none`,
  `action_execution_allowed: false`;
- content hash.

## 7. Migration behavior

- Existing v0.7 `local` workspaces, and existing Increment-19 `verify`/
  `attested` workspaces, continue operating exactly as before if no verifier
  or broker profile is ever configured. 20A introduces no default profile.
- Configuring a profile is strictly additive and does not itself change
  `identity.mode` — mode changes remain governed solely by 19C's
  `set_identity_mode`, unchanged by this stage.
- Configuring a profile must never retroactively alter, re-hash, or
  reinterpret any existing `idm-trust-input-set`, actor binding, or
  verification result written under 19A/19B/19C.
- No 20A command may create a profile as a side effect of an unrelated
  command (e.g., running `identity show-mode` must not implicitly create an
  empty verifier profile).
- A dedicated regression test must assert that a pre-20A workspace (no
  profile directory present) behaves identically before and after 20A code
  is present, mirroring the existing
  `test_new_and_legacy_workspaces_are_local` pattern from 19C.

## 8. Cross-platform acceptance evidence

All of the following must pass on Windows, Ubuntu, and macOS, at the exact
head of the 20A PR and again post-merge on protected `main`:

1. profile creation, show, and reload round-trip to byte-identical
   canonical JSON and content hash;
2. hash-mismatch rejection (commit/tree/wheel/source) is deterministic and
   identical across platforms;
3. `fixture-only` availability check against the existing 19D fixture
   broker harness succeeds identically across platforms, reusing
   `tests/fixtures/idm_fixture_broker.py` rather than a new broker;
4. diagnostics output contains no secret, credential, or bearer token on
   any platform — enforced by an automated secret-leak scan over captured
   CLI stdout/stderr and any written diagnostic artifact;
5. the complete existing CONCLAVE suite (892 tests plus 1 platform-conditional
   skip as of this freeze) remains green on all three platforms throughout.

## 9. Negative tests (required, non-exhaustive floor)

- tampered/wrong commit, tree, wheel hash, or source-archive hash in a
  verifier profile → refused;
- unknown/extra field in either profile schema → refused;
- broker-transport profile classification `production` (or any value
  outside `{fixture-only, sandbox}`) → refused;
- credential reference that resolves to an inline secret/key/passphrase
  value → refused;
- availability check with no profile configured → explicit fail-closed
  error, not empty success;
- availability check against a broker reporting a mismatched
  implementation identity → `FAIL`;
- availability check against an unreachable/timed-out broker → `FAIL`,
  not silently skipped;
- attempt to point a profile at B1/B2 rehearsal trust/identity material →
  refused;
- attempt to point a profile at `E:` or any offline-custody path → refused.

## 10. Logging and redaction policy

May appear in CLI output, logs, or any written diagnostic artifact:
profile id/label, pinned commit/tree/hash values, broker classification,
reachability boolean, deterministic reason codes, content hashes,
workspace-relative paths.

Must never appear, in any of the same surfaces: private key or passphrase
material, bearer tokens or credential values (only the credential
*reference name* may appear), full filesystem paths outside the workspace,
or unredacted broker response bodies (only their hash and reason code).
This restates Increment 19 §9's logging rule and applies it identically to
every new 20A surface, including thrown exceptions.

## 11. Sandbox broker scope — resolved

**Confirmed by Arthur:** 20A's availability check supports only the
existing `fixture-only` harness. A `sandbox` profile may be *stored*
(the schema accepts the value) but `broker-check` refuses to run against
it in this stage — `FAIL` with a stable reason code, not a silent skip.
Real transport to a `sandbox`-classified broker is deferred to 20B.

## 12. Explicit non-authorization

This protocol freeze does not authorize:

- any identity verification execution (`identity verify`) — remains a later
  stage;
- any signing-request preparation or envelope import (`evidence
  prepare-signing-request`, `evidence import-envelope`) — remain later
  stages;
- real (non-fixture) network transport to any broker, pending §11;
- access to `E:`, any offline custody, or any private key, passphrase, or
  vault;
- production or rehearsal trust-domain bootstrap;
- identity, K1, EID, MID, RID, or VID allocation or issuance;
- signing of any kind;
- membership, constitutional action, or ratification;
- changes to KOS, IDM, ADR-0009, ADR-0010, or the Constitution; or
- deployment, release, or production reliance.

---

*Content frozen by Arthur's confirmation, 2026-08-18. Committed locally,
unpushed, standing by for Arthur's push/PR authorization. No implementation
has occurred.*
