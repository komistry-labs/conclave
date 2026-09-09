# Increment 21A — Read-only GitHub foundation

## Status

**DECISION-COMPLETE DRAFT — NOT REVIEWED OR FROZEN.** Drafted on
8 September 2026 under the frozen Increment 21 master protocol identified by
the exact content identities in §0. This draft makes no claim about the branch
or commit at which that governing content is published.

This document defines a candidate implementation protocol and candidate schema
contracts only. It authorizes no implementation, runtime or test change,
credential access, GitHub App creation or installation, token minting, live
GitHub API call, branch, commit, push, pull request, merge, repository-setting
change, Stage 21B–21D work, deployment, production use, KOS or IDM change,
signing, identity allocation, or membership activation.

## 0. Governing baseline

This stage is subordinate to
`INCREMENT-21-GITHUB-REPOSITORY-AND-PR-ADAPTER.md` at frozen SHA-256
`89a05211a4323db2e79d2854952b24ce033c71f357430c7ac839457ff0878d75`
and Git blob `83d8fb2cabb9d343b6a8d089d920d25dcd8c5728`.

If this draft conflicts with the frozen master, the master controls and the
draft fails review. Existing CONCLAVE canonical hashing, closed-model,
immutable-write, conflict-retention, authority, redaction, and ledger rules
continue unchanged.

The implementation baseline is CONCLAVE v0.8.0 on Python 3.12–3.13. Stage 21A
adds no GitHub mutation and no general-purpose HTTP client.

## 1. Stage objective and completion boundary

21A may implement only the foundation required to make authenticated,
repository-scoped, read-only GitHub observations through a closed transport:

1. immutable repository and API profiles;
2. one immutable human read authorization and one generic operation intent per
   logical read operation;
3. atomic receipt of an external GitHub App installation-token lease;
4. authenticated transient lease-receipt validation and durable non-secret
   lease evidence before network I/O;
5. closed REST endpoint selection and closed response projections;
6. factual observations of repository, ref, commit, pull request, checks,
   statuses, reviews, comments, branch protection, and rulesets;
7. bounded pagination, time, size, retry, rate-limit, and failure behavior; and
8. deterministic fixture and cross-platform acceptance evidence.

Stage completion does not authorize a live exercise. A live read-only exercise
requires a separate authorization naming a disposable repository numeric ID,
the exact profile and operations, and the maximum request count.

## 2. Explicit exclusions

21A contains no POST, PUT, PATCH, or DELETE endpoint and no GraphQL operation.
It cannot create or update refs, commits, files, branches, pull requests,
reviews, comments, checks, statuses, protection, or rulesets. It cannot approve,
merge, resolve, dismiss, rerun, enable, disable, install, mint, or administer.

The following are also excluded:

- personal access, OAuth, GitHub App user, Actions, browser, cookie, SSH, deploy
  key, ambient Git-helper, or anonymous-authentication fallback;
- App private keys, App JWT creation, installation-token minting, and token
  renewal inside CONCLAVE;
- GitHub Enterprise Server, configurable origins, caller-supplied URLs,
  redirects, ambient proxies, arbitrary headers, and Git transport;
- raw response, response-header, comment-body, review-body, commit-message,
  patch, email-address, URL, token, token tag, or transient receipt retention;
- inference of authority, approval, identity, membership, correctness,
  no-bypass status, merge readiness, or production readiness; and
- any 21B publication, 21C merge-readiness or merge operation, or 21D closeout.

REST comment observations do not reveal the authoritative resolved/unresolved
state of GitHub review threads. 21A therefore records that visibility as
`not_observed` and cannot produce a conversation-resolution or no-bypass
attestation. Those gates remain 21C concerns.

## 3. Common canonical-record contract

All durable 21A records use the existing `ClosedModel`/`HashedRecord` contract:

- unknown fields are forbidden and values are strict and frozen;
- UTF-8 JSON is serialized with sorted keys, compact separators, and no
  non-finite numbers;
- `content_hash` is `sha256:` plus 64 lowercase hexadecimal characters and is
  computed with that field absent;
- timestamps are UTC RFC 3339 strings with `Z`, second precision, and no leap
  second;
- lists preserve protocol-defined order unless a schema says they are sorted;
- maps have an explicit closed key set;
- storage filenames contain the final content digest and never a GitHub name,
  login, ref, URL, lease ID, or credential selector, except the attempt claim's
  deterministic attempt-digest address defined in §5.3; and
- an existing unequal record is retained as a conflict and never overwritten.

Every record carries the invariant fields below in addition to its family
fields:

| Field | Contract |
|---|---|
| `profile` | Exact family name without the version suffix |
| `schema_version` | Exact family/version literal |
| `created_at` | Canonical UTC timestamp |
| `authority_effect` | `none`, except read authorization uses `github_read_only` |
| `decision_effect` | Always `none` |
| `membership_effect` | Always `none` |
| `production_use_allowed` | Always `false` in 21A |
| `content_hash` | Canonical content hash |

References are workspace-relative POSIX paths paired with the referenced
record's exact `content_hash`. A reference without its matching hash is invalid.

## 4. Immutable profile schemas

### 4.1 `github-repository-profile/0.1.0`

This record allowlists exactly one repository.

| Field | Type and rule |
|---|---|
| `repository_profile_id` | ASCII lower-kebab identifier, 1–64 characters |
| `host` | Literal `github.com` |
| `api_origin` | Literal `https://api.github.com` |
| `owner` | GitHub owner name, 1–39 ASCII characters, case preserved for display only |
| `repository` | GitHub repository name, 1–100 permitted ASCII characters, no `.git` suffix |
| `repository_id` | Positive GitHub numeric repository ID |
| `repository_node_id` | Optional bounded GitHub node ID, display/evidence only |
| `account_id` | Positive numeric owner account ID |
| `git_object_format` | Exact repository object format: `sha1` or `sha256` |
| `default_branch` | Exact full ref tail, 1–255 UTF-8 bytes, no control, backslash, ambiguity, or traversal form |
| `allowed_base_refs` | Sorted unique list of 1–8 full refs in `refs/heads/<tail>` form |
| `credential_provider_selector` | Opaque local selector, 1–128 safe ASCII characters; never a command, path, URL, or environment-variable expansion |
| `expected_provider_id` | Safe ASCII provider identifier, 1–64 characters |
| `expected_provider_versions` | Sorted unique allowlist of 1–8 safe ASCII version identifiers |
| `provider_key_reference` | Workspace-relative reference to one `github-credential-provider-key/0.1.0` record |
| `provider_key_hash` | Exact content hash of that provider-key record |
| `expected_provider_key_id` | Safe ASCII Ed25519 verification-key identifier, 1–128 characters |
| `expected_provider_public_key_sha256` | `sha256:` plus the SHA-256 of exactly the 32 decoded Ed25519 public-key bytes, as 64 lowercase hexadecimal characters |
| `expected_app_id` | Positive GitHub App numeric ID |
| `expected_installation_id` | Positive installation numeric ID |
| `repository_selection` | Literal `selected` |
| `permission_ceiling` | Closed permission map from §6.2 |
| `read_operations` | Sorted unique subset of the operation keys in §7.2 |
| `live_use_allowed` | Always `false` in the 21A implementation baseline |

Owner and repository names form only path parameters for the profile's numeric
identity; successful `repository.get` must return the exact `repository_id` and
`account_id`. A name match with either numeric mismatch is
`REPOSITORY_IDENTITY_MISMATCH`.

### 4.2 `github-api-profile/0.1.0`

