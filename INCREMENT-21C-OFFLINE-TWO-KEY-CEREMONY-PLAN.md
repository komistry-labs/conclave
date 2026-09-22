# CONCLAVE Stage 21C — Offline Two-Key Ceremony Plan

Status: `REMEDIATED DRAFT / NOT FROZEN / NOT EXECUTABLE`

Authority class: ceremony-procedure governance only

Draft base: protected `main` commit
`154394c570a9919fc00b7c00779f565f742508e2`

Controlling Stage 21C protocol SHA-256:
`d3701754c7ab782835bc92db07c055509e415a69765373ed5cd30f250164b257`

Controlling collection-protocol SHA-256:
`6ea468c1cdd3a4ac0befecd3ffa3c2c26cfb51218902fb3af20366e4dbbb91c2`

Bound repository:

- numeric repository ID: `1335850028`;
- repository node ID: `R_kgDOT590LA`;
- descriptive repository name: `komistry-labs/conclave`; and
- protected base branch: `refs/heads/main`.

The numeric repository ID is authoritative. The descriptive name is not an
identity selector.

## 1. Purpose and authority boundary

This plan defines a future, separately authorized offline ceremony that may
create exactly two distinct Ed25519 key pairs:

1. one `control_attestor` key pair; and
2. one `human_authorizer` key pair.

The ceremony exists only to produce independently generated private keys,
their public facts, custody packages, and secret-free evidence suitable for
later exact Arthur-issued Stage 21C trust authorizations. It does not itself
create either trust authorization and does not make either key trusted,
active, deployed, current, or usable by CONCLAVE.

This draft grants no authority to generate a key, select a custodian, access a
credential, sign a Stage 21C record, install a trust store, modify runtime or
test code, contact GitHub, create a GitHub App, or perform a repository
mutation. Review or freeze of this plan also grants none of those authorities.

Execution requires a later Arthur authorization naming the exact frozen plan,
exact ceremony manifest, exact reviewed tool bundle, exact offline environment,
roles, media, time window, and maximum outputs. Activation requires still later
trust-authorization, build-pinning, deployment, and implementation decisions.

## 2. Governing invariants

The ceremony and every derived artifact shall satisfy all of the following:

1. The two private keys are generated independently from separate CSPRNG draws.
2. No seed, private key, passphrase, recovery material, plaintext envelope,
   signing handle, or secret-derived diagnostic enters Git, chat, browser,
   cloud storage, clipboard history, screen capture, logs, shell history, CI,
   CONCLAVE, KOS, IDM, or the Stage 21C record store.
3. Any secret previously typed into a chat, terminal transcript, issue, pull
   request, document, or other recorded channel is permanently ineligible.
4. The two keys use different media custodians, different passphrase holders,
   different passphrases, different primary media, and different recovery
   media. No person controls both a medium and its matching passphrase.
5. The control-attestor custodian and configured human-authorizer custodian are
   distinct governed principals. Neither may be a counted independent reviewer
   for an action using these keys.
6. Key purpose is fixed at creation. A key cannot change purpose, repository,
   principal, or protocol binding.
7. Exactly 32 raw Ed25519 public-key bytes and their public representations may
   leave the offline boundary. Private material may leave only inside the
   approved encrypted custody envelopes on the named custody media.
8. CONCLAVE never generates, imports, stores, unwraps, displays, or receives a
   private key.
9. A successful ceremony is not a trust decision, approval, identity grant,
   membership grant, deployment, or production authorization.
10. Any uncertainty, role collision, unexpected device, extra output, missing
    evidence, verification mismatch, or secret-exposure suspicion fails closed.

## 3. Key purposes and prohibited uses

### 3.1 Control-attestor key

The control-attestor key is reserved for signatures over the exact Stage 21C
attestation domain:

`CONCLAVE-GITHUB-NO-BYPASS-ATTESTATION-V2`

It may eventually be used only through the separately reviewed external key
provider described by the frozen collection protocol. That provider must
release no key bytes and must expose no generic signing interface. A future
signature requires a one-use handle bound to the approved verifier/signer in
its terminal verified state.

The ceremony does not build, authorize, or activate that provider. Except for
the ceremony proof-of-possession operation in §12, this key may not sign until
the provider, verifier/signer, exact implementation manifest, trust
authorization, and deployment are separately approved.

### 3.2 Human-authorizer key

The human-authorizer key is reserved for signatures over the exact Stage 21C
human authorization domain:

`CONCLAVE-GITHUB-HUMAN-MERGE-AUTHORIZATION-V1`

It may eventually sign one exact canonical
`github-human-merge-authorization-evidence/0.1.0` object only after the
governed human has independently inspected the exact readiness evidence. It
does not authorize CONCLAVE to merge and cannot bypass GitHub protection.

Except for the ceremony proof-of-possession operation in §12, the key may not
sign until its exact trust authorization and approved offline signing workflow
are separately frozen and activated.

### 3.3 Prohibited uses

Neither key may be used for Git commits or tags, SSH, TLS, GitHub authentication,
GitHub App JWTs, software or package signing, email, IDM identity proofs, KOS
decisions, general documents, cryptocurrency, password recovery, encryption,
or any purpose not named above. The keys are not GitHub credentials.

## 4. Required actors and separation

One human may hold only one ceremony role in a given execution unless this plan
expressly permits combination. The execution manifest fixes immutable
principal identifiers before the offline session.

Required roles are:

1. **Arthur / ceremony authorizer** — approves the exact execution manifest and
   later accepts or rejects the secret-free result. Arthur does not need access
   to either private key.
2. **ceremony operator** — boots and operates the approved offline environment;
   must not become a key custodian.
3. **independent witness** — observes device identity, isolation, displayed
   public facts, verification results, and cleanup; never receives a secret.
4. **control-attestor primary-media custodian** — controls only the sealed
   control-attestor primary medium.
5. **control-attestor primary-passphrase holder** — controls only that primary
   envelope's passphrase.
6. **control-attestor recovery-media custodian** — controls only the sealed
   control-attestor recovery medium.
7. **control-attestor recovery-passphrase holder** — controls only that recovery
   envelope's passphrase.
8. **human-authorizer primary-media custodian** — controls only the sealed
   human-authorizer primary medium.
9. **human-authorizer primary-passphrase holder** — controls only that primary
   envelope's passphrase and must be the configured human principal.
10. **human-authorizer recovery-media custodian** — controls only the sealed
    human-authorizer recovery medium.
11. **human-authorizer recovery-passphrase holder** — controls only that
    recovery envelope's passphrase.

The operator and witness must be distinct. The eight media/passphrase roles
must be held by eight distinct principals; no holder may be operator, witness,
or a holder for the other key. Arthur may also be the configured human and
therefore the human-authorizer primary-passphrase holder, but while occupying
that role may not occupy any other ceremony role. The control-attestor and
human-authorizer principals must be distinct. A counted independent reviewer
may occupy no ceremony role. Any prohibited collision stops before secret
creation.

The control-attestor principal may occupy none of the eleven ceremony roles,
may hold no medium or passphrase, and may not be Arthur, the configured human,
an operator, witness, custodian, holder, or counted reviewer. The configured
human's sole permitted overlap is the Arthur/human-primary-passphrase exception
above. Every other role/principal pair must be distinct.

The governance-signature profile's Arthur and witness principals and keys are
distinct. Its witness may be neither a ceremony actor nor any current custody
holder, destination, auditor, configured principal, or counted reviewer for the
same action. Exact public-key bytes, Ed25519 algorithm, canonical unpadded
base64url signature encoding, trust records, and key fingerprints are fixed by
that profile; an ID or fingerprint without the exact trusted public bytes is
insufficient.

Council review of the plan or result is advisory evidence and does not replace
Arthur's authorization, the witness, or either custodian.

## 5. Closed artifact contract and ceremony input manifest

### 5.1 Inherited primitive and canonical contract

Every JSON object introduced by this plan inherits the frozen Stage 21A
`ClosedModel`/`HashedRecord` canonical contract: UTF-8 JSON, lexicographically
sorted object keys, compact separators, no byte-order mark, no floats, no
non-finite numbers, no duplicate member names, no invalid Unicode, no unknown
members, and no implementation-defined values. Only schemas that explicitly
list `content_hash` are independently hashed records; for them it is computed
with that member absent and is `sha256:` followed by 64 lowercase hexadecimal
characters. Named nested structures such as `pre_gate_check`, `public_file`,
and `platform_result` are embedded values, expressly omit `content_hash`, and
cannot be stored or referenced independently. Records are immutable-created,
durably read back, and rejected on same-path conflict or reopen mismatch.

The notation is normative: `id` is an integer from 1 through
9,223,372,036,854,775,807; `count` is an integer from 0 through
9,223,372,036,854,775,807; `hash` is the exact `sha256:` form above; `ts` is UTC
RFC 3339 with literal `Z`, second precision, and no leap second; `ascii(N)` is
safe printable ASCII excluding backslash, quote, and control characters with a
maximum of N characters; `s(N)` is valid NFC UTF-8 of at most N bytes; `bool`
is exact JSON true or false; `T?` is nullable; `[T,N]` is an ordered array of at
most N values; `literal(x)` is exactly x; and `enum(...)` is exactly one listed
ASCII value. Unless a field rule states otherwise, arrays are nonempty, sorted
by canonical encoded bytes, and contain no duplicates.

Every independently hashed record has a 1,048,576-byte canonical pre-parse
ceiling except lifecycle and custody registries and full custody-audit records,
whose ceiling is 8,388,608
bytes, and retained physical-receipt byte artifacts, whose ceiling is 4,194,304
bytes. Embedded values share their containing record's ceiling. Objects over a
ceiling fail before semantic processing. Every record's schema version is a
literal and every nullable state is stated explicitly below.

All time windows are closed intervals: `not_before <= evaluated_at <= expires_at`.
Creation or issuance time must not exceed `not_before`, and `not_before` must be
strictly earlier than `expires_at`. A clock reading with uncertainty `u` is
valid only when both `displayed_utc - u >= not_before` and
`displayed_utc + u <= expires_at`; boundary overlap fails closed.

The complete reason-code vocabulary for this plan is:

```text
AUTHORIZATION_INVALID, TIME_WINDOW_INVALID, ROLE_COLLISION,
PROTOCOL_HASH_MISMATCH, REPOSITORY_ID_MISMATCH, MANIFEST_INVALID,
HOST_IDENTITY_MISMATCH, FIRMWARE_MISMATCH, BOOT_MEASUREMENT_INVALID,
TOOL_IDENTITY_MISMATCH, VERIFIER_IDENTITY_MISMATCH, MEDIA_IDENTITY_MISMATCH,
  MEDIA_ROLE_MISMATCH, DEVICE_CLASS_INVALID, DEVICE_REENUMERATION,
  DEVICE_ATTESTATION_INVALID,
NETWORK_ISOLATION_UNPROVEN, WRITABLE_DISK_PRESENT, SWAP_ENABLED,
HIBERNATION_ENABLED, CRASH_DUMP_ENABLED, TELEMETRY_ENABLED,
CAPTURE_PATH_ENABLED, CLOCK_UNCERTAINTY_EXCESSIVE, PASSPHRASE_PROFILE_INVALID,
PASSPHRASE_CONFIRMATION_FAILED, RANDOMNESS_FAILURE, KEY_GENERATION_FAILED,
KEY_COLLISION, ENVELOPE_WRITE_FAILED, ENVELOPE_READBACK_FAILED,
ENVELOPE_PROFILE_INVALID, POP_FAILED, ZEROIZATION_UNPROVEN,
UNEXPECTED_OUTPUT, EXPORT_BOUNDARY_INVALID, ORIGIN_AUTHENTICATION_FAILED,
PUBLIC_ALLOWLIST_FAILED, WITNESS_MISMATCH, CUSTODY_HANDOFF_FAILED,
  LIFECYCLE_REGISTRY_UNAVAILABLE, LIFECYCLE_CONFLICT, REGISTRY_ROLLBACK,
  REGISTRY_FORK, CUSTODY_CONFLICT, AUDIT_OVERDUE, SEAL_BROKEN,
  RECOVERY_FAILED, CLEANUP_INCOMPLETE,
COMPROMISE_SUSPECTED, MEDIA_LOST, REVOCATION_REQUIRED, RETIREMENT_REQUIRED,
DESTRUCTION_INCOMPLETE, OPERATOR_ABORT, UNEXPECTED_FAILURE
```

Reason arrays use only this vocabulary, sort by ASCII bytes, and contain no
duplicates. They are empty only where a schema-specific rule below expressly
permits it; otherwise they are nonempty.

### 5.2 Closed supporting objects

Each hash placed in the manifest below names one already immutable object of
the stated schema. A hash without the exact available object is invalid.
Every acquisition, firmware, device, controller, sanitization, hardware,
Secure-Boot, TPM, PCR, peripheral, or authenticator-security hash resolves to a
`security_attestation` of the matching role. Validation verifies its Ed25519
signature and immutable trust record, subject match, validity window, payload,
and role-specific validation profile; self-issued or merely descriptor-derived
objects fail.

