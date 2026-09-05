# Increment 21 — Governed GitHub repository and pull-request adapter

## Status

**DECISION-COMPLETE CANDIDATE — NOT FROZEN.** Prepared on 5 September 2026
after successful completion of the CONCLAVE v0.8.0 R0–R5 release protocol.
Arthur accepted the nine dispositions recorded in §12. Exact-draft Council
review and an explicit Arthur freeze remain required.

This document is a protocol candidate only. It authorizes no implementation,
credential access, GitHub App creation or installation, API call made as the
adapter, branch creation, commit publication, pull request, review, merge,
repository-setting change, push, release, deployment, KOS change, IDM change,
identity operation, signing operation, or production use.

## 0. Preflight basis

| Item | Verified baseline |
|---|---|
| CONCLAVE protected `main` | `c444cc76e611c74da2f6c6c50aba4b82083403e5` |
| Tree | `abef271be7b5463479a27c265c67d83323876339` |
| Current release | annotated `v0.8.0`, R5 `PASS_EXACT_RELEASE` |
| Supported Python | 3.12–3.13 |
| Current full-suite evidence | 1,088 tests on each required platform; zero failures, errors, or skips |
| Required CI platforms | Windows/Python 3.12, Ubuntu/Python 3.12, Ubuntu/Python 3.13, macOS/Python 3.12 |
| Existing GitHub adapter | none |
| Existing merge-authority rule | providers and CONCLAVE may not assert human approval or merge authority |
| Existing credential storage | none in governed artifacts; selectors only |

The Phase 1B archive is not an input to this increment. Its sealed context
records a now-superseded constitutional disposition and its historical browser
responses were never imported. Increment 21 must not replay or reinterpret it.

## 1. Objective

Increment 21 adds a least-privilege, repository-scoped GitHub boundary that can:

1. verify the identity and current state of one explicitly configured GitHub
   repository;
2. publish one exact, already-governed proposal to a new non-protected branch;
3. create and observe one pull request bound to the exact proposal head;
4. retain factual checks, reviews, conversations, protection, and mergeability
   evidence without treating them as authority; and
5. execute a merge only after a separate, exact-head, human-principal merge
   authorization passes every continuing repository protection rule.

The adapter is an execution boundary, not a decision-maker. It does not decide
what should be changed, whether a review is substantively correct, whether a
governance object is approved, or whether branch protection should be bypassed.

## 2. Maximum boundary and exclusions

Increment 21 is limited to GitHub-hosted repositories explicitly allowlisted by
immutable repository profile. GitHub Enterprise Server, GitLab, Bitbucket,
Azure DevOps, arbitrary Git hosting, local network endpoints, and user-supplied
API origins are deferred.

Increment 21 must not:

- grant a provider, model, reviewer bot, or CONCLAVE itself approval authority;
- change repository visibility, collaborators, teams, organization membership,
  rulesets, branch protection, required checks, review counts, secrets,
  variables, environments, deploy keys, webhooks, Apps, Actions permissions,
  security settings, billing, or repository ownership;
- force-push, delete a branch or tag, rewrite history, update a protected branch
  directly, dismiss a review, resolve a conversation, approve its own pull
  request, or use an administrator bypass;
- create, move, replace, delete, or publish a tag or Release;
- modify `.github/workflows/**`, a CODEOWNERS file, security policy, KOS, IDM,
  constitutional material, offline custody, identity, membership, trust, key,
  signing, or production state;
- store a token, App private key, JWT, refresh token, cookie, or passphrase in
  a governed record, repository, log, exception, test artifact, command line,
  or ledger event. The only permitted credential-derived values are the
  external provider's non-reversible token-instance tag inside the transient
  credential-lease receipt defined by §5 and the non-reversible content hash
  of that complete sanitized receipt in the separate durable lease-evidence
  record. Non-secret mint claims are not credential-derived values and are
  retained in that evidence record. CONCLAVE never computes the tag from the
  token and never writes the receipt or tag itself to public or durable
  evidence;
- send repository content to an AI provider as a side effect of GitHub access;
  or
- infer that GitHub authentication, a green check, an approving review, a merge,
  or repository presence establishes truth, constitutional authority, identity,
  membership, or production readiness.

## 3. Governing order

Implementation shall conform, in descending order, to:

1. KOS authority and governance records explicitly supplied to the task;
2. the active CONCLAVE authority, egress, evidence, orchestration, and human
   decision boundaries through v0.8.0;
3. the exact repository protection and ruleset state observed at operation time;
4. this protocol after exact-draft review and Arthur freeze; and
5. GitHub's versioned API contract for the explicitly selected endpoints.

A GitHub response may provide factual evidence. It cannot supersede a governed
human authorization or weaken a CONCLAVE fail-closed rule.

## 4. Staged delivery

Each stage requires separate implementation, publication, review, merge, and
live-use authority. Completion of one stage does not authorize the next.

### 21A — repository profile and read-only state

Add immutable repository and API-profile records, a credential-independent
transport protocol, credential-lease receipt validation, read-only metadata/
ref/commit/pull-request/check/review/conversation/protection queries, bounded
pagination, redacted diagnostics, and factual observation records. No token is
resolved until all public profile, endpoint, and requested-operation checks
pass; no GitHub request is made until the atomic lease and receipt pass §5.

21A performs no GitHub write and must work against deterministic fixtures in CI.
A live read-only exercise remains separately authorized.

### 21B — bounded branch and pull-request publication

Publish one exact governed proposal to one newly named non-protected branch and
create one pull request. The operation must bind the repository numeric ID,
base ref and commit, new head ref, exact proposal tree/commit, Task Packet,
Handoff, scope review, human publication authorization, title/body hashes, and
allowed file paths before credential resolution.

21B cannot update an existing remote branch, modify workflow or governance
control files, create multiple pull requests, request a merge, or treat PR
creation as approval. Ambiguous publication outcomes stop for reconciliation;
they never trigger an automatic repeat.

### 21C — exact-head review gate and human-authorized merge

Observe and bind the exact PR head, base, required status contexts, reviews,
review freshness, unresolved conversations, mergeability, protection/ruleset
state, and any head change. Prepare a merge-readiness report with no authority
effect.

A merge attempt requires a new immutable authorization authored by the
configured human principal and naming the exact repository, PR number, base,
head commit, merge method, required checks, accepted independent-review record,
expiry, and `maximum_attempts: 1`. Any head change, stale or missing review,
pending/failed check, unresolved conversation, base drift outside the accepted
policy, protection change, or authorization mismatch blocks the attempt.

21C performs no administrator exception and cannot lower protection. If GitHub
reports that an authorized exact-head merge is blocked, CONCLAVE records the
fact and stops for the human principal.

### 21D — security and conformance closeout

Complete cross-platform threat, credential-leak, API-confusion, replay,
pagination, race, ambiguous-outcome, packaging, and installed-wheel evidence.
Prove that no test credential, private App material, GitHub fixture, or live
repository identifier is shipped. Produce an immutable conformance record and
retain exact-head independent review.

21D does not authorize production deployment or unattended merge operation.

## 5. Authentication and least privilege

The preferred actor is a GitHub App installation restricted to selected
repositories. Installation access tokens are short-lived and may be further
restricted at mint time to named repositories and a subset of the App's
granted permissions. CONCLAVE must not assume a fixed token length or parse a
token prefix.

CONCLAVE does not generate or store the GitHub App private key and does not mint
the App JWT. After operation authorization, an external credential provider
atomically supplies one short-lived token and one provider-authenticated,
tamper-evident transient `github-credential-lease-receipt/0.1.0`. The receipt
is a closed canonical in-memory object, not a durable record. It is constructed
atomically from the exact installation-token mint request and successful
response after removal of the token, together with authenticated provider and
installation context, and binds at minimum:

- provider identity and version, unique lease ID, credential class, App ID,
  installation ID, account and repository numeric IDs, and repository
  selection;
- the exact granted permissions, mint and expiry times, and GitHub API version;
  and
- a provider-generated non-reversible token-instance tag, such as an HMAC made
  with a provider-local non-exported key, that binds the receipt to the token
  without exposing or permitting recovery of it.