One profile fixes the complete HTTP behavior:

| Field | Frozen candidate value |
|---|---|
| `api_profile_id` | `github-rest-2026-03-10-read-only-v1` |
| `origin` | `https://api.github.com` |
| `api_version` | `2026-03-10` |
| `accept` | `application/vnd.github+json` |
| `user_agent` | `conclave-github-adapter/21a` |
| `authentication_scheme` | `Bearer` |
| `tls_policy` | `system-ca-hostname-tls12-plus` |
| `redirect_policy` | `deny` |
| `proxy_policy` | `ignore-environment-and-deny` |
| `connect_timeout_seconds` | `5` |
| `read_timeout_seconds` | `20` |
| `operation_timeout_seconds` | `60` |
| `maximum_request_header_bytes` | `16384` |
| `maximum_response_header_bytes` | `32768` |
| `maximum_response_body_bytes_per_page` | `2097152` |
| `maximum_total_response_body_bytes` | `8388608` |
| `default_page_size` | `100` |
| `maximum_pages` | `10` |
| `maximum_items` | `1000` |
| `maximum_retry_transmissions_per_operation` | `1` |
| `maximum_transmissions_for_one_page` | `2` |
| `retry_delays_milliseconds` | `[250]` |
| `endpoint_table_version` | `github-21a-rest-endpoints/0.1.0` |
| `response_projection_version` | `github-21a-rest-projections/0.1.0` |

Only these application-controlled request headers may be emitted: `Accept`,
`Authorization`, `X-GitHub-Api-Version`, and `User-Agent`. The HTTP stack may
add protocol-required `Host` and connection framing, but compression is
disabled and environment-derived or caller-supplied headers are refused.
`Content-Type`, cookies, conditional headers, custom correlation headers, and
caller headers are refused. The Authorization value is constructed inside the
transport and is never exposed through a record or diagnostic.

The selected REST version is currently supported by GitHub. API-version
support remains an implementation preflight: an unsupported selected version
fails closed; it is never silently replaced with GitHub's default or a newer
version.

### 4.3 `github-credential-provider-key/0.1.0`

This public trust-anchor record contains `provider_id`, `key_id`,
`algorithm: "Ed25519"`, a canonical unpadded base64url 32-byte public key,
`public_key_sha256`, `valid_from`, `valid_until`, `status: "active"`, and the
common invariant fields. `public_key_sha256` is computed over exactly the 32
decoded public-key bytes and must equal
`expected_provider_public_key_sha256`; its provider ID and key ID must also
equal the repository profile. Its validity window must contain both local
signature-validation times defined in §6.5. It contains no secret, grants no
identity or governance authority, and is not fetched or replaced during an
operation.

Key rotation requires a new immutable profile and trust-anchor record. An
unknown, expired, future-valid, superseded, or locally conflicting key blocks
credential resolution; the transport never performs key discovery.

## 5. Authorization and intent schemas

### 5.1 `github-operation-authorization/0.1.0`

A configured workspace human principal creates one authorization for one exact
logical read. Required fields are:

- `authorization_id`: UUIDv7 string;
- repository-profile reference and hash;
- API-profile reference and hash;
- exact repository numeric ID and account numeric ID;
- `stage: "21A"` and `operation_mode: "read_only"`;
- one endpoint operation key from §7.2;
- exact canonical path and query parameters, excluding owner/repository values
  already bound by the repository profile;
- `purpose`, 1–512 UTF-8 bytes with controls forbidden;
- `authorized_principal`, exactly equal to the workspace principal;
- `issued_at` and `expires_at`, with a lifetime from 1 second through 15 minutes;
- `maximum_logical_operations: 1`; and
- `maximum_network_requests`, exactly the endpoint's page ceiling plus one
  possible retry transmission across the whole logical operation.

This authorization grants only bounded GitHub read egress. It is not an
approval of repository content or a delegation of governance authority.

### 5.2 `github-operation-intent/0.1.0`

The intent is written before credential resolution. Required fields are:

- `intent_id`: UUIDv7 string;
- authorization reference and hash;
- repository- and API-profile references and hashes;
- repository numeric ID, account numeric ID, App ID, and installation ID;
- `stage: "21A"`, `http_method: "GET"`, and one operation key;
- canonical path parameters and canonical query parameters;
- `request_body_hash: null` and `request_body_bytes: 0`;
- the exact size, pagination, timeout, and retry values copied from the API
  profile, reduced further where the endpoint table requires;
- `attempt_id`: `attempt:sha256:<digest>` computed by the closed preimage
  contract below;
- `created_at` and `not_after`, where `not_after` is no later than the
  authorization expiry; and
- `maximum_credential_resolutions: 1`.

For a paginated endpoint, one logical intent binds the deterministic sequence
`page=1..N`, constant `per_page=100`, `N<=maximum_pages`, and early termination
only when GitHub's pagination response proves there is no next page. A Link URL
is never followed. It is parsed only as evidence; the next request is rebuilt
from the closed endpoint template and the incremented integer. A different
origin, endpoint, immutable path parameter, query key, decreasing/repeated page,
or page above the bound fails the operation as incomplete.

An intent is single-use. Existing attempt or observation evidence for the same
`attempt_id` blocks replay unless a separately authorized reconciliation reads
the retained factual result without network I/O.

The attempt digest is frozen as follows. Construct a closed object with exact
`schema_version: "github-operation-attempt-preimage/0.1.0"` and only these
members: `authorization_hash`, `repository_profile_hash`, `api_profile_hash`,
`operation_key`, `path_parameters`, `query_parameters`,
`maximum_response_body_bytes_per_page`, `maximum_total_response_body_bytes`,
`maximum_pages`, `maximum_items`, `operation_timeout_seconds`,
`maximum_retry_transmissions_per_operation`, and `maximum_network_requests`.
Hashes and strings use their already validated exact forms; parameter maps use
their closed endpoint-specific scalar types; integer bounds are unsigned JSON
integers. Serialize that object as the canonical JSON contract in §3 with
lexicographically sorted keys and no `content_hash`. The preimage bytes are the
ASCII domain `CONCLAVE-GITHUB-OPERATION-ATTEMPT-V1`, one zero byte, and those
canonical UTF-8 JSON bytes. `<digest>` is the lowercase hexadecimal SHA-256 of
that byte sequence. Unknown, omitted, null-substituted, differently typed, or
noncanonical input fails before claim creation. This framing is the only valid
attempt-ID computation on every platform.

### 5.3 `github-operation-attempt-claim/0.1.0`

Before credential resolution, CONCLAVE atomically creates one immutable claim
at `github/attempt-claims/attempt-<attempt-digest>.json` using exclusive-create
semantics (`CREATE_NEW` on Windows and `O_CREAT|O_EXCL` on POSIX). The digest is
the 64-hex suffix of `attempt_id`; no caller controls the path. The closed claim
contains `attempt_id`, authorization/intent/profile references and hashes,
repository/account/App/installation IDs, operation key, claim time, intent
expiry, `state: "claimed"`, and the common invariant fields.

The file passes the complete durable-write gate in §6.5 before credential
resolution. Any existing path—even an equal claim—or an inability to prove
exclusive creation and durable persistence blocks another
resolution and request. Unequal content is additionally
`ATTEMPT_CLAIM_CONFLICT`; equal content is `ATTEMPT_ALREADY_CLAIMED`. A crash
leaves the claim in place and therefore fails closed. No automatic stale-claim
deletion, takeover, or retry exists. A later local-only reconciliation may
report the retained claim but cannot authorize network I/O. Lease evidence,
observations, and ledger events bind the claim reference and content hash.
This attempt-digest path is the claim's sole atomic-exclusion key and the only
exception to content-digest filenames. The claim body still carries and
verifies its normal final `content_hash`; immutable conflict retention applies
at that deterministic addressed path.