```text
byte_artifact = {
  role: enum(environment_image,boot_measurement_verifier,ceremony_tool_bundle,
             ceremony_tool_executable,dependency_inventory,verifier_bundle,
             verifier_executable,verifier_dependency_inventory,
             verifier_environment_image,post_secret_authenticator_inventory,
             public_export_filesystem_profile,device_monitor_executable,
             device_monitor_profile,recovery_tool_bundle,recovery_tool_executable,
             other_profile),
  sha256: hash,
  byte_count: count,
  media_type: ascii(64),
  provenance_sha256: hash,
  canonical_json_record: bool
}

security_attestation = {
  schema_version: literal(conclave-stage21c-security-attestation/0.1.0),
  role: enum(acquisition_provenance,firmware_attestation,device_attestation_trust,
             controller_allowlist,sanitization,hardware_inventory,
             firmware_configuration,tpm_attestation_key,secure_boot_policy,
             pcr_profile,peripheral_inventory,authenticator_attestation,
             capture_device_attestation),
  subject_identity_sha256: hash,
  issuer_principal_id: ascii(128),
  issuer_key_id: ascii(128),
  issuer_public_key_base64url: ascii(43),
  issuer_trust_record_sha256: hash,
  algorithm: literal(Ed25519),
  evidence_payload_sha256: hash,
  validation_profile_sha256: hash,
  valid_from: ts,
  valid_until: ts,
  signature_base64url: ascii(86),
  content_hash: hash
}

security_validation_profile = {
  schema_version: literal(conclave-stage21c-security-validation-profile/0.1.0),
  role: enum(acquisition_provenance,firmware_attestation,device_attestation_trust,
             controller_allowlist,sanitization,hardware_inventory,
             firmware_configuration,tpm_attestation_key,secure_boot_policy,
             pcr_profile,peripheral_inventory,authenticator_attestation,
             capture_device_attestation),
  payload_schema_sha256: hash,
  verifier_executable_sha256: hash,
  trust_root_hashes: [hash,16],
  permitted_signature_algorithms: [ascii(32),4],
  maximum_evidence_age_seconds: id,
  required_claim_names_sha256: hash,
  rejection_vector_inventory_sha256: hash,
  content_hash: hash
}

media_binding = {
  schema_version: literal(conclave-stage21c-media-binding/0.1.0),
  role: enum(control_primary,control_recovery,human_primary,human_recovery,public_export),
  device_identity_sha256: hash,
  manufacturer_sha256: hash,
  model_sha256: hash,
  firmware_revision_sha256: hash,
  capacity_bytes: id,
  bus_type: enum(usb,nvme,sata,sd),
  removable: literal(true),
  expected_interface_classes: [ascii(32),8],
  acquisition_provenance_sha256: hash,
  firmware_attestation_sha256: hash,
  device_attestation_trust_sha256: hash,
  controller_allowlist_profile_sha256: hash,
  sanitization_method: enum(new_device,crypto_erase,physical_reprovision),
  sanitization_evidence_sha256: hash,
  content_hash: hash
}

media_identity_preimage = {
  manufacturer: s(128),
  model: s(128),
  firmware_revision: ascii(64),
  hardware_serial: s(128),
  capacity_bytes: id,
  bus_type: enum(usb,nvme,sata,sd),
  interface_classes: [ascii(32),8]
}

host_profile = {
  schema_version: literal(conclave-stage21c-host-profile/0.1.0),
  hardware_inventory_sha256: hash,
  motherboard_identity_sha256: hash,
  cpu_identity_sha256: hash,
  firmware_image_sha256: hash,
  firmware_configuration_sha256: hash,
  peripheral_controller_inventory_sha256: hash,
  tpm_attestation_key_sha256: hash,
  secure_boot_policy_sha256: hash,
  expected_pcr_profile_sha256: hash,
  internal_storage_absent: literal(true),
  content_hash: hash
}

tpm_quote_evidence = {
  schema_version: literal(conclave-stage21c-tpm-quote-evidence/0.1.0),
  host_profile_sha256: hash,
  nonce_sha256: hash,
  attestation_key_sha256: hash,
  attestation_key_trust_record_sha256: hash,
  pcr_selection_sha256: hash,
  pcr_values_sha256: hash,
  secure_boot_state_sha256: hash,
  tpm_clock: count,
  tpm_reset_count: count,
  tpm_restart_count: count,
  quote_bytes_sha256: hash,
  quote_signature_sha256: hash,
  verifier_executable_sha256: hash,
  verified_at: ts,
  result: literal(pass),
  content_hash: hash
}

custody_media_encryption_profile = {
  schema_version: literal(conclave-stage21c-media-encryption-profile/0.1.0),
  implementation_name: ascii(64),
  implementation_version: ascii(32),
  executable_sha256: hash,
  format: ascii(64),
  algorithm_profile: ascii(128),
  minimum_volume_key_bits: literal(256),
  authenticated_metadata: literal(true),
  unlock_kdf: literal(Argon2id-1.3),
  unlock_kdf_output_bytes: literal(32),
  unlock_salt_bytes: literal(16),
  unlock_minimum_memory_kib: literal(262144),
  unlock_iterations: literal(4),
  unlock_parallelism: literal(1),
  unlock_passphrase_profile_sha256: hash,
  network_unlock_allowed: literal(false),
  recovery_escrow_allowed: literal(false),
  content_hash: hash
}

governance_signature_profile = {
  schema_version: literal(conclave-stage21c-governance-signature-profile/0.1.0),
  algorithm: literal(Ed25519),
  signature_encoding: literal(unpadded-base64url-64-bytes),
  arthur_principal_id: ascii(128),
  arthur_key_id: ascii(128),
  arthur_public_key_base64url: ascii(43),
  arthur_public_key_sha256: hash,
  arthur_trust_record_sha256: hash,
  witness_principal_id: ascii(128),
  witness_key_id: ascii(128),
  witness_public_key_base64url: ascii(43),
  witness_public_key_sha256: hash,
  witness_trust_record_sha256: hash,
  principals_distinct: literal(true),
  keys_distinct: literal(true),
  content_hash: hash
}

key_envelope_profile = {
  schema_version: literal(conclave-stage21c-key-envelope-profile/0.1.0),
  cbor_profile: literal(RFC8949-deterministic-core),
  kdf: literal(Argon2id-1.3),
  kdf_output_bytes: literal(32),
  salt_bytes: literal(16),
  minimum_memory_kib: literal(262144),
  iterations: literal(4),
  parallelism: literal(1),
  aead: literal(XChaCha20-Poly1305-IETF),
  nonce_bytes: literal(24),
  tag_bytes: literal(16),
  seed_bytes: literal(32),
  content_hash: hash
}

passphrase_profile = {
  schema_version: literal(conclave-stage21c-passphrase-profile/0.1.0),
  generator_executable_sha256: hash,
  word_list_sha256: hash,
  word_list_entry_count: id,
  word_list_encoding: literal(ASCII-LF),
  sampling: literal(unbiased-rejection-sampling),
  randomness_source_profile_sha256: hash,
  word_count: literal(7),
  separator: literal(-),
  normalization: literal(ASCII-exact),
  minimum_entropy_bits: literal(90),
  content_hash: hash
}

origin_authentication_profile = {
  schema_version: literal(conclave-stage21c-origin-authentication-profile/0.1.0),
  operator_principal_id: ascii(128),
  operator_key_id: ascii(128),
  operator_public_key_base64url: ascii(43),
  operator_public_key_sha256: hash,
  operator_trust_record_sha256: hash,
  witness_principal_id: ascii(128),
  witness_key_id: ascii(128),
  witness_public_key_base64url: ascii(43),
  witness_public_key_sha256: hash,
  witness_trust_record_sha256: hash,
  algorithm: literal(Ed25519),
  content_hash: hash
}

post_secret_authenticator_inventory = {
  schema_version: literal(conclave-stage21c-origin-authenticator-inventory/0.1.0),
  operator_device_identity_sha256: hash,
  operator_device_firmware_sha256: hash,
  operator_acquisition_provenance_sha256: hash,
  operator_device_attestation_sha256: hash,
  operator_expected_interface_classes: [ascii(32),8],
  witness_device_identity_sha256: hash,
  witness_device_firmware_sha256: hash,
  witness_acquisition_provenance_sha256: hash,
  witness_device_attestation_sha256: hash,
  witness_expected_interface_classes: [ascii(32),8],
  controller_allowlist_profile_sha256: hash,
  devices_distinct: literal(true),
  attach_phase: literal(post_secret_origin_signing_only),
  content_hash: hash
}

public_export_filesystem_profile = {
  schema_version: literal(conclave-stage21c-public-export-filesystem-profile/0.1.0),
  filesystem: ascii(32),
  implementation_sha256: hash,
  case_sensitive: bool,
  symlinks_allowed: literal(false),
  hardlinks_allowed: literal(false),
  alternate_streams_allowed: literal(false),
  extended_attributes_allowed: literal(false),
  executable_files_allowed: literal(false),
  maximum_files: literal(64),
  maximum_total_bytes: literal(1048576),
  content_hash: hash
}

storage_binding = {
  role: enum(control_primary_media,control_primary_passphrase,
             control_recovery_media,control_recovery_passphrase,
             human_primary_media,human_primary_passphrase,
             human_recovery_media,human_recovery_passphrase),
  holder_principal_id: ascii(128),
  destination_principal_id: ascii(128),
  storage_location_commitment_sha256: hash,
  seal_policy_sha256: hash,
  maximum_audit_interval_days: literal(92)
}

storage_location_commitment = {
  schema_version: literal(conclave-stage21c-storage-location/0.1.0),
  location_id: ascii(128),
  holder_principal_id: ascii(128),
  access_principal_ids: [ascii(128),4],
  physical_zone_sha256: hash,
  container_identity_sha256: hash,
  access_control_profile_sha256: hash,
  environmental_control_profile_sha256: hash,
  no_networked_secret_storage: literal(true),
  content_hash: hash
}

seal_policy = {
  schema_version: literal(conclave-stage21c-seal-policy/0.1.0),
  seal_type: ascii(64),
  unique_serial_required: literal(true),
  destructive_opening_required: literal(true),
  photograph_hash_required: literal(true),
  dual_observation_required: literal(true),
  content_hash: hash
}

custody_audit_policy = {
  schema_version: literal(conclave-stage21c-custody-audit-policy/0.1.0),
  maximum_interval_days: literal(92),
  auditor_count: literal(2),
  auditors_distinct_from_current_holders: literal(true),
  register_update_required: literal(true),
  overdue_action: literal(suspend),
  content_hash: hash
}

custody_recovery_policy = {
  schema_version: literal(conclave-stage21c-custody-recovery-policy/0.1.0),
  separate_arthur_authorization_required: literal(true),
  recovery_custodian_and_passphrase_holder_distinct: literal(true),
  primary_holders_excluded: literal(true),
  network_prohibited: literal(true),
  arbitrary_signing_prohibited: literal(true),
  content_hash: hash
}

custody_plan = {
  schema_version: literal(conclave-stage21c-custody-plan/0.1.0),
  ceremony_id: ascii(64),
  repository_id: literal(1335850028),
  expected_main_commit: ascii(64),
  expected_custody_register_sha256: hash,
  expected_custody_checkpoint_sha256: hash,
  storage_bindings: [storage_binding,8],
  custody_governance_profile_sha256: hash,
  custody_register_path: literal(docs/governance/stage-21c-key-custody/REGISTRY.json),
  custody_checkpoint_path: literal(docs/governance/stage-21c-key-custody/CHECKPOINT.json),
  audit_policy_sha256: hash,
  recovery_policy_sha256: hash,
  governance_signature_profile_sha256: hash,
  created_at: ts,
  content_hash: hash
}
```

Every `media_binding` identity is computed from the exact
`media_identity_preimage` using ASCII
`CONCLAVE-STAGE21C-MEDIA-IDENTITY-V1`, one zero byte, and its canonical JSON.
No field is nullable or omittable; interface classes sort by ASCII bytes and
are unique. Manufacturer and model are NFC before canonical encoding; hardware
serial is the exact NFC string exposed by the approved attestation path, not a
display alias. Cross-platform golden vectors fix representative USB, NVMe,
SATA, and SD preimages. Raw serials never enter a public result, Git, or chat.
Exactly five bindings with five distinct device identities and roles are
required.

Every device must have approved acquisition provenance and a cryptographically
verified firmware/device attestation rooted in the manifest-bound trust object.
Self-reported descriptors alone are insufficient. The controller allowlist and
monitor enforce the exact interface classes for the whole attachment interval
and retain authenticated attach, reset, interface-change, detach, and re-
enumeration events. Any transient unapproved class or event quarantines the
ceremony even if final enumeration later matches.

Security-attestation signing bytes are ASCII
`CONCLAVE-STAGE21C-SECURITY-ATTESTATION-V1`, one zero byte, then canonical JSON
with `signature_base64url` and `content_hash` absent. The issuer signs those
bytes; `content_hash` is computed afterward over the complete signed record with
only `content_hash` absent. No other preimage is permitted.

`storage_bindings` contains exactly eight items, exactly one in the enum order,
and each `destination_principal_id` equals its `holder_principal_id`. Those eight
IDs equal the corresponding eight manifest role IDs; no additional destination
actor exists. Every storage, seal, audit, and recovery hash resolves to the
closed object above and is available to the verifier. Every security-attestation
payload is an exact byte artifact; its matching `security_validation_profile`,
payload schema, verifier, trust roots, required-claim inventory, and rejection
vectors are also available and manifest-bound. Storage-location access
lists cannot contain the matching medium/passphrase counterpart, operator,
witness, control attestor, configured human except for her expressly permitted
holder role, or another package holder. Across the eight bindings, location ID,
physical-zone hash, container hash, and storage-commitment hash are each unique;
co-location in one zone or container is prohibited.

The passphrase list contains unique nonempty ASCII words and no carriage return,
hyphen, whitespace, control, or duplicate entry. Its LF-terminated final byte
form is hashed exactly. The generator proves
`floor(7 * log2(word_list_entry_count)) >= 90` and uses rejection sampling so
every seven-word tuple is equiprobable.

Each custody medium has a separately generated seven-word volume-unlock
passphrase under the same generator profile. It is distinct from all four
envelope passphrases and the other three volume passphrases. The corresponding
media formatter derives the 32-byte unlock key using the profile's exact
Argon2id parameters and a fresh 16-byte salt stored only in authenticated volume
metadata; no recovery keyslot, escrow token, TPM auto-unlock, or network unlock
exists. The corresponding
named passphrase holder receives two separately sealed inner papers—one envelope
passphrase and one volume passphrase—inside that role's single outer custody
package; neither secret is held by a media custodian. Holder records bind both
inner seal IDs but no secret-derived value. Loss of either inner secret invokes
the same recovery or terminal-loss rule as loss of that role's envelope
passphrase. Rotation is permitted only through the separately authorized
recovery transaction and creates new secrets, seals, records, and register
entries; reuse is prohibited.

### 5.3 Ceremony input manifest

Before execution, a secret-free canonical manifest shall be reviewed and
authorized. Its closed content is:

