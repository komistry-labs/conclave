# CONCLAVE Stage 21C Offline Two-Key Ceremony Plan — Council Review 0001

Status: `COMPLETE / FAIL_EXACT_DRAFT / REMEDIATION REQUIRED`

Review date: 2026-09-19

## 1. Exact reviewed object

- candidate: `INCREMENT-21C-OFFLINE-TWO-KEY-CEREMONY-PLAN.md`
- candidate SHA-256:
  `a6fb191334c66837cb201d7896f79f552e48ec46a9c18df20774528f3ca3058b`
- candidate Git blob:
  `f27fb8979226a95ed92b351bb8ab6822714f3c91`
- candidate size: `31,449` bytes
- candidate length: `668` LF-terminated lines
- candidate base:
  `154394c570a9919fc00b7c00779f565f742508e2`
- controlling Stage 21C protocol SHA-256:
  `d3701754c7ab782835bc92db07c055509e415a69765373ed5cd30f250164b257`
- controlling Stage 21C protocol Git blob:
  `6553d2371c534e0c8159aa9a8ddd2fec964dc208`
- controlling collection-protocol SHA-256:
  `6ea468c1cdd3a4ac0befecd3ffa3c2c26cfb51218902fb3af20366e4dbbb91c2`
- controlling collection-protocol Git blob:
  `f51fb51ed85e93b12ad6ecd74d44b56963b17faa`

Every seat independently verified the candidate SHA-256 and Git blob before
review. No reviewer edited the candidate. The verdicts bind only the exact
object above and transfer to no amended file.

## 2. Council disposition

| Seat | Review domain | Verdict |
|---|---|---|
| 1 | Governance | `FAIL_EXACT_DRAFT` |
| 2 | Cryptography | `PASS_EXACT_DRAFT` |
| 3 | Custody and operations | `FAIL_EXACT_DRAFT` |
| 4 | Security and threat model | `FAIL_EXACT_DRAFT` |
| 5 | Testability and operability | `FAIL_EXACT_DRAFT` |

Aggregate disposition:

`1/5 PASS_EXACT_DRAFT / 4/5 FAIL_EXACT_DRAFT / REMEDIATION REQUIRED`

The draft is not eligible for freeze, ceremony-tool implementation, execution
authorization, key generation, or any later trust or runtime operation.

## 3. Consolidated blocking findings

### CR-0001-01 — Later trust authorization retains a hash cycle

The frozen Stage 21C trust-authorization object contains
`arthur_decision_sha256`. The candidate's final sequence says complete trust-
authorization candidates are drafted from ceremony facts and then approved,
but does not define how the decision hash can exist before the canonical object
that embeds it without the approving decision circularly binding that object.

Required remediation: define one acyclic sequence: fixed public-facts proposal;
external Arthur issuance decision binding those facts without referencing the
not-yet-derived trust-authorization hash; canonical trust authorization
containing the issuance-decision hash; independent exact-object verification;
and a separate acceptance/build-pin record referencing the completed object's
hash. Identify exactly which decision fills `arthur_decision_sha256` and which
later act activates or build-pins the authorization.

### CR-0001-02 — Recovery custody and passphrase holders are not closed

The invariants require different custodians, but the actor model permits one
recovery custodian to hold both recovery media and the manifest provides only
one recovery-custodian identity. It does not identify the two recovery-
passphrase holders, define all role collisions, bind separate storage, or
define the recovery quorum.

Required remediation: identify separate control-attestor and human-authorizer
recovery-media custodians and all four passphrase holders; require the two
recovery roles to be distinct; state exact permitted and prohibited overlap
with primary custodians, operator, witness, Arthur, configured human, attestor,
and reviewers; bind handoff receipts and storage commitments; and define the
two-person recovery authorization and quorum.

### CR-0001-03 — Independent result verification is not build-pinned

The candidate requires operator and witness recomputation using a separate
approved verifier but binds only the ceremony executable. No verifier bundle,
executable, dependencies, environment, device, or offline transfer path is in
the manifest.