## 6. Credential lease boundary

### 6.1 Provider authentication mechanism

The candidate 21A mechanism is `conclave-github-lease-ed25519-v1`:

1. The external credential provider owns the App key, App JWT, token-minting
   process, provider signing key, and provider-local token-tag key.
2. CONCLAVE stores only the provider's public Ed25519 verification key in a
   separately immutable public provider-key record. The repository profile
   pins its record hash, key ID, and SHA-256 fingerprint over the decoded key.
3. `resolve_once()` returns one atomic in-memory envelope containing the token,
   transient receipt, receipt signature, and a provider-owned pair-validation
   capability. A partial envelope is unusable.
4. CONCLAVE verifies the receipt signature and public bindings, then invokes
   `validate_pair_once()` on that same capability. The provider recomputes and
   constant-time compares its private-keyed token-instance tag against the
   exact token currently held in the envelope. Success returns one signed,
   non-secret provider-claims projection; substitution returns no claims and
   fails before network I/O.
5. Each signature is the canonical unpadded base64url encoding of exactly 64
   Ed25519 signature bytes. Padding, non-URL alphabets, alternate encodings, or
   noncanonical lengths are rejected. It covers ASCII domain separation, one
   zero byte, and canonical JSON bytes with the signature field absent:
   `CONCLAVE-GITHUB-LEASE-RECEIPT-V1` or
   `CONCLAVE-GITHUB-LEASE-CLAIMS-V1`.
6. CONCLAVE verifies both signatures, all bindings, the receipt hash, and exact
   receipt/claims projection equality, then creates the durable lease evidence
   and a private sealed in-memory lease object.
7. Only that object can enter the transport. There is no bare-token transport
   method. One consumption admits one logical operation with no more than the
   authorized page ceiling plus one internal retry transmission.

The provider performs the tag comparison; CONCLAVE treats the tag as opaque
and never computes, displays, logs, persists, or compares it. The internal
lease is built from the exact token that passed `validate_pair_once()` and has
no public constructor or token mutator. Arbitrary mutation of trusted process
memory after validation is outside this protocol's threat model; caller- or
provider-level token/receipt substitution before validation is required to
fail in fixtures.

The token carrier returned by `resolve_once()` must be a provider-owned mutable
erasable byte buffer; Python `str` and immutable `bytes` are forbidden token
carriers. From the instant resolution returns, CONCLAVE enters one `finally`
cleanup scope covering receipt authentication, pair validation, claims
authentication, durable evidence creation, lease construction, transport, and
every normal, exceptional, cancellation, and timeout exit. Cleanup overwrites
the full buffer in place on best effort, asks the provider capability to close
and erase any provider-side transient state, and releases all references. A
cleanup failure is retained as a redacted factual failure and prevents any
later request or reuse. No Python implementation claims forensic-proof memory
erasure, but no failure before sealed-lease construction may bypass the cleanup
attempt.

Ed25519 public-signature verification uses the PyCA `cryptography` package,
with runtime declaration `cryptography>=49,<50` and exact version `49.0.0`
plus distribution hashes in the implementation lock evidence. No private-key
operation is exposed. Missing backend support, a dependency outside the range,
an unlocked distribution, or an unverified wheel/sdist fails installation or
conformance; it never falls back to a handwritten or alternate verifier.

The exact 21A provider channel is an injected in-process
`GitHubCredentialLeaseProvider` interface. The embedding caller supplies an
already-constructed provider object directly to the library operation; the
profile selector is used only to compare the object's declared provider ID.
CONCLAVE performs no provider discovery, dynamic import, executable launch,
shell call, subprocess, stdin/stdout exchange, file polling, environment lookup,
local or remote socket, browser flow, or CLI credential input. Any vault,
network, key custody, JWT, minting, or secret retrieval behind that object is
provider-owned behavior outside CONCLAVE and outside 21A.

CONCLAVE calls `resolve_once(request)` exactly once and
`validate_pair_once()` at most once. The validation call cannot mint, renew,
replace, or return another token. `request` is a closed,
ephemeral, non-secret `github-credential-resolution-request/0.1.0` containing
the provider selector/ID/version allowlist, profile and key-record hashes,
repository/account/App/installation numeric IDs, exact operation permission
envelope, API version, authorization and intent hashes, intent expiry, and a
fresh 32-byte resolution nonce represented only by its `sha256:` hash. The
provider returns the atomic envelope directly by value. The request and
envelope are never serialized or stored by CONCLAVE. The transient receipt,
provider claims, and durable evidence must all bind the resolution-nonce hash;
replay of an envelope for another resolution therefore fails before network
I/O. Tests inject a deterministic nonce source, while non-test operation
requires the operating-system cryptographic random source.

### 6.2 Closed permission envelope

The only recognized repository permission keys and maximum values in 21A are:

| Permission | Maximum | Required by |
|---|---|---|
| `metadata` | `read` | repository and active branch-rule reads |
| `contents` | `read` | ref and commit reads |
| `pull_requests` | `read` | pull request, reviews, and PR comment reads |
| `checks` | `read` | check-run reads |
| `statuses` | `read` | commit-status reads |
| `administration` | `read` | branch-protection read only |

Every other permission is implicitly `none` and must be absent or literal
`none`. In particular, every write permission is prohibited. The repository
profile ceiling is the union of permissions available to its allowlisted
operations; it is not the permission request for every token. Each token must
be narrowed to the exact per-operation envelope from §7.2: mandatory
`metadata: read` plus only that row's additional permission. The receipt and
evidence maps must equal that minimum envelope and remain a subset of the
profile ceiling. This deliberately rejects any additional read or write access.

`administration: read` may be included only when the authorized operation is
`branch_protection.get`. No other 21A operation can inherit Administration-read
merely for convenience.

### 6.3 Transient `github-credential-lease-receipt/0.1.0`

This strict in-memory object is never written. It contains:

- family/version, provider ID/version/key ID, unique lease ID, and credential
  class literal `github_app_installation_access_token`;
- App ID, installation ID, account ID, exact one-element repository-ID list,
  and `repository_selection: "selected"`;
- the closed exact permission map;
- `minted_at` and `expires_at`, with expiry after mint and no more than 60
  minutes later;
- GitHub API version `2026-03-10`;
- repository-profile, API-profile, authorization, and operation-intent hashes;
- exact credential-resolution-request nonce hash;
- `provider_receipt_validation_outcome: "pass"` and
  `provider_receipt_validation_at`;
- opaque `token_instance_tag`, 16–256 safe ASCII characters; and
- provider authentication scheme/version/key ID and Ed25519 signature.

At durable-evidence admission time, the token must have at least 90 seconds
remaining: the 60-second operation ceiling plus a 30-second local-clock margin.
Clock tolerance never enlarges the signed mint-to-expiry interval. The receipt
must not predate the authorization. Unknown fields, unknown permission
keys, missing claims, repeated repository IDs, or extra repositories fail
before network I/O.

### 6.4 Durable `github-credential-lease-evidence/0.1.0`