```text
schema_version: literal(conclave-stage21c-key-ceremony-manifest/0.1.0)
ceremony_id: ascii(64)
frozen_plan_sha256: hash
stage_21c_protocol_sha256: hash
collection_protocol_sha256: hash
repository_id: literal(1335850028)
repository_node_id: literal(R_kgDOT590LA)
control_attestor_principal_id: ascii(128)
human_authorizer_principal_id: ascii(128)
control_attestor_github_user_id: id?
human_authorizer_github_user_id: id
control_attestor_key_id: ascii(128)
human_authorizer_key_id: ascii(128)
operator_principal_id: ascii(128)
witness_principal_id: ascii(128)
control_attestor_primary_custodian_principal_id: ascii(128)
control_attestor_primary_passphrase_holder_principal_id: ascii(128)
control_attestor_recovery_custodian_principal_id: ascii(128)
control_attestor_recovery_passphrase_holder_principal_id: ascii(128)
human_authorizer_primary_custodian_principal_id: ascii(128)
human_authorizer_primary_passphrase_holder_principal_id: ascii(128)
human_authorizer_recovery_custodian_principal_id: ascii(128)
human_authorizer_recovery_passphrase_holder_principal_id: ascii(128)
environment_image_sha256: hash
host_profile_sha256: hash
boot_measurement_verifier_sha256: hash
expected_boot_measurement_sha256: hash
device_monitor_executable_sha256: hash
device_monitor_profile_sha256: hash
ceremony_tool_bundle_sha256: hash
ceremony_tool_executable_sha256: hash
dependency_inventory_sha256: hash
verifier_bundle_sha256: hash
recovery_tool_bundle_sha256: hash
recovery_tool_executable_sha256: hash
verifier_executable_sha256: hash
verifier_dependency_inventory_sha256: hash
  verifier_environment_image_sha256: hash
  verifier_host_profile_sha256: hash
  verifier_expected_boot_measurement_sha256: hash
media_bindings: [media_binding,5]
byte_artifacts: [byte_artifact,32]
custody_media_encryption_profile_sha256: hash
key_envelope_profile_sha256: hash
passphrase_profile_sha256: hash
  origin_authentication_profile_sha256: hash
  governance_signature_profile_sha256: hash
post_secret_authenticator_inventory_sha256: hash
public_export_filesystem_profile_sha256: hash
lifecycle_registry_snapshot_sha256: hash
lifecycle_governance_profile_sha256: hash
lifecycle_base_main_commit: ascii(64)
  lifecycle_base_checkpoint_sha256: hash
  control_planned_lifecycle_event_sha256: hash
  human_planned_lifecycle_event_sha256: hash
custody_plan_sha256: hash
scheduled_not_before: ts
scheduled_not_after: ts
maximum_keypairs: literal(2)
maximum_proof_signatures: literal(2)
created_at: ts
content_hash: hash
```

The content hash uses the inherited `sha256:` representation of SHA-256 over
canonical JSON with `content_hash` omitted. The two principal IDs, key IDs, custodians, and all tool/environment
hashes must be fixed before execution. Separate ceremony-host and verifier-host
boot measurements are mandatory; each is a fresh TPM 2.0 quote over that
profile's exact PCR selection and an independently supplied nonce. A missing
TPM trust chain, unapproved attestation key, unknown
firmware state, mismatched PCR value, or unverifiable quote aborts before secret
creation. There is no null or self-asserted boot-measurement path.
Each observed measurement hash resolves to `tpm_quote_evidence`; the nonce is
freshly generated by the pinned verifier after boot and never reused. Quote
clock/reset/restart state, PCR selection/values, Secure Boot state, attestation
key trust, exact quote bytes/signature, verifier, and observation time must all
validate. A prior valid quote with a different nonce fails.

Each direct manifest SHA-256 naming image, executable, bundle, dependency
inventory, authenticator inventory, filesystem profile, verifier, or other
byte artifact must match exactly one `byte_artifact` entry. Raw artifacts hash
their exact bytes. Canonical JSON records hash their exact canonical bytes and
set `canonical_json_record: true`. Roles and hashes are unique; missing,
ambiguous, multiply matching, or unaccounted commitments invalidate the
manifest.

Arthur's execution authorization is deliberately outside this manifest. It
names the already-computed manifest `content_hash`, time window, and maximum
outputs. The manifest does not point back to that authorization, avoiding a
hash cycle. The ceremony result records both hashes after both objects exist.

Its exact public record is:

```text
schema_version: literal(conclave-stage21c-key-ceremony-execution-authorization/0.1.0)
ceremony_manifest_sha256: hash
frozen_plan_sha256: hash
repository_id: literal(1335850028)
authorized_by_principal_id: ascii(128)
custody_plan_sha256: hash
lifecycle_current_main_commit: ascii(64)
lifecycle_current_checkpoint_sha256: hash
control_planned_lifecycle_event_sha256: hash
human_planned_lifecycle_event_sha256: hash
governance_signature_profile_sha256: hash
not_before: ts
expires_at: ts
maximum_keypairs: literal(2)
maximum_proof_signatures: literal(2)
permitted_outputs: literal(encrypted-custody-and-secret-free-evidence-only)
key_activation_authorized: literal(false)
runtime_operation_authorized: literal(false)
issued_at: ts
arthur_signature_base64url: ascii(86)
content_hash: hash
```

The authorization is the Arthur decision for the ceremony execution itself.
It is adopted only after the manifest hash exists and does not point to a
result, key, or later trust authorization. Its hash is copied into every
execution artifact after authorization.
Arthur signs ASCII `CONCLAVE-STAGE21C-CEREMONY-AUTHORIZATION-V1`, one zero byte,
then canonical JSON with `arthur_signature_base64url` and `content_hash` absent,
using the key in the governance-signature profile. Pre-gate verifies that
signature, trust record, exact current protected-main commit/checkpoint, and the
two planned event hashes. A hash match without this authentication fails.

Key IDs are safe public labels, unique across all CONCLAVE trust records, and
must match `^[a-z0-9][a-z0-9._-]{15,127}$`. They contain no email address,
device serial number, secret, display name, or mutable GitHub login.

The human GitHub user ID is mandatory because the configured human is a GitHub
actor in the frozen Stage 21C target. The control-attestor GitHub user ID is
null only when the attestor has no GitHub user identity, matching the frozen
attestation schema. Login names remain descriptive and are excluded.

## 6. Approved tool and environment prerequisite

The ceremony may run only from a separately reviewed, deterministic ceremony
tool bundle whose exact bytes are fixed in the manifest. The tool shall:

- obtain randomness only from the approved operating-system CSPRNG;
- generate Ed25519 keys without accepting caller-supplied seed bytes;
- implement Ed25519 key derivation and signing exactly as RFC 8032, with a
  uniformly random 32-byte seed and no serialization of the expanded secret;
- never print, echo, return, serialize to logs, or expose private key bytes;
- produce canonical unpadded base64url public keys and exact SHA-256 public-key
  fingerprints;
- create encrypted custody envelopes directly on named destination media;
- require distinct passphrases for every envelope;
- verify both written envelopes by readback before plaintext key state is
  destroyed;
- create only the bounded proof-of-possession signatures in §12;
- expose no arbitrary-message signing mode;
- write no crash dump, telemetry, usage data, shell history, temporary plaintext
  file, recovery file, swap, or hibernation image; and
- terminate unsuccessfully if it cannot produce the exact bounded evidence
  required for those properties; it never claims universal physical erasure.

The tool source, build recipe, dependency lock, executable hash, dependency
inventory, supported environment, test evidence, and secret-leak assessment
must be independently reviewed before the execution authorization. General
OpenSSL, Python, PowerShell, shell, browser, password-manager, Git, or cloud
commands are not ceremony substitutes unless incorporated into that exact
reviewed bundle.

The execution environment shall be an approved boot image on the exact host in
the manifest-bound `host_profile`. Before boot, networking radios and wired
interfaces are physically removed or hardware-disabled. Internal writable
disks, unapproved USB devices, cloud sync, printers, cameras, microphones,
screen recording, clipboard managers, remote management, and telemetry are
disabled or inaccessible. Swap, hibernation, and crash dumps are disabled.
Firmware write protection and Secure Boot are enabled under the pinned policy.
A fresh TPM quote with a verifier nonce must match the approved attestation key
and PCR profile before any custody medium is attached.

The independent verifier uses the separately bound verifier image, host,
bundle, executable, and dependencies. It has read-only access only to copied
public candidate artifacts after secret cleanup. It never receives a custody
medium, passphrase, envelope plaintext, or private key. Evidence transfer uses
the public-export medium only after §13 opens the post-secret export phase.

A Windows drive letter such as `E:` is descriptive and unstable; it is never a
media identity. Media are selected only by the immutable device facts and
inventory commitments authorized in the manifest.

## 7. Media and custody profile

The execution uses exactly five removable data media:

1. control-attestor primary custody medium;
2. control-attestor recovery custody medium;
3. human-authorizer primary custody medium;
4. human-authorizer recovery custody medium; and
5. public-evidence export medium.

No physical medium may serve more than one role. Each custody medium must be
newly prepared or cryptographically sanitized under a documented device method,
then encrypted before any key is created. SSD file deletion, quick format, or
free-space overwrite is not accepted as secure erasure because wear leveling
can retain blocks. Full-media encryption must precede secret creation so later
retirement can rely on cryptographic erasure plus physical destruction under
the retirement procedure.

Only the primary/recovery pair for the key currently being generated may be
attached during a secret-bearing phase. The public-evidence medium and both
pre-existing origin-authentication devices remain physically absent. The other
key's media remain sealed outside the ceremony host until the first key's
plaintext state is destroyed, its media are unmounted, and the witness records
the transition. This prevents cross-key selection, composite-USB injection,
and simultaneous exposure.

Each key has one primary and one recovery encrypted envelope containing the
same private seed and purpose metadata. The two key pairs never share an
envelope, volume, passphrase, recovery code, or media. Public evidence contains
no encrypted private envelope because even ciphertext is not repository or
chat material.

Custody-media encryption and envelope encryption are independent layers. The
full-media encryption profile and tool version are fixed in the execution
manifest and independently reviewed with the environment. The portable key
envelope itself uses exactly Argon2id version 1.3 to derive a 32-byte key from
the UTF-8 passphrase and a fresh 16-byte random salt, followed by
XChaCha20-Poly1305 with a fresh 24-byte random nonce. The minimum Argon2id
parameters are 262,144 KiB memory, four iterations, and parallelism one; the
exact values are fixed in the tool bundle and encoded in the authenticated
header. A parameter below those minima, an unknown parameter, a duplicate
member, or an algorithm/version other than the exact profile is rejected.

The authenticated envelope is RFC 8949 deterministic CBOR. Its top-level map
uses unsigned integer keys and contains exactly: `1` format-version unsigned
integer `1`; `2` purpose unsigned integer (`1` control, `2` human); `3`
repository ID unsigned integer; `4` principal-ID UTF-8 text; `5` key-ID ASCII
text; `6` public-fingerprint 32-byte byte string; `7` Argon2id profile map;
`8` 16-byte salt; `9` 24-byte nonce; `10` ciphertext byte string; and `11`
detached 16-byte authentication-tag byte string. The Argon2id map contains
exactly integer keys `1` version `0x13`, `2` memory KiB, `3` iterations, and
`4` parallelism. The associated data is the deterministic CBOR encoding of a
map containing exactly keys `1` through `9`. Ciphertext is the same length as
the plaintext.

The plaintext is deterministic CBOR containing exactly integer keys: `1`
32-byte Ed25519 seed; `2` purpose integer; `3` repository ID; `4` principal ID;
`5` key ID; `6` 32-byte public fingerprint; `7` ceremony ID; and `8` 32-byte
raw manifest digest. Text length is bounded by its corresponding manifest
field. Primary and recovery envelopes use independent salts and nonces. Unknown
keys, noncanonical ordering or shortest-form violations, unsupported tags,
floats, indefinite lengths, duplicate map keys, invalid UTF-8, or trailing
bytes fail closed. The separately hashed `key_envelope_profile` fixes these
bytes and supplies golden vectors.

The bundle must therefore provide authenticated encryption, memory-hard
passphrase derivation, unique random salts and nonces, integrity verification,
and downgrade rejection. No recovery escrow service, cloud KMS, online HSM,
vendor account, or network unlock is permitted by this plan.

Every passphrase is produced only by the manifest-bound passphrase generator
and profile. Seven words are drawn by unbiased rejection sampling from the
exact ASCII-LF word list using the approved offline CSPRNG and joined by ASCII
hyphens, producing at least 90 bits under the profile's recorded calculation.
A passphrase is never user-selected or based on a quotation, personal fact,
repeated phrase, keyboard pattern, or previously used or disclosed secret. It
is displayed only to its named holder, recorded once on physical paper,
verified by concealed re-entry, sealed, and stored separately from its medium.
The tool records only profile compliance. It compares passphrases transiently
inside locked memory by constant-time equality, rejects reuse, and destroys all
comparison state without retaining a digest, tag, similarity score, or other
secret-derived diagnostic.

## 8. Pre-ceremony gate

Before secret creation, the operator and witness shall jointly establish and
record only public facts:

1. Arthur's authorization matches the manifest hash and time window.
2. The frozen plan and both controlling protocol hashes match exactly.
3. Repository numeric identity and the two governed principal identities match.
4. All role-separation rules hold.
5. Host, firmware, Secure Boot, TPM quote, boot image, tool bundle, executable,
   dependency, verifier, and profile hashes match the manifest.
6. The five media bindings match physical device facts and expose only their
   authorized interface classes; no device has re-enumerated.
7. Both encryption-profile objects and the passphrase profile match.
8. Every network interface is physically absent or hardware-disabled, there is
   no route, and a bounded outbound probe also fails.
9. Internal writable disks and unapproved devices are absent, not merely
   unmounted.
10. Clock source and worst-case uncertainty are documented without a network.
11. Logging, swap, hibernation, crash dumps, telemetry, history, capture paths,
    and remote management are configuration-disabled.
12. The current lifecycle-registry snapshot is available and contains no
    conflicting entry for either new ceremony ID or key ID.
13. Exactly two key pairs and two proof signatures are permitted.
14. An abort record can be created without retaining any secret.

Any failed item ends the session before key generation. Correction requires a
new manifest or new execution authorization when an authorized fact changes.

The retained pre-gate evidence classifies claims as follows:

| Predicate | Producer and exact evidence | Classification |
|---|---|---|
| manifest, protocol, repository, role and profile match | ceremony verifier over canonical objects and hashes | machine-verified |
| host, firmware and boot state | offline verifier validates fresh TPM quote, attestation chain and expected PCR profile | machine-verified |
| network isolation | interface inventory, radio hardware state, route-table absence and bounded probe; witness confirms cables/radios absent | machine-verified plus physically witnessed |
| device identity and class | pre/post enumeration against each `media_binding`; witness observes physical labels and connections | machine-verified plus physically witnessed |
| internal storage absence | firmware inventory and bus enumeration; witness observes approved host configuration | machine-verified plus physically witnessed |
| swap, hibernation, dumps, logging, telemetry and capture | exact configuration projection produced by the approved image and checked against a closed expected projection | configuration-attested |
| clock uncertainty | local trusted-clock identifier, displayed time and bounded uncertainty entered by operator and witnessed | physically witnessed bounded observation |
| cleanup | process reports bounded buffer-destruction attempts and device unmount; witness observes transition | machine-attempted plus physically witnessed, never proof of physical erasure |
| public export safety | exact file allowlist, byte counts and hashes on freshly attached export medium | machine-verified |

The acceptance record never upgrades a configuration-attested or witnessed
fact into universal proof. A tool cannot claim that no firmware or operating
system copy ever existed; it records only the exact controls and observations
above. Failure codes identify the producer and predicate.

