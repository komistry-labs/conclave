# CONCLAVE Stage 21B Implementation Council Re-review 0001

## Status

`0/5 PASS — CHANGES_REQUIRED`

Review date: 2026-09-10

This is a local review record. It does not freeze or approve the
implementation and grants no authority to commit, push, create or merge a
pull request, access credentials, perform a live GitHub operation, deploy, or
use Stage 21B in production.

## Exact reviewed worktree

- Branch: `feature/increment-21b-bounded-publication`
- Base commit: `c3804e2077bfe38f66623404da51d1bd0478846b`
- Bundle-manifest SHA-256: `4dcf234da23406c36394669f155ba9bf9e639f76aa0880d0b2452f995aac4761`
- Manifest algorithm: concatenate each listed UTF-8 path, one NUL byte, its
  lowercase SHA-256, and one LF byte, in the order below; hash the result with
  SHA-256.

Reviewed file hashes:

1. `src/conclave/github_publication.py` — `efef3d951717561f69afca17dba5f83a4ac2f803ab702d03efb239a1999676c5`
2. `src/conclave/github_publication_records.py` — `f566d6083694fce0eac1bcbd4a3b3be2f5f356a31af8f7e5497038deba4c99c2`
3. `src/conclave/github_publication_engine.py` — `8ae6dfae004f79aab93c6689f5bbf903602c9041c871d770466324fbd0cf9cae`
4. `src/conclave/ledger.py` — `55b04226fc9a34baaa6841c048123d11e2f50748e110c21ef99757d0e488ad6d`
5. `src/conclave/workspace.py` — `9886543b3411245f76fc55eb45216ceb17b7a7bee3a1c5fbd97ba684eb8f5a96`
6. `tools/conformance_evidence.py` — `495b8db5a776dd78138b944f1f4786a52ea8dc6c4b70bbe2106aedd9775ab8d6`
7. `tools/installed_wheel_probe.py` — `59c2d1d16fbde1abd99c09ef34397f93009b47bfd4099abc03a415ae08397980`
8. `tests/test_github_publication.py` — `b45b208ca103a4489c72859062b841493c5b5f2753080611d0f5ff5e46c99427`
9. `tests/test_conformance_evidence_tool.py` — `533436667f1dc73ee8a32e5b280addc1f2bef15197daf0b983d16ee34449e2d3`
10. `tests/test_installed_wheel_probe.py` — `fa8d5cb3fd0e616806ef4498d5fe7c9cc8f35daaedd5cb9075b35dde1b73f7e2`
11. `INCREMENT-21B-IMPLEMENTATION-REMEDIATION-0001.md` — `e891302a750768e77d0a02cef9dc39353991032c5ae7417fa8e9f5ea43ad9f2e`

The frozen findings were independently rechecked and remain unchanged:

- SHA-256: `d7fe3b0ac171cc8af3ec737531c16f018598582eb94d4391fb6fcca0270c8abb`
- Git blob: `b42d2368ce3741d4995da3c88fc2c3248f3f294f`

## Council verdicts

1. Governance and authority — `CHANGES_REQUIRED`
2. Security and credentials — `CHANGES_REQUIRED`
3. Git and GitHub correctness — `CHANGES_REQUIRED`
4. Evidence and schema integrity — `CHANGES_REQUIRED`
5. Cross-platform and installed-package evidence — `CHANGES_REQUIRED`

## Consolidated blocking findings

### CR-1 — Response provenance remains spoofable

The production package exposes a freely constructible `PublicationResponse`
and accepts a caller-provided response sequence. Matching dictionaries can
produce `proposal_published:true` and a publication ledger event without a
verified provider-authenticated transport receipt or observation chain.
Renaming the former fixture surface did not remove the trust-boundary defect.

### CR-2 — Frozen protocol identities are not pinned

Increment 21, Stage 21A, Stage 21B, and Erratum 0001 hashes are validated only
for syntax or internal equality. The passing fixture uses placeholder repeated
digits. The implementation must pin and negatively test the exact frozen
identifiers, including Stage 21B SHA-256
`b90c97284afec9ac7cef44fd9186b38f9e2a86630e283c593dc2ed95e88384c4`
and Erratum 0001 SHA-256
`f79aae70e15dd90bda10948ee172f77acac3557a87ff2d2f1c35a65a1ed0658e`.

