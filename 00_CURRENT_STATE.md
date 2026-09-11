# CONCLAVE Current Project State

Last verified: 2026-09-11
Status class: `GOVERNED_MAIN_BASELINE / INCREMENT_21_ERRATUM_0001_FROZEN_APPLIED_LOCAL`

## 1. Product baseline

- product version: `0.8.0`
- Python floor: `>=3.12`
- protected remote `main`:
  `dda5961fa4aa0c67acafac2de230e9ce9313a03e`
- active local branch: `docs/increment-21c-protocol`
- merged Stage 21B pull request: `#20`
- accepted Stage 21B pull-request head:
  `c6a3a2bc0aea7afb6135d13b25593d905299d3a7`
- accepted Stage 21B implementation and recovery commit:
  `4fad8b03823b724913ecf8454a84c8837fc47b2e`
- accepted implementation tree:
  `7540069356b5fe0f627dba7822e007652c3e5878`

The Stage 21B branch was merged by a normal merge commit after exact-head
verification. This CPS reconciliation begins Stage 21C at the protocol layer
only; it changes no runtime or test file and grants no implementation or live
operation authority.

## 2. Current increment disposition

Increment 21's master protocol, Stage 21A, the Stage 21B protocol, Stage 21B
Erratum 0001, and the corrected Stage 21B implementation are present on the
current protected `main` baseline.

Corrected Stage 21B implementation is now:

- merged into protected `main` through PR #20 at exact reviewed head
  `c6a3a2bc0aea7afb6135d13b25593d905299d3a7`;
- fixture- and loopback-only;
- locally verified on Windows/Python 3.12;
- approved across the preserved five-seat Council implementation and recovery
  review chain, with the final correction delta bound to exact aggregate
  `f545344b57a0aba4cad4b959014dd94d829de6f0d2bbbd2ef6ae3ba821fc1a1f`;
- remotely accepted before merge and again after merge on Windows/Python
  3.12, macOS/Python 3.12, Ubuntu/Python 3.12, and Ubuntu/Python 3.13; and
- supported by four retained, secret-free conformance artifacts.

The accepted pre-merge run is `34448996906`:

`https://github.com/komistry-labs/conclave/actions/runs/34448996906`

The successful post-merge run on `main` is `34451869051`:

`https://github.com/komistry-labs/conclave/actions/runs/34451869051`

All four post-merge matrix jobs completed successfully and published their
expected conformance artifacts.

## 3. Evidence and recovery history

- initial implementation commit:
  `930af95f72bd8de3c7d32f78af165515f13b5715`
- first-recovery commit:
  `e334eefb2800681165a781bbbfbe9da607726694`
- accepted recovery commit:
  `4fad8b03823b724913ecf8454a84c8837fc47b2e`
- exact PR #20 head: `c6a3a2bc0aea7afb6135d13b25593d905299d3a7`
- merge commit: `dda5961fa4aa0c67acafac2de230e9ce9313a03e`
- rejected remote runs: `34444730211`, `34446903733`
- accepted pre-merge run: `34448996906`
- accepted post-merge run: `34451869051`
- Council closeout review:
  `INCREMENT-21B-IMPLEMENTATION-COUNCIL-REREVIEW-0013.md`
- complete recovery narrative:
  `INCREMENT-21B-PUBLICATION-RECOVERY-0001.md`
- remote acceptance closeout:
  `INCREMENT-21B-PUBLICATION-RECOVERY-CLOSEOUT-0001.md`

Local acceptance for the final correction recorded `1,301 passed`, two
permitted platform skips, `1,303` collected, a passing clean installed-wheel
probe, a 47-member wheel inventory, and empty static and secret findings.

## 4. Current authority boundary

The Stage 21B runtime and adapter accessed no credential and performed no live
GitHub adapter operation. This statement is limited to the evaluated Stage
21B capability and does not characterize the separately governed Git and CI
publication path. No GitHub App was created or installed. No KOS or IDM
repository was changed. No signing, identity allocation, membership
activation, deployment, or production use is authorized by the Stage 21B
evidence or merge.

