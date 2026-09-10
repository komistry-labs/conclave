# CONCLAVE Stage 21B Implementation Remediation 0001

## Status

LOCAL CORRECTIONS APPLIED — the blockers preserved through Council re-review
0006 have been remediated locally. Independent re-review and cross-platform CI
remain pending. The implementation is not frozen.

## Basis

This record responds to the exact frozen findings at SHA-256
`d7fe3b0ac171cc8af3ec737531c16f018598582eb94d4391fb6fcca0270c8abb`
and Git blob `b42d2368ce3741d4995da3c88fc2c3248f3f294f`.

## Finding closure map

- **P0-1:** added closed proposal-manifest, publication-authorization,
  publication-plan, operation-intent 0.2.0, publication-intent, attempt-claim,
  lease-evidence, separate branch-rules and ruleset observations,
  rate-observation, and complete cross-binding models. Execution now requires
  the complete validated chain and configured human principal.
- **P0-2:** replaced descriptive-label success with canonical request bodies,
  locally recomputed blob/tree/commit OIDs, exact structured response
  projections, ref identity, and head/base/title/body/commit PR identity.
- **P0-3:** added the closed four-variant step-state union. A lost response
  retains its durable read or mutation admission in the terminal receipt.
- **P0-4:** added one canonical v2 reconciliation authorization, intent,
  exclusive claim, read-only lease evidence, terminal-artifact inventory,
  durable read admission/result, single-read classification, and
  no-continuation control.
- **P1-1:** recursive-tree observations now reconstruct and compare their root
  OID before they may claim completeness.
- **P1-2:** base-tree closures now directly bind the source authorization,
  intent, claim, lease evidence, repository extension, source/base timestamps,
  and the 15-minute preparation window.
- **P1-3:** rate evidence is cross-bound by repository/API profile, repository
  and account IDs, App/installation, provider/version/key/fingerprint, API
  version, and resource bucket. Each response must carry the same bounded rate
  scope and cannot expand the local budget.
- **P1-4:** ambiguous ref and PR dispatches now produce `AMBIGUOUS`, never
  `NOT_ATTEMPTED`.
- **P1-5:** canonical request construction now covers blobs, tree overlay,
  commit, ref, PR creation, and the created PR's numeric read route. Artifact
  bytes and commit identity bytes are reverified before dispatch.
- **P1-6:** expanded adversarial evidence includes exact-chain substitution,
  content mutation, request-body inspection, dispatch loss, rate-scope
  substitution, terminal capsule fallback, reconciliation, non-live-runtime
  inspection, and independent Git SHA-1/SHA-256 vectors covering executable,
  symlink, submodule, file/tree-prefix, and non-ASCII entries.

## Second-review closure

The subsequent implementation review identified eight additional binding and
input-control defects. The local correction now:

- validates GitHub owner/repository syntax and derives every route from the
  hash-bound `GitHubRepositoryProfile`, not from free request input;
- carries and cross-checks the full authorization, plan, operation-intent,
  publication-intent, attempt, provider, permission, ref, object, artifact,
  endpoint, request-hash, count, and rate-scope fields;
- computes the proposal aggregate hash from its canonical manifest projection
  and computes a domain-separated publication attempt identifier;
- requires the actual repository profile, base-identity observation, and
  recursive-tree source observation and cross-checks them against the closure;
- reads proposal artifacts once from a controlled root with traversal,
  symlink, reparse-point, non-regular-file, containment, size, and opened-file
  identity checks;
- reopens durable predecessor records by their governed references and refuses
  any byte or content-hash substitution before claiming an attempt;
- records the final numeric pull-request read as derived from the exact retained
  pull-request-create result while preserving the frozen request template; and
- reopens reconciliation predecessors, validates principal and authorization
  lifetime, binds the read to the original attempt and ambiguous admission, and
  inspects the original evidence directory for a structurally valid receipt or
  terminal-failure capsule instead of trusting caller booleans.

## Quick-Council amendment closure

