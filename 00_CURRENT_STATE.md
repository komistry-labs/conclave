# CONCLAVE Current Project State

Last verified: 2026-09-10
Status class: `GOVERNED_BRANCH_CANDIDATE`

## 1. Product baseline

- product version: `0.8.0`
- Python floor: `>=3.12`
- protected remote `main`:
  `c3804e2077bfe38f66623404da51d1bd0478846b`
- active branch: `feature/increment-21b-bounded-publication`
- accepted Stage 21B implementation and recovery commit:
  `4fad8b03823b724913ecf8454a84c8837fc47b2e`
- accepted implementation tree:
  `7540069356b5fe0f627dba7822e007652c3e5878`

The governance-record commit containing this CPS will advance the feature
branch beyond the accepted implementation commit without changing its
runtime or test tree. This record does not claim that the active branch has
been merged into `main`; an exact pull-request head must be verified only if
PR creation is later authorized.

## 2. Current increment disposition

Increment 21's master protocol, Stage 21A, the Stage 21B protocol, and Stage
21B Erratum 0001 are already present in the governed history leading to the
current `main` baseline.

Corrected Stage 21B implementation is now:

- implemented on the isolated feature branch;
- fixture- and loopback-only;
- locally verified on Windows/Python 3.12;
- approved across the preserved five-seat Council implementation and recovery
  review chain, with the final correction delta bound to exact aggregate
  `f545344b57a0aba4cad4b959014dd94d829de6f0d2bbbd2ef6ae3ba821fc1a1f`;
- remotely accepted on Windows/Python 3.12, macOS/Python 3.12,
  Ubuntu/Python 3.12, and Ubuntu/Python 3.13; and
- supported by four retained, secret-free conformance artifacts.

The exact remote acceptance run is `34448996906`:

`https://github.com/komistry-labs/conclave/actions/runs/34448996906`

## 3. Evidence and recovery history

- initial implementation commit:
  `930af95f72bd8de3c7d32f78af165515f13b5715`
- first-recovery commit:
  `e334eefb2800681165a781bbbfbe9da607726694`
- accepted recovery commit:
  `4fad8b03823b724913ecf8454a84c8837fc47b2e`
- rejected remote runs: `34444730211`, `34446903733`
- accepted remote run: `34448996906`
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
branch evidence.

CONCLAVE provides bounded capability and evidence. KOS remains external and
retains authority.

## 5. Next governed gate

The next step is explicit authorization to create a pull request from
`feature/increment-21b-bounded-publication` into `main` at an exact head.
After PR creation, merge still requires exact-head independent review, passing
required checks, and separate merge authority under the repository's
protection policy.

Stages 21C and 21D remain outside the authority recorded here.

## 6. Session-start checklist

Before continuing work:

1. verify `main`, the active branch head, remote branch state, and working-tree
   status;
2. read this file and the Stage 21B protocol, Erratum 0001, recovery record,
   re-review 0013, and closeout record;
3. preserve the distinction between a verified branch candidate, an open pull
   request, a merged change, and production authority; and
4. obtain the next explicit authorization before creating a PR, merging,
   enabling credentials, or attempting a live adapter operation.
