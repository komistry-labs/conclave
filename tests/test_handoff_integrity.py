"""Corrections to Increment 4: raw byte hashing, strict decoding, write-time sealing."""

import pytest

from conclave.errors import ValidationError
from conclave.handoff import (
    HandoffPacket,
    compute_handoff_content_hash,
    decode_raw,
    handoff_filename,
    import_response,
    preserve_raw,
    seal_handoff,
    verify_handoff_content_hash,
    write_handoff,
)
from conclave.hashing import hash_bytes, hash_file
from conclave.workspace import Workspace, utcnow


@pytest.fixture
def ws(tmp_path):
    return Workspace.create(tmp_path, principal="Arthur")


# -- raw bytes are evidentiary --------------------------------------------

def test_crlf_and_lf_raw_responses_are_distinct_artifacts(ws, tmp_path):
    """Canonical hashing would collapse these. The raw artifact must not."""
    lf, crlf = tmp_path / "lf.md", tmp_path / "crlf.md"
    lf.write_bytes(b"same text\nsecond line\n")
    crlf.write_bytes(b"same text\r\nsecond line\r\n")
    _, hash_lf, _ = preserve_raw(ws, lf)
    _, hash_crlf, dup = preserve_raw(ws, crlf)
    assert hash_lf != hash_crlf
    assert dup is False


def test_raw_hash_is_binary_hash_of_exact_bytes(ws, tmp_path):
    src = tmp_path / "r.md"
    body = b"payload with trailing spaces   \r\n"
    src.write_bytes(body)
    path, raw_hash, _ = preserve_raw(ws, src)
    assert raw_hash == hash_bytes(body, binary=True)
    assert hash_file(path, binary=True) == raw_hash


def test_bom_prefixed_response_is_a_distinct_artifact(ws, tmp_path):
    plain, bom = tmp_path / "a.md", tmp_path / "b.md"
    plain.write_bytes(b"text\n")
    bom.write_bytes(b"\xef\xbb\xbftext\n")
    _, h1, _ = preserve_raw(ws, plain)
    _, h2, _ = preserve_raw(ws, bom)
    assert h1 != h2


def test_trailing_whitespace_difference_preserved(ws, tmp_path):
    a, b = tmp_path / "a.md", tmp_path / "b.md"
    a.write_bytes(b"text\n")
    b.write_bytes(b"text\n\n\n")
    _, h1, _ = preserve_raw(ws, a)
    _, h2, _ = preserve_raw(ws, b)
    assert h1 != h2


# -- strict decoding -------------------------------------------------------

def test_decode_rejects_invalid_utf8(ws, tmp_path):
    p = tmp_path / "bad.md"
    p.write_bytes(b"valid start \xff\xfe then garbage")
    text, defects = decode_raw(p)
    assert text is None
    assert defects[0].code == "invalid-response-encoding"


def test_decode_accepts_valid_multibyte(ws, tmp_path):
    p = tmp_path / "ok.md"
    p.write_bytes("café — ✓\n".encode("utf-8"))
    text, defects = decode_raw(p)
    assert defects == []
    assert "café" in text


def test_invalid_utf8_import_preserves_raw_and_requests_repair(ws, tmp_path):
    src = tmp_path / "bad.md"
    body = b"```yaml\nstatus: \xff\xfe\n```\n"
    src.write_bytes(body)
    result = import_response(ws, src)
    assert result.status == "rejected"
    assert {d.code for d in result.defects} == {"invalid-response-encoding"}
    assert result.raw_path.read_bytes() == body     # verbatim, not mangled
    assert result.repair_path.exists()
    assert result.handoff_path is None


def test_invalid_utf8_bytes_stored_without_replacement_characters(ws, tmp_path):
    """errors='replace' would write U+FFFD into the evidentiary artifact."""
    src = tmp_path / "bad.md"
    src.write_bytes(b"\xff\xfe")
    stored = import_response(ws, src).raw_path.read_bytes()
    assert stored == b"\xff\xfe"
    assert "�".encode("utf-8") not in stored


# -- write-time integrity --------------------------------------------------