The 0/5 quick-Council review identified further fail-closed and packaging
issues. The immediate local amendment now:

- excludes every concrete test transport, response cassette, and fixture
  executor from the wheel; the installed package exposes a credential-free
  offline evaluator whose transport seam is explicitly untrusted and limited
  to fixture/loopback conformance;
- converts admission persistence, result construction or persistence, response
  loss, rate-observation failure, receipt persistence, terminal-capsule
  persistence, and ledger persistence into bounded, sanitized outcomes while
  preserving every durable predecessor that was successfully written;
- binds the exact 17-record upstream tuple in fixed order across the plan,
  operation intent, publication intent, claim, lease, admission, results, and
  receipt, with explicit reorder, duplicate, and substitution rejection;
- incorporates the full authorization, manifest, and plan records into the
  domain-separated attempt preimage;
- records both wall-clock and monotonic first-dispatch evidence and performs
  the required pre-lease and pre-dispatch rate checks;
- records only the bounded
  `github_proposal_publication_fixture_verified` ledger event after a durable
  fixture receipt, never asserts `proposal_published`, and never records the
  fixture event after terminal persistence failure;
- reads artifacts once by controlled-root descriptor-relative traversal where
  supported, rejects root or component links and Windows reparse points, and
  refuses conflicting duplicate references;
- enforces the frozen 4 KiB commit-message and 256-byte pull-request-title
  ceilings;
- keeps branch-rule and ruleset observations as distinct records and verifies
  both bindings independently; and
- extends installed-wheel and conformance inspection to all Stage 21B runtime
  modules without conditional Stage 21B skips.

## CR-1 through CR-10 correction execution

The replacement correction unit additionally:

- removes the constructible publication-response sequence from the packaged
  trust boundary; the coordinator accepts only raw bounded transport bytes and
  derives every response projection itself;
- pins and negatively tests the exact Increment 21, Stage 21A, Stage 21B, and
  Erratum 0001 protocol identities;
- carries, reopens, and cross-binds the API profile, repository extension,
  Task Packet, Handoff, scope review, recursive-tree source chain, source
  credential-lease evidence, provider key, and full branch/ruleset observation
  chains;
- derives reconciliation identity from a genuine retained publication
  admission and operation-specific blob, tree, commit, ref, or pull-request
  data, admits `commit.get`, and preserves the complete separate reconciliation
  chain in predecessor order;
- binds pull-request repository identity and base commit identity, enforces the
  closed Stage 21B diagnostic vocabulary, and distinguishes base drift,
  existing heads, duplicate proposals, invalid refs, invalid pull requests,
  and invalid Git objects;
- terminalizes every demonstrated post-claim lease, clock, rate, receipt, and
  capsule-persistence failure with sanitized diagnostics;
- rejects floating-point and non-JSON evidence recursively, uses integer
  monotonic milliseconds, and rejects artifact aliases before deduplication;
  and
- verifies a clean installed wheel by inventory and SHA-256 for all four Stage
  21B modules, a complete 16-step publication, durable receipt, ledger linkage,
  ambiguous mutation terminalization, and an eight-record reconciliation
  chain reconstructed from a retained real admission.

## Third-review correction closure

The preserved 0/5 Council re-review 0002 identified six remaining trust and
evidence defects. The next bounded correction now:

- removes the production-shaped publication success assertion from the
  fixture receipt and ledger; success means only complete offline fixture
  conformance and explicitly records that no live operation occurred;
- cross-binds the exact proposed paths to the Task Packet, Handoff, and Scope
  Review, including provider, role, packet hashes, in-target classification,
  and per-object grant identity;
- replaces fabricated branch/ruleset summaries with complete signed Stage 21A
  observation chains and genuine empty `rules` and `rulesets` projections;
- verifies the recursive-tree source credential claims, signature,
  permissions, repository/API/provider/key/app/install/account bindings, and
  issuance/claim/observation/expiry order;