The provider's signed `github-credential-lease-claims/0.1.0` contains every
non-secret receipt field except `token_instance_tag` and the receipt signature;
it retains the receipt authentication scheme/version/key ID, adds
`provider_pair_validation_outcome: "pass"` and
`provider_pair_validation_at`, retains the exact nonce hash, and includes
`sanitized_transient_receipt_hash` over the
complete canonical transient receipt including its opaque tag and receipt
signature but never the token. It contains no CONCLAVE validation claim. The
claims signature uses the provider key and canonical representation fixed in
§6.1. The provider-claims canonical `sha256:` hash is computed over the complete
signed claims object including its claims signature; the Ed25519 signature
itself covers only the unsigned canonical claims payload as defined in §6.1.

After receipt and claims verification, CONCLAVE creates the durable
`github-credential-lease-evidence/0.1.0`. It contains:

- the complete provider-claims object and its Ed25519 signature, plus its
  canonical `sha256:` hash;
- every non-secret receipt claim as the exact nested provider projection;
- `receipt_signature_validation: "pass"` and
  `receipt_signature_validated_at`, `pair_validation_completed_at`, and
  `claims_signature_validation: "pass"` and
  `claims_signature_validated_at`, which are CONCLAVE observations and are not
  presented as provider claims;
- exact attempt-claim, authorization, and intent references and hashes;
- exact credential-resolution-request nonce hash;
- `sanitized_transient_receipt_hash`, recomputed by CONCLAVE and exactly equal
  to the provider claim;
- `logical_operation_use_limit: 1`, `maximum_network_requests` copied exactly
  from the authorization,
  `network_started_at_evidence_creation: false`, and
  `credential_material_persisted: false`, meaning the durable evidence record
  contains no credential material while the separately held mutable in-memory
  token may still exist until cleanup; and
- the normal CONCLAVE `content_hash`.

CONCLAVE durably commits this evidence through the persistence gate in §6.5
before the first network request. Every
non-secret claims projection must equal the corresponding authenticated receipt
value exactly. The nested signed claims make the durable evidence
provider-authenticated without asking the provider to attest to CONCLAVE's
later validation result. The stored record contains neither token, tag,
transient receipt, nor receipt signature.

### 6.5 Frozen time and persistence gates

All comparisons use parsed UTC instants; serialized times remain the canonical
second-precision form in §3. The signed provider sequence must satisfy
`authorization.issued_at <= minted_at <= provider_receipt_validation_at <=
provider_pair_validation_at < expires_at`. The local call sequence must satisfy
`receipt_signature_validated_at <= pair_validation_completed_at <=
claims_signature_validated_at <= evidence.created_at <=
first_network_request_started_at`; equal adjacent values are permitted because
records have second precision. Both local signature-validation times must fall
inside the provider-key record's inclusive `valid_from`/`valid_until` window.
`evidence.created_at` must be no later than the authorization expiry and intent
`not_after`.

The only clock-skew allowance is 30 seconds for a provider timestamp that is
ahead of its corresponding local observation. `minted_at` and
`provider_receipt_validation_at` must each be no later than
`receipt_signature_validated_at + 30 seconds`; `provider_pair_validation_at`
must be no later than `pair_validation_completed_at + 30 seconds`. A violation
is `CREDENTIAL_TIME_INVALID`, including a future-minted credential beyond that
allowance. No skew is applied to expiry, authorization expiry, intent
`not_after`, the 60-minute signed mint-to-expiry ceiling, or the 90-second
remaining-life requirement. Immediately before durable evidence commit and
again immediately before the first transmission, the local clock must be at or
before all applicable unadjusted deadlines; otherwise the operation terminates
without network I/O. The second gate repeats the full requirement that at least
90 seconds remain until `expires_at`; merely being unexpired is insufficient.
Every later page or retry must still be within the monotonic 60-second operation
deadline and the unadjusted credential, authorization, and intent deadlines.

The 21A durable immutable-write primitive is a stricter admission wrapper around
the existing immutable record encoder. For both the attempt claim and lease
evidence it must exclusively create the final validated path, write the complete
canonical bytes, flush language buffers, complete the applicable platform
sequence below, then reopen and byte-verify the record and its content hash:

- Linux/POSIX: `fsync` the file, close it, open the parent directory without
  following links, and `fsync` then close the directory handle.
- macOS: issue `F_FULLFSYNC` on the file, close it, then open, `fsync`, and close
  the parent directory. Absence or failure of `F_FULLFSYNC` fails closed.
- Windows: create the final file with exclusive `CREATE_NEW` semantics, write
  through its file handle, call `FlushFileBuffers` on that final file handle,
  close it, then reopen and byte/hash verify it. Windows does not require or
  attempt a directory-handle flush; this named sequence is the frozen 21A
  Windows persistence barrier.

The attempt claim uses its deterministic addressed-path exception; lease
evidence uses its final content-digest filename. Existing equal content is not
success for an attempt claim. Any unsupported filesystem, partial write,
required barrier/close/readback error, wrong bytes, or hash mismatch fails
closed.
Only this wrapper may create a private
`DurableLeaseEvidenceAdmission` capability, and only after every barrier,
close, readback, and hash check succeeds. It is non-serializable,
non-deserializable, not publicly constructible, and contains process-local
unforgeable object identity plus the exact evidence path, evidence
`content_hash`, `attempt_id`, and attempt-claim hash. The wrapper incorporates
that capability directly into the sealed in-memory lease; callers cannot pass
an admission value separately. The transport accepts only that combined lease,
atomically consumes both the lease and admission capability for one logical
operation, and rejects a mismatched, reused, copied, deserialized, fabricated,
or prior-process value. No admission capability survives process restart. An
in-memory return from `write_immutable_record` alone is insufficient. Tests
must inject barrier failures at every step and prove zero transport calls, and
must also prove zero calls for attempted direct construction, serialization or
deserialization, lease/admission mismatch, reuse, copying, and fabrication.

## 7. Closed REST transport

### 7.1 URI construction and network rules

The transport owns the literal origin and templates. Each raw path parameter is
validated by type, percent-encoded once by one route-aware implementation, and
then substituted into a fixed template. Caller-supplied percent escapes,
backslash, empty or dot segments, userinfo, fragment, control, CR/LF, NUL,
double encoding, and ambiguous ref forms are rejected. A validated branch may
contain `/`; only the transport may encode or place those separators according
to the fixed GitHub route. The final encoded path must round-trip to the exact
validated raw parameter and still match the selected endpoint template.

Commit and check/status selectors must be full lowercase hexadecimal object IDs
whose length exactly matches the verified repository `git_object_format`: 40
characters for `sha1` or 64 for `sha256`. Branch or tag names are not accepted
in object-ID slots. The ref operation accepts only a full
`refs/heads/<tail>` allowed by the repository profile and deterministically
constructs GitHub's `heads/<tail>` ref parameter from it. Pull-request and
ruleset IDs are positive decimal integers in canonical form.

DNS resolution is performed by the system resolver, but the HTTPS request must
retain the exact `api.github.com` hostname for TLS verification. Direct IP
origins, alternate ports, redirects, and proxy tunneling are refused. The HTTP
library's environment trust is disabled.

The concrete implementation uses Python's standard-library
`http.client.HTTPSConnection` with `ssl.create_default_context()`, certificate
verification and hostname checking enabled, and TLS 1.2 as the minimum. It does
not use a general URL opener, shell command, GitHub CLI, or third-party HTTP
client. `http.client` performs no automatic redirect or environment-proxy
handling. Responses are read in bounded chunks and `Content-Encoding` must be
absent or `identity`; compressed bodies are rejected rather than decompressed.
The connection uses the five-second timeout through connect/TLS, then applies
the 20-second socket read timeout while a monotonic 60-second deadline bounds
the whole logical operation. It is closed after each logical operation and
cannot be reused for a different intent or lease.