Pre-gate evidence is closed:

```text
pre_gate_check = {
  predicate: enum(authorization,protocols,repository,roles,host_boot,media,
                  encryption_profiles,network,internal_storage,clock,
                  system_controls,lifecycle_registry,operation_bounds,
                  abort_path),
  classification: enum(machine_verified,configuration_attested,
                       physically_witnessed,machine_and_witnessed),
  producer_executable_sha256: hash?,
  evidence_schema_version: enum(conclave-stage21c-pre-gate-hash-comparison/0.1.0,
                                conclave-stage21c-network-isolation-evidence/0.1.0,
                                conclave-stage21c-system-controls-evidence/0.1.0,
                                conclave-stage21c-clock-evidence/0.1.0,
                                conclave-stage21c-device-enumeration-evidence/0.1.0),
  evidence_sha256: hash,
  operator_observed: bool,
  witness_observed: bool,
  passed: bool,
  reason_codes: [ascii(64),32]
}

schema_version: literal(conclave-stage21c-key-ceremony-pre-gate/0.1.0)
ceremony_id: ascii(64)
ceremony_manifest_sha256: hash
arthur_execution_authorization_sha256: hash
checks: [pre_gate_check,14]
started_at: ts
completed_at: ts
result: enum(pass,fail)
reason_codes: [ascii(64),32]
content_hash: hash
```

The referenced evidence objects are closed:

```text
hash_comparison_evidence = {
  schema_version: literal(conclave-stage21c-pre-gate-hash-comparison/0.1.0),
  predicate: enum(authorization,protocols,repository,roles,host_boot,
                  encryption_profiles,lifecycle_registry,operation_bounds,
                  abort_path),
  expected_hashes: [hash,64],
  observed_hashes: [hash,64],
  all_equal: bool,
  observed_at: ts,
  content_hash: hash
}

network_probe = {
  destination: enum(192.0.2.1:443,198.51.100.1:443,203.0.113.1:443),
  attempts: literal(1),
  timeout_milliseconds: literal(1000),
  result: enum(no_interface,no_route,unexpected_transmission,timeout,other_error)
}

network_isolation_evidence = {
  schema_version: literal(conclave-stage21c-network-isolation-evidence/0.1.0),
  interface_inventory_sha256: hash,
  enabled_interface_count: literal(0),
  route_inventory_sha256: hash,
  usable_route_count: literal(0),
  hardware_radio_state_sha256: hash,
  probes: [network_probe,3],
  witness_cable_absence: bool,
  observed_at: ts,
  result: enum(pass,fail),
  content_hash: hash
}

system_controls_evidence = {
  schema_version: literal(conclave-stage21c-system-controls-evidence/0.1.0),
  expected_projection_sha256: hash,
  observed_projection_sha256: hash,
  swap_enabled: literal(false),
  hibernation_enabled: literal(false),
  crash_dump_enabled: literal(false),
  telemetry_enabled: literal(false),
  shell_history_enabled: literal(false),
  clipboard_history_enabled: literal(false),
  screen_capture_enabled: literal(false),
  remote_management_enabled: literal(false),
  unexpected_writable_volume_count: literal(0),
  observed_at: ts,
  content_hash: hash
}

clock_evidence = {
  schema_version: literal(conclave-stage21c-clock-evidence/0.1.0),
  clock_device_identity_sha256: hash,
  displayed_utc: ts,
  maximum_uncertainty_seconds: count,
  permitted_uncertainty_seconds: literal(120),
  within_limit: bool,
  operator_observed: bool,
  witness_observed: bool,
  content_hash: hash
}

media_binding_observation = {
  media_binding_sha256: hash,
  role: enum(control_primary,control_recovery,human_primary,human_recovery,public_export),
  observed_identity_sha256: hash,
  observed_interface_inventory_sha256: hash,
  attached_at: ts,
  detached_at: ts,
  result: literal(pass)
}

device_enumeration_evidence = {
  schema_version: literal(conclave-stage21c-device-enumeration-evidence/0.1.0),
  expected_media_binding_hashes: [hash,5],
  binding_observations: [media_binding_observation,5],
  continuous_monitor_started_at: ts,
  continuous_monitor_executable_sha256: hash,
  controller_allowlist_profile_sha256: hash,
  unexpected_event_count: literal(0),
  observed_at: ts,
  content_hash: hash
}

device_interval_evidence = {
  schema_version: literal(conclave-stage21c-device-interval-evidence/0.1.0),
  ceremony_id: ascii(64),
  monitor_executable_sha256: hash,
  monitor_profile_sha256: hash,
  started_at: ts,
  ended_at: ts,
  ordered_event_log_sha256: hash,
  event_count: count,
  liveness_sample_count: id,
  maximum_liveness_gap_seconds: literal(5),
  unexpected_event_count: count,
  final_attached_device_count: count,
  all_expected_detach_events_observed: bool,
  result: enum(pass,fail),
  reason_codes: [ascii(64),32],
  monitor_key_id: ascii(128),
  monitor_public_key_base64url: ascii(43),
  monitor_trust_record_sha256: hash,
  monitor_signature_base64url: ascii(86),
  content_hash: hash
}

device_monitor_event = {
  sequence: id,
  event_type: enum(monitor_start,liveness,attach,reset,interface_change,
                   reenumerate,detach,monitor_stop),
  device_identity_sha256: hash?,
  interface_classes: [ascii(32),8],
  observed_at: ts,
  previous_event_sha256: hash?,
  content_hash: hash
}

device_event_log = {
  schema_version: literal(conclave-stage21c-device-event-log/0.1.0),
  ceremony_id: ascii(64),
  ordered_event_hashes: [hash,100000],
  first_sequence: literal(1),
  final_sequence: id,
  maximum_liveness_gap_seconds: literal(5),
  monitor_key_id: ascii(128),
  monitor_signature_base64url: ascii(86),
  content_hash: hash
}

device_monitor_snapshot = {
  schema_version: literal(conclave-stage21c-device-monitor-snapshot/0.1.0),
  ceremony_id: ascii(64),
  event_log_prefix_sha256: hash,
  latest_sequence: id,
  currently_attached_device_count: count,
  unexpected_event_count: count,
  captured_at: ts,
  monitor_key_id: ascii(128),
  monitor_signature_base64url: ascii(86),
  content_hash: hash
}

cleanup_buffer_result = {
  buffer_role: enum(seed,derived_key,passphrase,plaintext_cbor,aead_scratch,
                    sampler_scratch,comparison_scratch,proof_signing),
  allocation_count: count,
  destruction_attempt_count: count,
  verification_method: enum(overwrite_readback,allocator_release_only),
  result: enum(attempted_verified,attempted_unverifiable)
}

cleanup_evidence = {
  schema_version: literal(conclave-stage21c-cleanup-evidence/0.1.0),
  ceremony_id: ascii(64),
  tool_executable_sha256: hash,
  buffer_results: [cleanup_buffer_result,8],
  all_enumerated_buffers_covered: literal(true),
  custody_media_unmounted: literal(true),
  writable_scratch_media_count: literal(0),
  witness_observed: literal(true),
  completed_at: ts,
  result: enum(pass,fail),
  reason_codes: [ascii(64),32],
  content_hash: hash
}
```

Cleanup contains exactly eight enum-ordered buffer results. Allocation count
equals destruction-attempt count for each role and every count is nonzero when
that role was allocated; a role not allocated is represented by count zero only
when the tool's closed allocation trace proves absence. Any
`attempted_unverifiable` result fails ceremony completion and triggers
quarantine; the retained record still makes only the bounded attempt claim.
Device-interval `pass` requires zero unexpected events, zero finally attached
devices, every expected detach, nonzero liveness samples, no gap over five
seconds, and an authenticated event log covering every attach/reset/class-
change/detach event. Otherwise it is `fail` with nonempty reasons and the abort
record binds it.
Each event points to its exact predecessor and sequences are gapless. The log
contains every event hash in sequence order and its counts equal the interval
record. The monitor signs both log and interval using ASCII domains
`CONCLAVE-STAGE21C-DEVICE-LOG-V1` and
`CONCLAVE-STAGE21C-DEVICE-INTERVAL-V1`, respectively, zero byte, then canonical
JSON with signature/content hash absent. Its immutable trust record and exact
public key are manifest-bound. Truncation, restart, key change, gap, missing
start/stop, or inconsistent count fails.
Nonterminal snapshots use domain `CONCLAVE-STAGE21C-DEVICE-SNAPSHOT-V1` with the
same construction, bind an exact prefix of the still-running log, and never
claim completion.

Network isolation passes only when all three probes return `no_interface` or
`no_route`; timeout and every other result fail because they could conceal a
transmission. The three probes appear in the enum order above. System controls
pass only when expected and observed projection hashes match and every literal
has the required value. Clock passes only when uncertainty is at most 120
seconds and both humans observed it. Before secret creation, each of the five
media is attached alone, identity/interface checked, and detached, producing
exactly five enum-ordered observations; secret-phase attachment remains governed
by §7. The device monitor begins before the first survey attachment and remains
active through final detachment of custody, export, and origin-authenticator
devices. Its authenticated append-only event log and five-second liveness
samples feed the terminal interval record, which can be created only after all
devices detach and is referenced only by the completion record or abort—not by the
earlier provisional record.

There are exactly fourteen checks in the listed predicate order. A physically
witnessed-only check has null producer hash; every other check has the exact
producer executable. `pass` requires every check to pass. A failed pre-gate
record is retained with no seed creation and cannot be retried under the same
manifest. Passing checks and a passing record have empty reason arrays; failed
checks and a failed record have nonempty reason arrays.

## 9. Control-attestor key generation

The two control-attestor passphrase holders separately generate and confirm
their assigned passphrases while the two control media custodians present only
their assigned media. The operator starts
the exact purpose-specific tool flow. The tool:

1. verifies the manifest and purpose `control_attestor`;
2. draws a fresh 32-byte Ed25519 seed from the approved CSPRNG;
3. derives the public key in memory;
4. computes the canonical public facts in §11;
5. writes the encrypted primary envelope directly to the named primary medium;
6. writes a separately salted and nonced encrypted copy directly to the named
   recovery medium;
7. reads back, authenticates, decrypts in protected memory, and proves that both
   envelopes reconstruct the same public key;
8. produces the single bounded proof-of-possession signature in §12; and
9. performs and verifies bounded destruction attempts over every tool-owned
   mutable seed buffer, derived-key buffer, passphrase input buffer, plaintext-
   CBOR buffer, AEAD scratch buffer, equality-check buffer, and proof-signing
   buffer before reporting readiness for the next phase.

The exact reviewed tool must enumerate those buffer classes and demonstrate
that its language, compiler, runtime, and libraries provide mutable non-copying
storage for them. Unavoidable library, firmware, or operating-system copies are
treated as residual risk controlled by the ephemeral host and power-down, not
misreported as zeroized. An unenumerated or non-destroyable tool-owned secret
buffer produces `ZEROIZATION_UNPROVEN` and quarantine.

Neither the operator, witness, nor a media custodian sees or handles a
passphrase or private key. Failure after seed creation makes the whole ceremony
ineligible under §15; partial-key acceptance is prohibited.

## 10. Human-authorizer key generation

After the control-attestor plaintext state is destroyed, the two human-
authorizer passphrase holders separately generate and confirm their assigned
passphrases while the two human media custodians present their assigned media.
The tool repeats
the §9 flow under purpose `human_authorizer`, new randomness, different media,
and the authorized human key ID. It must prove the public key and seed differ
from the control-attestor key before writing a successful result.

A collision, repeated seed, repeated public key, reused salt or nonce, reused
passphrase detected by the tool, or any cross-purpose envelope acceptance is a
hard failure. The atomic failure rules in §15 quarantine every medium used in
the ceremony and place both planned key IDs into the exact abandoned or
quarantined states in §15, including any already completed
control-attestor key.

## 11. Public facts

For each key the tool emits only:

```text
schema_version: literal(conclave-stage21c-key-public-facts/0.1.0)
purpose: enum(control_attestor,human_authorizer)
stage_21c_protocol_sha256: hash
collection_protocol_sha256: hash?
repository_id: literal(1335850028)
principal_id: ascii(128)
key_id: ascii(128)
algorithm: literal(Ed25519)
public_key_base64url: ascii(43)
public_key_sha256: hash
generated_at: ts
ceremony_id: ascii(64)
ceremony_manifest_sha256: hash
content_hash: hash
```

`collection_protocol_sha256` is the frozen collection-protocol hash only for
`control_attestor` and null for `human_authorizer`. The 43-character unpadded
base64url value must decode canonically to exactly 32 raw public-key bytes.
`public_key_sha256` is lowercase SHA-256 over those exact raw bytes and is
represented with the frozen `sha256:` hash syntax where the controlling Stage
21C schema requires it.

Public facts are candidates for later trust authorizations. They are not
self-authenticating and do not activate trust.

## 12. Bounded proof of possession

The tool constructs exactly one proof message per generated key:

```text
ASCII("CONCLAVE-STAGE21C-KEY-CEREMONY-POP-V1")
|| 0x00
|| canonical_json({
     ceremony_manifest_sha256,
     purpose,
     repository_id,
     principal_id,
     key_id,
     public_key_base64url,
     public_key_sha256
   })
```

It produces one canonical unpadded base64url Ed25519 signature of exactly 64
bytes, immediately verifies it against the emitted public key, and records the
message hash and signature in public evidence. No other bytes can be supplied
to this signing path. Proof signatures are ceremony evidence only and cannot
be accepted as a Stage 21C attestation or human merge authorization.

The tool then performs negative tests proving that each signature fails under
the other key, other purpose, altered manifest hash, altered repository ID,
altered principal, and altered key ID.

## 13. Secret-free provisional evidence and terminal schemas

After both custody-media pairs are unmounted and the tool has completed its
bounded destruction attempts for every plaintext secret, the operator and
witness verify that no secret-bearing medium remains attached. Only then may
the previously absent public-export medium be attached. Device enumeration must
match its exact `media_binding`; any additional interface or re-enumeration
quarantines the ceremony before export. The tool first writes one nonterminal
provisional record:

```text
schema_version: literal(conclave-stage21c-key-ceremony-provisional/0.1.0)
ceremony_id: ascii(64)
ceremony_manifest_sha256: hash
arthur_execution_authorization_sha256: hash
frozen_plan_sha256: hash
stage_21c_protocol_sha256: hash
collection_protocol_sha256: hash
repository_id: literal(1335850028)
control_attestor_public_facts: key_public_facts
human_authorizer_public_facts: key_public_facts
control_attestor_pop_message_sha256: hash
control_attestor_pop_signature: ascii(86)
human_authorizer_pop_message_sha256: hash
human_authorizer_pop_signature: ascii(86)
key_distinctness_verified: literal(true)
control_primary_envelope_sha256: hash
control_recovery_envelope_sha256: hash
human_primary_envelope_sha256: hash
human_recovery_envelope_sha256: hash
control_primary_readback_verified: literal(true)
control_recovery_readback_verified: literal(true)
human_primary_readback_verified: literal(true)
human_recovery_readback_verified: literal(true)
media_binding_hashes: [hash,5]
pre_gate_evidence_sha256: hash
cleanup_evidence_sha256: hash
observed_environment_boot_measurement_sha256: hash
observed_verifier_boot_measurement_sha256: hash
lifecycle_registry_before_sha256: hash
operator_principal_id: ascii(128)
witness_principal_id: ascii(128)
started_at: ts
completed_at: ts
status: literal(ready_for_handoff)
reason_codes: [ascii(64),32]
content_hash: hash
```

`key_public_facts` is exactly the closed object in §11 with no additional
members. The observed boot measurement is non-null and must match the manifest.
The four envelope hashes are SHA-256 over the exact encrypted envelope bytes;
the envelopes themselves never enter public evidence. This record proves only
readiness for custody handoff. It is not a completed result, cannot be accepted
or origin-authenticated as success, and remains nonterminal if later handoff
fails.

All public facts and proof fields are present and all literal verification
values are true/pass. Reason codes are empty.

An unsuccessful session does not use this success-result schema. It instead
emits the following separate closed abort record:

```text
schema_version: literal(conclave-stage21c-key-ceremony-abort/0.1.0)
ceremony_id: ascii(64)
ceremony_manifest_sha256: hash
arthur_execution_authorization_sha256: hash
frozen_plan_sha256: hash
repository_id: literal(1335850028)
stage_reached: enum(pre_gate,control_key,human_key,verification,cleanup,export,
                    origin_authentication,handoff)
secret_was_created: bool
known_public_key_sha256: [hash,2]
reserved_key_ids: [ascii(128),2]
affected_media_inventory_sha256: [hash,4]
terminal_disposition_sha256: hash
terminal_state: enum(aborted,quarantined)
reason_codes: [ascii(64),32]
recorded_at: ts
content_hash: hash
```

The three evidence arrays in the abort object are sorted and unique;
`known_public_key_sha256` and `affected_media_inventory_sha256` may be empty,
but `reserved_key_ids` contains exactly the manifest's two IDs. Reason codes
are always nonempty. If
`secret_was_created` is true, terminal state must
be `quarantined`, every affected medium is sealed for destruction or governed
recovery, and every known generated key ID is permanently non-reusable and
enters the exact §15 disposition path. The abort
record never asserts that cleanup succeeded merely because the process ended.

The final result or abort record contains no media serial number, passphrase,
private-key envelope, seed-derived identifier other than the public key, host
user name, personal email, raw log, environment dump, device path, or unbounded
text. The provisional record is never supplied to the success form of the
witness or origin schema.

Only after the final result exists, or immediately after an abort and terminal
disposition exist, the operator and witness independently recompute that final
result or abort hash on
the manifest-bound verifier host using two separate verifier executions and
compare outputs without sharing a mutable workspace. The witness records this
closed, detached,
secret-free observation:

```text
schema_version: literal(conclave-stage21c-key-ceremony-witness/0.1.0)
ceremony_id: ascii(64)
ceremony_manifest_sha256: hash
arthur_execution_authorization_sha256: hash
result_or_abort_sha256: hash
operator_principal_id: ascii(128)
witness_principal_id: ascii(128)
role_separation_verified: bool
environment_hashes_verified: bool
media_inventory_verified: bool
network_absence_observed: bool
displayed_public_facts_verified: bool
cleanup_observed: bool
terminal_state: enum(ready_for_origin,aborted,quarantined)
reason_codes: [ascii(64),32]
observed_at: ts
content_hash: hash
```

For `ready_for_origin`, every verification boolean is true and reason codes are empty.
For another state, booleans record only what the witness actually observed and
reason codes are nonempty. This observation is factual, is not a cryptographic
trust authorization, and does not activate either key.

The verifier next constructs one origin commitment:

```text
schema_version: literal(conclave-stage21c-key-ceremony-origin/0.1.0)
ceremony_id: ascii(64)
ceremony_manifest_sha256: hash
arthur_execution_authorization_sha256: hash
result_or_abort_sha256: hash
witness_record_sha256: hash
pre_origin_inventory_sha256: hash
public_key_fingerprints: [hash,2]
operator_principal_id: ascii(128)
operator_key_id: ascii(128)
witness_principal_id: ascii(128)
witness_key_id: ascii(128)
origin_authentication_profile_sha256: hash
signed_at: ts
operator_signature: ascii(86)
witness_signature: ascii(86)
content_hash: hash
```

For a completed result, `public_key_fingerprints` contains exactly two values;
for an abort it contains zero through two known values. The operator and witness
attach their two pre-approved authentication devices only during this post-
secret phase and separately sign the ASCII domain
`CONCLAVE-STAGE21C-CEREMONY-ORIGIN-V1`, one zero byte, and canonical JSON with
both signature fields and `content_hash` absent. Both signatures are canonical
unpadded base64url encodings of exactly 64 Ed25519 bytes and must verify against
the two distinct pre-existing keys pinned by the origin profile. Neither newly
generated ceremony key can authenticate origin. Missing, same-key, untrusted,
or nonmatching signatures invalidate the entire result.

Before origin signing, the verifier constructs `pre_origin_inventory_sha256`
over a canonical inventory of the manifest, execution-authorization public
record, pre-gate evidence, public facts, proof signatures, final result or
abort, witness record, planned lifecycle events/snapshot, and, for success, all
four custody receipts, all four passphrase-holder records, the custody register,
and its signed checkpoint. The origin signatures bind that inventory. After origin signing, the
export medium contains those exact objects, the origin commitment, and one
final canonical public-file inventory naming every exact relative filename,
size, and SHA-256 hash. The allowlist forbids every other file, alternate
data stream, extended attribute, hidden partition, executable, device interface,
or writable metadata object. The verifier reformats no artifact and accepts no
raw log, environment dump, encrypted envelope, or secret-derived diagnostic.

Both the pre-origin and final inventories use:

```text
public_file = {
  relative_path: ascii(240),
  byte_count: count,
  sha256: hash
}

schema_version: literal(conclave-stage21c-public-file-inventory/0.1.0)
ceremony_id: ascii(64)
phase: enum(pre_origin,final)
files: [public_file,64]
filesystem_profile_sha256: hash
created_at: ts
content_hash: hash
```

Paths are single canonical POSIX relative paths with no empty component, dot
component, traversal, backslash, drive prefix, control, Unicode, symlink,
hardlink, reparse point, alternate stream, or case-fold collision. Files sort
by path ASCII bytes and every path is unique. The final inventory contains the
pre-origin inventory and origin commitment in addition to the files named by
the pre-origin inventory; it cannot list itself.

This `final` inventory is final only for the ceremony export medium. It
intentionally cannot list the later terminal interval or completion record.
After detachment, the independently powered, manifest-bound monitor displays
and optically emits its signed terminal log/interval hashes without any storage
device being reattached to the ceremony host. A separate governed verification
workstation verifies those signatures and constructs the completion record from
the immutable export inventory plus terminal interval. Those two later public
records are preserved in the governed review workspace, not written back to the
ceremony export medium, and are governed by their own closed schemas/ceilings.
No claim that the export inventory contains itself or those later records is
made; this ordering terminates without reattachment or a hash cycle.

## 14. Post-generation custody handoff

After successful verification:

1. The tool completes its bounded destruction attempts for transient secret
   state and unmounts all custody media; evidence records the attempt and
   observed outcome without claiming physical proof of zeroization.
2. The operator and witness verify the public-export allowlist and confirm no
   unexpected public file or device interface is present.
3. Primary and recovery media are sealed in separate tamper-evident containers
   with public custody labels only.
4. Each source and destination media custodian signs the same physical custody
   receipt identifying ceremony ID, purpose, key ID, public-key fingerprint,
   provisional-record hash, encrypted-envelope hash, media-binding hash, seal
   ID, authorized storage commitment, date, source, and destination. It contains
   no passphrase, ciphertext, or private material.
5. Passphrase papers are sealed and stored apart from their corresponding media.
6. The two primary packages, two recovery packages, and all four passphrase
   records occupy separate approved storage locations according to the
   execution authorization.
7. A custody register records every seal, receipt, holder record, and authorized
   storage commitment.
8. Only after all eight packages and the custody register candidate verify does
   the tool construct the ready-for-origin result. The witness and origin
   records in §13 authenticate it; the final file inventory is sealed; all
   devices detach; terminal interval evidence is created; and only then is the
   completion record created.
9. The public evidence is imported into the governed review workspace only
   after the exact verifier rechecks the file allowlist, origin signatures,
   canonical encodings, hashes, and absence of any non-allowlisted object on a
   separately authorized review host.
10. Quarterly physical audits require two distinct witnesses, compare every
    seal and receipt, and publish only a secret-free audit hash and disposition.

Each custody receipt is a two-step, acyclic physical-and-digital record:

```text
schema_version: literal(conclave-stage21c-custody-receipt-preimage/0.1.0)
ceremony_id: ascii(64)
purpose: enum(control_attestor,human_authorizer)
media_role: enum(control_primary,control_recovery,human_primary,human_recovery)
key_id: ascii(128)
public_key_sha256: hash
provisional_record_sha256: hash
encrypted_envelope_sha256: hash
media_binding_sha256: hash
seal_id_sha256: hash
seal_photograph_sha256: hash
storage_location_commitment_sha256: hash
source_custodian_principal_id: ascii(128)
destination_custodian_principal_id: ascii(128)
prepared_at: ts
content_hash: hash

schema_version: literal(conclave-stage21c-custody-receipt/0.1.0)
custody_receipt_preimage_sha256: hash
physical_receipt_sha256: hash
source_acknowledgement_observed: literal(true)
destination_acknowledgement_observed: literal(true)
witness_principal_id: ascii(128)
transferred_at: ts
content_hash: hash
```

The physical receipt prints the exact preimage `content_hash`; operator and
witness compare it before the source and destination sign. Its scanned or
independently digitized exact bytes then supply `physical_receipt_sha256` to the
final digital receipt, and both acknowledgements are witnessed. The final
receipt hash is never printed in or used to derive the physical receipt, so the
ordering is acyclic: preimage → signed physical receipt → final receipt.

Every `physical_receipt_sha256` names exact PDF/A-2b bytes no larger than
4,194,304 bytes. A closed private artifact descriptor records that hash, byte
count, MIME type `application/pdf`, capture-device security-attestation hash,
capture time, two signer principal IDs, retention-location commitment, and
retention-until date. Exact bytes are retained in the separately controlled
custody evidence store and must be available to authorized audit/verifier
sessions; they never enter Git, chat, CI, or public export. The public pre-origin
inventory contains the descriptor and receipt hash, not the identity-bearing
PDF bytes. `retain_until` must be at least seven years after the later of key
destruction or the last governed obligation; it cannot expire while the key is
not destroyed. Unavailable bytes make custody unverifiable and suspend the key.
Every required seal photograph is retained as another private
`physical_receipt_artifact` bound by its photograph hash.

```text
physical_receipt_artifact = {
  schema_version: literal(conclave-stage21c-physical-receipt-artifact/0.1.0),
  receipt_sha256: hash,
  byte_count: id,
  media_type: literal(application/pdf),
  format_profile: literal(PDF-A-2b),
  capture_device_attestation_sha256: hash,
  signer_principal_ids: [ascii(128),2],
  retention_location_commitment_sha256: hash,
  captured_at: ts,
  retain_until: ts,
  content_hash: hash
}
```

Passphrase custody uses the same two-step ordering:

```text
schema_version: literal(conclave-stage21c-passphrase-holder-preimage/0.1.0)
ceremony_id: ascii(64)
purpose: enum(control_attestor,human_authorizer)
passphrase_role: enum(control_primary,control_recovery,human_primary,human_recovery)
key_id: ascii(128)
holder_principal_id: ascii(128)
destination_principal_id: ascii(128)
storage_location_commitment_sha256: hash
outer_seal_id_sha256: hash
envelope_passphrase_inner_seal_id_sha256: hash
volume_passphrase_inner_seal_id_sha256: hash
seal_photograph_sha256: hash
prepared_at: ts
content_hash: hash

schema_version: literal(conclave-stage21c-passphrase-holder-record/0.1.0)
passphrase_holder_preimage_sha256: hash
physical_receipt_sha256: hash
holder_acknowledgement_observed: literal(true)
destination_acknowledgement_observed: literal(true)
witness_principal_id: ascii(128)
transferred_at: ts
content_hash: hash
```

The passphrase paper and its transfer form print only the holder-preimage hash.
After both parties sign the transfer form, its exact-byte scan is hashed into
the final holder record. Neither record contains the passphrase or a verifier
for it, and the same acyclic preimage → physical receipt → final-record ordering
applies.

The custody register is:

```text
custody_package = {
  package_id: ascii(128),
  ceremony_id: ascii(64),
  purpose: enum(control_attestor,human_authorizer),
  key_id: ascii(128),
  role: enum(control_primary_media,control_primary_passphrase,
             control_recovery_media,control_recovery_passphrase,
             human_primary_media,human_primary_passphrase,
             human_recovery_media,human_recovery_passphrase),
  holder_principal_id: ascii(128),
  destination_principal_id: ascii(128),
  storage_location_commitment_sha256: hash,
  seal_id_sha256: hash,
  custody_record_sha256: hash,
  status: enum(sealed,suspended,missing,broken,transferred,destroyed),
  last_audit_at: ts?,
  next_audit_due_at: ts
}

schema_version: literal(conclave-stage21c-custody-register/0.2.0)
repository_id: literal(1335850028)
previous_register_sha256: hash?
packages: [custody_package,10000]
generated_at: ts
content_hash: hash

custody_checkpoint = {
  schema_version: literal(conclave-stage21c-custody-checkpoint/0.1.0),
  repository_id: literal(1335850028),
  register_sha256: hash,
  previous_checkpoint_sha256: hash?,
  generation: count,
  governance_profile_sha256: hash,
  signed_at: ts,
  arthur_signature_base64url: ascii(86),
  independent_witness_signature_base64url: ascii(86),
  content_hash: hash
}

custody_governance_profile = {
  schema_version: literal(conclave-stage21c-custody-governance-profile/0.1.0),
  repository_id: literal(1335850028),
  base_ref: literal(refs/heads/main),
  register_path: literal(docs/governance/stage-21c-key-custody/REGISTRY.json),
  checkpoint_path: literal(docs/governance/stage-21c-key-custody/CHECKPOINT.json),
  governance_signature_profile_sha256: hash,
  witness_excluded_from_all_current_custody_roles: literal(true),
  required_review_count: id,
  content_hash: hash
}
```