- replaces caller-projected reconciliation with accepted fixture-read
  evidence, reopens the original retained records, preserves admission-only
  response loss without inventing a result, and verifies the complete
  resultant Git tree including surviving base entries and directory OIDs;
- removes the incompatible legacy 0.1.0 reconciliation family so only the
  canonical v2 `/0.2.0` record family remains;
- records existing-head and duplicate-pull-request observations as factual
  conflicts, stops at the observation step, and produces no later admission;
  and
- preconstructs post-claim references and terminalizes malformed clocks,
  hashes, dynamic request construction, and terminal-record failures using
  the closed sanitized reason vocabulary.

## Fourth-review correction closure

The preserved 0/3 Council re-review 0003 halted the five-seat review after
three unanimous blockers. The next bounded correction now:

- gives the offline evaluator only an exact immutable transcript of bounded
  response bytes and request hashes; the runtime invokes no caller callback,
  transport object, socket, resolver, credential provider, or live API;
- uses fixture-specific admission, result, receipt, failure, inventory,
  outcome, reconciliation, and ledger vocabulary. It never represents fixture
  success as a published proposal or a completed live GitHub operation;
- derives every writable Stage 21B evidence location beneath the verified
  external CONCLAVE workspace and rejects repository-contained, linked,
  reparse-point, or escaped workspace paths before a claim is retained;
- signs and verifies the recursive-tree credential claims against the exact
  `git_tree_recursive.get` authorization, intent, claim, route, repository,
  provider, permission, and time bounds;
- derives the authenticated rate observation from a complete signed Stage 21A
  `repository.get` evidence chain and cross-binds the exact repository,
  account, application, installation, provider, key, API, resource bucket,
  limit, remaining, reset, retry, and observation time, including
  `0 <= remaining <= limit`;
- requires a domain-separated provider signature over the exact one-shot
  fixture publication lease claims, including every predecessor hash,
  permission ceiling, request/mutation ceiling, expiry, repository identity,
  provider identity, and explicit live-use prohibition; and
- replaces caller-declared reconciliation authentication with a complete
  signed Stage 21A repository observation as the credential and repository
  foundation, while the exact object-read route, request hash, accepted status,
  response-completeness marker, and projection remain an explicitly untrusted
  immutable fixture transcript.
  The reconciliation result uses only `FIXTURE_*` classifications and never
  authorizes continuation.

Before Council re-review 0004, the focused corrected Stage 21B,
governance-chain, reconciliation, installed-wheel, and evidence-tool suite
passed 146 tests. The full Windows Python 3.12 suite passed 1,228 tests with 2
permitted environment-dependent skips. A fresh wheel and source distribution
build and a clean isolated Python 3.12 installation passed. That rejected
bundle's exact wheel SHA-256 was
`3c94186619047b3f0c0f31d237dd42b9bcce5999f82a657b8a41c1e4a9af942e`;
its exact source-distribution SHA-256 was
`346e009125f5c549b4d982736731ec14ea4143e0ebe51966fd8e0c8d693661b3`.
The installed probe emitted `github-publication-probe-ok`, reported no stderr,
verified the exact four Stage 21B module hashes and 47-member wheel inventory,
and confirmed that the wheel contained no prohibited test, response-cassette,
executable caller-transport, or loopback-executor surface. That local Windows
conformance evidence reported 1,230 collected tests, 0 failures, 0 errors, 2
permitted skips, empty static and secret findings, and status `PASS`.

## Fifth-review correction closure

The preserved 0/3 Council re-review 0004 identified two remaining boundary
defects. The immediate local correction now:

- accepts reconciliation persistence only with a verified external
  `Workspace`, derives the destination under the dedicated
  `github/publication-fixture-reconciliations/<safe-id>` directory, and rejects
  repository-contained workspaces, escaped or unsafe reconciliation IDs,
  linked directories, and Windows reparse points before writing any record;
  and