### 7.2 Endpoint table `github-21a-rest-endpoints/0.1.0`

All entries are GET and use the frozen headers. No other route exists.

| Operation key | Fixed path | Query | Additional permission beyond mandatory metadata/read | Page/item ceiling |
|---|---|---|---|---|
| `repository.get` | `/repos/{owner}/{repo}` | none | none | 1/1 |
| `repository_hash_algorithm.get` | `/repos/{owner}/{repo}/hash-algorithm` | none | none | 1/1 |
| `ref.get` | `/repos/{owner}/{repo}/git/ref/{ref}` | none | contents/read | 1/1 |
| `commit.get` | `/repos/{owner}/{repo}/git/commits/{commit_sha}` | none | contents/read | 1/1 |
| `pull_request.get` | `/repos/{owner}/{repo}/pulls/{pull_number}` | none | pull_requests/read | 1/1 |
| `check_runs.list` | `/repos/{owner}/{repo}/commits/{commit_sha}/check-runs` | `per_page=100&page=N` | checks/read | 10/1000 |
| `combined_status.get` | `/repos/{owner}/{repo}/commits/{commit_sha}/status` | `per_page=100&page=N` | statuses/read | 10/1000 |
| `reviews.list` | `/repos/{owner}/{repo}/pulls/{pull_number}/reviews` | `per_page=100&page=N` | pull_requests/read | 10/1000 |
| `issue_comments.list` | `/repos/{owner}/{repo}/issues/{pull_number}/comments` | `per_page=100&page=N` | pull_requests/read | 10/1000 |
| `review_comments.list` | `/repos/{owner}/{repo}/pulls/{pull_number}/comments` | `per_page=100&page=N` | pull_requests/read | 10/1000 |
| `branch_protection.get` | `/repos/{owner}/{repo}/branches/{branch}/protection` | none | administration/read | 1/1 |
| `branch_rules.list` | `/repos/{owner}/{repo}/rules/branches/{branch}` | `per_page=100&page=N` | none | 10/1000 |
| `repository_rulesets.list` | `/repos/{owner}/{repo}/rulesets` | `includes_parents=true&per_page=100&page=N` | none | 10/1000 |
| `repository_ruleset.get` | `/repos/{owner}/{repo}/rulesets/{ruleset_id}` | `includes_parents=true` | none | 1/1 |

`repository.get` followed by `repository_hash_algorithm.get` are mandatory
profile-verification operations for every newly loaded profile. Each has its own
authorization, intent, attempt claim, lease evidence, and observation. Profile verification is
cached only by both immutable observation hashes and expires after five minutes;
a later logical read still rechecks the bound repository ID from its endpoint
response wherever GitHub supplies it.

Ruleset endpoints may omit bypass actors when the actor lacks write access.
21A prohibits that write access. Ruleset projections therefore always record
`bypass_actor_visibility: "incomplete_by_permission"` unless the response
explicitly supplies the field, in which case they record
`"observed_not_attested"`. Neither state proves absence or completeness.

### 7.3 Retry and rate-limit behavior

Only a read may be retried, and only once across the entire logical operation,
after an explicitly classified DNS, connect, TLS-handshake, or connection-loss
failure before response headers. The retry consumes the authorization's one
additional network request beyond the endpoint page ceiling; no later page may
retry.
HTTP responses, body-parse failures, size failures, timeouts after response
headers, pagination failures, 304, 403, 404, 409, 422, 429, 5xx, and unknown
errors are never retried. The retry remains inside the same admitted logical
lease use and reuses the intent and page request; it does not resolve another
credential. The lease is consumed when the logical operation terminates; the
§6.1 cleanup scope then performs its mandatory best-effort buffer overwrite and
provider-capability close on every exit.

Primary or secondary rate limiting stops immediately. Only a safe subset is
retained: rate-limit resource class, numeric limit, remaining, UTC reset time,
and a boolean `retry_after_present`. `Retry-After` values, raw headers, request
IDs, and error bodies are not retained. 21A never sleeps until a reset and never
automatically resumes partial pagination.

### 7.4 Pagination completeness

Every page is independently bounded and hashed before projection. The operation
fails closed as `INCOMPLETE` if any page is missing, repeated, oversized,
malformed, inconsistent, or beyond bounds; if item IDs repeat; if total counts
contradict retained items; or if a next relation exists after page 10.
Partial items may be retained only inside an observation explicitly marked
`complete: false`; they cannot satisfy any later gate.

GitHub documents a separate check-run visibility horizon: when a reference has
more than 1,000 check suites, `check_runs.list` considers only runs from the
1,000 most recent suites. Returned run count cannot prove whether that horizon
was applied. Therefore every successful check-run observation records
`visibility: "complete_within_github_check_suite_horizon"`,
`github_check_suite_horizon: 1000`, and `global_history_complete: false`.
`complete: true` for this endpoint means only complete pagination of the
bounded response GitHub made visible; it never asserts all historical suites or
runs were observable.

## 8. Closed response projections

Response JSON is parsed once into a closed endpoint projection. Security-
relevant unknown enum values produce `UNKNOWN_SECURITY_STATE`; additive
irrelevant fields are discarded only after the endpoint-specific projection
has confirmed all required keys and types.

The projection families retain only the following normalized facts:

| Observation kind | Retained facts |
|---|---|
| repository | repository/account numeric and node IDs; canonical full name; private/archived/disabled flags; visibility; default branch; merge-method enablement |
| repository hash algorithm | exact `sha1` or `sha256`, matched to the immutable repository profile |
| ref | requested full ref, returned ref, object SHA/type; only `commit` object type passes |
| commit | commit SHA, tree SHA, ordered parent SHAs, GitHub verification boolean/reason/time; no names, emails, message, signature, or payload |
| pull request | numeric PR/repository/base/head identities and SHAs; state, draft, merged, mergeable, mergeable_state; author numeric ID; timestamps; no title/body/URLs |
| check runs | total count; sorted run ID, App ID, name hash, head SHA, status, conclusion, started/completed times; no output text, annotations, URLs, or external IDs |
| combined status | target SHA, aggregate state, total count; sorted status ID, context hash, state, creator numeric ID, updated time; no description, target URL, or login |
| reviews | sorted review ID, reviewer numeric ID/type, state, submitted time, commit ID, dismissal marker where supplied; body excluded |
| issue comments | sorted comment ID, author numeric ID/type, created/updated times, minimized flag; body excluded |
| review comments | sorted comment/review/parent IDs, author numeric ID/type, path hash, commit/original-commit IDs, created/updated times; body and diff hunk excluded |
| branch protection | required checks as sorted context/App-ID pairs, strictness, admin enforcement, review count, stale/code-owner/last-push flags, conversation resolution, required signatures, block creations, force-push/deletion/linear-history/lock/fork-sync flags, and restriction actor numeric IDs/types when supplied |
| branch rules | sorted rule type and canonical parameter hash, ruleset source/type/ID when supplied; enforcement visibility facts |
| repository ruleset | ruleset numeric ID/source/target/enforcement/update time, condition hash, sorted rule type/parameter hashes, bypass actor numeric IDs/types/modes only when supplied, plus explicit bypass visibility |

### 8.1 Normative raw-field and type contract

The following notation is normative: `id` is a strict integer from 1 through
`2^63-1` (a JSON boolean is not an integer); `oid` is lowercase hexadecimal of
the repository's verified object-format length; `ts` is a second-precision UTC
RFC 3339 string; `s(N)` is UTF-8 text of at most N bytes with NUL and controls
forbidden; `hash` is `sha256:` plus 64 lowercase hex; `T?` is a required key
whose value may be JSON null; and `[T]` is an array within the endpoint item
ceiling. Every unmarked key below is required and non-null. A missing required
key differs from an explicit null and is invalid.

