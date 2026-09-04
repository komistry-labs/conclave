# CONCLAVE v0.8.0 release protocol

Snapshot status: Candidate Draft when authored  
Protocol authority: Arthur  
Prepared: 4 September 2026 (Asia/Kuala_Lumpur)  
Target repository: `komistry-labs/conclave`  

This status line is immutable drafting provenance. The current operational
disposition is determined by the latest Arthur-authored freeze record that
names this document's exact Git commit, Git blob and SHA-256. A later freeze
record supersedes the drafting-time status without editing this snapshot.

## 1. Authority and present effect

Arthur authorized drafting this bounded protocol. That authorization does not
freeze the protocol and does not authorize implementation, a version change,
a commit, push, pull request, merge, tag, GitHub Release, publication,
deployment or production use.

This snapshot becomes the governing v0.8.0 release procedure only after it is
committed and pushed on a protocol-only branch, passes exact-draft review, and
Arthur explicitly freezes it by exact commit, Git blob and SHA-256 in a record
retained in the protocol PR. The protocol file is not edited merely to say it
is frozen. Even after freeze, every later stage remains separately authorized.
A completed stage cannot be treated as authority for the next stage.

## 2. Verified drafting baseline

| Item | Drafting baseline |
|---|---|
| Protected `main` | `de651d05170898dd71fad8aa07429199ffc8d994` |
| Latest release | `v0.7.0` |
| `v0.7.0` tag target | `9c8682373ffbc3279c4bf660eeb147dc21fe60fa` |
| Current package version | `0.7.0` |
| Commits after `v0.7.0` | 25 |
| Current local Windows result | 1,044 passed; 2 documented capability skips |
| Current protected-main CI | Windows/Python 3.12, Ubuntu/Python 3.13, macOS/Python 3.12: PASS |
| Current package probe | isolated sdist/wheel build, inventory, secret scan, static scan and installed-wheel probe: PASS |

The baseline includes the reviewed implementations of Increments 19A–19D and
20A–20D plus the post-20D CI-evidence maintenance change. Any advance of
`main` before release preparation must be inspected and must replace this
baseline explicitly; it must not be assumed equivalent.

## 3. Release purpose and classification

v0.8.0 is the first release candidate containing:

- the Increment 19 verification-only IDM identity and signed-evidence
  boundary;
- opt-in local, verify and attested workflow gates;
- immutable signing requests, external evidence import, conflict retention
  and factual ledger evidence;
- the pinned public IDM conformance adapter and fixture-only broker;
- the Increment 20 public verifier and broker configuration boundary;
- bounded sandbox HTTPS transport, one-attempt authorization and explicit
  recovery;
- three-platform security and conformance evidence; and
- the post-20D Node.js 24 workflow maintenance and oversized-JUnit guard test.

v0.8.0 is a normal semantic-versioned project release, but it is explicitly
**not production-ready**. A non-prerelease GitHub label means only that the
bounded v0.8.0 feature set is complete; it does not authorize production
trust, production credentials, production signing or production reliance.

## 4. Non-goals and prohibited effects

The release must not:

- enable a sandbox or production endpoint by default;
- make a CONCLAVE provider, broker or sandbox call as part of release
  preparation or qualification; dependency acquisition from approved package
  and GitHub Action sources is permitted only under section 9;
- create, import, inspect or use a private key;
- allocate an EID, MID, RID, VID, UUIDv7 or any governed identity;
- bootstrap a trust domain or activate membership;
- treat identity, signature or evidence verification as truth, approval,
  authority, ratification or membership;
- weaken a fail-closed rule, immutable record or replay boundary;
- modify KOS, IDM, offline custody or historical evidence;
- publish to PyPI or another package registry;
- attach any asset other than the exact reviewed public, secret-free
  qualification bundle
  defined in sections 9 and 11;
- deploy CONCLAVE or enable production use; or
- move, replace, delete or recreate any existing tag.

## 5. Separately authorized stages

### R0 — protocol freeze

R0 consists of: exact-draft Council review; one protocol-only commit; an
explicit push when authorized; a protocol PR; and an Arthur-authored freeze
record naming the exact commit, Git blob and SHA-256. The freeze record is
retained in the PR and supersedes the immutable drafting-time snapshot status.
Merging the protocol PR requires separate authorization and the continuing
branch-protection policy. R0 does not authorize release-preparation edits.