- validates and defensively copies each transcript response into exact bounded
  built-in `int`, `tuple`, `str`, and `bytes` values. Header names are
  canonicalized, header count and aggregate size are bounded, body size is
  bounded, control characters are rejected, and the evaluator snapshots the
  transcript again before any claim. A caller-supplied iterable is rejected
  without invocation.

Before Council re-review 0005, the focused Stage 21B, governance-chain,
reconciliation, installed-wheel, and evidence-tool suite passed 155 tests. The
full Windows Python 3.12 suite passed 1,237 tests with 2 permitted
environment-dependent skips. A fresh wheel and source distribution build and
clean isolated Python 3.12 installation passed. That rejected bundle's exact
wheel SHA-256 was
`18c7f4c30942d6574b8e97420c1b13f1acb71e5720a167a66a61e2a4b785d772`;
its exact source-distribution SHA-256 was
`275aa8864cf905038388c2ed65e7853234b3e035d391cbc2832be83d7fd554b8`.
The installed probe emitted `github-publication-probe-ok` with no stderr and a
clean 47-member wheel inventory. Local Windows conformance reported 1,239
collected tests, 0 failures, 0 errors, 2 permitted skips, empty static and
secret findings, and status `PASS`.

## Sixth-review correction closure

Council re-review 0005 passed governance but reproduced one remaining
repository-boundary bypass: both write guards inspected every ancestor of the
workspace root but omitted the workspace root itself. The immediate correction
now rejects a `.git` marker at the `.conclave` root as well as at every
ancestor. Separate adversarial tests cover both `.git` directories and Git
worktree-style `.git` files for publication evidence and reconciliation
evidence. The governance pass from the rejected bundle is historical and does
not carry forward.

Before Council re-review 0006, the focused Stage 21B, governance-chain,
reconciliation, installed-wheel, and evidence-tool suite passed 159 tests. The
full Windows Python 3.12 suite passed 1,241 tests with 2 permitted
environment-dependent skips. A fresh wheel and source distribution build and
clean isolated Python 3.12 installation passed. That rejected bundle's exact
wheel SHA-256 was
`c12169d3ec36430fe842eb17830e34527f3f0196ac812845775e0dabaa6a4db6`;
its exact source-distribution SHA-256 was
`ea12166b3c3796405ca5679f292ab53476f35e91a68de81c40b1123ddae0841b`.
The installed probe emitted `github-publication-probe-ok` with no stderr and a
clean 47-member wheel inventory. Local Windows conformance reported 1,243
collected tests, 0 failures, 0 errors, 2 permitted skips, empty static and
secret findings, and status `PASS`.

## Seventh-review correction closure

Council re-review 0006 identified two remaining exact-evidence defects. The
immediate correction now:

- rejects any `FixtureReadTranscript` subclass before accessing its fields,
  rejects every projection or nested-entry subclass before accessing its
  fields, reconstructs a fresh exact projection from admitted built-in values,
  and reconstructs a fresh exact transcript before classification. Tests prove
  hostile transcript and projection accessors are never invoked and a
  bypass-mutated transcript is rejected; and
- includes the complete signed Stage 21A rate-source chain in the evaluator's
  durable reopen set. Twelve adversarial cases independently remove or alter
  the provider key, authorization, intent, attempt claim, lease evidence, and
  observation and prove rejection before fixture-attempt evidence is created.

The final focused Stage 21B, governance-chain, reconciliation, installed-wheel,
and evidence-tool suite passes 174 tests. The full Windows Python 3.12 suite
passes 1,256 tests with 2 permitted environment-dependent skips. A fresh wheel
and source distribution build and clean isolated Python 3.12 installation
pass. The exact wheel SHA-256 is
`f66e3d7614889bf1ea76f19e90df27713db59d18625ab1e9f5bef1e9bdbea791`;
the exact source-distribution SHA-256 is
`b2758282734262b871557caf52d64df71290e7f425c4ac6b533bf976a9d3f1b6`.
The installed probe emits `github-publication-probe-ok` with no stderr and a
clean 47-member wheel inventory. Local Windows conformance reports 1,258
collected tests, 0 failures, 0 errors, 2 permitted skips, empty static and
secret findings, and status `PASS`.