Documented optional security blocks use `{present: bool, value: T?}` in the
normalized projection so absence and null cannot collapse into `false` or an
empty collection. Additive raw fields not named below are discarded only after
the full named contract validates. Objects and arrays are limited to depth 16,
10,000 total JSON nodes per page, 256 object keys, and the byte limits in §4.2.
Duplicate JSON keys are rejected before projection.

Normalized collections are sorted by their numeric primary ID; ties or
duplicate IDs fail. Required-status pairs sort by `(context_hash, app_id)` and
rules by `(type, parameter_hash, ruleset_id)`. Git commit parents alone retain
GitHub's source order. Raw API order has no authority effect.

| Operation | Required raw contract; documented nullable/optional fields |
|---|---|
| `repository.get` | object: `id:id`, `node_id:s(128)`, `name:s(100)`, `full_name:s(256)`, `owner:{id:id,node_id:s(128)}`, `private:bool`, `archived:bool`, `disabled:bool`, `visibility:repository_visibility`, `default_branch:s(255)`, `allow_merge_commit:bool`, `allow_squash_merge:bool`, `allow_rebase_merge:bool` |
| `repository_hash_algorithm.get` | object: `hash_algorithm:git_object_format` |
| `ref.get` | object: `ref:s(1024)`, `node_id:s(128)`, `object:{sha:oid,type:git_object_type}` |
| `commit.get` | object: `sha:oid`, `node_id:s(128)`, `tree:{sha:oid}`, `parents:[{sha:oid}]`, `verification:{verified:bool,reason:verification_reason,verified_at:ts?}`; names, emails, message, payload, and signature are ignored, never retained |
| `pull_request.get` | object: `id:id`, `number:id`, `state:pull_state`, `draft:bool`, `merged:bool`, `mergeable:bool?`, `mergeable_state:mergeable_state`, `user:{id:id,type:actor_type}`, `head:{sha:oid,ref:s(255),repo:{id:id}?}`, `base:{sha:oid,ref:s(255),repo:{id:id}}`, `created_at:ts`, `updated_at:ts`, `closed_at:ts?`, `merged_at:ts?` |
| `check_runs.list` | object: `total_count:int>=0`, `check_runs:[{id:id,name:s(512),head_sha:oid,status:check_status,conclusion:check_conclusion?,app:{id:id}?,started_at:ts?,completed_at:ts?}]` |
| `combined_status.get` | object: `sha:oid`, `state:commit_status_state`, `total_count:int>=0`, `statuses:[{id:id,context:s(512),state:commit_status_state,creator:{id:id,type:actor_type}?,updated_at:ts}]` |
| `reviews.list` | array: `[{id:id,user:{id:id,type:actor_type}?,state:review_state,submitted_at:ts?,commit_id:oid?}]` |
| `issue_comments.list` | array: `[{id:id,user:{id:id,type:actor_type}?,created_at:ts,updated_at:ts,minimized:bool?}]` |
| `review_comments.list` | array: `[{id:id,pull_request_review_id:id?,in_reply_to_id:id?,user:{id:id,type:actor_type}?,path:s(4096),commit_id:oid,original_commit_id:oid?,created_at:ts,updated_at:ts}]` |
| `branch_protection.get` | object with documented optional blocks `required_status_checks`, `enforce_admins`, `required_pull_request_reviews`, `restrictions`, `required_signatures`, `block_creations`, `required_linear_history`, `allow_force_pushes`, `allow_deletions`, `required_conversation_resolution`, `lock_branch`, `allow_fork_syncing`; each block preserves presence, validates documented booleans/IDs, and hashes but does not retain URLs or names |
| `branch_rules.list` | array: `[{type:rule_type,ruleset_source_type:ruleset_source_type,ruleset_source:s(256),ruleset_id:id,parameters:bounded_json_object?}]`; full canonical parameters are hashed before discard |
| `repository_rulesets.list` | array: `[{id:id,node_id:s(128),source_type:ruleset_source_type,source:s(256),enforcement:ruleset_enforcement,created_at:ts,updated_at:ts,target:ruleset_target?}]`; names and links are discarded |
| `repository_ruleset.get` | object: list-summary fields plus `target:ruleset_target`, `conditions:bounded_json_object`, `rules:[{type:rule_type,parameters:bounded_json_object?}]`, documented optional `bypass_actors:[{actor_id:id?,actor_type:bypass_actor_type,bypass_mode:bypass_mode}]`; conditions/parameters are fully canonical-hashed before discard |

For branch protection, each present block has this minimum closed sub-contract:

- `required_status_checks`: `strict:bool`, `contexts:[s(512)]`, and optional
  `checks:[{context:s(512),app_id:id?}]`;
- `enforce_admins`, `required_signatures`, `block_creations`,
  `required_linear_history`, `allow_force_pushes`, `allow_deletions`,
  `required_conversation_resolution`, `lock_branch`, and `allow_fork_syncing`:
  `enabled:bool`;
- `required_pull_request_reviews`: `dismiss_stale_reviews:bool`,
  `require_code_owner_reviews:bool`, `required_approving_review_count:int[0,6]`,
  `require_last_push_approval:bool`, plus optional restriction arrays whose
  entries require numeric actor IDs and closed actor types; and
- `restrictions`: optional `users`, `teams`, and `apps` arrays whose entries
  require numeric IDs. Missing numeric identity makes the block incomplete.

URLs and additional presentation fields inside these blocks are ignored.
Unknown top-level branch-protection keys or unknown keys within a named security
block are retained only through a `security_extension_hash` over their bounded
canonical JSON and force `complete:false` with `UNKNOWN_SECURITY_STATE`; they
never silently disappear. Additive presentation fields explicitly excluded by
the projection—URLs and display names only—do not trigger that failure.

### 8.2 Closed enum contract

The only accepted values in response projections are:

- `git_object_format`: `sha1`, `sha256`;
- `git_object_type`: `commit` (any tag/tree/blob result fails this stage);
- `repository_visibility`: `public`, `private`, `internal`;
- `actor_type`: `User`, `Bot`, `Organization`, `Mannequin`;
- `pull_state`: `open`, `closed`;
- `mergeable_state`: `clean`, `dirty`, `blocked`, `behind`, `unstable`,
  `draft`, `has_hooks`, `unknown`;
- `check_status`: `queued`, `in_progress`, `completed`, `waiting`, `requested`,
  `pending`;
- non-null `check_conclusion`: `action_required`, `cancelled`, `failure`,
  `neutral`, `success`, `skipped`, `stale`, `startup_failure`, `timed_out`;
- `commit_status_state`: `error`, `failure`, `pending`, `success`;
- `review_state`: `APPROVED`, `CHANGES_REQUESTED`, `COMMENTED`, `DISMISSED`,
  `PENDING`;
- `verification_reason`: `valid`, `invalid`, `malformed_signature`,
  `unknown_key`, `bad_email`, `unverified_email`, `no_user`, `unsigned`,
  `gpgverify_unavailable`, `gpgverify_error`, `not_signing_key`, `expired_key`,
  `ocsp_pending`, `ocsp_error`, `revoked_key`, `not_verified`;