The provider is the credential-authority boundary and must authenticate the
whole receipt. CONCLAVE treats the tag as opaque: it does not inspect, log,
display, compare, or persist the token or the tag itself. After successful
validation, CONCLAVE stores a separate provider-authenticated
`github-credential-lease-evidence/0.1.0` containing every non-secret receipt
claim, the provider and lease identities, provider-authentication scheme and
version, validation time and outcome, operation-intent binding, and a content
hash commitment to the complete sanitized transient receipt. That commitment
binds the undisclosed tag without storing it. The evidence record contains
neither token nor tag and is received through the same authenticated provider
boundary; the exact channel/authentication mechanism is frozen in 21A. This is
credential-bound operational evidence, not a KOS/IDM identity or governance
signature. Before credential use, every field in the durable non-secret
projection must equal its corresponding authenticated transient-receipt field
exactly, and both objects must bind the same operation intent. The durable
lease-evidence record binds the already-immutable operation-authorization and
operation-intent hashes. Every subsequent observation, publication or merge
receipt, and ledger event binds the lease-evidence record's content hash. This
preserves causal ordering: no pre-existing immutable authorization or intent is
rewritten to name later evidence. The lease-evidence record is durably stored
before the first network request and itself serves as the credential-use
binding; the transport accepts only the exact authorization-hash → intent-hash
→ lease-evidence-hash chain and exact operation named by that intent. A
separate circular precomputation or mutable back-reference is prohibited. Any
inequality or missing binding fails before network I/O. The token and verified
receipt are one indivisible,
in-memory lease; either one without the other is unusable. Receipt
authentication, freshness, App/installation/repository identity, repository
selection, API version, and the exact stage permission envelope are validated
before the first GitHub request. Missing, forged, stale, mismatched, broader,
or additional receipt content fails closed. GitHub repository-access reads may
corroborate but cannot replace the mint receipt's permission evidence.

The governed profile stores only a provider selector and public expected App,
installation, and repository identities. The exact receipt authentication and
token-instance binding mechanism must be frozen in 21A before implementation;
it grants no identity, approval, or governance authority.

Permission envelopes are stage-specific:

- 21A: metadata read plus only the read permissions required by the exact
  observation endpoints;
- 21B: pull-request write and the minimum contents/Git permission needed for
  the reviewed branch-publication mechanism;
- 21C: the minimum merge permission accepted by the exact GitHub endpoint,
  without administration permission or bypass capability; and
- 21D: no additional GitHub permission.

Actions, checks, administration, and contents permissions must be justified
endpoint by endpoint. Workflow write, administration write, secrets,
environments, members, webhooks, deployments, packages, pages, and organization
permissions are prohibited. An API response indicating broader granted access
than the stage profile permits is a hard failure before mutation.

GitHub App installation tokens are the only permitted credential class in
Increment 21. Personal access tokens, OAuth user tokens, GitHub App user access
tokens, Actions tokens, deploy keys, SSH keys, browser sessions, cookies, and
ambient Git credential helpers are prohibited. A credential provider returning
any credential class other than a GitHub App installation token must fail
before network I/O. A future credential class would require a new protocol,
not an Increment 21 fallback.

## 6. Immutable durable record families

Exact schemas are fixed only at stage freeze. The master protocol reserves:

- `github-repository-profile/0.1.0` — host, owner, repository name and numeric
  ID, default branch, allowed base refs, credential-provider selector, expected
  App/installation identity, permission ceiling, and production-use flag;
- `github-credential-lease-evidence/0.1.0` — every non-secret mint claim,
  provider/lease identity, provider-authentication scheme/version, validation
  time/result, operation-intent binding, and the content hash of the complete
  sanitized transient receipt, but never the receipt, token, or token-instance
  tag itself;
- `github-operation-authorization/0.1.0` — human-principal authorization for
  one exact read, publication, or merge operation;
- `github-operation-intent/0.1.0` — the exact authenticated read or mutation,
  authorization hash, repository/profile numeric identity, stage and closed
  endpoint-table operation key, canonical path/query parameters and request-
  body hash, size/pagination/time/retry bounds, and attempt identity, written
  before credential resolution;
- `github-observation/0.1.0` — normalized factual response identities, hashes,
  pagination completion, timestamps, rate-limit class, and reason codes;
- `github-publication-intent/0.1.0` and `github-publication-receipt/0.1.0` —
  publication-specific durable pre-network intent cross-bound to the generic
  operation intent, and observed branch/PR outcome;
- `github-merge-readiness/0.1.0` — exact-head checks/review/protection evidence
  with `authority_effect: none` and `merge_authorized: false`;