### R1 — release-preparation implementation

R1 may make only the changes listed in section 6 on one branch created from
the then-current protected `main`. It ends at a locally verified commit. Push
and PR creation require explicit authorization.

### R2 — reviewed release-preparation PR

R2 may push the exact R1 commit, open a PR, collect exact-head CI and obtain an
independent `PASS_EXACT_HEAD` review. Merge requires explicit authorization
and the continuing branch-protection policy. Any administrator exception must
be separately authorized for the exact PR head and restored immediately.

### R3 — protected-main qualification

R3 begins only after R2 is merged. It verifies protected-main CI, reconstructs
the exact candidate packages from the merged commit, records hashes and
performs the checks in sections 7–9. R3 produces evidence only; it creates no
tag or release.

### R4 — tag and GitHub Release

R4 requires Arthur to approve the exact protected-main commit, release-note
hash and R3 evidence. Only then may one annotated `v0.8.0` tag and one GitHub
Release be created. Tag creation and GitHub Release publication are one
explicitly bounded authorization but remain separately verified operations.

### R5 — post-release verification

R5 verifies tag type and target, release metadata, source links, protected
branch state and release-note identity. It performs no deployment or package
registry publication.

## 6. Exact R1 change scope

The release-preparation diff is limited to:

1. `pyproject.toml`
   - change the project version from `0.7.0` to `0.8.0`;
   - pin the build backend to the exact reviewed Hatchling version used by the
     release build;
   - do not alter runtime dependency ranges or the declared Python floor.
2. `src/conclave/__init__.py`
   - change `__version__` from `0.7.0` to `0.8.0`;
   - no other runtime source change is allowed.
3. `src/conclave/workspace.py`
   - change only `BOOTSTRAP_VERSION` from `0.7.0` to `0.8.0` so newly created
     workspaces identify the release that created them;
   - do not rewrite or migrate an existing workspace.
4. `tests/test_workspace.py` and `tests/test_ledger.py`
   - update only the bootstrap-version assertions required by item 3.
5. `README.md`
   - change the displayed release version to `0.8.0`;
   - correct the verified platform description to include macOS;
   - distinguish the required cross-platform matrix from Python-minor
     compatibility jobs;
   - retain all non-production, authority and KOS-read-only boundaries;
   - describe the public CLI accurately without implying automatic or
     unauthorized provider/broker execution.
6. `RELEASE-NOTES-v0.8.0.md`
   - add the content required by section 8.
7. `.github/workflows/tests.yml`
   - retain Windows/Python 3.12, Ubuntu/Python 3.13 and macOS/Python 3.12;
   - add Ubuntu/Python 3.10 and Ubuntu/Python 3.11 compatibility jobs;
   - retain package building, inventory, secret scanning, installed-wheel
     probing and secret-free evidence publication for every matrix entry;
   - pin every third-party action, including checkout, setup-python and
     upload-artifact, to an independently verified full commit SHA with a
     human-readable release comment;
   - use a Node.js-24-native upload-artifact release;
   - run the installed-wheel probe before final evidence indexing;
   - publish the exact sdist, wheel and finalized secret-free evidence together
     for each job, with the repository's maximum supported retention period;
   - do not add credentials, secrets, deployment permissions or release
     publication.
8. `tools/conformance_evidence.py`
   - add only `ubuntu-latest-py3.10` and `ubuntu-latest-py3.11` to the closed
     platform set, each with an empty skip allowlist;
   - require and validate the installed-wheel probe and bind it into the final
     evidence index after every other report exists;
   - exclude the index itself from its own hash set;
   - inspect bounded decompressed regular-file members of both package formats
     for high-confidence private-key and credential material, rather than
     searching only compressed archive bytes;
   - fail closed on archive/member count or decompressed-size limits.
9. `tests/test_conformance_evidence_tool.py`
   - prove both new platform IDs accept skip-free reports and reject every
     unexpected skip;
   - prove member-level secret scanning detects representative PEM, OpenSSH,
     PKCS container and high-confidence credential fixtures while clean
     packages pass;
    - prove the final index includes the installed-wheel probe, binds exact
      hashes and cannot self-reference.