## Eighth-review correction closure

Council re-review 0007 passed governance and security but identified one
remaining request-identity defect: an allowed base ref could contain valid Git
characters with special URL meaning and was inserted directly into REST path
and query targets. The immediate correction now:

- uses one shared full `refs/heads/*` validator and canonical encoder in both
  publication planning and reconciliation;
- enforces complete Git reference grammar, NFC and UTF-8 validity, and the Git
  byte ceiling before planning;
- applies UTF-8 percent encoding with `/` preserved only in the GitHub ref-path
  form and encoded in the query-component form;
- derives all request hashes from the resulting encoded targets; and
- tests `?`, `#`, `&`, `=`, `%`, spaces, controls, Unicode, malformed percent
  text, prohibited component forms, and the shared publication/reconciliation
  target policy.

The `ProposalManifest` validator rejects invalid base refs before request
planning. Valid Git refs containing URL-reserved or Unicode characters are
represented by one deterministic ASCII target rather than repaired or
interpreted as query syntax. The two passes from the rejected bundle remain
historical and do not carry forward; the changed exact bundle requires a fresh
five-seat review.

After this correction, the focused Stage 21B, governance-chain,
reconciliation, installed-wheel, and evidence-tool suite passes 194 tests. The
full Windows Python 3.12 suite passes 1,276 tests with 2 permitted
environment-dependent skips. A fresh wheel and source distribution build and
clean isolated Python 3.12 installation pass. The exact wheel SHA-256 is
`d2a640dd07b72ee71656bc17750fe8ddbf3a0f1cde54dd42de3785394bc4ada3`;
the exact source-distribution SHA-256 is
`b0c54dd4246a3e8bb37eb37d8e28d051269814801bcc9faa9a2b5a1f9a0306d8`.
The installed probe emits `github-publication-probe-ok` with no stderr and a
clean 47-member wheel inventory. Local Windows conformance reports 1,278
collected tests, 0 failures, 0 errors, 2 permitted skips, empty static and
secret findings, and status `PASS`.

## Ninth-review correction closure

Council re-review 0008 passed four seats but identified one remaining durable
write-boundary defect: a reconciliation record could be bypass-mutated after
bundle assembly and persisted with a stale content hash. The immediate
correction now performs all validation before deriving or creating the output
directory. It:

- rejects a `ReconciliationBundle` subclass and every direct or recursively
  nested closed-model subclass before serialization;
- rejects non-exact scalar and container types in the record graph;
- reconstructs a fresh exact `ReconciliationBundle` through strict schema,
  content-hash, and predecessor-chain validation; and
- writes only the records from that fresh verified snapshot.

Adversarial tests bypass-mutate each of the eight durable records in turn and
substitute subclasses for the bundle and for each durable record. Every case
must fail before producing any reconciliation JSON file. The four passes from
the rejected bundle remain historical and do not carry forward; the changed
exact bundle requires a fresh five-seat review.

After this correction, the focused Stage 21B, governance-chain,
reconciliation, installed-wheel, and evidence-tool suite passes 213 tests. The
full Windows Python 3.12 suite passes 1,295 tests with 2 permitted
environment-dependent skips. A fresh wheel and source distribution build and
clean isolated Python 3.12 installation pass. The exact wheel SHA-256 is
`90e8c9845b23fc81a1b3bffd4c5ce1dd9f97d2d818163e9d865dc9a7e8eb3273`;
the exact source-distribution SHA-256 is
`a56794bba8c84bb4cb95f35cfcdc4584666dd89e980ebb26269dde79114b5e98`.
The installed probe emits `github-publication-probe-ok` with no stderr and a
clean 47-member wheel inventory. Local Windows conformance reports 1,297
collected tests, 0 failures, 0 errors, 2 permitted skips, empty static and
secret findings, and status `PASS`.

## Tenth-review correction closure

