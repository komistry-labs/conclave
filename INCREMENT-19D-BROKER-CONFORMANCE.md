# Increment 19D — Broker conformance fixture

## Disposition

**IMPLEMENTED WITHIN THE AUTHORIZED 19D BOUNDARY.** Repository application is
governed by a separate reviewed PR, exact-head CI and protected-main
post-merge CI.

## Delivered

Increment 19D provides a fixture-only external signing broker and a
verification-only adapter for the frozen IDM v1 reference implementation. The
adapter refuses to operate unless both retained distributions match the exact
accepted hashes:

- wheel `idm_reference-0.1.0.dev0-py3-none-any.whl`:
  `07120effab0182701e47449e572b94e5a952c210aebfdf217fd965696154d903`;
- source `idm-3769ce3-source.zip`:
  `98335d16dd0dd7bdfeb27fa77374e741e575cec3bbafc009a66c80374188efb7`;
- IDM commit `3769ce3943c87e6a5a72bf94b0efdaa2b11c3bd2`, tree
  `425f650696a798c10f2a553781fee45e0950dc2a`.

The public runtime adapter exposes only identity and evidence verification. It
has no key-loading, key-generation, allocation, issuance or signing method.
Actual signing occurs in an un-packaged test harness subprocess that requires
both the `--fixture-only` flag and `CONCLAVE_FIXTURE_BROKER=1`. It returns only
the public COSE envelope and a hash-only receipt.

## Fixture boundary

The fixture trust domain, identities, delegation and keys are freshly derived
from visibly non-production test labels. They are not B1/B2 rehearsal objects
and are not accepted by any production trust configuration. Temporary private
fixture bytes exist only in the isolated test workspace passed to the external
harness. No private-key artifact is committed, returned, logged or exposed by
the CONCLAVE runtime.

The retained wheel, source archive and dependency lock are public dependency
evidence. Their presence does not adopt any KOS or IDM authority state,
identity registry, trust bundle, custody material or membership record.

## Conformance evidence

The suite exercises the real IDM implementation and actual COSE_Sign1 bytes:

- exact distribution pinning and valid identity verification;
- external-broker signing, evidence import and an attested gate end to end;
- signed empty revocation state plus entity, manifest-lineage, revision, key
  and delegation revocation rejection;
- wrong context, detached payload, unknown field, future/expired evidence,
  wrong role and workspace cross-binding rejection;
- tampered envelope, malformed revocation state and distribution substitution
  rejection;
- byte-identical canonical CBOR/COSE vectors across platforms; and
- absence of a runtime signing/key surface or tracked private-key artifact.

Local Windows validation on 2026-08-16:

- focused 19D suite: **21 passed**;
- complete suite: **892 passed, 1 platform-conditional symlink test skipped**;
- deterministic COSE vector SHA-256:
  `36c3325004291ae27d1f143128d736ffc3d46595b9f9ec46923c9637e3df4523`.

The reviewed PR and protected-main matrices cover Python 3.12 on Windows,
Python 3.13 on Ubuntu and Python 3.12 on macOS.

## Preserved non-authorization

19D is conformance evidence, not production broker integration. It does not
authorize production or rehearsal trust-domain bootstrap, access to offline
custody, identity or K1 allocation, key generation or import, manifest
issuance, membership, constitutional action, KOS or IDM mutation, deployment,
release or production reliance.