10. `tools/installed_wheel_probe.py` and
    `tests/test_installed_wheel_probe.py`
    - extend the probe to run both CLI help and `conclave version` from the
      freshly installed wheel;
    - record both commands, return codes, normalized stdout and stderr;
    - require both commands to succeed without stderr and require normalized
      version stdout to contain exactly two lines: `conclave 0.8.0` followed by
      the unchanged `schema  task-packet/0.1.0` line;
    - add deterministic positive and wrong-version/error-path tests.
11. `tools/release_evidence.py` and `tests/test_release_evidence_tool.py`
    - add deterministic, secret-free qualification-content and final R3
      manifest generators and their tests;
    - bind the release commit, protocol and release-note hashes, per-platform
      workflow/run/artifact identities, exact canonical package hashes,
      qualification reports and protection snapshot/restoration evidence in
      the qualification-content manifest;
    - deterministically create and scan the qualification ZIP, limiting it to
      256 members, 16 MiB per decompressed member and 128 MiB aggregate
      decompressed bytes;
    - reject encrypted, duplicate, absolute, drive-qualified, backslash,
      traversal, symlink and other non-regular member entries;
    - scan every ordinary member for the same high-confidence secret and
      private-material classes as package evidence, verify the nested canonical
      wheel and sdist byte hashes, and require their member-scan PASS reports;
    - emit a deterministic bundle-scan PASS report binding the ZIP SHA-256,
      limits, member inventory, canonical-package hashes and scanner version;
    - produce, outside the ZIP, a final R3 manifest that binds the
      qualification-content manifest, ZIP and bundle-scan-report hashes without
      self-reference;
    - provide no upload, signing, key, credential, provider or broker API.
12. `release/requirements-v0.8.0.lock`
    - retain the fully resolved build, runtime and test inputs used for R3,
      including exact versions and cryptographic hashes;
    - contain no index credential, token or private repository URL.

No other file is in scope. In particular, no module under `src/conclave/`
other than the two version literals in `__init__.py` and `workspace.py` may
change, and neither change may alter an existing workspace.

## 7. Compatibility acceptance matrix

The release claims Python 3.10 through 3.13 compatibility, not every
operating-system/Python Cartesian combination. Required jobs are:

| Environment | Purpose |
|---|---|
| Windows latest / Python 3.12 | Windows behavior and path semantics |
| Ubuntu latest / Python 3.10 | declared minimum-Python compatibility |
| Ubuntu latest / Python 3.11 | intermediate-minor compatibility |
| Ubuntu latest / Python 3.13 | Linux and newest declared minor |
| macOS latest / Python 3.12 | macOS behavior and path semantics |

Every job must complete the full suite, build both package formats, inspect
bounded decompressed package members, install the wheel in a fresh environment,
exercise CLI help/version, finalize an index that includes the probe, and
publish the exact packages plus secret-free evidence. Expected
platform-capability skips must be exactly allowlisted. Any unexpected skip,
failure, error, scan finding, missing report, missing artifact, incomplete
index or evidence-generator nonzero exit blocks release.

The required protected-branch contexts remain the existing Windows 3.12,
Ubuntu 3.13 and macOS 3.12 contexts unless a separate branch-protection change
is reviewed and authorized. Python 3.10 and 3.11 are additional release
compatibility gates and must still pass before merge and release.

## 8. Release-note requirements

`RELEASE-NOTES-v0.8.0.md` must include:

- an accurate summary of Increments 19A–19D and 20A–20D;
- the post-20D CI maintenance correction;
- installation requirements and the tested compatibility matrix;
- upgrade behavior for an existing v0.7.0 workspace;
- the rule that a missing identity-mode record remains `local` and no upgrade
  silently strengthens mode;
- the continuing external and read-only status of KOS;
- explicit statements that the release includes no embedded signer, private
  key API, production broker, production trust domain or automatic retry;
- known limitations already stated in the README.

The GitHub Release body must be byte-for-byte the retained release-note file
or be generated from it without semantic alteration.

The release notes must not embed their own commit identity or post-merge R3
results. The exact release commit and final results belong in the separate R3
manifest, which binds them to the retained release-note hash without changing
the release-note file.