def _packet(**over):
    data = {
        "packet_ref": "TP-x-0123456789@v1",
        "packet_content_hash": "sha256:" + "a" * 64,
        "provider": "claude",
        "role": "governance_critic",
        "status": "submitted",
        "objects_touched": [{"object_id": "RA-001", "action": "read"}],
        "output": {}, "findings": [], "assumptions": [], "abstentions": [],
        "unresolved": [], "evidence_used": [],
        "recommended_next_action": "revise",
        "raw_response_hash": "sha256:" + "1" * 64,
        "prompt_hash": "sha256:" + "2" * 64,
        "imported_at": utcnow(),
    }
    data.update(over)
    return seal_handoff(HandoffPacket.model_validate(data))


def test_sealed_packet_verifies():
    assert verify_handoff_content_hash(_packet())


def test_unsealed_packet_fails_verification():
    assert not verify_handoff_content_hash(_packet().model_copy(update={"content_hash": None}))


def test_content_hash_excludes_itself():
    p = _packet()
    assert compute_handoff_content_hash(
        p.model_copy(update={"content_hash": "sha256:" + "0" * 64})
    ) == compute_handoff_content_hash(p)


def test_model_copy_leaves_hash_stale():
    """Freezing forces changes through model_copy, which strands the hash."""
    p = _packet()
    changed = p.model_copy(update={"status": "blocked"})
    assert not verify_handoff_content_hash(changed)


def test_write_refuses_unsealed(ws):
    with pytest.raises(ValidationError, match="not sealed"):
        write_handoff(ws, _packet().model_copy(update={"content_hash": None}))


def test_write_refuses_stale_hash(ws):
    p = _packet()
    stale = p.model_copy(update={"status": "blocked"})
    with pytest.raises(ValidationError, match="stale"):
        write_handoff(ws, stale)


def test_write_refuses_stale_hash_on_objects_touched(ws):
    p = _packet()
    stale = p.model_copy(update={"objects_touched": []})
    with pytest.raises(ValidationError, match="stale"):
        write_handoff(ws, stale)


def test_resealing_after_change_permits_write(ws):
    p = _packet()
    resealed = seal_handoff(p.model_copy(update={"status": "blocked"}))
    assert write_handoff(ws, resealed).exists()


def test_write_refuses_overwrite(ws):
    p = _packet()
    write_handoff(ws, p)
    with pytest.raises(ValidationError, match="immutable"):
        write_handoff(ws, p)


def test_filename_uses_raw_response_hash():
    p = _packet()
    assert handoff_filename(p).endswith("__" + "1" * 12 + ".yaml")


# -- pinned submission vocabulary -----------------------------------------

@pytest.mark.parametrize("status", ["submitted", "abstained", "blocked"])
def test_valid_statuses_accepted(status):
    assert _packet(status=status).status == status


@pytest.mark.parametrize("action", ["revise", "accept", "escalate", "abstain"])
def test_valid_next_actions_accepted(action):
    assert _packet(recommended_next_action=action).recommended_next_action == action


@pytest.mark.parametrize("status", ["approved", "ratified", "merged", "COMMISSIONED", ""])
def test_invalid_statuses_rejected(status):
    """KOS lifecycle states are not submission states."""
    with pytest.raises(Exception):
        _packet(status=status)


@pytest.mark.parametrize("action", ["approve", "merge", "commission", "ratify"])
def test_invalid_next_actions_rejected(action):
    with pytest.raises(Exception):
        _packet(recommended_next_action=action)


def test_invalid_status_in_submission_is_a_defect(ws, tmp_path):
    import yaml
    body = {
        "handoff_packet": "handoff-packet/0.1.0",
        "packet_ref": "TP-x-0123456789@v1",
        "packet_content_hash": "sha256:" + "a" * 64,
        "provider": "claude", "role": "governance_critic",
        "status": "approved",
        "objects_touched": [], "output": {}, "findings": [], "assumptions": [],
        "abstentions": [], "unresolved": [], "evidence_used": [],
        "recommended_next_action": "merge",
    }
    src = tmp_path / "r.md"
    src.write_text("```yaml\n" + yaml.safe_dump(body) + "```\n", encoding="utf-8")
    result = import_response(ws, src)
    codes = {d.code for d in result.defects}
    assert "invalid-status" in codes
    assert "invalid-next-action" in codes
