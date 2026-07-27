"""Task Packet identity, hashing, and write-once storage.

Immutability is enforced here, mechanically. `write_packet` refuses to
overwrite an existing version file. There is no update path and no edit
command: revision creates a new packet at the next version, carrying a
`supersedes` reference to its predecessor.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

import yaml

from .errors import ValidationError, WorkspaceError
from .hashing import hash_text
from .models import TaskPacket
from .workspace import Workspace, utcnow

_SLUG_STRIP = re.compile(r"[^a-z0-9]+")
SLUG_MAX = 40
DIGEST_LEN = 10


# -- identity --------------------------------------------------------------

def slugify(text: str) -> str:
    slug = _SLUG_STRIP.sub("-", text.lower()).strip("-")[:SLUG_MAX].strip("-")
    return slug or "task"


def derive_task_id(objective: str, target_object_ids: list[str]) -> str:
    """Derive a deterministic, collision-resistant task_id.

    Deterministic: the same objective and the same target objects always
    produce the same id, so re-issuing an identical task is detectable rather
    than silently duplicated - the write-once store will refuse it.

    Collision-resistant: a 10-hex-digit truncated sha256 over the normalised
    identity payload. Note this is truncated, so it is collision-*resistant*,
    not collision-proof; the store refusing to overwrite is what actually
    guarantees no packet is lost to a collision.

    The timestamp is deliberately NOT part of the digest. Including it would
    make ids non-deterministic, which is the property being asked for.
    """
    payload = "\n".join(
        [objective.strip(), *sorted(t.strip() for t in target_object_ids)]
    )
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:DIGEST_LEN]
    return f"TP-{slugify(objective)}-{digest}"


# -- hashing ---------------------------------------------------------------

def canonical_packet_text(data: dict[str, Any]) -> str:
    """Deterministic serialisation of a packet, excluding content_hash.

    Sorted keys so the bytes do not depend on field insertion order. The
    content_hash field is removed before hashing - a hash cannot cover itself.
    """
    payload = {k: v for k, v in data.items() if k != "content_hash"}
    return yaml.safe_dump(payload, sort_keys=True, allow_unicode=True, default_flow_style=False)


def compute_content_hash(packet: TaskPacket) -> str:
    return hash_text(canonical_packet_text(packet.to_serialisable()))


def seal(packet: TaskPacket) -> TaskPacket:
    """Return a copy with content_hash set. Called once, before writing."""
    return packet.model_copy(update={"content_hash": compute_content_hash(packet)})


def verify_content_hash(packet: TaskPacket) -> bool:
    if not packet.content_hash:
        return False
    return packet.content_hash == compute_content_hash(packet)


# -- storage ---------------------------------------------------------------

def packet_path(ws: Workspace, task_id: str, version: int) -> Path:
    return ws.task_dir(task_id) / f"v{version}.yaml"


def write_packet(ws: Workspace, packet: TaskPacket) -> Path:
    """Write a sealed packet. REFUSES to overwrite.

    This is where immutability stops being a convention and becomes a
    property of the system.
    """
    if not packet.content_hash:
        raise ValidationError("packet is not sealed; call seal() before writing")

    # A sealed packet that was copied-with-changes carries a hash describing
    # the body it no longer has. Refuse it here rather than writing a file
    # whose own hash disproves it.
    if not verify_content_hash(packet):
        raise ValidationError(
            f"content_hash is stale for {packet.ref}: it does not match the packet "
            "body. The packet was modified after sealing. Re-seal it, or build a "
            "revision with build_revision()."
        )

    path = packet_path(ws, packet.task_id, packet.version)
    if path.exists():
        raise WorkspaceError(
            f"{packet.ref} already exists at {path}. Task Packets are immutable "
            "and are never overwritten. To revise, create the next version with "
            "'conclave task revise'."
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    text = yaml.safe_dump(
        packet.to_serialisable(), sort_keys=False, allow_unicode=True, default_flow_style=False
    )
    # Written as canonical UTF-8/LF bytes so the file hashes identically on
    # every platform.
    path.write_bytes(text.replace("\r\n", "\n").encode("utf-8"))
    return path


def read_packet(ws: Workspace, task_id: str, version: int) -> TaskPacket:
    path = packet_path(ws, task_id, version)
    if not path.exists():
        raise WorkspaceError(f"no packet at {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return TaskPacket.model_validate(data)


def list_versions(ws: Workspace, task_id: str) -> list[int]:
    d = ws.task_dir(task_id)
    if not d.is_dir():
        return []
    out = []
    for p in d.glob("v*.yaml"):
        try:
            out.append(int(p.stem[1:]))
        except ValueError:
            continue
    return sorted(out)


def latest_version(ws: Workspace, task_id: str) -> int | None:
    versions = list_versions(ws, task_id)
    return versions[-1] if versions else None


def list_tasks(ws: Workspace) -> list[str]:
    if not ws.tasks_dir.is_dir():
        return []
    return sorted(p.name for p in ws.tasks_dir.iterdir() if p.is_dir())


# -- construction ----------------------------------------------------------

def build_packet(
    *,
    objective: str,
    created_by: str,
    target_objects: list[dict] | None = None,
    read_only_objects: list[dict] | None = None,
    prohibited_objects: list[dict] | None = None,
    assigned_providers: list[dict] | None = None,
    egress: dict | None = None,
    constraints: list[str] | None = None,
    acceptance_criteria: list[str] | None = None,
    interpreted_objective: str | None = None,
    extra: dict[str, Any] | None = None,
) -> TaskPacket:
    """Build and seal a version-1 packet."""
    targets = target_objects or []
    data: dict[str, Any] = {
        "task_id": derive_task_id(objective, [t["object_id"] for t in targets]),
        "version": 1,
        "created_at": utcnow(),
        "created_by": created_by,
        "objective": objective,
        "interpreted_objective": interpreted_objective,
        "target_objects": targets,
        "read_only_objects": read_only_objects or [],
        "prohibited_objects": prohibited_objects or [],
        "assigned_providers": assigned_providers or [],
        "egress": egress or {},
        "constraints": constraints or [],
        "acceptance_criteria": acceptance_criteria or [],
    }
    if extra:
        data.update(extra)
    return seal(TaskPacket.model_validate(data))


def build_revision(previous: TaskPacket, *, reason: str, changes: dict[str, Any]) -> TaskPacket:
    """Build the next version of a task as a NEW immutable packet.

    task_id is inherited - it identifies the logical task and is stable across
    versions. The predecessor is untouched and remains citable at its own ref.
    """
    if not reason.strip():
        raise ValidationError("a revision must state a reason")

    forbidden = {"task_id", "version", "supersedes", "content_hash", "created_at"}
    bad = forbidden & set(changes)
    if bad:
        raise ValidationError(f"a revision may not set these fields directly: {sorted(bad)}")

    data = previous.to_serialisable()
    data.update(changes)
    data.update(
        {
            "task_id": previous.task_id,
            "version": previous.version + 1,
            "created_at": utcnow(),
            "supersedes": previous.ref,
            "revision_reason": reason,
            "content_hash": None,
        }
    )
    return seal(TaskPacket.model_validate(data))