## 9. Exact package qualification

R3 has one connected acquisition phase and one network-disabled qualification
phase. Acquisition may download only the exact versions and hashes named by
`release/requirements-v0.8.0.lock` into a temporary wheelhouse. Qualification
must install/build from that wheelhouse with index access disabled. GitHub
Actions are fetched only through the full commit SHAs reviewed in R2.

R3 must run from a clean checkout of the exact protected-main candidate:

1. confirm `pyproject.toml`, `conclave.__version__` and `conclave version` all
   report `0.8.0`;
2. run the full suite with machine-readable JUnit output;
3. build exactly one `conclave-0.8.0.tar.gz` and one
   `conclave-0.8.0-py3-none-any.whl` in an isolated build environment;
4. record SHA-256 for the exact package bytes;
5. require package inventory, forbidden-marker scan, bounded decompressed-
   member secret scan and static capability scan to return PASS with no
   findings;
6. install the exact wheel in a fresh environment and require CLI help and
   version probes to pass without stderr;
7. confirm the wheel and sdist contain the pinned public policy but exclude
   test fixtures, private material, environment files, tokens and credentials;
8. bind every per-job report, including the installed-wheel probe, by hash in
   a finalized self-excluding evidence index;
9. designate the Ubuntu/Python 3.13 sdist and wheel as the canonical
   qualification package bytes; cross-platform packages remain corroborating
   evidence rather than competing release objects;
10. generate a qualification-content manifest that binds the exact release
    commit, protocol and release-note hashes, all five run/job/artifact
    identities, canonical package hashes, per-job evidence indexes and branch-
    protection evidence;
11. use `tools/release_evidence.py` to create
    `conclave-v0.8.0-qualification-evidence.zip` containing the exact
    canonical sdist/wheel, qualification-content manifest, all referenced
    secret-free reports and the dependency lock;
12. run its bounded bundle scan, require PASS, and record the ZIP and bundle-
    scan-report SHA-256 values; and
13. generate the external, self-reference-free final R3 manifest binding the
    qualification-content manifest, ZIP and bundle-scan-report hashes before
    R4.

The packages are qualification artifacts only. v0.8.0 does not authorize PyPI
or package-registry publication. Because the CONCLAVE repository is public,
the qualification ZIP is deliberately retained as the sole public GitHub
Release asset for the lifetime of the release. Before R4 authorization, its
exact bytes and every decompressed member must pass the bounded secret and
private-material scan defined in section 6, its bundle-scan PASS report must be
bound into the R3 manifest, and Arthur's R4 authorization must explicitly
approve public disclosure of its recorded SHA-256. It must be labelled
evidence-only and not for production installation. GitHub's automatically
generated tag source archives may remain available normally. The lifetime
retention rule is subject only to the post-publication security-incident rule
in section 12.

## 10. Pull-request and review controls

- R1 begins from clean, current `origin/main`.
- Only the files in section 6 may be staged.
- The complete staged diff and exact tree must be recorded.
- Both local and exact-head GitHub checks must pass.
- Independent review must verify scope, version consistency, compatibility
  evidence, packaging, release notes and non-production boundaries.
- The accepted verdict is `PASS_EXACT_HEAD` tied to the full commit and tree.
- A later commit invalidates that review.
- Review text must be retained in the PR record.
- Merge must not occur with pending, stale or failed checks.
- Branch protection must not be bypassed without a fresh exact-head Arthur
  authorization. Before any exception, retain the complete protection JSON
  and its canonical SHA-256. Change only the approval count, perform no other
  merge, restore unconditionally after success or failure, read the complete
  object back, and require canonical equality with the pre-change snapshot.
  Failed equality is an active protection incident and blocks every later
  release stage.

## 11. Tag and GitHub Release procedure

Before R4:

- `v0.8.0` must not already exist locally or remotely;
- protected `main` must still equal the approved R3 commit;
- the worktree and index must be clean;
- all required and compatibility checks must be successful;
- R3 package and report hashes must be retained;
- the final release-note content hash must be recorded; and
- Arthur must name the exact commit in the release authorization.