For PR #20, Arthur authorized one temporary administrator exception changing
only `required_approving_review_count` from `1` to `0`. No other merge occurred
during the window. The setting was restored immediately after the merge and
the complete protection state was verified unchanged: strict required checks
remain enabled for Windows/Python 3.12, Ubuntu/Python 3.13, and macOS/Python
3.12; administrator enforcement and conversation resolution remain enabled;
stale-review dismissal remains enabled; and force pushes and deletion remain
disabled. No protection gap remains.

CONCLAVE provides bounded capability and evidence. KOS remains external and
retains authority.

## 5. Next governed gate

Stage 21B is closed. Stage 21C has begun at protocol drafting only under the
frozen Increment 21 master protocol. Its purpose is to define exact-head
readiness evaluation and a separately human-authorized, single-attempt normal
merge that preserves all continuing protections and has no administrator
exception or bypass path.

Council Review 0001 rejected the first exact draft unanimously at SHA-256
`5cce5525659cccea9be2d0c8ee180a3609c17cf72fa7f1bcde120b2173ccd6e1`
and Git blob `bbec3ba2f7b6a9f50c88ad61f0192584e3c3c1e6`. The disposition is
`5/5 FAIL_EXACT_DRAFT / REMEDIATION REQUIRED`; the complete preserved findings
are in `INCREMENT-21C-COUNCIL-REVIEW-0001.md`.

Bounded remediation produced a new review candidate:
`INCREMENT-21C-EXACT-HEAD-REVIEW-AND-HUMAN-AUTHORIZED-MERGE.md` at exact
SHA-256 `f306134fa93a61b14393579f018a348c7958fe445de36e6bdd90d934d056bafd`,
Git blob `6f22c4d167cbeb8f1a4c6e6b886d787b22ca8821`, 70,117 bytes, and 1,340
lines. Council Review 0002 rejected those exact bytes unanimously. Its
disposition is `5/5 FAIL_EXACT_DRAFT / REMEDIATION REQUIRED`; the complete
preserved findings are in `INCREMENT-21C-COUNCIL-REVIEW-0002.md`.

Review 0002 remediation produced the Review 0003 candidate at the same
protocol path at exact SHA-256
`cc865b616dcda1edaa0dbb689ed16292b47d21f44aa67748e03dfcd11d946bec`,
Git blob `8a369a65ac72e91d214ca800cfb6d4abecd6f76e`, 80,280 bytes, and 1,508
lines. Council Review 0003 returned `1/5 PASS_EXACT_DRAFT / 4/5
FAIL_EXACT_DRAFT / REMEDIATION REQUIRED`; its complete preserved findings are
in `INCREMENT-21C-COUNCIL-REVIEW-0003.md`.

Review 0003 remediation produced the Review 0004 candidate at the same
protocol path at exact SHA-256
`95fa98ce569f1f0553c3d0d75ef9804029bdf3832bc2185f25862de1b3b3d3c1`,
Git blob `291cdd8782c5604bc69c16fb8494a28fb1369842`, 89,714 bytes, and 1,649
lines. Council Review 0004 returned `2/5 PASS_EXACT_DRAFT / 3/5
FAIL_EXACT_DRAFT / REMEDIATION REQUIRED`; its complete preserved findings are
in `INCREMENT-21C-COUNCIL-REVIEW-0004.md`.

Review 0004 found three unresolved areas: the interrupted-read union could not
represent a complete page-10 result with continuation; a valid `Retry-After`
on a non-403/429 response could evade the global stop rule; and the
`other_valid` media class lacked a closed deterministic grammar.

Bounded Review 0004 remediation produced the Review 0005 candidate at the
same protocol path at exact SHA-256
`d82af781441b916855861322c5c8143d70abf3211c21f823d31866046eb954a1`,
Git blob `ff68bd9ab22080a526e2a9d17f45335fe7615a08`, 93,777 bytes, and 1,712
lines. Council Review 0005 returned `1/5 PASS_EXACT_DRAFT / 4/5
FAIL_EXACT_DRAFT / REMEDIATION REQUIRED`; its complete preserved findings are
in `INCREMENT-21C-COUNCIL-REVIEW-0005.md`. The correction closed the
ten-page continuation and partial-result inventory states, applied valid
`Retry-After` precedence to every HTTP status, and replaced open media parsing
with one bounded ASCII byte grammar and deterministic classifier.

