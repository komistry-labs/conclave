# Stage 21C method reset proposal

Status: PROPOSED METHOD / LOCAL DRAFT / NOT ADOPTED
Date: 2026-09-19

## 1. Decision in plain language

Prove the evidence workflow with fixtures; qualify a concrete external key
provider; then write the smallest offline ceremony supported by that provider.
Do not continue extending the rejected generic custody architecture.

This proposal is a design recommendation. It does not amend a frozen protocol,
authorize implementation, select equipment, generate keys, or confer trust.

## 2. Verified baseline and why the method changes

Local base: `154394c570a9919fc00b7c00779f565f742508e2`.

- Frozen Stage 21C readiness protocol SHA-256:
  `d3701754c7ab782835bc92db07c055509e415a69765373ed5cd30f250164b257`.
- Frozen collection protocol SHA-256:
  `6ea468c1cdd3a4ac0befecd3ffa3c2c26cfb51218902fb3af20366e4dbbb91c2`.
- Failed ceremony candidate SHA-256:
  `1b11eba699e64dfca11e1f2a9cb6e7a5b43174cb0ab5bebb69dda69993f63057`.
- Failed ceremony candidate blob:
  `4d881064a596b45034bbe2c30ca576cd4c0464fa`.

The frozen requirements include two distinct external Ed25519 purposes,
independent principals, exact public trust bindings, offline custody, and an
external provider that releases no private key bytes and permits only the
approved verifier's bounded signing operation. Readiness section 4.3 and
collection section 20 require real trust authorizations before implementation.
The collection protocol also requires executable identity and one-use release
enforcement; possession of an ordinary signing device alone is insufficient.

The rejected draft additionally designs volume encryption, custom envelopes,
eight custody roles, generalized recovery, global custody/lifecycle ledgers,
signed audits, and device-monitor infrastructure. These are draft design
choices; their review findings must be retained, but they are not all inherited
requirements of the frozen two-purpose signature contract.

Successive repairs introduced new dependencies, including receipts referring to
future receipts, offline steps requiring a later online publication, and final
inventories depending on evidence created after export. Another prose expansion
does not demonstrate that an available provider can execute the procedure.

## 3. Work packages and gates

| Package | Concrete output | Completion condition |
|---|---|---|
| A. Small sequencing erratum | Explicit fixture-only exception to readiness 4.3 and collection 20 | Reviewed and adopted before implementation |
| B. Evidence workflow prototype | Disposable fixture executable, schemas, failure cases, dependency checks | Deterministic outcomes and independent review; no operational artifact |
| C. Provider qualification | One identified provider, exact versions, custody owner, capability evidence | Every mandatory capability demonstrated or recorded unavailable |
| D. Provider-specific ceremony | Instructions, bounded inputs/outputs, failure steps, custody acknowledgement | Review of a procedure the selected provider can perform |
| E. Operational enrollment | Separately authorized offline generation, external acceptance and exact trust objects | Public evidence accepted and exact operational build independently approved |

Packages B and C may be planned together. B's implementation awaits A plus
implementation authority. C may begin with documentary assessment; procurement,
installation, disposable-key experiments, and real enrollment require their
own applicable authorization. E cannot be inferred from success in B.

## 4. Fixture prototype boundary

Use fixed public cryptographic test vectors or clearly designated disposable
test keys, synthetic principals/repositories, and deterministic local fixtures.
The prototype has no live GitHub transport, credential discovery, operational
key provider, operational trust loader, or merge path. Test seeds, if introduced
under later test authority, are public fixtures and permanently ineligible for
operational use.

Use a separately identifiable test executable/package. There is no environment
variable or runtime switch that turns it into an operational build. Keep test
provenance in an enclosing fixture artifact; do not add fields to frozen signed
record schemas. A test result named `ready` is a simulated outcome only.

Acceptance must cover known-good and altered signatures, wrong purpose,
wrong repository/principal, stale/expired/revoked trust, conflicting trust,
tampered evidence, missing evidence, and interrupted collection. Packaging
checks prove the test artifact cannot acquire live credentials or load real
custody material. Negative tests must demonstrate rejection, not merely match
textual declarations. Windows, Linux, and macOS evidence is required for claims
about those platforms; none is claimed by this document.

Any future operational build separately pins the exact accepted trust objects,
excludes fixture keys and providers, receives fresh package review, and remains
subject to all existing operational gates.

## 5. Qualify the provider before designing custody

