# Stage 21C fixture-first sequencing erratum candidate

Status: DRAFT / NOT FROZEN / NOT APPLIED / NO IMPLEMENTATION AUTHORITY
Date: 2026-09-19

This is an unnumbered proposal. It does not occupy an accepted erratum number.

## Affected requirements

- Readiness protocol section 4.3, SHA-256
  `d3701754c7ab782835bc92db07c055509e415a69765373ed5cd30f250164b257`:
  preservation and build pinning of operational trust before implementation.
- Collection protocol section 20, SHA-256
  `6ea468c1cdd3a4ac0befecd3ffa3c2c26cfb51218902fb3af20366e4dbbb91c2`:
  implementation sequence placing key generation and operational trust ahead
  of implementation.

## Proposed exception

After this erratum is separately reviewed and adopted, and after separate
bounded implementation authorization, a fixture-only Stage 21C prototype may
be implemented and tested before operational key generation or issuance of
operational trust authorizations.

The exception applies only to a separately identifiable test executable/package
using synthetic identities, fixture transports, and public test vectors or
explicitly disposable test keys. It confers no operational trust. It must not
contain a live GitHub transport, live credential discovery, operational key
provider, merge path, or an operational trust-loading path. Runtime switches
cannot convert that test artifact into an operational artifact.

Test provenance belongs to an enclosing fixture artifact, not new fields in
frozen signed schemas. No synthetic trust record is an Arthur-issued decision,
and no test `ready` result authorizes a human or machine action.

## Unchanged operational requirements

Before an operational implementation build is approved, the exact two accepted
Arthur-issued trust authorizations must exist and be pinned under readiness
section 4.3. The external collector/verifier implementation trust store and
one-use key-provider enforcement remain mandatory under the collection
protocol. Operational artifact review must prove fixture seeds/providers and
test-only trust are excluded.

No changes are proposed to signature algorithms, domains, record schemas,
canonical encoding, role separation, endpoint permissions, no-bypass evidence,
request budgets, human-only merge, or fail-closed result handling.

This erratum does not authorize operational key generation, signing, credentials,
live collection, trust-store deployment, merge, repository settings, Stage 21D,
production, KOS, IDM, identity allocation, or membership activation. It does not
authorize its own commit, push, adoption, or implementation.

## Review acceptance

Review must establish that the fixture build has no path to operational use,
that the exception cannot be used to skip operational trust gates, and that its
scope fits the governing Increment 21 human-merge split. Changes elsewhere
remain separately governed. Author review of this draft is not independent
Council approval.
