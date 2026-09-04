# CONCLAVE v0.8.0

## Identity verification and governed evidence

- Increment 19A added closed, immutable public trust-input, actor-binding and
  verification-result records with fail-closed identity, domain, role, scope,
  time, revocation and content-binding checks.
- Increment 19B added closed signing requests and fail-closed import of
  externally produced evidence through an explicitly injected, pinned public
  verifier. Exact envelope bytes and verification bindings remain immutable.
- Increment 19C added explicit `local`, `verify` and `attested` workspace modes
  and fail-closed gates for egress, authority decisions, evidence receipts and
  ledger checkpoints. Verification remains authority-neutral and confers no
  membership or decision authority.
- Increment 19D added a fixture-only external broker and public verification
  adapter for the exact hash-pinned IDM v1 baseline, with end-to-end attached-
  payload COSE_Sign1, delegation, scope, trusted-time and revocation tests.

## Sandbox configuration, operation and conformance

- Increment 20A added immutable exact-reference verifier and broker profiles
  plus source-checkout-only, keyless fixture diagnostics. It does not select a
  default profile, strengthen identity mode or open a network connection.
- Increment 20B added a dormant sandbox-only HTTPS transport library with a
  durable pre-network attempt intent, one-attempt authorization, strict TLS and
  destination controls, and secret-free receipts. It added no operator command
  and performs no automatic retry.
- Increment 20C added exact-reference operator commands for sandbox endpoints,
  one-attempt authorizations, submission, inspection and recovery. An ambiguous
  result may be abandoned without transmission or replayed once only under a
  new exact authorization, using the original bytes and idempotency key.
- Increment 20D added the closed security-conformance record and fourteen
  frozen threat-control findings, package inventory and scanning, static
  capability checks, fresh-wheel probing and secret-free CI evidence.
- Post-20D CI maintenance upgraded artifact publication to the Node.js-24-
  native upload action and added regression coverage for the bounded JUnit XML
  input limit. This was a maintenance correction, not a runtime capability.

## Requirements and tested compatibility

CONCLAVE requires Python 3.12 or newer. The v0.8.0 release matrix is targeted,
not a claim that every operating-system/Python combination is tested:

| Environment | Coverage |
|---|---|
| Windows latest / Python 3.12 | required Windows behavior and path semantics |
| Ubuntu latest / Python 3.12 | declared minimum-Python compatibility |
| Ubuntu latest / Python 3.13 | required Linux and newest declared minor |
| macOS latest / Python 3.12 | required macOS behavior and path semantics |

Every release job runs the full suite, builds and inspects both package
formats, installs the wheel in a fresh environment, exercises CLI help and
version, and retains finalized secret-free evidence.

## Upgrading an existing v0.7.0 workspace

Installing v0.8.0 does not rewrite or migrate an existing workspace. Its
existing `bootstrap_version` continues to identify the release that originally
created it. New workspaces record `bootstrap_version: 0.8.0`.

A workspace with no identity-mode record continues to resolve to `local`.
Upgrade does not silently strengthen the mode to `verify` or `attested`; those
modes still require an explicit principal-confirmed operation and their
existing fail-closed prerequisites.

Komistry OS remains external and read-only. CONCLAVE does not modify KOS, and
the governed workflows use explicit operator-supplied source manifests rather
than silently traversing a KOS repository.

## Security and authority boundaries

This release includes no embedded signer, private-key API, production broker,
production trust domain or automatic retry. It allocates no identity, activates
no membership and does not turn identity, signature or evidence verification
into truth, approval, authority or ratification. Provider and sandbox broker
calls remain explicit operations subject to exact human authorization; none is
scheduled or inferred by CONCLAVE.

Arthur remains the sole constitutional authority. Providers are advisory,
Council output remains pending for human decision, and CONCLAVE cannot approve,
ratify, commission or merge an action.

## Known limitations

- There is no runtime GitHub repository adapter or automated pull-request
  creation or merge.
- Human confirmation is local and single-operator, not multi-custodian. There
  is no production signing broker or key integration.
- There is no trust or calibration tracking and no semantic comparison of
  provider prose.
- Undeclared object use is not detected; only declarations are evaluated, and
  `conclave validate` covers Task Packets only.
- Most ledger events are wired at the CLI boundary, so direct library calls do
  not record operational artifacts; authority-decision recording is the stated
  exception.
- The local ledger lock coordinates writers on one machine only.