- `github-ruleset-no-bypass-attestation/0.1.0` — independently governed,
  expiring evidence of the complete applicable ruleset and bypass-actor state,
  bound to the repository, base, App, and installation identities;
- `github-merge-authorization/0.1.0` — exact-head, one-attempt, expiring human
  authorization; and
- `github-merge-attempt/0.1.0` and `github-merge-receipt/0.1.0` — merge-specific
  durable intent cross-bound to the generic operation intent, and factual
  outcome without approval inference.

Every durable record family listed in this section is closed-schema, canonical,
content-hashed, immutable, bounded, stored under a hash-safe filename, and
cross-bound to its inputs. The transient credential-lease receipt in §5 is
validated canonically in memory and is expressly excluded from durable record
storage. Repository
display names, branch names, PR numbers, URLs, status labels, and review states
are not trusted selectors without the numeric repository ID and exact commit.

## 7. Transport and API boundary

- 21A and every REST operation support only `https://api.github.com`. If the
  separately reviewed 21B mechanism selects credential-safe Git transport,
  its exact HTTPS Git origin, protocol surface, credential injection boundary,
  and redirect rules must be frozen in 21B before implementation. This master
  protocol neither authorizes that origin nor silently makes REST-only wording
  select the competing REST Git-database mechanism.
- TLS and hostname verification are mandatory; redirects, proxies from ambient
  environment, userinfo, alternate origins, arbitrary headers, and caller-
  supplied URLs are refused.
- Use one frozen GitHub API version and the documented media type.
- Endpoints are selected from a closed operation table, never concatenated from
  an arbitrary path.
- Request and response sizes, pagination pages/items, timeouts, retries, and
  rate-limit handling are bounded.
- Every authenticated read and mutation has one generic durable operation
  intent written before credential resolution and network I/O. Mutations also
  require their publication- or merge-specific intent cross-bound to it before
  credential resolution. Automatic mutation retry is prohibited.
- Credential resolution returns the token and authenticated lease receipt
  atomically. Receipt validation precedes all GitHub network I/O; the transport
  cannot accept a bare token or resolve a second credential during an operation.
- Read-only retries may occur only for explicitly classified pre-response
  transport failures, within a small frozen ceiling, and must not hide partial
  pagination.
- Response bodies are parsed through closed projections; unknown security-
  relevant states block rather than disappear.
- Raw headers or bodies that may contain credentials, cookies, internal URLs,
  email addresses, or unbounded user content are not retained.

## 8. Git and pull-request invariants

1. Repository identity is numeric-ID-bound and rechecked immediately before
   every mutation.
2. The base branch and exact base commit are explicit; no implicit default is
   accepted for mutation.
3. A publication branch is new, task-scoped, safe-name validated, and proven
   absent immediately before creation.
4. The proposal tree contains only paths authorized by the Task Packet and
   accepted scope review.
5. Symlinks, submodules, Git LFS pointers, `.git*` paths, workflow files,
   CODEOWNERS, and control-plane files fail closed unless a later protocol
   explicitly governs them.
6. No force update, ref deletion, tag operation, default-branch update, or
   direct protected-branch write exists in the adapter.
7. PR title and body are bounded canonical inputs; provider text cannot smuggle
   mentions, commands, hidden markup, or authority claims into them unchecked.
8. A PR head is re-read immediately before any merge attempt. Authorization is
   invalidated by any different head SHA.
9. Merge readiness requires a fresh, independently governed
   `github-ruleset-no-bypass-attestation/0.1.0`. It binds the repository numeric
   ID, exact base ref and commit, App ID, installation ID, every applicable
   repository and organization ruleset ID/source/target/enforcement/version or
   update marker, the complete bypass-actor set, observation and expiry times,
   and an assertion that neither the App, its installation, nor its acting
   account is a bypass actor. The attestation's authentication mechanism is
   frozen in 21C. It supplies factual no-bypass evidence only and cannot
   authorize a merge. Missing, expired, incomplete, unverifiable, or mismatched
   evidence blocks the merge. A GitHub response that omits `bypass_actors`, or
   an Administration-read response whose completeness is not independently
   established, is insufficient. CONCLAVE receives no Administration-write.