- `ruleset_source_type`: `Repository`, `Organization`, `Enterprise`;
- `ruleset_target`: `branch`, `tag`, `push`;
- `ruleset_enforcement`: `disabled`, `active`, `evaluate`, `enabled`;
- `bypass_actor_type`: `Integration`, `RepositoryRole`, `Team`, `User`,
  `OrganizationAdmin`, `DeployKey`;
- `bypass_mode`: `always`, `pull_request`, `exempt`; and
- `rule_type`: `authorization`, `branch_name_pattern`, `code_scanning`,
  `commit_author_email_pattern`, `commit_message_pattern`,
  `committer_email_pattern`, `copilot_code_review`, `creation`, `deletion`,
  `file_extension_restriction`, `file_path_restriction`,
  `license_compliance_scanning`, `max_file_path_length`, `max_file_size`,
  `merge_queue`, `non_fast_forward`, `pull_request`, `required_deployments`,
  `required_linear_history`, `required_signatures`, `required_status_checks`,
  `tag_name_pattern`, `update`, `workflows`.

Any other enum produces `UNKNOWN_SECURITY_STATE`, retains only a hash of the
bounded offending projection, and sets `complete:false`. Explicit null is
accepted only at fields marked `?`; for identity-bearing nullable objects or
IDs, null also sets `identity_match:false` or `complete:false` as applicable.

Names and contexts needed for operator correlation are retained only as SHA-256
hashes unless the value is itself a governed selector. GitHub text is untrusted
data and must not be emitted to a terminal without bounded JSON escaping.

## 9. `github-observation/0.1.0`

One immutable observation represents one completed or failed logical intent:

- observation ID and kind;
- repository/API-profile, authorization, intent, attempt-claim, and
  lease-evidence references and hashes;
- repository, account, App, and installation numeric IDs;
- operation key, canonical parameters, attempt ID, and `observed_at`;
- status class (`2xx`, `3xx`, `4xx`, `5xx`, `transport`, or `none`) without a
  raw status phrase;
- sorted per-page records containing page number, response-byte count,
  `sha256:` wire-body hash, item count, and safe rate-limit projection;
- response-projection version, observation kind, and exact normalized
  projection object;
- `complete`, `pagination_complete`, and `identity_match` booleans;
- `visibility` from the closed set `complete_for_endpoint`,
  `complete_within_github_check_suite_horizon`, `not_observed`,
  `incomplete_by_permission`, or `observed_not_attested`;
- sorted unique reason codes from §10;
- `authority_effect: "none"`, `decision_effect: "none"`,
  `membership_effect: "none"`, `merge_authorized: false`, and
  `action_execution_allowed: false`.

An HTTP success does not imply a successful observation. `complete: true`
requires identity match, accepted status, complete bounded pagination, valid
closed projection, and no failure reason. An empty collection is valid only
when GitHub positively returns an empty complete collection.

Every ledger event stores only observation and upstream content hashes,
operation key, completion booleans, safe reason codes, and authority constants.
It stores no raw GitHub data, name, ref, URL, response, header, credential
selector, lease ID, provider authentication, or exception text.

## 10. Closed outcomes and diagnostics

Top-level outcomes are `COMPLETE`, `INCOMPLETE`, `NOT_SENT`, and `REJECTED`.
The initial reason-code set is:

`AUTHORIZATION_INVALID`, `AUTHORIZATION_EXPIRED`, `PROFILE_INVALID`,
`ENDPOINT_NOT_ALLOWED`, `PARAMETER_INVALID`, `INTENT_CONFLICT`,
`INTENT_REPLAYED`, `ATTEMPT_ALREADY_CLAIMED`, `ATTEMPT_CLAIM_CONFLICT`,
`ATTEMPT_CLAIM_STORE_FAILED`, `LEASE_MISSING`, `LEASE_PARTIAL`,
`LEASE_AUTH_INVALID`, `CREDENTIAL_TIME_INVALID`,
`LEASE_STALE`, `LEASE_BINDING_MISMATCH`, `LEASE_PERMISSION_MISMATCH`,
`LEASE_TOKEN_SUBSTITUTION`, `LEASE_EVIDENCE_STORE_FAILED`,
`LEASE_ADMISSION_INVALID`, `CREDENTIAL_CLEANUP_FAILED`,
`REPOSITORY_IDENTITY_MISMATCH`, `TRANSPORT_DNS_FAILED`,
`TRANSPORT_CONNECT_FAILED`, `TRANSPORT_TLS_FAILED`, `TRANSPORT_TIMEOUT`,
`TRANSPORT_CONNECTION_LOST`, `REDIRECT_REFUSED`, `PROXY_REFUSED`,
`RESPONSE_HEADERS_TOO_LARGE`, `RESPONSE_BODY_TOO_LARGE`,
`HTTP_RESPONSE_REJECTED`, `RATE_LIMITED`, `RESPONSE_JSON_INVALID`,
`RESPONSE_PROJECTION_INVALID`, `UNKNOWN_SECURITY_STATE`,
`PAGINATION_INVALID`, `PAGINATION_LIMIT_REACHED`, `ITEM_LIMIT_REACHED`, and
`OBSERVATION_STORE_FAILED`.

Public exceptions contain only a stable reason code and operation key. They do
not interpolate provider output, HTTP-library text, GitHub content, header
values, URI objects, environment values, paths, selectors, or credentials.
Diagnostics are JSON objects with a closed safe-field allowlist and are subject
to a final sentinel scan before stdout, stderr, test report, or CI artifact
emission.

The §6.1 cleanup attempt occurs before the final observation is sealed on every
exit. Cleanup success is therefore an input to the observation outcome rather
than a later mutation. A cleanup failure before the first transmission yields
`NOT_SENT` with `CREDENTIAL_CLEANUP_FAILED` only if lease evidence was already
stored; without stored lease evidence it creates no lease-evidence or
observation record, emits only that sanitized local reason, and leaves the
pre-existing attempt claim retained. A cleanup failure after any transmission
yields `INCOMPLETE` with `CREDENTIAL_CLEANUP_FAILED`, even if the response would
otherwise have been complete. It cannot trigger another request or credential
resolution.

Any other failure before the first transmission creates a factual `NOT_SENT`
observation only if the lease-evidence record was already stored; otherwise it
creates no lease-evidence or observation record, emits only a sanitized local
diagnostic, and leaves the pre-existing attempt claim retained.
Any other failure after a transmission creates an `INCOMPLETE` observation
whenever immutable storage remains available. An observation-storage failure
stops immediately and never causes a repeat request; cleanup has already been
attempted before that store operation.

## 11. Implementation order after separate authority

This draft proposes the following indivisible implementation sequence:

1. schema constants, closed models, validators, canonical sealing, workspace
   directories, and safe record readers/writers;
2. immutable repository/API profiles and public provider-key pin;
3. read authorization, generic operation intent, and atomic attempt-claim
   creation;
4. fixture credential provider, transient receipt/provider-claims
   authentication, durable evidence construction, exact projection comparison,
   and single-logical-use in-memory lease;
5. closed endpoint table, safe parameter encoder, and credential-independent
   fixture transport;
6. response bounds, pagination, projections, observations, ledger binding, and
   sanitized diagnostics;
7. concrete HTTPS transport with environment trust disabled and no live target
   in tests; and
8. packaging, threat matrix, installed-wheel, and cross-platform evidence.

No step may expose a partially usable transport. Until the full pre-network
chain and fixture security tests pass, the concrete transport entry point must
remain unreachable from the CLI.

## 12. Required deterministic acceptance evidence

### 12.1 Functional and integrity tests

Tests must prove:

- exact schema closure, strict typing, stable cross-platform hashes, immutable
  writes, idempotent equal writes, and unequal conflict retention;