Review 0005 found narrower defects: mixed valid and invalid rate headers lack
one explicit validation-before-precedence algorithm; the GraphQL interrupted-
read union overlaps at a zero-pair absent-admission prefix and omits corruption
combinations; and a successful zero-transmission mutation terminal could not
bind the admission-path inventory it requires.

Bounded Review 0005 remediation produced the Review 0006 candidate at the
same protocol path at exact SHA-256
`2bded70672d5ceb8f671f5bce46692670a53d73473f2cb3f1af6635cf289b515`,
Git blob `041c456b97a49d013e0247de30d8ef6e5bc59288`, 102,837 bytes, and 1,844
lines. Council Review 0006 returned `2/5 PASS_EXACT_DRAFT / 3/5
FAIL_EXACT_DRAFT / REMEDIATION REQUIRED`; its complete preserved findings are
in `INCREMENT-21C-COUNCIL-REVIEW-0006.md`. The correction made rate
classification validation-first and total; made GraphQL page-path states
exclusive and exhaustive under artifact corruption; and introduced immutable
mutation-prefix evidence with same-process proven-zero, valid-admission one,
and conservative restart accounting propagated through terminal, capsule,
receipt, reconciliation, and ledger records.

Review 0006 found four narrower closure defects: GraphQL `lease_present`
mentions only absent page-one paths and overlaps a retained-later-artifact
state; path-valid but chain-invalid mutation artifacts have no terminal arm;
an unusable permanent target-claim path has no downstream evidence variant;
and rate-header occurrence extraction is not closed against case variation,
coalescing, or lossy transport maps.

Bounded Review 0006 remediation produced the Review 0007 candidate at the same
protocol path at exact SHA-256
`2373bb9dbb96146c8b22d868a284ea0be54015720c18ef80406c2633f9a7d6d4`,
Git blob `84dbb36abd719bc1c60f14ef4c541b9f6e2880fc`, 117,392 bytes, and
2,062 LF-terminated lines. It makes the all-absent GraphQL lease state depend
on every ordinal through 10; adds conservative terminal closure for path-valid
but chain-invalid mutation artifacts; adds immutable unusable-target evidence
through capsule, terminal inventory, reconciliation, receipt, and ledger; and
requires a lossless pre-normalization response-header occurrence stream with
case-insensitive name matching, duplicate preservation, comma rejection, and
lossy-adapter failure. The full repository suite passes with `1301 passed, 2
skipped`.

Council Review 0007 independently reviewed those exact bytes using five
distinct `gpt-5.6-sol` seats at `xhigh` reasoning. It returned `1/5
PASS_EXACT_DRAFT / 4/5 FAIL_EXACT_DRAFT / REMEDIATION OR SCOPE DECISION
REQUIRED`. The complete preserved record is
`INCREMENT-21C-COUNCIL-REVIEW-0007.md` at SHA-256
`87f5129b76738133faf28b7193b22cf78907fb4e1a8298947a495a08aa023e42`,
Git blob `2ebcd6e2182898ed9e4ea2730be689d9bdeff172`, 9,452 bytes, and 198
LF-terminated lines.

Review 0007 found eight consolidated closure issues: the lossy-header result
has no unavailable media/rate shape; a contender blocked by a foreign valid
target claim has no terminal arm; target evidence is not exclusive when
artifacts coexist; the target-inventory failure capsule is not standalone and
does not retain both path commitments; total absent-path storage failure cannot
prove permanent consumption across restart; the mutation-inventory failure
capsule cannot start reconciliation; its fallback loses chain-invalid
admission/result evidence; and two unusable-mutation variants overlap.

Arthur selected the recommended scope split: CONCLAVE prepares exact-head
readiness and later observes a human-performed protected merge, but issues no
merge mutation. A compatibility check found that the frozen Increment 21
master explicitly selects Stage 21C merge permission, endpoint, intent,
attempt, receipt, and execution. The split therefore requires a governed
master erratum rather than reinterpretation of the frozen text.