Do not select a vendor from feature names or assume a hardware token satisfies
the frozen contract. Record exact evidence for:

1. Offline Ed25519 generation and canonical public-key/signature output.
2. Separation of the two purposes and their controlling principals.
3. No private-key export to CONCLAVE or the external verifier.
4. Enforcement of the approved executable identity and one-use release state.
5. Rejection of caller-selected signing requests and unapproved executables.
6. Documented custody, loss, disablement, and replacement behavior.
7. A reproducible qualification procedure on the actual execution platform.

Each capability receives DEMONSTRATED, DOCUMENTED-ONLY, UNAVAILABLE, or NOT-RUN,
with exact source/version and evidence location. Only DEMONSTRATED closes an
execution gate. A provider that supports Ed25519 but cannot enforce item 4 or 5
does not qualify. No particular provider is qualified by this proposal.

Avoid designing a second encryption layer, a backup scheme, or a custom device
attestation system until an actual requirement and provider capability justify
it. Provider limitations are reported as limitations, never papered over with
an opaque evidence hash.

## 6. Smaller initial operational scope

Propose a first enrollment with no seed backup, seed reconstruction, or recovery
signing path. Loss or suspected compromise stops use and requires governed
replacement with new keys and new trust bindings. This trades availability for
a smaller initial implementation. It requires explicit acceptance before the
ceremony is frozen; it is not already an adopted policy.

Separate control of the two signing purposes and independent witnessing remain.
The eight-person structure of the failed draft is not automatically inherited.
The qualified provider's actual custody model must be reviewed before actors
are appointed. Review must establish what one compromised custodian can do.

Keep a bounded enrollment evidence bundle for the two keys, plus an external
record of acceptance and subsequent disablement/replacement. Do not build a
general institutional custody product inside the ceremony plan. Existing
governed processes may be referenced only when their exact records and owners
are identified; otherwise that dependency remains open.

No recovery promise, high-availability claim, or production claim is made.

## 7. One-way evidence ordering

Every arrow below means that the later object may reference an already fixed
earlier object. No earlier object contains the hash of a later one.

1. Provider qualification and exact tool identity.
2. Arthur's separately authenticated execution authority.
3. Provider generation receipt containing permitted public facts only.
4. Custody acknowledgements referring to that receipt.
5. Independent public-evidence verification receipt.
6. Evidence manifest listing those completed objects; it excludes itself and
   all future acceptance/trust/publication records.
7. External acceptance record referring to the manifest.
8. Public trust proposal referring to accepted public facts.
9. Arthur's issuance decision referring to the proposal.
10. Frozen-schema trust object referring to the issuance decision.
11. Separate acceptance/build-pin decision referring to the trust object.

Offline activity ends before external acceptance or Git publication. No offline
process waits for a future merge, and publication is not retroactively inserted
into the offline manifest. Any later transport receipt refers to the existing
manifest; it does not change it. The provider-specific plan must specify how
evidence leaves its actual hardware boundary and who verifies that transfer.

## 8. Review the interfaces before the prose

Before requesting five seats, require a local precheck of record dependencies,
schema closure, signer/key mapping, bounds, time rules, and every failure exit.
Reviewers first assess whether the chosen provider and end-to-end procedure are
feasible. Detailed Council review follows a stable candidate with those checks.

A Council verdict remains advisory. Reviews performed by assistant subagents
must be labelled as internal technical review; they do not independently
establish another provider's assurance or replace Arthur's disposition.

Do not claim PASS from a simplified scope merely because old findings were
removed. Map each retained finding to a demonstrated test, a provider gate, or
an expressly deferred capability. No PASS target overrides a real blocker.

## 9. Checks performed on this proposal

The in-session abstract graph has eleven nodes in the order above. Its
dependency check found no cycle. It rejected three deliberate cyclic variants:
generation receipt depending on the manifest, manifest depending on acceptance,
and issuance decision depending on the trust object. Missing dependencies and
duplicate node identifiers were also rejected.

These are abstract ordering checks, not cryptographic, provider, runtime, or
cross-platform acceptance evidence. The candidate has not received Council or
independent approval.

## 10. Required next decision

Adopt the bounded fixture-first sequencing erratum after review and authorize
the fixture prototype separately. Accept or reject the proposed initial
loss-and-replacement policy before provider-specific ceremony freeze. No key
purchase, creation, migration, or deletion is needed for the present decision.

The failed plan and Reviews 0001-0005 remain unchanged local historical files.
The frozen protocols remain unchanged. This proposal is local drafting only.
