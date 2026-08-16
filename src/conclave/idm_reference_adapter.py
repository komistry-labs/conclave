"""Verification-only adapter for the hash-pinned IDM v1 reference build.

The optional ``idm-reference`` distribution is provisioned outside CONCLAVE.
This adapter verifies its retained wheel and source-archive hashes before use.
It exposes no key, signing, issuance, allocation, or broker method.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .evidence import (
    EVIDENCE_CONTEXT,
    EvidenceVerificationFindings,
    IDMEvidenceVerifierReport,
    SignedEvidencePayload,
)
from .identity import (
    FROZEN_IDM_IMPLEMENTATION,
    IDM_BASELINE_SOURCE_SHA256,
    IDM_BASELINE_WHEEL_SHA256,
    IDMVerifierReport,
    VerificationFindings,
)

FIXTURE_EMPTY_REVOCATION_CONTEXT = "conclave-fixture/revocation-state/1.0"


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while block := handle.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


class PinnedIDMReferenceVerifier:
    """Pinned public verifier boundary; deliberately contains no signer API."""

    def __init__(self, *, wheel_path: Path, source_archive_path: Path) -> None:
        self.wheel_path = Path(wheel_path)
        self.source_archive_path = Path(source_archive_path)

    def _assert_distribution(self) -> None:
        if (
            not self.wheel_path.is_file()
            or _file_sha256(self.wheel_path) != IDM_BASELINE_WHEEL_SHA256
        ):
            raise ValueError("installed IDM wheel does not match the frozen baseline")
        if (
            not self.source_archive_path.is_file()
            or _file_sha256(self.source_archive_path) != IDM_BASELINE_SOURCE_SHA256
        ):
            raise ValueError("IDM source archive does not match the frozen baseline")
        # Import only after the retained distribution evidence is verified.
        import idm  # noqa: F401

    @staticmethod
    def _bundle(data: bytes):
        from idm.trust import TrustBundle

        value = json.loads(data.decode("utf-8"))
        bundle = TrustBundle.model_validate(value)
        bundle.validate_delegations()
        return bundle

    @staticmethod
    def _revocations(values: tuple[bytes, ...], bundle, evaluation_time: str):
        from idm.attestation import parse_attestation, verify_attestation
        from idm.revocation import RevocationSet, verify_revocation
        from idm.trust import decode_public_key

        if not values:
            raise ValueError("authoritative revocation evidence is required")
        statements = []
        empty_state_seen = False
        for value in values:
            try:
                statements.append(verify_revocation(value, bundle))
                continue
            except Exception:
                pass
            attestation = parse_attestation(
                value, expected_context=FIXTURE_EMPTY_REVOCATION_CONTEXT
            )
            payload = attestation.payload
            if not isinstance(payload, dict) or set(payload) != {
                "profile", "trust_domain_id", "effective_at", "revoked"
            }:
                raise ValueError("fixture revocation state has an unsupported payload")
            if (
                payload["profile"] != "conclave-fixture-revocation-state/1.0"
                or payload["trust_domain_id"] != bundle.trust_domain_id
                or payload["revoked"] != []
                or payload["effective_at"] > evaluation_time
            ):
                raise ValueError("fixture empty revocation state is not current or empty")
            authority = bundle.find_anchor(attestation.kid)
            if (
                authority is None
                or "revocation.issue" not in authority.scopes
                or "revocation_authority" not in authority.roles
                or payload["effective_at"] < authority.valid_from
                or (
                    authority.valid_until is not None
                    and payload["effective_at"] > authority.valid_until
                )
            ):
                raise ValueError("fixture empty revocation signer is unauthorized")
            verify_attestation(attestation, decode_public_key(authority.public_key))
            empty_state_seen = True
        if not statements and not empty_state_seen:
            raise ValueError("no authoritative revocation state was established")
        return RevocationSet(statements)

    def verify_identity(
        self,
        *,
        artifact: bytes,
        trust_bundle: bytes,
        revocation_evidence: tuple[bytes, ...],
        evaluation_time: str,
        accepted_roles: tuple[str, ...],
        required_role: str | None,
        required_claim: str | None,
        required_scopes: tuple[str, ...],
    ) -> IDMVerifierReport:
        del required_claim  # IDM v1 fixture profile carries no free-form claim evaluator.
        self._assert_distribution()
        from idm.verification import verify_artifact

        bundle = self._bundle(trust_bundle)
        revocations = self._revocations(revocation_evidence, bundle, evaluation_time)
        report = verify_artifact(
            artifact,
            bundle,
            revocations=revocations,
            evaluation_time=evaluation_time,
        )
        roles = sorted({item.role for item in report.signatures if item.issuer_authorized})
        scopes = sorted({scope for item in report.signatures for scope in item.scope})
        signature_ok = bool(report.signatures) and all(
            item.cryptographically_valid for item in report.signatures
        )
        delegation_ok = bool(report.signatures) and all(
            item.anchor_recognized and item.issuer_authorized for item in report.signatures
        )
        role_ok = bool(set(accepted_roles).intersection(roles)) and (
            required_role is None or required_role in roles
        )
        scope_ok = set(required_scopes).issubset(scopes)
        time_ok = not any("time" in error.lower() for error in report.errors)
        revocation_ok = not report.revoked
        findings = VerificationFindings(
            trust=report.trusted,
            signature=signature_ok,
            lineage=report.structurally_valid and report.schema_valid,
            delegation=delegation_ok,
            role=role_ok,
            scope=scope_ok,
            time=time_ok,
            revocation=revocation_ok,
            actor_binding=True,
        )
        codes = []
        for name, code in {
            "trust": "IDM_UNTRUSTED",
            "signature": "SIGNATURE_INVALID",
            "lineage": "LINEAGE_INVALID",
            "delegation": "DELEGATION_INVALID",
            "role": "ROLE_INVALID",
            "scope": "SCOPE_INVALID",
            "time": "TIME_INVALID",
            "revocation": "REVOCATION_INVALID",
        }.items():
            if not getattr(findings, name):
                codes.append(code)
        return IDMVerifierReport(
            implementation=FROZEN_IDM_IMPLEMENTATION,
            trusted=all(findings.model_dump().values()),
            eid=report.entity_id,
            mid=report.manifest_id,
            vid=report.vid,
            trust_domain_id=bundle.trust_domain_id,
            verified_roles=roles,
            verified_scopes=scopes,
            findings=findings,
            reason_codes=sorted(set(codes)),
        )

    def verify_evidence(
        self,
        *,
        envelope: bytes,
        expected_context: str,
        trust_bundle: bytes,
        revocation_evidence: tuple[bytes, ...],
        evaluation_time: str,
        required_role: str,
        required_scope: str,
    ) -> IDMEvidenceVerifierReport:
        self._assert_distribution()
        from idm.attestation import parse_attestation, verify_attestation
        from idm.revocation import RevocationTargetType
        from idm.trust import decode_public_key

        if expected_context != EVIDENCE_CONTEXT:
            raise ValueError("unsupported CONCLAVE evidence context")
        bundle = self._bundle(trust_bundle)
        revocations = self._revocations(revocation_evidence, bundle, evaluation_time)
        attestation = parse_attestation(envelope, expected_context=expected_context)
        payload = SignedEvidencePayload.model_validate(attestation.payload)
        authority = bundle.find_anchor(attestation.kid)
        trust_ok = authority is not None
        signature_ok = False
        if authority is not None:
            verify_attestation(attestation, decode_public_key(authority.public_key))
            signature_ok = True
        identity_ok = bool(authority) and (
            payload.attester_eid == authority.signer_eid
            and payload.attester_mid == authority.signer_mid
        )
        role_ok = bool(authority) and required_role == payload.attester_role and (
            required_role in authority.roles
        )
        scope_ok = bool(authority) and required_scope == payload.asserted_scope and (
            required_scope in authority.scopes
        )
        time_ok = bool(authority) and payload.issued_at <= evaluation_time and (
            payload.expires_at is None or payload.expires_at >= evaluation_time
        ) and authority.valid_from <= payload.issued_at and (
            authority.valid_until is None or payload.issued_at <= authority.valid_until
        )
        revoked = False
        if authority is not None:
            targets: list[tuple[Any, str]] = [
                (RevocationTargetType.KEY, attestation.kid),
                (RevocationTargetType.ENTITY, payload.attester_eid),
                (RevocationTargetType.MANIFEST, payload.attester_mid),
            ]
            if authority.delegation_id is not None:
                targets.append((RevocationTargetType.DELEGATION, authority.delegation_id))
            revoked = any(
                revocations.matches(kind, identifier, at_time=evaluation_time)
                for kind, identifier in targets
            )
        findings = EvidenceVerificationFindings(
            attached_payload=True,
            canonical_cbor=True,
            context=attestation.context == expected_context,
            trust=trust_ok and identity_ok,
            signature=signature_ok,
            delegation=trust_ok,
            role=role_ok,
            scope=scope_ok,
            time=time_ok,
            revocation=not revoked,
            cross_binding=True,
        )
        codes = [
            code for name, code in {
                "trust": "IDM_UNTRUSTED",
                "signature": "SIGNATURE_INVALID",
                "delegation": "DELEGATION_INVALID",
                "role": "ROLE_INVALID",
                "scope": "SCOPE_INVALID",
                "time": "TIME_INVALID",
                "revocation": "REVOCATION_INVALID",
            }.items() if not getattr(findings, name)
        ]
        return IDMEvidenceVerifierReport(
            implementation=FROZEN_IDM_IMPLEMENTATION,
            evidence_id=attestation.evidence_id,
            context=attestation.context,
            trust_domain_id=bundle.trust_domain_id,
            signer_kid=attestation.kid,
            verified_roles=sorted(authority.roles) if authority else [],
            verified_scopes=sorted(authority.scopes) if authority else [],
            payload=payload,
            findings=findings,
            reason_codes=sorted(set(codes)),
        )