Required remediation: bind an exact verifier bundle, executable, dependency
inventory, environment, and independent device, plus a one-way or tightly
bounded offline evidence-transfer procedure. Alternatively define a separately
invocable verifier mode in the same reviewed bundle while preserving separate
execution, device, and human recomputation.

### CR-0001-04 — Quarantine and retirement ineligibility is unenforceable

The draft promises quarantined key IDs and public keys can never activate, but
defines no canonical quarantine/retirement registry, authoritative location,
update rule, conflict handling, or mandatory consultation gate.

Required remediation: define a closed, secret-free, content-addressed registry
and immutable event objects covering ceremony ID, purpose, key ID, public-key
fingerprint when known, state, reason, authority, and time. Later trust-
authorization creation and activation must fail closed on a matching ceremony,
key ID, or fingerprint and on unavailable, conflicting, or incomplete registry
state.

### CR-0001-05 — New schemas and the encrypted envelope are not serialization-closed

The manifest, public facts, result, abort, witness, and envelope objects do not
expressly inherit or define a complete primitive grammar, canonicalization,
field ceilings, timestamp and hash syntax, null rules, or total reason-code
vocabulary. The CBOR envelope does not freeze exact keys, primitive types,
integer bounds, byte/text representation, deterministic-CBOR profile, complete
plaintext map, ciphertext/tag layout, or unambiguous associated data. A
canonical map has no semantic concept of fields "preceding" ciphertext.

Required remediation: define or expressly inherit a complete closed grammar
for every new object; specify exact size and count ceilings; freeze the
deterministic-CBOR profile and every envelope member; define associated data as
one exact named canonical map; state nonce, salt, tag, ciphertext, and plaintext
lengths; close the reason-code vocabulary; and require cross-platform golden
vectors for every serialization and rejection path.

### CR-0001-06 — Failure after the first successful key has no total disposition

The control-attestor key may complete before human-authorizer generation. A
failure during the second flow explicitly quarantines the human media but does
not deterministically state whether the completed control-attestor key, ID,
envelopes, media, and public facts remain eligible, are quarantined, are
destroyed, or are permanently retired.

Required remediation: define a total ceremony state machine for every failure
point. Every generated seed, key ID, public fingerprint, envelope, medium, and
result must have exactly one terminal disposition. The default safe rule should
make the ceremony atomic for eligibility: unless both keys and all evidence
complete, neither key may later activate.

### CR-0001-07 — Mandatory verification claims lack measurement semantics

The plan serializes claims such as network absence, secret-scan pass, cleanup,
logging absence, swap/hibernation state, crash-dump absence, media state, and
displayed-fact verification without assigning exact producers, scopes,
measurements, retained evidence, or stable failures. A failed outbound probe
does not prove network absence, and software cannot generally prove that an
operating system will never emit a crash dump.

Required remediation: classify every predicate as machine-verified,
configuration-attested, physically witnessed, or not provable; define its exact
producer, procedure, evidence, time, scope, and failure code; replace universal
claims with bounded observations where necessary; define required failure
injections and expected terminal artifacts; and add a closed acceptance-evidence
schema.

### CR-0001-08 — Media and encryption-profile commitments hash undefined objects

The manifest contains aggregate media-inventory and encryption-profile hashes
but no closed objects whose hashes can be reproduced. Device roles, permitted
device facts, sanitization state, encryption implementation, and supply path
cannot be mechanically checked, and media role swapping is not closed.

Required remediation: define canonical per-medium inventory and role-binding
objects, custody-media encryption profiles, key-envelope profiles, availability
rules, and verification procedures. Bind each of the five media roles to one
exact inventory entry rather than relying only on primary/recovery aggregates.

### CR-0001-09 — Public evidence has no independent ceremony-origin authentication

Proofs made by newly generated keys and ordinary content hashes establish
self-consistency, not origin. The witness object is unsigned, and physical
custody receipts do not bind the result hash or both public fingerprints. An
attacker replacing the export evidence could generate replacement keys and a
self-consistent result using public manifest facts.

Required remediation: require an independently authenticated origin commitment
over at least the manifest hash, execution-authorization hash, result or abort
hash, both public-key fingerprints, and witness identity. It must use a
pre-existing governed authentication mechanism or two independently conveyed
and verifiable witnessed records; newly generated ceremony keys cannot provide
this origin anchor. Custody receipts must bind envelope hashes, media
commitments, public fingerprints, and the result hash.