Packages sort by ceremony ID, key ID, then `storage_binding.role`; package IDs
are globally unique. A ceremony update adds exactly its eight packages and
preserves every earlier package until a separately authorized destroyed-state
update. The repository genesis register is an explicitly empty array (the sole
exception to the default nonempty-array rule), has null predecessor, and its
checkpoint has null predecessor and generation zero. It exists before any
ceremony. Every update names the exact prior register and checkpoint and
increments generation by one. Checkpoint signatures use ASCII domain
`CONCLAVE-STAGE21C-CUSTODY-CHECKPOINT-V1`, one zero byte, then canonical JSON
with both signature fields and `content_hash` absent.
For each initial-handoff package, `last_audit_at` is null and
`next_audit_due_at` is no later than 92 days after its transfer time. After the
first passing audit, `last_audit_at` is non-null. A custody suspension changes
every affected intact package to `suspended`; resolution requires an authorized
audit/replacement update, never a silent return to `sealed`.

The only authoritative current register is the pair at the two fixed paths on
protected `refs/heads/main`. Publication is one compare-and-replace pull request
and one atomic merge commit: its base commit, prior register, prior checkpoint,
protection projection, and two checkpoint signatures must match; the tree may
replace only the register and checkpoint plus separately reviewed public
evidence named by the register. After merge, the verifier reconstructs ordered
Git ancestry, requires the merge tree to equal the reviewed head tree, and
selects the new pair only if it uniquely supersedes the prior pair. A stale
base, missing predecessor, replay, rollback, competing generation, fork,
signature mismatch, changed protection, same-path conflict, or multiple current
candidate fails closed. Automatic retry and sequence-based fork choice are
prohibited; a new proposal and Arthur authorization against actual current
protected `main` are required.

Custodian or holder replacement requires a separate dual-reviewed replacement
proposal naming the exact current register/checkpoint, affected role, outgoing
and incoming principals, new storage commitment and seal, transfer receipt,
effective time, and reason. It cannot change any other package. Broken seals,
missing packages, conflicting receipts, or an overdue audit require immediate
`suspended` lifecycle proposals before any replacement. Missing, stale,
conflicting, multiply current, overdue, broken, or unverifiable custody state
suspends both keys and blocks signing.

Every initial handoff, passing audit, holder replacement, recovery
reconstruction, suspension, retirement, and destruction uses one current-head
transaction:

```text
custody_change_review = {
  schema_version: literal(conclave-stage21c-custody-change-review/0.1.0),
  proposal_sha256: hash,
  reviewer_principal_id: ascii(128),
  reviewer_key_id: ascii(128),
  reviewer_public_key_base64url: ascii(43),
  reviewer_trust_record_sha256: hash,
  verdict: literal(pass_exact_proposal),
  reviewed_at: ts,
  signature_base64url: ascii(86),
  content_hash: hash
}

custody_update_proposal = {
  schema_version: literal(conclave-stage21c-custody-update-proposal/0.1.0),
  action: enum(initial_handoff,audit,holder_replacement,recovery_reconstruction,
               suspend,retire,destroy),
  repository_id: literal(1335850028),
  expected_main_commit: ascii(64),
  expected_register_sha256: hash,
  expected_checkpoint_sha256: hash,
  affected_package_ids: [ascii(128),10000],
  evidence_hashes: [hash,32],
  proposed_register_sha256: hash,
  proposed_checkpoint_sha256: hash,
  effective_at: ts,
  content_hash: hash
}

custody_update_authority = {
  schema_version: literal(conclave-stage21c-custody-update-authority/0.1.0),
  proposal_sha256: hash,
  expected_main_commit: ascii(64),
  governance_signature_profile_sha256: hash,
  authorized_by_principal_id: ascii(128),
  issued_at: ts,
  expires_at: ts,
  arthur_signature_base64url: ascii(86),
  content_hash: hash
}
```

Holder replacement requires exactly two `custody_change_review` records whose
reviewers, keys, and trust records are distinct and collide with no affected
holder, custodian, operator, witness, or configured principal. Each signs ASCII
`CONCLAVE-STAGE21C-CUSTODY-CHANGE-REVIEW-V1`, zero byte, then canonical JSON
with signature and content hash absent. Their hashes occupy the update
proposal's evidence list before Arthur signs the authority.

Arthur signs the authority using domain
`CONCLAVE-STAGE21C-CUSTODY-UPDATE-AUTHORITY-V1`, one zero byte, then canonical
JSON with `arthur_signature_base64url` and `content_hash` absent. The proposed register changes
only the affected packages, preserves all others, and the proposed checkpoint
advances exactly one generation. Merge uses the compare-and-replace checks
above; post-merge verification proves exact head/tree and current pair before
the action takes effect. This is the sole holder-replacement procedure and
closes both initial and later updates.

Each audit uses:

```text
custody_package_observation = {
  package_id: ascii(128),
  role: enum(control_primary_media,control_primary_passphrase,
             control_recovery_media,control_recovery_passphrase,
             human_primary_media,human_primary_passphrase,
             human_recovery_media,human_recovery_passphrase),
  custody_record_sha256: hash,
  seal_match: bool,
  storage_match: bool,
  observed_at: ts
}

schema_version: literal(conclave-stage21c-custody-audit/0.1.0)
custody_register_sha256: hash
auditor_principal_ids: [ascii(128),2]
auditor_key_ids: [ascii(128),2]
auditor_public_key_base64url: [ascii(43),2]
auditor_trust_record_hashes: [hash,2]
package_observations: [custody_package_observation,10000]
completed_at: ts
next_audit_due_at: ts
result: enum(pass,missing,broken,stale,conflict)
reason_codes: [ascii(64),32]
auditor_signatures_base64url: [ascii(86),2]
content_hash: hash
```

The auditors are distinct from every current custodian and holder. A passing
audit is signed independently by both auditors over ASCII
`CONCLAVE-STAGE21C-CUSTODY-AUDIT-V1`, one zero byte, then canonical JSON with
`auditor_signatures_base64url` and `content_hash` absent; keys and trust records
must be distinct and valid. A passing
audit contains exactly one enum/ID-sorted observation for every non-destroyed
package, sets each package `last_audit_at` to `completed_at`, and sets
`next_audit_due_at` no later than 92 days afterward through an authorized
`audit` update. A non-pass audit or missed due time requires an immediate
`suspended` lifecycle batch and custody `suspend` update.

After all receipts, holder records, and the custody-register candidate verify,
the ready-for-origin ceremony result is:

```text
schema_version: literal(conclave-stage21c-key-ceremony-result/0.1.0)
ceremony_id: ascii(64)
ceremony_manifest_sha256: hash
arthur_execution_authorization_sha256: hash
provisional_record_sha256: hash
custody_plan_sha256: hash
custody_receipt_hashes: [hash,4]
passphrase_holder_record_hashes: [hash,4]
custody_register_candidate_sha256: hash
custody_checkpoint_unsigned_preimage_sha256: hash
lifecycle_registry_sha256: hash
cleanup_evidence_sha256: hash
ready_at: ts
status: literal(ready_for_origin)
reason_codes: [ascii(64),32]
content_hash: hash
```

The two four-item arrays sort by the corresponding control-primary, control-
recovery, human-primary, human-recovery role order. Reason codes are empty. If
any handoff step fails, no final result exists; the provisional record is
retained as nonterminal evidence, an abort record is created, both keys and all
four media are quarantined, and origin authentication binds the abort instead.
The offline result binds only the proposed register and unsigned checkpoint
preimage. After the ceremony shuts down, those public bytes move through the
governed review workspace. Arthur and the independent governance witness sign
the checkpoint externally with their approved devices; no governance device is
attached to the ceremony host. The resulting custody update must reproduce the
bound register/preimage exactly, merge, and verify current before acceptance.
This result is not terminal. After origin signing, final inventory creation,
detachment of every device, and construction of terminal device-interval
evidence, the verifier creates:

```text
schema_version: literal(conclave-stage21c-key-ceremony-completion/0.1.0)
ceremony_id: ascii(64)
ceremony_result_sha256: hash
origin_commitment_sha256: hash
witness_record_sha256: hash
final_public_file_inventory_sha256: hash
device_interval_evidence_sha256: hash
observed_verifier_boot_measurement_sha256: hash
completed_at: ts
status: literal(completed)
reason_codes: [ascii(64),32]
content_hash: hash
```

The completion record has an empty reason array and is the sole success
terminal artifact. Completion does not itself change either key from `planned`
to `accepted`. Arthur must later accept the exact completion record, result,
and origin commitment, after
the exact initial custody update has merged and its protected-main register and
checkpoint are verified current. Only then may separately authorized atomic
compare-and-append publication create the two
`accepted` lifecycle events.

The offline boot environment is shut down without hibernation. Temporary RAM is
allowed to lose power. If the environment used any writable scratch medium, it
is quarantined for cryptographic erasure or destruction and never becomes an
evidence or custody medium.

## 15. Abort, compromise, loss, and revocation

Eligibility is atomic across the two-key ceremony. The total terminal rules are:

| Failure point | Key and media disposition |
|---|---|
| before any seed | `aborted`; both reserved key IDs become `abandoned`; no key exists; all media remain in pre-use state unless separately implicated |
| during control key generation | control ID becomes `quarantined`; human ID becomes `abandoned`; both control media quarantine; unused human media return sealed only after inventory verification |
| after control completion but before human seed | control key and ID become `quarantined`; human ID becomes `abandoned`; both control media quarantine |
| during or after human generation | both keys and IDs become `quarantined`; all four custody media quarantine |
| verification, cleanup, export, origin authentication, or handoff | both keys and IDs become `quarantined`; all four custody media quarantine; only abort evidence may become terminal |

Every row produces one closed disposition record:

```text
key_disposition = {
  purpose: enum(control_attestor,human_authorizer),
  key_id: ascii(128),
  public_key_sha256: hash?,
  seed_created: bool,
  terminal_state: enum(abandoned,quarantined,suspended,revoked,retired,destroyed)
}

media_disposition = {
  media_binding_sha256: hash,
  role: enum(control_primary,control_recovery,human_primary,human_recovery,
             replacement_primary),
  terminal_state: enum(unused_sealed,quarantined,transferred,destroyed),
  seal_id_sha256: hash?,
  disposition_evidence_sha256: hash
}

schema_version: literal(conclave-stage21c-key-terminal-disposition/0.2.0)
operation: enum(ceremony,recovery,compromise,revocation,retirement,destruction)
ceremony_id: ascii(64)?
failure_stage: enum(pre_gate,control_key,human_key,verification,cleanup,export,
                    origin_authentication,handoff,recovery_unlock,
                    recovery_readback,custody_publication,compromise_response,
                    revocation,retirement,destruction)
key_dispositions: [key_disposition,10000]
media_dispositions: [media_disposition,10000]
authority_sha256: hash
reason_codes: [ascii(64),32]
recorded_at: ts
content_hash: hash
```

For `ceremony`, both key entries and all four media entries are mandatory even
when no seed was created or media stayed unused. For other operations, arrays
contain exactly every affected key and medium and at least one key; unrelated
objects are prohibited. Ceremony ID is non-null for ceremony/recovery and may
be null only for a later cross-ceremony lifecycle action. Key entries sort
control then human; media sort by binding hash. Nullable
public fingerprints and seal IDs are null only when they never existed. The
abort record, lifecycle proposals, failure-injection oracle, and later
destruction evidence all bind this same disposition hash.

No completed first key survives a failed second-key flow. Unknown cleanup state
is quarantine, never success. A tool crash cannot resume a ceremony or reuse a
key ID. A new attempt requires new IDs, new authorization, and new media after
the governed disposition of every affected device.

The authoritative lifecycle evidence is append-only and secret-free. Its only
authoritative publication channel is repository ID `1335850028`, protected
`refs/heads/main`, under these exact paths:

- `docs/governance/stage-21c-key-lifecycle/events/`;
- `docs/governance/stage-21c-key-lifecycle/REGISTRY.json`; and
- `docs/governance/stage-21c-key-lifecycle/CHECKPOINT.json`.

Files on another ref, fork, repository, path, local cache, or network response
are not current. One protected-main Git commit atomically adds the new event and
replaces both registry and checkpoint. Direct writes, force pushes, history
rewrites, and partial publication are prohibited.

The closed objects are:

