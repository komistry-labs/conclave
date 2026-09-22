# Stage 21C: GitHub-backed human approval transition

Date: 2026-09-19
Status: USER-SELECTED DIRECTION / LOCAL REPLACEMENT DESIGN / NOT FROZEN

## 1. Decision and authority

Arthur selected option 2: "okay, apply your solutions option 2 and move on".
The selected direction is GitHub-backed human approval with external signing
deferred. This document applies that decision to the local design and work plan.
It is not a claim that a replacement protocol has passed review or is deployed.

No additional keys or offline key ceremony are prerequisites for this proposed
profile. Two-factor authentication protects accounts; it is not a replacement
signature format and does not prove that a particular approval used a second
factor. CONCLAVE remains an observer and assistant, never the merge authority.

This direction supersedes the fixture-first/key-provider method as the active
local proposal. Preserve that proposal, its sequencing-erratum candidate, the
failed ceremony plan, and Reviews 0001-0005 as historical evidence. Do not
represent their unresolved findings as fixed or passed: the associated signing
and custody capability is deferred, not successfully implemented.

## 2. Frozen-baseline transition

Verified local base: `154394c570a9919fc00b7c00779f565f742508e2`.

The following frozen files remain byte-for-byte unchanged:

- Readiness protocol SHA-256:
  `d3701754c7ab782835bc92db07c055509e415a69765373ed5cd30f250164b257`.
- Collection protocol SHA-256:
  `6ea468c1cdd3a4ac0befecd3ffa3c2c26cfb51218902fb3af20366e4dbbb91c2`.

This is a substantive assurance-profile change, not merely a sequencing erratum.
Before runtime implementation, a separately reviewed replacement must explicitly
resolve the following affected contracts and be adopted as the governing profile:

| Existing contract | Replacement design |
| --- | --- |
| Readiness 3, 4.2-4.3: independent signers, signed record families and pinned trust | Separately named GitHub-backed observation records; no unsigned records accepted as signed ones |
| Readiness 7-8: independent no-bypass attestation and ready predicate | Bounded advisory policy observation; unavailable facts prevent a positive assessment |
| Readiness 9-11: signed human handoff, post-action observation and reconciliation | Exact-head GitHub review/action references and observed merge reconciliation, without independent authorization claims |
| Readiness 14-15: acceptance and implementation prerequisites | Tests for reduced-assurance profile, fixture-only implementation first; no operational signing gate |
| Collection 3-4, 8, 15: verifier, signer, envelopes and bundle | Read-only source collection and locally hashed observations; hashes show local integrity, not issuer authenticity |
| Collection 12-14, 16: bypass inventory, interval continuity and results | Retain visibility limits; snapshots do not establish uninterrupted protection or absence of undisclosed bypass |
| Collection 19-20: tests and implementation sequence | Replacement acceptance criteria and separate implementation/live-operation gates |

This impact map is a drafting checklist, not a claim of exhaustive review.
Master-protocol compatibility and every dependent schema must be checked before
freeze. Existing signed-profile consumers must reject the new profile unless
explicitly updated under that reviewed contract; no fallback on signature failure.

## 3. Intended workflow

1. Establish the human owner's GitHub account security and repository policy.
   Current 2FA, permissions, organization enforcement and protection settings
   are NOT VERIFIED by this document. A browser login alone is not evidence.
2. Collect read-only observations for one repository ID, PR number, exact head,
   base and policy snapshot. Preserve source identities, observation times,
   coverage, bounded response evidence and local integrity hashes.
3. Report one advisory assessment: SATISFIED_AS_OBSERVED, BLOCKED or UNKNOWN.
   Observed failure takes precedence over missing evidence; missing required
   evidence takes precedence over a positive assessment. A positive result
   means only that the configured observable criteria matched at collection.
4. The human checks GitHub's current PR and performs any approval or merge in
   GitHub. CONCLAVE cannot approve for a person, change controls or merge.
5. Observe the resulting merge, exact head, merge parents/tree as applicable,
   checks and artifacts. Report mismatches or incomplete evidence explicitly.

Head/base/policy drift invalidates the earlier assessment and requires a new
bounded observation. This does not promise an atomic view of GitHub or close
the race between observation and human action. GitHub's controls and the human
remain responsible at the action boundary.

## 4. Controls and limitations

- Retain required checks, review policy, conversation resolution, code-owner and
  last-push requirements, administrator enforcement and force-push/deletion
  restrictions. This document grants no exception or setting change.
- Independent review means another person, not a second account controlled by
  the author. Missing independent approval remains blocked when policy requires
  it; 2FA does not satisfy that requirement.
- Preserve repository/organization/enterprise ruleset visibility and bypass
  inventory limitations. Denied, incomplete, unsupported, stale or conflicting
  evidence is never interpreted as no restriction or no bypass.
- Do not claim independently authenticated control attestations, independently
  signed authorization, protection continuity, or proof of a second factor at
  merge time. A GitHub merged state is an observation, not proof of compliance.
- A valid GitHub session or API credential is not made safe solely by account
  2FA. Credential scopes, storage, expiry and compromise remain separate gates.
- No secret values, recovery codes, cookies or tokens belong in evidence.
- Keep existing transport ceilings as upper bounds; derive the read budget so
  retries and pagination cannot exceed the 96-envelope ceiling. Exhaustion
  produces an incomplete result, never relaxed limits or a positive result.
- Retain captured review IDs, author/account IDs, commit binding, timestamps and
  mutable-source caveats. Do not assume comments or reviews are immutable.

## 5. Next bounded work

Prepare a compact replacement protocol and closed observation schemas from this
impact map, then perform exact-draft review before freeze. This drafting work is
the next step under the selected direction; do not resume the generic ceremony.

The implementation acceptance plan must cover exact-head drift, stale/dismissed
reviews, same-person review, failed/missing checks, incomplete rulesets, hidden
bypass capability, altered evidence, budget exhaustion, interrupted pagination,
and the impossibility of emitting the old signed-profile success result.
Require fixture-based tests, installed-package boundary checks and actual
Windows/macOS/Linux evidence before platform claims. No tests have been run
for a replacement implementation because none is authorized or created here.

After protocol review and adoption, obtain bounded implementation authority.
Credentials and live collection remain separately authorized. No commit, push,
PR, merge, GitHub setting change, Stage 21D, production, KOS/IDM change, identity,
membership, key generation, signing or trust deployment is performed or inferred.

## 6. Factual references

Checked against official GitHub documentation on 2026-09-19:

- [Organization 2FA requirement](https://docs.github.com/en/organizations/keeping-your-organization-secure/managing-two-factor-authentication-for-your-organization/requiring-two-factor-authentication-in-your-organization): organization owners can require 2FA; enabling it can affect collaborator access and is not performed here.
- [Protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches): review/check requirements are repository controls distinct from account authentication.

## 7. Current disposition

Option 2 recorded as the selected design direction. External signing and key
ceremony deferred. Replacement protocol/schema drafting next. Frozen baseline
unchanged; no Council or independent PASS claimed; no runtime or remote mutation.