R4 creates an annotated tag named exactly `v0.8.0`, with message
`CONCLAVE v0.8.0`, targeting the approved commit. The tag is pushed explicitly;
no wildcard or all-tags push is allowed. The GitHub Release is named
`CONCLAVE v0.8.0`, is not a draft and is not marked prerelease, consistent
with v0.7.0. Its body comes from `RELEASE-NOTES-v0.8.0.md`. The only uploaded
asset is the exact public, secret-free evidence ZIP whose disclosure and
SHA-256 Arthur approved in R4; its SHA-256 must match the R3 record. No
standalone package asset is uploaded.

## 12. Rollback and failure handling

There is no history-rewriting rollback.

- Before merge: correct a defect with a new commit, rerun all checks and obtain
  a new exact-head review.
- After merge but before tag: do not revert automatically. Stop, assess the
  defect and use a reviewed corrective PR if required.
- After tag creation: never move, replace, delete or reuse `v0.8.0`. If the
  GitHub Release has not yet been published, stop and obtain Arthur's decision.
- If Release creation, metadata verification, exact ZIP upload or remote asset
  hash verification fails after the tag is pushed, do not move or delete the
  tag and do not improvise a different asset. Stop, report the exact partial
  state, and obtain fresh Arthur authorization before retrying only the
  identical SHA-bound ZIP or correcting Release metadata.
- After publication: correct release defects through a separately governed
  patch release such as v0.8.1; do not rewrite v0.8.0.
- If branch protection is temporarily changed, restoration is mandatory
  immediately after the merge attempt whether it succeeds or fails. The full
  post-restoration protection object must canonically equal the retained
  pre-change snapshot. A failed restoration or equality check is an active
  protection incident requiring continued remediation and immediate reporting.
- If an unexpected secret, private-material or malicious-content finding occurs
  before publication, stop. Do not print or preserve the sensitive content in
  ordinary evidence. Follow the applicable credential-revocation or incident
  procedure outside this release.
- A confirmed or reasonably suspected post-publication secret, private-material
  or malicious-content incident is the sole exception to lifetime asset
  retention. Immediately quarantine or remove the affected Release asset
  without changing the tag or Git history; retain a sanitized, evidence-
  preserving incident record that does not reproduce the sensitive content;
  revoke affected credentials; report the exact state; and obtain fresh Arthur
  authorization before uploading any replacement. Ordinary defects do not use
  this exception and remain subject to the v0.8.1 rule.
- Failure of a compatibility job, package probe or evidence check blocks R4;
  it cannot be waived by describing the release as non-production.

## 13. Completion evidence

v0.8.0 is complete only when all of the following are independently
verifiable:

- frozen protocol commit and content hash;
- reviewed release-preparation PR and exact-head verdict;
- protected-main release commit;
- full required and Python-minor compatibility results;
- exact sdist/wheel hashes, per-job PASS evidence indexes and R3 manifest;
- retained public, secret-free qualification ZIP identity, SHA-256,
  bundle-scan PASS report/hash and release-asset URL;
- final release-note hash;
- annotated tag object and exact target;
- GitHub Release metadata and source links;
- unchanged restored branch protection;
- clean synchronized local `main`; and
- a statement that no prohibited operation in section 4 occurred.

## 14. Decisions fixed by protocol freeze

Freezing this candidate records Arthur's acceptance of the following release
choices:

1. the next release number is `0.8.0`;
2. Python 3.10 and 3.11 are retained and evidenced rather than dropping or
   raising the declared compatibility floor;
3. the five-job matrix in section 7 is sufficient without claiming the full
   OS/Python Cartesian product;
4. the GitHub Release is a normal non-prerelease release while retaining the
   explicit non-production boundary;
5. one public, secret-free, evidence-only qualification ZIP is retained with
   the GitHub Release only after bounded scanning and explicit R4 disclosure
   authorization; standalone binary packages and package-registry publication
   are excluded; and
6. existing tags are immutable and post-release correction uses a new patch
   version.

## 15. Current disposition

This immutable snapshot was drafted as a protocol candidate. No external
freeze record yet applies to it. No release-preparation implementation has
begun. No version, README, workflow, release-note, runtime, tag, GitHub Release,
KOS, IDM, identity, trust, signing, deployment or production state has been
changed by this drafting stage.