- repository name reuse/transfer is rejected on numeric mismatch;
- authorization → intent → attempt claim → lease evidence → observation
  references and hashes are exact and cannot be substituted, reordered,
  omitted, or circular;
- exclusive attempt claiming permits exactly one concurrent caller; equal,
  unequal, and crash-retained claims all block another credential resolution;
- cross-platform golden vectors produce the exact attempt preimage bytes,
  digest, and path, while every omitted, extra, null-substituted, reordered,
  differently typed, or noncanonical preimage mutation fails;
- credential resolution occurs exactly once and only after all public checks;
- Windows, Linux, and macOS exercise their exact §6.5 durability success path;
  every injected create, write, file-barrier, required directory-barrier, close,
  reopen, byte-verification, and hash-verification failure records zero transport
  calls;
- deterministic clocks cover provider skew at -30, +30, and just beyond +30
  seconds; exactly 90 seconds and just below 90 seconds remaining at both
  evidence and transmission gates; expiry, authorization and intent boundaries;
  equal second-precision events; and forward/backward wall-clock movement while
  the monotonic operation deadline remains controlling;
- the mutable token buffer is overwritten and the provider capability closed
  on every success, validation error, persistence error, transport error,
  cancellation, and timeout; injected cleanup failure has the exact outcome and
  reason from §10 and can never admit another request;
- lease evidence is durable and its private admission capability is bound into
  the sealed lease before the fixture transport records a call;
- every endpoint permits only its fixed method, route, parameters, permission,
  response projection, and bounds;
- all list endpoints handle zero, one, exact-page, multi-page, and maximum-bound
  results deterministically; and
- branch-protection fixtures cover present, absent, explicit-null, malformed,
  and unknown-extension cases for every named block, including
  `required_signatures` and `block_creations`; and
- partial, duplicate, reordered, contradictory, truncated, stale, or unknown
  states remain factual failures.

### 12.2 Security and abuse tests

Adversarial fixtures must cover:

- bare tokens; wrong credential class; missing token or receipt; forged,
  malformed, replayed, expired, future-minted, substituted, or mismatched
  receipt/provider-claims/evidence; wrong signing key; wrong tag binding
  reported by provider;
- extra repository, account, App, installation, API-version, provider,
  permission, operation, intent, authorization, or profile claims;
- every extra read permission and every write permission;
- SSRF origins, alternate scheme/host/port, userinfo, redirects, ambient proxy
  variables, poisoned DNS fixture, TLS/hostname failure, arbitrary headers,
  CR/LF, path traversal, encoded slash, double encoding, Unicode ambiguity,
  ref/tag confusion, and caller URL injection;
- oversized request/headers/page/aggregate, decompression expansion, malformed
  JSON, deep/numerous JSON values, unknown security enums, and body/text/log
  injection;
- page loops, skipped/repeated pages, cross-origin Link targets, changed
  immutable parameters, duplicates, missing next page, and proof that check-run
  completeness is scoped to GitHub's documented 1,000-check-suite horizon;
- primary/secondary rate limits and every non-retryable HTTP class;
- concurrency, replay, crash before evidence, crash after request, failure to
  store observation, and proof that none triggers a second credential; and
- sentinel secrets across workspace, ledger, stdout, stderr, exception,
  JUnit, wheel, sdist, and CI artifacts.

Tests must assert no fixture network call on every precondition failure.

### 12.3 Platform and package matrix

The exact implementation head and protected `main` must pass the complete suite
with zero failures, errors, skips, or xfails on:

- Windows / Python 3.12;
- Ubuntu / Python 3.12;
- Ubuntu / Python 3.13; and
- macOS / Python 3.12.

Installed-wheel tests must prove the adapter imports and fixture conformance
run outside the source tree. Wheel and sdist inventories must contain no
credential, provider private key, live repository identifier, captured GitHub
response, HTTP cassette, test-only transport, or writable endpoint.
The dependency evidence must resolve `cryptography==49.0.0` from the exact
reviewed lock on every required platform and verify Ed25519 positive,
wrong-key, malformed-signature, and non-canonical-payload fixtures.

The CI harness must deny or detect external network access. All GitHub replies
are deterministic local fixtures. The production constructor has no origin,
dial-target, resolver, or trust-root injection. A separate test-only constructor
available only from the test-support module accepts an in-process loopback dial
target, fixture hostname, and fixture CA context while still exercising the
same request encoder, TLS verification, bounded reader, and response parser.
Production packaging excludes that constructor and module, and a source scan
proves the production entry point cannot receive those overrides. The TLS
fixture must never contact `api.github.com` in CI.

## 13. Review and freeze gates

Before implementation authority, this exact draft requires:

1. hash and Git-blob calculation without committing it;
2. a 5/5 exact-draft Council review covering governance, security, transport,
   evidence/schema integrity, and cross-platform testability;
3. reconciliation of every blocker into a new exact draft;
4. an explicit Arthur freeze naming the exact SHA-256 and Git blob; and
5. a separate implementation authorization scoped to the frozen 21A protocol.

Any change after exact-draft review invalidates that review. Protocol freeze
does not authorize a branch, commit, push, PR, implementation, credential, live
request, or later stage.

## 14. Rollback and failure rules

A draft defect is corrected in a new draft hash. Accepted evidence is never
rewritten. Implemented immutable records are never repaired in place; a new
record supersedes them factually. A partially completed observation remains
`INCOMPLETE` and cannot satisfy a later gate.

Credential suspicion requires external provider revocation and sanitized
incident handling. CONCLAVE never copies the suspected credential into its
record. Removing or disabling 21A must not delete historical factual evidence.

## 15. Official factual references

Consulted on 8 September 2026; these platform facts grant no authority:

- REST API versioning and supported versions:
  `https://docs.github.com/en/rest/about-the-rest-api/api-versions`
- GitHub App installation-token minting and permission narrowing:
  `https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/generating-an-installation-access-token-for-an-app`
- GitHub App endpoint permission mapping:
  `https://docs.github.com/en/rest/authentication/permissions-required-for-github-apps`
- repositories: `https://docs.github.com/en/rest/repos/repos`
- Git references: `https://docs.github.com/en/rest/git/refs`
- Git commits: `https://docs.github.com/en/rest/git/commits`
- pull requests: `https://docs.github.com/en/rest/pulls/pulls`
- check runs: `https://docs.github.com/en/rest/checks/runs`
- commit statuses: `https://docs.github.com/en/rest/commits/statuses`
- pull-request reviews: `https://docs.github.com/en/rest/pulls/reviews`
- issue/PR comments: `https://docs.github.com/en/rest/issues/comments`
- pull-request review comments:
  `https://docs.github.com/en/rest/pulls/comments`
- branch protection:
  `https://docs.github.com/en/rest/branches/branch-protection`
- repository rules and rulesets:
  `https://docs.github.com/en/rest/repos/rules`
- pagination: `https://docs.github.com/en/rest/using-the-rest-api/using-pagination-in-the-rest-api`
- rate limits: `https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api`
- Ed25519 verification API and supported platforms:
  `https://cryptography.io/en/latest/hazmat/primitives/asymmetric/ed25519/`
- selected cryptography distribution metadata:
  `https://pypi.org/project/cryptography/49.0.0/`

## 16. Current disposition

Stage 21A has not begun. This local document is an unfrozen protocol and schema
candidate. No implementation, runtime, test, credential, network, branch,
commit, push, pull request, merge, repository setting, KOS, IDM, signing,
identity, or membership operation is authorized or performed by this draft.
