"""Fail-closed public verification runtime provisioning for 20C CLI calls."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from .configuration import FROZEN_IMPLEMENTATION, _safe_record_path
from .errors import ValidationError
from .identity import TrustInputSet
from .idm_reference_adapter import PinnedIDMReferenceVerifier
from .sandbox_transport import _read_trust
from .workspace import Workspace

MAX_PUBLIC_EVIDENCE_BYTES = 8 * 1024 * 1024
WHEEL_SELECTOR = "CONCLAVE_IDM_WHEEL"
SOURCE_SELECTOR = "CONCLAVE_IDM_SOURCE_ARCHIVE"
MAX_DISTRIBUTION_BYTES = 64 * 1024 * 1024


@dataclass(frozen=True)
class OperatorVerificationRuntime:
    public_evidence: dict[str, bytes]
    verifier: PinnedIDMReferenceVerifier


def _distribution_path(value: str, *, expected_name: str | None = None) -> Path:
    try:
        candidate = Path(value)
        if not candidate.is_absolute() or candidate.is_symlink():
            raise ValidationError("PINNED_PUBLIC_VERIFIER_RUNTIME_INVALID")
        info = candidate.lstat()
        if getattr(info, "st_file_attributes", 0) & 0x400:
            raise ValidationError("PINNED_PUBLIC_VERIFIER_RUNTIME_INVALID")
        if not candidate.is_file() or not 1 <= info.st_size <= MAX_DISTRIBUTION_BYTES:
            raise ValidationError("PINNED_PUBLIC_VERIFIER_RUNTIME_INVALID")
        if expected_name is not None and candidate.name != expected_name:
            raise ValidationError("PINNED_PUBLIC_VERIFIER_RUNTIME_INVALID")
        return candidate
    except ValidationError:
        raise
    except Exception as exc:
        raise ValidationError("PINNED_PUBLIC_VERIFIER_RUNTIME_INVALID") from exc


def _public_bytes(ws: Workspace, reference: str) -> bytes:
    try:
        path = _safe_record_path(
            ws, reference, ws.identity_trust_inputs_dir, ("identity", "trust-inputs")
        )
        size = path.stat().st_size
        if size < 1 or size > MAX_PUBLIC_EVIDENCE_BYTES:
            raise ValidationError("PUBLIC_EVIDENCE_SIZE_INVALID")
        return path.read_bytes()
    except ValidationError:
        raise
    except Exception as exc:
        raise ValidationError("PUBLIC_EVIDENCE_UNAVAILABLE") from exc


def load_operator_verification_runtime(
    ws: Workspace, *, trust_input_reference: str
) -> OperatorVerificationRuntime:
    """Load public-only pinned verification inputs; never resolves a broker token."""
    trust, _ = _read_trust(ws, trust_input_reference)
    if not isinstance(trust, TrustInputSet) or not trust.idm_implementation.is_frozen_baseline():
        raise ValidationError("PINNED_PUBLIC_VERIFIER_RUNTIME_INVALID")
    wheel = os.environ.get(WHEEL_SELECTOR)
    source = os.environ.get(SOURCE_SELECTOR)
    if not wheel or not source:
        raise ValidationError("PINNED_PUBLIC_VERIFIER_RUNTIME_UNAVAILABLE")
    references = [trust.trust_bundle, *trust.revocation_evidence, trust.time_evidence]
    public_evidence = {item.reference: _public_bytes(ws, item.reference) for item in references}
    return OperatorVerificationRuntime(
        public_evidence=public_evidence,
        verifier=PinnedIDMReferenceVerifier(
            wheel_path=_distribution_path(
                wheel, expected_name=FROZEN_IMPLEMENTATION.wheel_filename
            ),
            source_archive_path=_distribution_path(source),
        ),
    )