### CR-3 — Durable predecessor closure is incomplete

The evaluator does not carry, reopen, parse, and verify the actual API
profile, repository extension, Task Packet, Handoff, scope review, recursive
source authorization, source intent, source claim, source lease evidence, and
provider-key records. Mutually consistent references can therefore name
missing or unrelated objects. This also leaves allowed-head-prefix,
prohibited-path, and `live_use_allowed:false` policy unverified.

### CR-4 — Head-policy evidence is not an accepted Stage 21A chain

The two Stage-21B-specific branch-rule and ruleset boolean records do not bind
the Stage 21A authorization, intent, claim, lease, operation, pagination,
visibility, and factual observation provenance required by the frozen gate.

### CR-5 — Reconciliation is neither complete nor compatible with real steps

The reconciliation authorization, intent, claim, and lease are not all
durably stored and reopened. An admission names a lease filename that was not
stored and binds the original publication claim rather than the reconciliation
claim. The receipt omits required predecessor, provider, rate, inventory, and
base-tree-closure bindings.

Normal publication steps hash an expected projection object, while
reconciliation compares that field with the hash of a caller-supplied string;
the current test succeeds only with a synthetic admission. Commit
reconciliation selects `commit.get`, which is absent from the admitted read
keys, and all reconciliation uses a generic identity projection rather than
the operation-specific blob, tree, commit, ref, or pull-request proof.

### CR-6 — Pull-request and terminal classifications are incomplete

The PR creation/final-read projection omits repository numeric identity and
the exact base commit OID. Existing head, base drift, duplicate PR, invalid
ref, and invalid PR conditions collapse into generic dispatch reasons instead
of the frozen reason codes and `REFUSED`/`CONFLICT` outcomes. Receipt reason
codes are not restricted to the closed vocabulary.

### CR-7 — Some post-claim failures lack terminal evidence

After the claim and lease are stored, clock discontinuity and second rate
admission can still raise directly without a receipt or terminal capsule.
Lease-store failure after a retained claim has the same gap.

### CR-8 — Durable schema and sanitization requirements remain open

`PublicationStepAdmission` stores a prohibited floating-point monotonic value,
and arbitrary response projections may include floats or non-finite values.
Receipt and reconciliation failures retain underlying exception causes, and
terminal-capsule failure is silently discarded instead of producing only the
closed sanitized diagnostic.

### CR-9 — Artifact aliases defeat the one-read invariant

Raw references such as `a//b` and `a/./b` normalize to the same filesystem
object but are deduplicated as different strings, permitting the same artifact
to be opened more than once.

### CR-10 — Required installed and platform evidence is incomplete

The installed-wheel probe verifies imports, one blob hash, and sequence
length; it does not run a governed publication transaction, durable receipt,
ledger event, terminal path, or reconciliation from the installed wheel.
Valid `receipt_present` and `failure_capsule_present` reconciliation paths,
several concurrency and failure boundaries, and exact-current Ubuntu 3.12,
Ubuntu 3.13, and macOS 3.12 evidence remain absent.

## Positive evidence retained

- The focused Stage 21B and tool suite passed 101 tests.
- The complete Windows suite passed 1,183 tests with two permitted
  non-Stage-21B environment-dependent skips.
- Wheel and source distribution construction passed.
- Clean installed-wheel help, version, and limited publication-module probes
  passed.
- Package inventory, static scan, and secret/member scan passed.
- No socket, HTTP, subprocess Git, credential resolver, token, signing,
  identity, membership, KOS, IDM, deployment, or production operation was
  introduced in the Stage 21B modules.
- Descriptor-relative no-follow access exists where supported, with Windows
  reparse checks and opened-file identity comparison.
- Publication evidence and ledger sequencing are materially improved.

## Disposition

The exact reviewed worktree is not suitable to freeze, commit, push, or create
a pull request. Stage 21B remains local and unfrozen. All CR-1 through CR-10
must be corrected and the replacement exact worktree must receive a fresh 5/5
Council re-review before any freeze request.