```text
lifecycle_event_proposal = {
  schema_version: literal(conclave-stage21c-key-lifecycle-event-proposal/0.1.0),
  expected_main_commit: ascii(64),
  expected_checkpoint_sha256: hash,
  expected_registry_sha256: hash,
  ceremony_id: ascii(64),
  purpose: enum(control_attestor,human_authorizer),
  key_id: ascii(128),
  public_key_sha256: hash?,
  from_state: enum(none,planned,abandoned,accepted,activated,suspended,quarantined,revoked,retired),
  to_state: enum(planned,abandoned,quarantined,accepted,activated,suspended,revoked,retired,destroyed),
  transition_evidence_sha256: hash?,
  origin_commitment_sha256: hash?,
  terminal_disposition_sha256: hash?,
  custody_receipt_hashes: [hash,4],
  passphrase_holder_record_hashes: [hash,4],
  reason_codes: [ascii(64),32],
  effective_at: ts,
  content_hash: hash
}

lifecycle_event_authority = {
  schema_version: literal(conclave-stage21c-key-lifecycle-event-authority/0.1.0),
  proposal_sha256: hash,
  repository_id: literal(1335850028),
  expected_main_commit: ascii(64),
  expected_checkpoint_sha256: hash,
  governance_signature_profile_sha256: hash,
  authorized_by_principal_id: ascii(128),
  issued_at: ts,
  expires_at: ts,
  arthur_signature_base64url: ascii(86),
  content_hash: hash
}

lifecycle_batch_authority = {
  schema_version: literal(conclave-stage21c-key-lifecycle-batch-authority/0.1.0),
  proposal_hashes: [hash,10000],
  expected_main_commit: ascii(64),
  expected_checkpoint_sha256: hash,
  governance_signature_profile_sha256: hash,
  authorized_by_principal_id: ascii(128),
  issued_at: ts,
  expires_at: ts,
  arthur_signature_base64url: ascii(86),
  content_hash: hash
}

lifecycle_event = {
  schema_version: literal(conclave-stage21c-key-lifecycle-event/0.1.0),
  proposal_sha256: hash,
  sequence: id,
  previous_event_sha256: hash?,
  ceremony_id: ascii(64),
  purpose: enum(control_attestor,human_authorizer),
  key_id: ascii(128),
  public_key_sha256: hash?,
  from_state: enum(none,planned,abandoned,accepted,activated,suspended,quarantined,revoked,retired),
  state: enum(planned,abandoned,quarantined,accepted,activated,suspended,revoked,retired,destroyed),
  authority_sha256: hash,
  transition_evidence_sha256: hash?,
  origin_commitment_sha256: hash?,
  terminal_disposition_sha256: hash?,
  custody_receipt_hashes: [hash,4],
  passphrase_holder_record_hashes: [hash,4],
  reason_codes: [ascii(64),32],
  effective_at: ts,
  content_hash: hash
}

lifecycle_registry = {
  schema_version: literal(conclave-stage21c-key-lifecycle-registry/0.1.0),
  repository_id: literal(1335850028),
  previous_registry_sha256: hash?,
  previous_checkpoint_sha256: hash?,
  ordered_event_hashes: [hash,10000],
  latest_sequence: count,
  generated_at: ts,
  content_hash: hash
}

lifecycle_checkpoint = {
  schema_version: literal(conclave-stage21c-key-lifecycle-checkpoint/0.1.0),
  repository_id: literal(1335850028),
  registry_sha256: hash,
  previous_checkpoint_sha256: hash?,
  latest_sequence: count,
  latest_event_sha256: hash?,
  governance_profile_sha256: hash,
  signed_at: ts,
  arthur_signature_base64url: ascii(86),
  independent_witness_signature_base64url: ascii(86),
  content_hash: hash
}

lifecycle_governance_profile = {
  schema_version: literal(conclave-stage21c-key-lifecycle-governance-profile/0.1.0),
  repository_id: literal(1335850028),
  base_ref: literal(refs/heads/main),
  events_path: literal(docs/governance/stage-21c-key-lifecycle/events/),
  registry_path: literal(docs/governance/stage-21c-key-lifecycle/REGISTRY.json),
  checkpoint_path: literal(docs/governance/stage-21c-key-lifecycle/CHECKPOINT.json),
  governance_signature_profile_sha256: hash,
  required_review_count: id,
  content_hash: hash
}
```

An individual authority is permitted only for a genuinely single-key later
transition. A ceremony reservation, acceptance, abandonment, or quarantine uses
one batch authority containing exactly the control then human proposal hashes;
both proposals share ceremony ID and expected protected-main state. Arthur signs
the batch using domain `CONCLAVE-STAGE21C-LIFECYCLE-BATCH-AUTHORITY-V1`.
One repository-wide audit/compromise batch may contain up to 10,000 proposal
hashes, exactly one for every affected key across ceremonies, sorted by ceremony
ID then purpose; it publishes all events and one checkpoint atomically. Partial
coverage, splitting one incident across commits, or exceeding the bound fails
and requires a separately governed emergency disable outside this plan.
Every lifecycle authority signature uses its literal domain—
`CONCLAVE-STAGE21C-LIFECYCLE-EVENT-AUTHORITY-V1` for individual or the batch
domain above—one zero byte, then canonical JSON with
`arthur_signature_base64url` and `content_hash` absent.

The authority binds already immutable proposal(s) and expected protected-main
state, so the final event can contain the authority hash without a cycle. Every
final event copies the proposal fields exactly. The first event has null
predecessor; every later event names the prior event, sequence increases by one,
and the registry lists hashes in sequence order. A public fingerprint is null
only before a key is known. The checkpoint signatures use ASCII domain
`CONCLAVE-STAGE21C-LIFECYCLE-CHECKPOINT-V1`, one zero byte, then canonical JSON
with both signature fields and `content_hash` absent.

The repository has a separately frozen empty genesis registry/checkpoint:
`ordered_event_hashes` is expressly empty, latest sequence is zero, latest
event is null, and both predecessors are null. Every first proposal binds those
existing genesis hashes.

Publication performs compare-and-append: the PR base commit, checkpoint, and
registry must equal the proposal(s) and authority; the proposed tree adds
exactly one later event or exactly two ceremony-batch events at
`<sequence>-<content-hash>.json`, preserves all prior events, and
updates only registry and checkpoint. Any advanced base, duplicate proposal,
replayed authority, sequence reuse, alternative next event, competing head,
signature mismatch, or changed protection aborts. Resolution requires a new
proposal and authority against the actual current protected-main checkpoint;
automatic retry or fork choice is prohibited.

After merge, current state is selected only by reading the three fixed paths
from the new protected-main head, verifying ordered Git history from the
expected predecessor, both checkpoint signatures, complete event availability,
registry reconstruction, and exact merge-tree equality. The new checkpoint
supersedes exactly its predecessor. A missing, rolled-back, forked,
discontinuous, conflicting, multiply current, or over-capacity state fails
closed. Every consumer binds the selected protected-main commit and checkpoint
hash; cached or merely higher sequence numbers have no authority.

Lifecycle states `planned`, `accepted`, and `activated` have an empty reason
array. Every other state has at least one reason code. `accepted` requires the
exact accepted ceremony completion, origin commitment, four custody receipts, and
four passphrase-holder records in the proposal and event; `activated` requires a
later exact trust-authorization and activation decision not authorized here.

The only allowed transitions are `none→planned`; `planned→abandoned`,
`planned→quarantined`, or `planned→accepted`; `accepted→activated`,
`accepted→suspended`, or `accepted→revoked`; `activated→suspended` or
`activated→revoked`; `suspended→activated` or `suspended→revoked`;
`abandoned→retired`; `quarantined→retired`; `revoked→retired`; and
`retired→destroyed`. No other edge exists. `transition_evidence_sha256` is null
only for `planned`: it names the completion record for `accepted`, the abort
record for `abandoned` or `quarantined`, and
the exact audit, compromise, trust, retirement, or destruction evidence for
later states. `origin_commitment_sha256` is non-null for `accepted`; for
`abandoned` or `quarantined` it is non-null only if origin authentication
succeeded and otherwise null with reason `ORIGIN_AUTHENTICATION_FAILED`. It is
null for other states. Both custody arrays
have exactly four hashes for `accepted` and are empty otherwise. For `planned`,
the public key, transition evidence, origin, terminal-disposition, and both
custody arrays are null or empty as applicable;
for `abandoned`, a public key may be null only when no seed was created.
Terminal disposition is non-null for `abandoned`, `quarantined`, `revoked`,
`retired`, and `destroyed`; it is null for `planned`, `accepted`, `activated`,
and `suspended`, where suspension evidence remains in transition evidence.
These cardinality and nullability rules are identical for proposal and event
and are validated before authority issuance.

Before drafting, accepting, activating, loading, or build-pinning a trust
authorization, the governed process must load the exact current registry and
reject any matching ceremony ID, key ID, or public fingerprint whose latest
state is `quarantined`, `suspended`, `revoked`, `retired`, or `destroyed`.
Registry unavailability is never interpreted as absence. The manifest binds a
base checkpoint; two `planned` events are then appended atomically under one
batch authority. The manifest and execution authorization bind both exact event
hashes, and pre-gate positively verifies their ceremony ID, purposes, key IDs,
`planned` state, current registry membership, and latest-state selection.
Arthur's execution authorization binds the resulting protected-main commit and
checkpoint. Pre-gate verifies they remain current. Abort or completion produces
event proposals only after public evidence exists; later separately authorized
publication appends `abandoned`/`quarantined` events or, after Arthur accepts a
completed ceremony, `accepted` events. No ceremony process mutates Git.

Suspected disclosure after a completed ceremony immediately suspends use. A
later trust authorization must be set to `revoked`, or a planned authorization
must be abandoned, under a separate Arthur decision. No replacement key inherits
trust, key ID, validity, signature, or authorization. Replacement requires a new
ceremony ID, fresh manifest, fresh authorization, fresh key IDs, new media, and
new key material.

Loss of either primary medium does not authorize use of recovery material.
Recovery requires the purpose-specific recovery-media custodian and recovery-
passphrase holder, who must be distinct, plus a separate Arthur authorization
and independent witness. The offline event verifies both custody chains and
produces a secret-free recovery record. No primary custodian or primary-
passphrase holder may satisfy that recovery quorum. Loss of
both copies is terminal key loss; the correct response is revocation and a new
ceremony, never reconstruction from logs or partial material.

Recovery is limited to `verify_only` or reconstruction of one replacement
primary envelope on a new, separately authorized medium. It can never produce
a Stage 21C signature, export plaintext, change purpose, replace a recovery
envelope, or activate trust. Its closed authority and result are:

```text
schema_version: literal(conclave-stage21c-key-recovery-authorization/0.1.0)
repository_id: literal(1335850028)
expected_main_commit: ascii(64)
purpose: enum(control_attestor,human_authorizer)
key_id: ascii(128)
public_key_sha256: hash
current_custody_register_sha256: hash
current_custody_checkpoint_sha256: hash
recovery_media_binding_sha256: hash
replacement_primary_media_binding_sha256: hash?
replacement_primary_media_custodian_principal_id: ascii(128)?
replacement_primary_passphrase_holder_principal_id: ascii(128)?
replacement_storage_location_commitment_sha256: hash?
replacement_seal_policy_sha256: hash?
action: enum(verify_only,reconstruct_primary_envelope)
operator_principal_id: ascii(128)
recovery_media_custodian_principal_id: ascii(128)
recovery_passphrase_holder_principal_id: ascii(128)
witness_principal_id: ascii(128)
origin_authentication_profile_sha256: hash
governance_signature_profile_sha256: hash
frozen_plan_sha256: hash
recovery_tool_bundle_sha256: hash
recovery_tool_executable_sha256: hash
dependency_inventory_sha256: hash
environment_image_sha256: hash
host_profile_sha256: hash
expected_boot_measurement_sha256: hash
device_monitor_profile_sha256: hash
device_monitor_executable_sha256: hash
key_envelope_profile_sha256: hash
custody_media_encryption_profile_sha256: hash
passphrase_profile_sha256: hash
boot_measurement_verifier_sha256: hash
post_secret_authenticator_inventory_sha256: hash
public_export_filesystem_profile_sha256: hash
not_before: ts
expires_at: ts
signing_authorized: literal(false)
plaintext_export_authorized: literal(false)
issued_at: ts
arthur_signature_base64url: ascii(86)
content_hash: hash

schema_version: literal(conclave-stage21c-key-recovery-witness/0.1.0)
recovery_authorization_sha256: hash
operator_principal_id: ascii(128)
witness_principal_id: ascii(128)
current_head_verified: literal(true)
fresh_boot_verified: literal(true)
network_absence_observed: literal(true)
pre_origin_device_monitor_snapshot_sha256: hash
cleanup_evidence_sha256: hash
terminal_disposition_sha256: hash?
observed_at: ts
result: enum(pass,failed_quarantined)
reason_codes: [ascii(64),32]
content_hash: hash

schema_version: literal(conclave-stage21c-key-recovery-result/0.1.0)
recovery_authorization_sha256: hash
source_custody_receipt_sha256: hash
source_envelope_sha256: hash
replacement_envelope_sha256: hash?
replacement_media_binding_sha256: hash?
recovery_custody_receipt_sha256: hash?
public_key_sha256: hash
readback_verified: bool
custody_register_before_sha256: hash
custody_checkpoint_before_sha256: hash
custody_register_after_sha256: hash?
custody_checkpoint_after_sha256: hash?
terminal_state: enum(verified,reconstructed,failed_quarantined)
reason_codes: [ascii(64),32]
witness_record_sha256: hash
completed_at: ts
content_hash: hash

schema_version: literal(conclave-stage21c-recovery-custody-receipt/0.1.0)
recovery_authorization_sha256: hash
replacement_media_binding_sha256: hash
replacement_envelope_sha256: hash
replacement_passphrase_holder_principal_id: ascii(128)
replacement_passphrase_holder_record_sha256: hash
custody_receipt_preimage_sha256: hash
physical_receipt_artifact_sha256: hash
content_hash: hash

schema_version: literal(conclave-stage21c-key-recovery-origin-commitment/0.1.0)
recovery_result_sha256: hash
recovery_authorization_sha256: hash
custody_checkpoint_before_sha256: hash
custody_checkpoint_after_sha256: hash
operator_principal_id: ascii(128)
operator_key_id: ascii(128)
operator_signature_base64url: ascii(86)
witness_principal_id: ascii(128)
witness_key_id: ascii(128)
witness_signature_base64url: ascii(86)
signed_at: ts
content_hash: hash

schema_version: literal(conclave-stage21c-key-recovery-completion/0.1.0)
recovery_result_sha256: hash
recovery_origin_commitment_sha256: hash
terminal_device_interval_evidence_sha256: hash
final_public_file_inventory_sha256: hash
completed_at: ts
status: literal(completed)
content_hash: hash
```

Arthur signs recovery authority using domain
`CONCLAVE-STAGE21C-RECOVERY-AUTHORIZATION-V1`, one zero byte, then canonical JSON
with `arthur_signature_base64url` and `content_hash` absent. Verification requires the exact
current protected-main commit/register/checkpoint, signer trust, time window,
reviewed tool/environment, fresh TPM quote, closed system/network controls,
continuous device monitor, and both profile hashes before unlock. The
replacement holder is null for `verify_only` and otherwise mandatory, distinct
from the separately named replacement-media custodian, all other media
custodians, operator, witness, and recovery holder. For reconstruction, the
replacement custodian, holder, media binding, storage commitment, and seal
policy are all non-null and authenticated by Arthur before any replacement
secret is created; for verify-only they are null. Fresh volume
and envelope passphrases are generated under §7, confirmed once, separately
sealed, and never reused.
The reconstruction receipt binds the ordinary passphrase-holder record with its
outer and two inner seal IDs and storage commitment, so both new secrets enter
the same custody ledger as the replacement medium.