`INCREMENT-21-ERRATUM-0001-STAGE-21C-HUMAN-MERGE-SPLIT.md` is now a local
draft correction candidate. It supersedes only the master clauses that grant
or presuppose adapter-issued merge execution; preserves Stages 21A, 21B, and
21D; removes every Stage 21C merge credential, permission, endpoint, transport,
retry, and mutation path; assigns the normal protected merge to the configured
human outside CONCLAVE; and retains only read-only readiness, human-
authorization evidence, post-action observation, and reconciliation.

Council Review 0001 reviewed the exact erratum at SHA-256
`e2536bb262595785eb79a0e8a263d1727adeb3dd7e2242c65c2a259a7aa5ac0e`,
Git blob `1beb1435ef8ac57a78b79b3447f957d0133c3674`, 19,729 bytes, and 381
LF-terminated lines. It returned `4/5 PASS_EXACT_DRAFT / 1/5
FAIL_EXACT_DRAFT / REMEDIATION REQUIRED`. The full immutable findings are in
`INCREMENT-21-ERRATUM-0001-COUNCIL-REVIEW-0001.md`.

The selected scope-split architecture passed in substance. Two bounded text
defects prevent freeze: CONCLAVE cannot observe or prove the number of attempts
made by the external human client, and failed CONCLAVE readiness cannot prevent
the human from authoring an authorization. One verdict-label consistency
cleanup was also recorded.

Bounded remediation has now corrected only those findings. The one-attempt
field is explicitly a human-governance instruction that CONCLAVE cannot
observe, enforce, count, or attest; failed readiness now restricts only what
CONCLAVE may accept, validate, retain as current, present, authorize, or do;
and the verdict vocabulary is harmonized to `PASS_EXACT_DRAFT` or
`FAIL_EXACT_DRAFT`. Council Review 0001 and its rejected exact candidate remain
immutable historical evidence.

The remediated successor candidate is bound to SHA-256
`a0fa63884be7970e9c0463014b1091f118bc32d0702fc7ebb5402a8410a5c742`,
Git blob `acd0556124be766ec600b63519408952297a582e`, 20,342 bytes, and 389
LF-terminated lines.

Council Review 0002 independently reviewed those exact bytes through five
distinct seats and returned `5/5 PASS_EXACT_DRAFT`. The complete review is
`INCREMENT-21-ERRATUM-0001-COUNCIL-REVIEW-0002.md` at SHA-256
`05a0ec1c18164217983907f141da5a95532d76dc301bd37209a78c704c95f6da`,
Git blob `0453fe8a6d2d2836c69022b82b03d1cb8975f128`, 7,307 bytes, and 166
LF-terminated lines. No Council blocker remains.

Arthur subsequently froze that exact erratum and authorized its preservation
and application to the Increment 21 governance baseline only. The separate
`INCREMENT-21-ERRATUM-0001-FREEZE-RECORD.md` supplies the current disposition
at SHA-256
`d336f9fc98d424bda3907f864060967d66a8c1c417ee09892a557a63e44051b3`,
Git blob `bf8024cdb3c17673f34716d7bf40cd23fde2740d`, 4,300 bytes, and 108
LF-terminated lines, without changing the frozen erratum bytes. Corrected Stage
21C is therefore governed as a read-only readiness and human-merge-observation
stage; CONCLAVE has no merge mutation capability under Increment 21.

The next governed gate requires separate explicit authority either to commit
and publish the bounded governance record set or to draft the replacement
Stage 21C protocol under the frozen erratum. No replacement Stage 21C protocol
has been drafted under it. No freeze is available for the rejected Review 0007
candidate. Stage 21C
implementation, credentials, live GitHub operations, commit, push, pull
request, merge, deployment, production use, KOS changes, IDM changes, signing,
identity allocation, and membership activation remain unauthorized. Stage 21D
also remains outside the authority recorded here.

## 6. Session-start checklist

Before continuing work:

1. verify protected `main` at
   `dda5961fa4aa0c67acafac2de230e9ce9313a03e`, the active branch, remote state,
   and working-tree status;
2. read this file, the frozen Increment 21 master protocol, and the current
   Stage 21C draft and any later freeze/review records;
3. preserve the distinction between protocol drafting, protocol freeze,
   implementation, readiness evidence, exact human authorization, merge
   execution, and production authority; and
4. obtain the next explicit authorization before committing or publishing the
   protocol, changing runtime or tests, enabling credentials, or attempting a
   live adapter operation.