10. The merge mutation uses only GitHub's synchronous
   `PUT /repos/{owner}/{repo}/pulls/{pull_number}/merge` endpoint. Its request
   must carry the authorization-bound exact head SHA in `sha` and must set
   `merge_method` explicitly to `merge`. A missing parameter, head mismatch,
   HTTP 409, unknown response, or `merged` value other than literal `true` is
   non-success and permits no retry. The asynchronous merge endpoint, merge
   queues, default-method selection, squash, rebase, auto-merge, and branch-
   update endpoint are outside Increment 21.
11. Merge success is established only by the synchronous response's returned
    merge commit and a follow-up read proving the base contains the authorized
    head result.
12. Timeout or disconnect after a mutation is ambiguous and blocks repetition
    until read-only reconciliation establishes one factual outcome.

## 9. Threat and abuse cases

Acceptance evidence must cover at least:

- repository-name reuse or transfer while numeric ID differs;
- credential scope broader than the immutable permission ceiling;
- missing, forged, replayed, stale, mismatched, or over-broad credential-lease
  receipts; token/receipt substitution; and bare-token injection;
- confused-deputy access to an unlisted repository or organization;
- SSRF, redirect, proxy, DNS, TLS, path, query, header, and API-version abuse;
- pagination truncation, duplicate entries, reordered checks, missing pages,
  rate-limit partial state, and stale cached observations;
- branch/ref injection, Unicode confusables, case collision, tag/branch
  ambiguity, protected-base spoofing, and unsafe file modes;
- TOCTOU changes to base, head, protection, ruleset, reviews, checks,
  conversations, or repository identity;
- hidden, omitted, stale, or changed repository/organization rulesets and
  bypass actors; false no-bypass attestation; and App-as-bypass-actor cases;
- omission or substitution of the merge request's conditional `sha`, merge
  method, endpoint, or synchronous execution semantics;
- self-review, bot-review-as-human, dismissed/stale review, requested-changes,
  unresolved conversations, and checks with unknown or neutral conclusions;
- duplicate PR creation, duplicate branch mutation, replayed authorization,
  ambiguous network outcome, crash before receipt, and concurrent attempt;
- malicious PR content, Markdown command injection, log injection, and
  untrusted GitHub response text;
- token, cookie, App key, JWT, email, private URL, response-body, and diagnostic
  leakage across stdout, stderr, exceptions, ledger, artifacts, packages, and
  test reports; and
- any attempt to infer approval, authority, identity, membership, truth, or
  production readiness from GitHub state.

## 10. Required acceptance evidence

At each exact PR head and again on protected `main`, the required Windows,
Ubuntu, and macOS matrix must prove:

1. closed immutable records, exact hashes, idempotent reads, and conflict
   retention;
2. repository numeric-ID, host, ref, commit, Task Packet, Handoff, scope,
   authorization, and operation cross-binding;
3. complete endpoint/permission inventory with insufficient and excessive
   permission failures;
4. atomic credential-lease delivery; authenticated receipt validation; exact
   App/installation/repository/permission/API-version/expiry binding; bare,
   forged, stale, substituted, and excessive leases failing before network;
   credential non-storage, single-resolution timing, redaction, and sentinel
   leak scans; and refusal by 21A reads and every mutation to resolve or use a
   credential without the exact authorization → generic operation-intent →
   lease-evidence chain;
5. deterministic fixture transport for every allowed endpoint and response
   projection, with no CI access to a live GitHub mutation target;
6. all threats in §9, including race injection immediately before mutation;
7. durable intent, concurrency lock, replay refusal, ambiguous-outcome stop,
   and read-only reconciliation;
8. branch/PR publication cannot update an existing ref or touch a prohibited
   path;
9. merge cannot occur without the exact fresh human authorization, all
   continuing GitHub protections, and a fresh complete independently governed
   no-bypass attestation covering every applicable repository and organization
   ruleset; omitted or unverifiable bypass state fails closed;
10. factual ledger events and no-inference reconstruction;
11. package inventory and secret/static scans proving fixture and credentials
    are absent from installed artifacts; and
12. the complete existing suite remains green with no required security skip.

A separately authorized live exercise must use a disposable repository made
for conformance testing. It must not target KOS, IDM, CONCLAVE `main`, a client
repository, or any production repository.

## 11. Rollback and failure rules

- Before publication, correct defects with a new reviewed commit; do not rewrite
  accepted evidence.
