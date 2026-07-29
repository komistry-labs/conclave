"""Convert a sealed completed Run Record into a governed Handoff Packet."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .errors import ValidationError
from .execution import RunRecord, read_run_record
from .handoff import (
    HandoffPacket, extract_yaml_block, handoff_filename, parse_block,
    raw_dir, raw_filename, seal_handoff, validate_submission, write_handoff,
)
from .hashing import hash_bytes, hash_text
from .ledger import canonical_json
from .routing import read_route_plan
from .scope import read_handoff
from .taskpacket import read_packet, verify_content_hash
from .workspace import Workspace, utcnow


@dataclass(frozen=True)
class ConversionResult:
    packet: HandoffPacket
    handoff_path: Path
    raw_path: Path
    created: bool


def _submission(record: RunRecord) -> dict[str, Any]:
    if record.response.structured_output is not None:
        submission = dict(record.response.structured_output)
    else:
        block, defects = extract_yaml_block(record.response.text)
        if defects or block is None:
            detail = "; ".join(str(defect) for defect in defects)
            raise ValidationError(f"run response is not a Handoff submission: {detail}")
        submission, defects = parse_block(block)
        if defects or submission is None:
            detail = "; ".join(str(defect) for defect in defects)
            raise ValidationError(f"run response Handoff YAML is invalid: {detail}")
    defects = validate_submission(submission)
    if defects:
        raise ValidationError(
            "run response failed Handoff validation: "
            + "; ".join(str(defect) for defect in defects)
        )
    return submission


def _response_bytes(record: RunRecord) -> bytes:
    if record.response.structured_output is None:
        return record.response.text.encode("utf-8")
    return canonical_json({
        "text": record.response.text,
        "structured_output": record.response.structured_output,
    }).encode("utf-8")


def _preserve_response(ws: Workspace, record: RunRecord) -> tuple[Path, str]:
    body = _response_bytes(record)
    raw_hash = hash_bytes(body, binary=True)
    path = raw_dir(ws) / raw_filename(raw_hash)
    if path.exists():
        if path.read_bytes() != body:
            raise ValidationError(f"raw response hash collision at {path}")
        return path, raw_hash
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    return path, raw_hash


def convert_run(ws: Workspace, run_file: Path) -> ConversionResult:
    record = read_run_record(run_file)
    if record.status != "completed":
        raise ValidationError(
            f"run status is {record.status!r}; only completed runs may become Handoffs"
        )
    task_id, version_text = record.packet_ref.rsplit("@v", 1)
    packet = read_packet(ws, task_id, int(version_text))
    if not verify_content_hash(packet):
        raise ValidationError(f"Task Packet {packet.ref} does not verify")

    matching_routes = []
    for path in ws.routes_dir.glob("*.yaml"):
        route = read_route_plan(path)
        if route.content_hash == record.route_plan_hash:
            matching_routes.append(route)
    if len(matching_routes) != 1:
        raise ValidationError(
            f"expected exactly one stored Route Plan matching {record.route_plan_hash}, "
            f"found {len(matching_routes)}"
        )
    route = matching_routes[0]
    if route.packet_ref != packet.ref:
        raise ValidationError("Run Record Route Plan cites a different Task Packet")
    if record.stage_index >= len(route.stages):
        raise ValidationError("Run Record stage index is outside its Route Plan")
    stage = route.stages[record.stage_index]
    if (record.response.provider, record.role) != (stage.provider, stage.role):
        raise ValidationError("Run Record provider/role does not match its Route Plan stage")

    raw_path, raw_hash = _preserve_response(ws, record)
    submission = _submission(record)
    expected = {
        "packet_ref": packet.ref,
        "packet_content_hash": packet.content_hash,
        "provider": record.response.provider,
        "role": record.role,
    }
    for field, value in expected.items():
        if submission.get(field) != value:
            raise ValidationError(
                f"Handoff field {field!r} is {submission.get(field)!r}, expected {value!r}"
            )

    existing = []
    for path in ws.inbox_dir.glob("*.yaml"):
        handoff = read_handoff(path)
        if getattr(handoff, "run_record_hash", None) == record.content_hash:
            existing.append((path, handoff))
    if existing:
        if len(existing) > 1:
            raise ValidationError("multiple Handoffs cite the same Run Record")
        path, handoff = existing[0]
        raw_path = raw_dir(ws) / raw_filename(handoff.raw_response_hash)
        return ConversionResult(handoff, path, raw_path, False)

    data = dict(submission)
    data.pop("handoff_packet", None)
    data.update({
        "schema_version": HandoffPacket.model_fields["schema_version"].default,
        "raw_response_hash": raw_hash,
        "prompt_hash": hash_text(record.request.prompt),
        "imported_at": utcnow(),
        "run_record_hash": record.content_hash,
        "context_bundle_hash": record.context_bundle_hash,
        "route_plan_hash": record.route_plan_hash,
        "route_stage_index": record.stage_index,
    })
    handoff = seal_handoff(HandoffPacket.model_validate(data))
    path = write_handoff(ws, handoff)
    return ConversionResult(handoff, path, raw_path, True)