### CR-0001-10 — Offline host and boot-chain trust are optional and incomplete

The manifest binds an image and tool but not physical host identity, firmware,
UEFI configuration, boot-chain policy, or peripheral-controller provenance.
The expected boot measurement may be null. Compromised firmware could capture
secrets or alter approved media while every current check passes.

Required remediation: bind a specific host inventory, firmware/UEFI state,
boot policy, peripheral-controller inventory, and mandatory independently
verified boot measurement or define an equivalently strong disposable-hardware
procedure. Inability to establish the selected hardware root must abort before
secret creation.

### CR-0001-11 — Public-evidence media may be present while secrets exist

The plan permits the writable public-evidence medium to remain attached during
both secret-bearing key-generation flows. Inventory does not prove that USB
firmware exposes only storage; a malicious composite device could inject input
or retain secret-bearing data.

Required remediation: keep public-evidence media physically absent throughout
every secret-bearing phase. Attach it only after all plaintext state is
zeroized and custody media are unmounted, or use a separately reviewed one-way
export mechanism. Enumerate allowed device classes and interfaces and abort on
unexpected enumeration or re-enumeration.

### CR-0001-12 — Passphrase entropy is not profile-bound or reproducible

The plan claims at least 90 bits from an approved word list but binds no list,
selection algorithm, rejection rule, randomness source, separator, byte
encoding, normalization, or entropy calculation. Re-entry checks transcription,
not unbiased selection.

Required remediation: bind an exact reviewed passphrase-generation profile and
tool, including word-list hash, sampling and rejection algorithm, randomness
source, word count, separator, ASCII or Unicode normalization rule, UTF-8 byte
policy, and entropy derivation. Retain only non-secret compliance evidence.
Define any transient cross-passphrase equality check so no passphrase or
secret-derived diagnostic survives.

## 4. Non-blocking findings retained for remediation review

1. Clarify that primary and recovery readback success covers each of the four
   envelopes independently; per-purpose/per-medium fields are preferred.
2. Pin lowercase `sha256:` plus 64-hex syntax and equate
   `ceremony_manifest_sha256` with the manifest's canonical `content_hash`.
3. The tool review must prove the limits of zeroization across language,
   compiler, runtime, library, and operating-system copies; process termination
   alone is insufficient.
4. Bind public hashes of all four encrypted envelopes into the result and
   custody receipts without placing ciphertext in Git or chat.
5. Define seal inventory and periodic custody audits before execution.
6. Golden vectors should cover noncanonical base64url, malformed key and
   signature lengths, duplicate members, Unicode edge cases, modified purposes,
   modified identifiers, and canonicalization disagreement.
7. Cross-platform acceptance evidence should retain exact build/package hashes,
   platform facts, test totals, skip/xfail totals, golden-vector outcomes,
   failure-injection outcomes, and artifact hashes.

## 5. Findings that passed review

The cryptography seat found no blocker in the draft's high-level key
cryptography. Subject to the closure work above:

- independent CSPRNG draws and distinct principals, purposes, media, salts,
  nonces, and key IDs provide appropriate separation;
- the operational Stage 21C signature domains match the frozen protocol;
- the ceremony proof-of-possession domain is distinct and purpose-bound;
- canonical 32-byte Ed25519 public keys and 64-byte signatures are compatible
  with Stage 21C;
- Argon2id followed by XChaCha20-Poly1305 is a sound envelope construction; and
- failures are generally directed toward quarantine rather than silent success.

These passes do not override the aggregate failure or authorize implementation.

## 6. Required next action

Remediation must create a new exact candidate. Review 0001 and its rejected
candidate remain immutable historical evidence. The remediated candidate must
receive a fresh five-seat review; no Review 0001 verdict carries forward.

This review authorizes no amendment, commit, branch, push, pull request, freeze,
tool implementation, key generation, signature, trust authorization, key
activation, credential access, live GitHub operation, Stage 21D work,
deployment, production use, KOS or IDM change, identity allocation, or
membership activation.