For `verify_only`, both replacement fields and the recovery-receipt hash are
null and the custody-register
and checkpoint hashes are equal. For `reconstructed`, both replacement fields
and the recovery-receipt hash are non-null, a new custody receipt and atomically
published register/checkpoint
version are mandatory, and the source recovery package returns to its original
sealed state. Any failure quarantines every attached medium, creates terminal
dispositions, suspends the key, and permits no retry under the same authority.
For `failed_quarantined`, both after hashes are null unless an authorized
custody `suspend` update actually merged; the terminal-disposition hash in the
recovery-witness record is mandatory. The witness record, recovery receipt,
cleanup record, and device-interval record are closed objects above and are all
covered by recovery failure-injection acceptance.
The recovery result is completed before its origin commitment and therefore
cannot contain that later hash. Recovery origin authentication uses two distinct
pre-existing keys and the same canonical dual-signature construction as §13,
with ASCII domain `CONCLAVE-STAGE21C-RECOVERY-ORIGIN-V1`, one zero byte, then
canonical JSON of the recovery-origin object with both signature fields and
`content_hash` absent. This ordering is acyclic: authority → result → origin.
For reconstruction the fuller ordering is: authority → replacement envelope →
recovery custody receipt → authorized custody update and merged checkpoint →
recovery result → recovery origin. No object points to a later object.
The recovery witness binds the interval only through pre-origin cleanup and
detachment. Origin devices are then attached, signatures are made, and all
devices detach. The monitor optically emits the signed terminal interval as in
§13; a governed workstation constructs the recovery completion from result,
origin, terminal interval, and export inventory. The recovery result never
claims terminal completion, so this ordering has no backward reference.

The protected-main boundary divides reconstruction into two fresh offline
sessions. Phase one creates and seals the replacement, completes cleanup and a
terminal device interval, exports only the signed receipt/update proposal, and
shuts down. An external governed workstation publishes and verifies the custody
update. Phase two requires a fresh measured boot and a freshly sanitized public
transfer medium named in the recovery authority; it imports only the verified
main commit, merge tree, register, checkpoint, and publication proof under a
closed allowlist. It never decrypts either envelope. A closed pause record binds
the authorization, phase-one interval/cleanup, receipt, proposal, transfer-media
binding, and expected candidate checkpoint; a closed resume record binds the
pause hash, fresh phase-two boot, exact merged head/tree/checkpoint, import
inventory, and a new terminal interval. Stale, altered, additional, or missing
input fails without resume. Thus no live network or resumed secret-bearing
process crosses the boundary.

```text
recovery_pause_record = {
  schema_version: literal(conclave-stage21c-recovery-pause/0.1.0),
  recovery_authorization_sha256: hash,
  recovery_custody_receipt_sha256: hash,
  custody_update_proposal_sha256: hash,
  expected_candidate_checkpoint_sha256: hash,
  transfer_media_binding_sha256: hash,
  export_inventory_sha256: hash,
  cleanup_evidence_sha256: hash,
  device_interval_evidence_sha256: hash,
  paused_at: ts,
  content_hash: hash
}

recovery_resume_record = {
  schema_version: literal(conclave-stage21c-recovery-resume/0.1.0),
  recovery_pause_record_sha256: hash,
  observed_boot_measurement_sha256: hash,
  merged_main_commit: ascii(64),
  merged_tree: ascii(64),
  custody_register_sha256: hash,
  custody_checkpoint_sha256: hash,
  publication_proof_sha256: hash,
  import_inventory_sha256: hash,
  terminal_device_interval_sha256: hash,
  resumed_at: ts,
  content_hash: hash
}
```

An accepted, activated, or suspended key requires revocation before retirement.
An abandoned or quarantined key may retire directly because it never acquired
trust. Every retirement still requires confirmation that no current trust
authorization selects the key, cryptographic erasure where reliable, and an
authorized destruction plan. `destroyed` follows only after physical
destruction of all applicable custody and recovery media. The lifecycle event
and terminal disposition retain key ID, public fingerprint when known, reason,
authority, date, media outcomes, and destruction evidence without secrets.

## 16. Plan review and later tool acceptance evidence

Council review of this exact draft shall answer at least:

1. **Governance:** Does the plan keep key creation, trust authorization,
   activation, runtime implementation, and live operation as separate gates?
2. **Cryptography:** Are Ed25519 generation, public encoding, fingerprinting,
   proof-of-possession domains, and purpose separation closed and compatible
   with frozen Stage 21C?
3. **Custody:** Are media, passphrases, backups, handoff, recovery, revocation,
   retirement, and SSD limitations fail-closed and institutionally operable?
4. **Security:** Can any secret escape through logs, clipboard, swap, crashes,
   telemetry, evidence, Git, chat, CI, or the public result?
5. **Testability:** Can an exact reviewed tool and offline environment prove the
   procedure, bounds, negative cases, cleanup, and secret-free result without
   generating real keys during plan review?

Before the tool can be authorized for a real ceremony, its fixture and
disposable-key suite must pass on Windows/Python 3.12, Ubuntu/Python 3.12 and
3.13, and macOS/Python 3.12. The exact ceremony execution still uses only the
single environment image named in its manifest. Cross-platform tests establish
format and verifier portability; they do not permit multiple ungoverned
ceremony environments.

The later tool review retains this exact closed record:

```text
acceptance_inventory = {
  schema_version: literal(conclave-stage21c-acceptance-inventory/0.1.0),
  role: enum(golden_vectors,rejection_vectors,failure_injections,packages,
             static_scan,secret_leak_scan),
  ordered_item_hashes: [hash,10000],
  item_count: id,
  expected_case_ids_sha256: hash,
  content_hash: hash
}

acceptance_case = {
  schema_version: literal(conclave-stage21c-acceptance-case/0.1.0),
  case_id: ascii(128),
  category: enum(golden,rejection,failure_injection,static_scan,secret_leak),
  input_fixture_sha256: hash,
  expected_status: enum(pass,fail,aborted,quarantined),
  expected_schema_version: ascii(128),
  expected_reason_codes: [ascii(64),32],
  expected_output_sha256: hash?,
  content_hash: hash
}

acceptance_artifact = {
  schema_version: literal(conclave-stage21c-acceptance-artifact/0.1.0),
  platform_tuple: ascii(128),
  junit_xml_sha256: hash,
  junit_byte_count: id,
  inventory_hashes: [hash,6],
  collected_case_ids_sha256: hash,
  result: literal(pass),
  content_hash: hash
}

platform_result = {
  os: enum(windows,ubuntu,macos),
  os_version_sha256: hash,
  python_version: enum(3.12,3.13),
  architecture: enum(x86_64,arm64),
  tool_executable_sha256: hash,
  verifier_executable_sha256: hash,
  dependency_inventory_sha256: hash,
  tests_collected: id,
  tests_passed: id,
  tests_failed: literal(0),
  tests_skipped: literal(0),
  tests_xfailed: literal(0),
  golden_vectors_passed: id,
  failure_injections_passed: id,
  artifact_sha256: hash
}

schema_version: literal(conclave-stage21c-key-ceremony-tool-acceptance/0.1.0)
frozen_plan_sha256: hash
tool_bundle_sha256: hash
tool_source_commit: ascii(128)
tool_source_tree: ascii(128)
build_recipe_sha256: hash
dependency_lock_sha256: hash
key_envelope_profile_sha256: hash
passphrase_profile_sha256: hash
verifier_bundle_sha256: hash
golden_vector_inventory_sha256: hash
rejection_vector_inventory_sha256: hash
failure_injection_inventory_sha256: hash
platform_results: [platform_result,4]
secret_leak_scan_sha256: hash
static_scan_sha256: hash
package_inventory_sha256: hash
result: literal(pass)
created_at: ts
content_hash: hash
```

There are exactly four platform results: Windows/Python 3.12,
Ubuntu/Python 3.12, Ubuntu/Python 3.13, and macOS/Python 3.12. Architecture is
the actual runner architecture and may differ only through a separately
reviewed acceptance revision. Every test is mandatory. On each platform,
`tests_collected == tests_passed > 0`; vector and injection counts are nonzero
and equal their closed inventory counts; the collected case-ID hash equals the
union of required inventories. Each of the six inventory hashes resolves to the
matching `acceptance_inventory`, and every artifact hash resolves to the closed
`acceptance_artifact`. Missing, duplicate, extra, or zero coverage fails.
Every inventory item is an exact `acceptance_case`. Case IDs are unique ASCII;
the case-ID digest is SHA-256 over canonical JSON of the enum-ordered, then
ASCII-case-ID-sorted array of strings. The collected digest uses the identical
algorithm over executed IDs. All four platform artifacts bind the same exact
six top-level inventory hashes; their union and counts must be identical.

Golden vectors cover every canonical JSON object, deterministic CBOR envelope,
AAD construction, primary/recovery decrypt-and-readback path, public encoding,
proof message, signature, content hash, registry chain, origin commitment, and
file inventory. Rejection vectors cover duplicate members, unknown fields,
wrong primitive type, overflow, oversize, invalid Unicode, non-NFC text,
noncanonical timestamps, noncanonical base64url, malformed lengths, alternate
CBOR integer forms, indefinite CBOR, unknown tags, reordered or duplicate CBOR
keys, altered AAD, wrong tag, trailing bytes, and cross-purpose substitution.

Failure injections cover every pre-gate predicate and every transition in the
§15 table, including first-key success followed by second-key failure, storage
failure, power loss, tool crash, unproven cleanup, stale TPM quote, wrong
firmware, media swap, composite or re-enumerated USB, export media attached
early, route or interface present, profile mismatch, biased passphrase sampler,
passphrase reuse, registry unavailable/conflicting, verifier mismatch, forged
or same-key origin signatures, extra export file, and interrupted handoff. Each
fixture has one expected terminal schema, state, reason set, registry delta,
key-ID disposition, and media disposition. Any other outcome fails acceptance.
They also cover recovery verify-only, reconstruction, new-passphrase generation,
wrong passphrase, source corruption, stale custody head, failed fresh boot,
network/interface appearance, replacement write/readback failure, interrupted
custody publication, cleanup failure, and every `failed_quarantined` nullability
branch. The recovery tool is built, pinned, and cross-platform tested under the
same acceptance record; ceremony acceptance without those cases fails.

The acceptance `secret_leak_scan_sha256` names a canonical inventory and scan
result covering every source file, fixture, generated log, exception, result,
abort, witness object, exported artifact, built package, executable string
table, and CI artifact. Tests inject unique synthetic secret sentinels into
every secret-bearing boundary and prove those sentinels absent from every
forbidden output. This is a bounded test assertion about the reviewed build,
not a universal claim that an operating system can never copy memory.

Every reviewer binds the exact candidate SHA-256 and Git blob and returns only
`PASS_EXACT_DRAFT` or `FAIL_EXACT_DRAFT` with findings. Any byte change after
review invalidates all verdicts.

Plan review uses fixtures and disposable test keys only. Real Stage 21C key
generation is prohibited during plan review and tool testing.

## 17. Sequence after a 5/5 review

A unanimous Council pass does not freeze or execute this plan. The governed
order is:

1. Arthur freezes the exact plan bytes by SHA-256 and Git blob.
2. A separate tool protocol and implementation are reviewed against the frozen
   plan using disposable test keys only.
3. Arthur approves an exact ceremony manifest and execution window.
4. The offline ceremony occurs and produces only encrypted custody packages and
   the secret-free result.
5. Independent reviewers validate the public result and custody evidence.
6. Arthur separately accepts or rejects the completion record, its result, and
   origin commitment, but only after the initial custody update has merged and
   the protected-main custody checkpoint is verified current.
7. If accepted, one immutable public-facts proposal per key is constructed. It
   contains every eventual trust-authorization member except
   `arthur_decision_sha256`, plus the current lifecycle-registry hash. Its hash
   is independently verified.
8. Arthur issues one external issuance decision per proposal. The decision
   binds the proposal hash, key purpose, repository, principal, key ID, public
   key, protocol hashes, validity interval, lifecycle-registry hash, and status.
   It does not reference the not-yet-created trust-authorization hash. This
   issuance decision's own SHA-256 is exactly the value later placed in
   `arthur_decision_sha256`.
9. Only after that decision exists is the canonical Stage 21C trust-
   authorization object constructed by copying the proposal fields and the
   issuance-decision hash. Independent verification proves exact equality and
   computes the completed trust-authorization hash.
10. A separate Arthur acceptance/build-pin decision may then name that completed
    hash and its exact destination. It cannot alter the issuance decision or
    canonical object and is not the value stored in `arthur_decision_sha256`.
    Activation remains later and separately authorized. This sequence is
    acyclic: proposal → issuance decision → trust object → acceptance/build pin.
11. External collector, verifier/signer, trust store, Stage 21C runtime, live
   credentials, and any live exercise continue only under the remaining
   separately governed gates in the frozen collection protocol.

The public-facts proposal in step 7 is exactly:

```text
schema_version: literal(conclave-stage21c-trust-authorization-proposal/0.1.0)
purpose: enum(control_attestor,human_authorizer)
stage_21c_protocol_sha256: hash
repository_id: literal(1335850028)
principal_id: ascii(128)
key_id: ascii(128)
public_key_base64url: ascii(43)
public_key_sha256: hash
collection_protocol_sha256: hash?
not_before: ts
expires_at: ts
status: literal(active)
ceremony_completion_sha256: hash
ceremony_origin_commitment_sha256: hash
lifecycle_registry_sha256: hash
created_at: ts
content_hash: hash
```

Its first eleven trust fields copy exactly into the frozen Stage 21C trust-
authorization object; the ceremony and registry fields remain proposal evidence
and do not extend that frozen schema. `collection_protocol_sha256` is non-null
only for `control_attestor`. The issuance decision binds the entire proposal
hash, so omission or substitution of ceremony evidence is impossible without a
different decision.

## 18. Explicitly unauthorized by this draft

This draft does not authorize:

- key generation, test generation of real-purpose keys, proof signing, or use;
- selection or disclosure of a passphrase;
- custody-media preparation, mounting, erasure, or destruction;
- trust authorization, key activation, key import, or key-provider deployment;
- runtime or test changes in CONCLAVE;
- GitHub credentials, App creation or installation, token minting, or live API
  calls by the adapter or collector;
- branch creation, commit, push, pull request, merge, protection change, or
  repository visibility change;
- Stage 21D, deployment, or production use;
- KOS or IDM changes; or
- signing, identity allocation, or membership activation outside the two
  future proof-of-possession operations expressly governed here.

## 19. Current disposition

This file is a local drafting candidate prepared after PR #25 merged to
protected `main`. Council Review 0001 rejected its exact predecessor at
SHA-256 `a6fb191334c66837cb201d7896f79f552e48ec46a9c18df20774528f3ca3058b`
and Git blob `f27fb8979226a95ed92b351bb8ab6822714f3c91` with `1/5
PASS_EXACT_DRAFT / 4/5 FAIL_EXACT_DRAFT`. That review remains immutable history
and no verdict carries to these remediated bytes. This successor is not frozen.
No ceremony tool or execution manifest has been approved. No key, passphrase,
signature, custody package, trust authorization, credential, or live GitHub
operation was created or accessed while remediating it.

The next permitted action is technical review of these exact draft bytes. Any
commit, push, Council review, freeze, tool implementation, or ceremony execution
requires its own explicit authorization.