- A branch or PR created successfully is retained as factual state. Automatic
  deletion is not rollback.
- An ambiguous mutation stops. A read-only reconciliation may determine whether
  the exact operation occurred; it cannot authorize another attempt.
- No cleanup routine may delete a remote branch, close a PR, rewrite a commit,
  dismiss a review, or change protection without new exact human authority.
- A bad merge is never repaired by history rewriting. It requires the
  repository's governed corrective-change process.
- Credential suspicion triggers external revocation and sanitized incident
  handling; secrets are never copied into CONCLAVE evidence.

## 12. Arthur decisions accepted before exact-draft review

On 5 September 2026, Arthur accepted the following dispositions:

1. **Stage ordering:** accept 21A–21D as separately governed stages in the
   order defined by §4.
2. **Primary authentication:** require GitHub App installation authentication
   for a production-capable design. App private-key and JWT handling remain
   outside CONCLAVE.
3. **Personal-token fallback:** permit no personal access token fallback in
   Increment 21.
4. **Branch-publication mechanism:** defer the choice between credential-safe
   Git transport and bounded Git database REST calls until a 21B security
   implementation review can compare their concrete attack surfaces. 21A must
   not prejudge or implement either mechanism.
5. **Merge execution:** 21C may execute one merge only after a fresh exact-head
   authorization from the configured human principal and satisfaction of every
   continuing repository control. Merge execution remains dormant and
   separately authorized after implementation.
6. **Merge method:** initially permit only a normal merge commit when that
   method is enabled by the repository. Rebase and squash are excluded. An
   unavailable allowed method blocks rather than substitutes another method.
7. **Protection evidence permission:** Administration-read may be requested
   only when the selected read-only protection endpoint demonstrably requires
   it. The endpoint and accepted-permission evidence must be retained.
   Administration-write remains prohibited. Because GitHub may omit ruleset
   bypass actors without ruleset-write access, an Administration-read response
   alone cannot prove no-bypass status. Stage 21C must require the external,
   independently governed no-bypass attestation in §8 and fail closed when it
   is absent or incomplete.
8. **Live conformance target:** any later live exercise must use a dedicated
   disposable repository. Its exact identity and maximum operation count must
   be named in a separate authorization; this decision creates neither.
9. **Visibility:** repository visibility changes remain direct human operations
   outside CONCLAVE and outside Increment 21.

These decisions complete the policy inputs for master-protocol review. They do
not freeze the protocol or authorize a stage implementation or live operation.

## 13. Official factual references

The following GitHub documentation was consulted on 5 September 2026. These
references describe external platform behavior and do not grant authority:

- GitHub App permission selection and least privilege:
  `https://docs.github.com/en/apps/creating-github-apps/registering-a-github-app/choosing-permissions-for-a-github-app`
- GitHub App authentication modes:
  `https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/about-authentication-with-a-github-app`
- Installation-token repository/permission narrowing and one-hour expiry:
  `https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/generating-an-installation-access-token-for-an-app`
- Installation-token mint response fields:
  `https://docs.github.com/en/rest/apps/apps#create-an-installation-access-token-for-an-app`
- REST endpoints available to installation access tokens:
  `https://docs.github.com/en/rest/authentication/endpoints-available-for-github-app-installation-access-tokens`
- GitHub App endpoint permission mapping:
  `https://docs.github.com/en/rest/authentication/permissions-required-for-github-apps`
- Synchronous pull-request merge parameters, including conditional `sha`,
  explicit `merge_method`, and HTTP 409 on a head mismatch:
  `https://docs.github.com/en/rest/pulls/pulls#merge-a-pull-request`
- Repository ruleset response visibility, including conditional exposure of
  `bypass_actors`:
  `https://docs.github.com/en/rest/repos/rules#get-a-repository-ruleset`
- Organization ruleset endpoints and permission requirements:
  `https://docs.github.com/en/rest/orgs/rules`

## 14. Current disposition

The v0.8.0 release is complete and unchanged. This decision-complete candidate
records a proposed Increment 21 boundary only. No runtime or test file has
changed, no credential was accessed, and no GitHub adapter operation was
executed. The next step is exact-draft Council review. Implementation remains
prohibited unless the reviewed protocol is explicitly frozen and the relevant
stage is separately authorized.