Council re-review 0009 reproduced a callback seam in the new snapshot: it
called `model_dump_json` through the caller-owned exact bundle, so a
bypass-added instance attribute could shadow that method and execute. The
immediate correction removes every caller-owned serialization call. The
pre-write boundary now:

- requires every closed model to be one of the exact admitted model classes;
- obtains each exact built-in instance dictionary with `object.__getattribute__`
  and requires its keys to equal the model's declared field names exactly;
- extracts each field with `dict.__getitem__` into exact built-in dictionaries,
  tuples, and scalar values, rejecting any extra attribute or scalar/container
  subclass; and
- constructs and validates a fresh `ReconciliationBundle` from that primitive
  graph before deriving an output directory or writing a record.

Tests shadow serializer methods on both the exact bundle and an exact nested
record and prove that neither callback executes and no reconciliation JSON is
written. The rejected review produced no pass that can carry forward; the
changed exact bundle requires a fresh five-seat review.

After this correction, the focused Stage 21B, governance-chain,
reconciliation, installed-wheel, and evidence-tool suite passes 216 tests. The
full Windows Python 3.12 suite passes 1,298 tests with 2 permitted
environment-dependent skips. A fresh wheel and source distribution build and
clean isolated Python 3.12 installation pass. The exact wheel SHA-256 is
`98a6b4d38532372b7cfdb071afe6f02e3fed784616285b61e280402838fa881c`;
the exact source-distribution SHA-256 is
`2bf9b5ae879e2572bc8f0be81d0e1fb13dfb5377bbf0dcce6d91c1b7a1cd9792`.
The installed probe emits `github-publication-probe-ok` with no stderr and a
clean 47-member wheel inventory. Local Windows conformance reports 1,300
collected tests, 0 failures, 0 errors, 2 permitted skips, empty static and
secret findings, and status `PASS`.

## Eleventh-review correction closure

Council re-review 0010 identified one remaining virtual operation:
`isinstance` could consult an arbitrary injected object's hostile `__class__`
attribute. The immediate correction obtains the concrete type once with the
built-in `type` operation and dispatches only by exact membership in the closed
model allowlist or equality with an admitted built-in container or scalar
type. An unrecognized value is rejected without accessing any attribute.

An adversarial test inserts an arbitrary object whose `__getattribute__`
raises and records invocation. Persistence rejects it before directory
derivation, invokes it zero times, and writes zero reconciliation JSON files.
The three passes from the rejected bundle remain historical and do not carry
forward; the changed exact bundle requires a fresh five-seat review.

After this correction, the focused Stage 21B, governance-chain,
reconciliation, installed-wheel, and evidence-tool suite passes 217 tests. The
full Windows Python 3.12 suite passes 1,299 tests with 2 permitted
environment-dependent skips. A fresh wheel and source distribution build and
clean isolated Python 3.12 installation pass. The exact wheel SHA-256 is
`0171c3a4a3ffcff8e2cbf874cf2dfc67402168398f8f5f3b2f1edf4ee0329bec`;
the exact source-distribution SHA-256 is
`a8addedaf8a50d1dcb7599b9c60c5cd7ff8758c736681258c70882eb899148c7`.
The installed probe emits `github-publication-probe-ok` with no stderr and a
clean 47-member wheel inventory. Local Windows conformance reports 1,301
collected tests, 0 failures, 0 errors, 2 permitted skips, empty static and
secret findings, and status `PASS`.

## Boundaries

The corrected implementation contains no live GitHub transport, credential
resolution, token, signing operation, identity, membership, KOS, IDM,
deployment, or production operation. Its evaluator is offline and
credential-independent; immutable fixture transcript data is staged by the
external conformance probe and the installed package exposes no executable
fixture transport. No commit, push, pull request, or merge is authorized by
this record.

Windows local evidence is produced before handoff. Ubuntu/Python 3.12 and
3.13 and macOS/Python 3.12 evidence require the existing GitHub Actions matrix
after a separately authorized commit and push; they cannot be claimed from the
current local-only authorization.
