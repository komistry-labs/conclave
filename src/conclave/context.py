"""Immutable, provenance-bearing context bundles."""

from __future__ import annotations

from typing import Literal
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator
import yaml

from .errors import IntegrityError, ValidationError, WorkspaceError
from .hashing import hash_text
from .ledger import canonical_json
from .workspace import Workspace

CONTEXT_SCHEMA_VERSION = "context-bundle/0.1.0"
Classification = Literal["public", "internal", "restricted", "constitutional"]


class ContextSource(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    object_id: str = Field(min_length=1)
    status: str = Field(min_length=1)
    authority: str = Field(min_length=1)
    classification: Classification
    content: str
    content_hash: str

    @model_validator(mode="after")
    def verify_hash(self) -> "ContextSource":
        actual = hash_text(self.content)
        if self.content_hash != actual:
            raise IntegrityError(
                f"context source {self.object_id!r} hash mismatch: "
                f"recorded {self.content_hash}, computed {actual}"
            )
        return self

    @classmethod
    def seal(
        cls, *, object_id: str, status: str, authority: str,
        classification: Classification, content: str,
    ) -> "ContextSource":
        return cls(
            object_id=object_id, status=status, authority=authority,
            classification=classification, content=content,
            content_hash=hash_text(content),
        )


class ContextBundle(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = CONTEXT_SCHEMA_VERSION
    packet_ref: str = Field(min_length=1)
    packet_content_hash: str = Field(min_length=1)
    sources: tuple[ContextSource, ...]
    content_hash: str

    @model_validator(mode="after")
    def verify_bundle(self) -> "ContextBundle":
        identities = [source.object_id for source in self.sources]
        if len(identities) != len(set(identities)):
            raise ValidationError("context source object_id values must be unique")
        actual = compute_bundle_hash(self)
        if self.content_hash != actual:
            raise IntegrityError(
                f"context bundle hash mismatch: recorded {self.content_hash}, computed {actual}"
            )
        return self


def _bundle_body(bundle: ContextBundle) -> dict:
    return bundle.model_dump(mode="json", exclude={"content_hash"})


def compute_bundle_hash(bundle: ContextBundle) -> str:
    return hash_text(canonical_json(_bundle_body(bundle)))


def build_context_bundle(
    *, packet_ref: str, packet_content_hash: str, sources: list[ContextSource],
) -> ContextBundle:
    ordered = tuple(sorted(sources, key=lambda item: item.object_id))
    draft = ContextBundle.model_construct(
        schema_version=CONTEXT_SCHEMA_VERSION,
        packet_ref=packet_ref,
        packet_content_hash=packet_content_hash,
        sources=ordered,
        content_hash="pending",
    )
    return ContextBundle.model_validate({
        **_bundle_body(draft),
        "content_hash": compute_bundle_hash(draft),
    })


def render_context_prompt(bundle: ContextBundle, instruction: str) -> str:
    """Deterministic provider projection of one sealed context bundle."""
    if not instruction.strip():
        raise ValidationError("provider instruction must not be empty")
    lines = [
        "# CONCLAVE governed context",
        "",
        f"packet_ref: {bundle.packet_ref}",
        f"context_bundle_hash: {bundle.content_hash}",
        "",
        "## Sources",
        "",
    ]
    for source in bundle.sources:
        lines.extend([
            f"### {source.object_id}",
            f"status: {source.status}",
            f"authority: {source.authority}",
            f"classification: {source.classification}",
            f"content_hash: {source.content_hash}",
            "",
            source.content,
            "",
        ])
    lines.extend(["## Instruction", "", instruction.strip(), ""])
    return "\n".join(lines)


def context_path(ws: Workspace, bundle: ContextBundle) -> Path:
    task_id, version = bundle.packet_ref.rsplit("@v", 1)
    suffix = bundle.content_hash.split(":", 1)[-1][:12]
    return ws.context_dir / f"{task_id}__v{version}__{suffix}.yaml"


def write_context_bundle(ws: Workspace, bundle: ContextBundle) -> tuple[Path, bool]:
    path = context_path(ws, bundle)
    if path.exists():
        existing = read_context_bundle(path)
        if existing.content_hash != bundle.content_hash:
            raise WorkspaceError(f"different context bundle already exists at {path}")
        return path, False
    path.parent.mkdir(parents=True, exist_ok=True)
    text = yaml.safe_dump(
        bundle.model_dump(mode="json"), sort_keys=False, allow_unicode=True
    )
    path.write_bytes(text.replace("\r\n", "\n").encode("utf-8"))
    return path, True


def read_context_bundle(path: Path) -> ContextBundle:
    if not path.exists():
        raise WorkspaceError(f"no context bundle at {path}")
    return ContextBundle.model_validate(
        yaml.safe_load(path.read_text(encoding="utf-8"))
    )
