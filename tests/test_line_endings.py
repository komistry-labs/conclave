"""CRLF regression suite — byte-level fixtures, independent of the host OS.

Every fixture here writes BYTES. `Path.write_text()` performs newline
translation, so a test written with it exercises LF on Linux and CRLF on
Windows and silently tests something different on each. That is exactly how
the v0.1.0 blocker reached a release: 517 tests passed on Linux while
`relay import` was inoperable on Windows.

These tests exercise LF and CRLF explicitly and give the same result on every
platform.
"""

import yaml
import pytest

from conclave.handoff import (
    HandoffPacket,
    decode_raw,
    extract_yaml_block,
    import_response,
    normalise_line_endings,
    preserve_raw,
    verify_handoff_content_hash,
)
from conclave.hashing import hash_bytes, hash_file
from conclave.relay import export_prompts
from conclave.scope import review_handoff
from conclave.taskpacket import build_packet, write_packet
from conclave.workspace import Workspace

CRLF = b"\r\n"
LF = b"\n"


@pytest.fixture
def ws(tmp_path):
    return Workspace.create(tmp_path, principal="Arthur")


@pytest.fixture
def config(ws):
    return ws.load_config()


@pytest.fixture
def exported(ws, config):
    packet = build_packet(
        objective="Draft RA-001 Part I", created_by="Arthur",
        target_objects=[{"object_id": "RA-001", "section_id": "RA-001-PART-I"}],
        read_only_objects=[{"object_id": "ADR-0002"}],
        assigned_providers=[{"provider": "claude", "role": "governance_critic"}],
    )
    write_packet(ws, packet)
    export_prompts(ws, packet, config)
    return packet


def response_body(packet, **over):
    body = {
        "handoff_packet": "handoff-packet/0.1.0",
        "packet_ref": packet.ref,
        "packet_content_hash": packet.content_hash,
        "provider": "claude",
        "role": "governance_critic",
        "status": "submitted",
        "objects_touched": [
            {"object_id": "RA-001", "section_id": "RA-001-PART-I",
             "action": "proposed_change"},
        ],
        "output": {"type": "critique", "summary": "s", "body": "line one\nline two\n"},
        "findings": [], "assumptions": [], "abstentions": [],
        "unresolved": [], "evidence_used": [],
        "recommended_next_action": "revise",
    }
    body.update(over)
    return body


def write_reply_bytes(path, packet, *, newline: bytes, prose=b"Here is my reply.\n\n"):
    """Write a provider reply with EXPLICIT line endings. Never write_text()."""
    doc = "```yaml\n" + yaml.safe_dump(response_body(packet), sort_keys=False) + "```\n"
    raw = doc.encode("utf-8")
    if newline != LF:
        raw = raw.replace(LF, newline)
        prose = prose.replace(LF, newline)
    path.write_bytes(prose + raw)
    return path


# -- normalisation ---------------------------------------------------------

@pytest.mark.parametrize("raw,expected", [
    ("a\r\nb", "a\nb"),
    ("a\rb", "a\nb"),
    ("a\nb", "a\nb"),
    ("a\r\n\r\nb", "a\n\nb"),
    ("", ""),
    ("\r\n", "\n"),
])
def test_normalise_line_endings(raw, expected):
    assert normalise_line_endings(raw) == expected


def test_normalise_is_idempotent():
    for s in ("a\r\nb", "a\rb", "a\nb", ""):
        once = normalise_line_endings(s)
        assert normalise_line_endings(once) == once


# -- fence extraction ------------------------------------------------------

@pytest.mark.parametrize("nl", ["\n", "\r\n", "\r"])
def test_fence_extraction_all_line_endings(nl):
    """The v0.1.0 blocker: the closing fence never matched under CRLF."""
    text = f"intro{nl}{nl}```yaml{nl}k: v{nl}```{nl}"
    block, defects = extract_yaml_block(text)
    assert defects == [], [d.code for d in defects]
    assert block.strip() == "k: v"


@pytest.mark.parametrize("nl", ["\n", "\r\n"])
def test_extracted_block_contains_no_carriage_returns(nl):
    """A Windows reply and a Linux reply must yield identical block text."""
    text = f"```yaml{nl}a: 1{nl}b: 2{nl}```{nl}"
    block, _ = extract_yaml_block(text)
    assert "\r" not in block


def test_lf_and_crlf_yield_identical_blocks():
    lf = "```yaml\nk: v\nlist:\n  - one\n```\n"
    block_lf, _ = extract_yaml_block(lf)
    block_crlf, _ = extract_yaml_block(lf.replace("\n", "\r\n"))
    assert block_lf == block_crlf


@pytest.mark.parametrize("nl", ["\n", "\r\n"])
def test_zero_blocks_still_rejected(nl):
    block, defects = extract_yaml_block(f"just prose{nl}no fences{nl}")
    assert block is None
    assert defects[0].code == "no-yaml-block"


@pytest.mark.parametrize("nl", ["\n", "\r\n"])
def test_ambiguity_still_rejected(nl):
    text = f"```yaml{nl}a: 1{nl}```{nl}```yaml{nl}b: 2{nl}```{nl}"
    block, defects = extract_yaml_block(text)
    assert block is None
    assert defects[0].code == "ambiguous-yaml-blocks"


@pytest.mark.parametrize("nl", ["\n", "\r\n"])
def test_tag_preference_preserved(nl):
    text = f"```{nl}noise{nl}```{nl}```yaml{nl}a: 1{nl}```{nl}"
    block, defects = extract_yaml_block(text)
    assert defects == []
    assert block.strip() == "a: 1"


@pytest.mark.parametrize("nl", ["\n", "\r\n"])
def test_other_languages_still_excluded(nl):
    text = f"```python{nl}x = 1{nl}```{nl}```yaml{nl}a: 1{nl}```{nl}"
    block, _ = extract_yaml_block(text)
    assert block.strip() == "a: 1"


# -- raw preservation is unaffected ---------------------------------------

def test_crlf_raw_bytes_preserved_exactly(ws, tmp_path):
    """Normalising for parsing must not touch the evidentiary artifact."""
    body = b"```yaml\r\nstatus: submitted\r\n```\r\n"
    src = tmp_path / "reply.md"
    src.write_bytes(body)
    path, raw_hash, _ = preserve_raw(ws, src)
    assert path.read_bytes() == body
    assert b"\r\n" in path.read_bytes()
    assert raw_hash == hash_bytes(body, binary=True)


def test_lf_and_crlf_remain_distinct_artifacts(ws, tmp_path):
    """Byte-level evidence: the two replies are NOT the same artifact."""
    lf_file, crlf_file = tmp_path / "a.md", tmp_path / "b.md"
    lf_file.write_bytes(b"```yaml\nk: v\n```\n")
    crlf_file.write_bytes(b"```yaml\r\nk: v\r\n```\r\n")
    _, h_lf, _ = preserve_raw(ws, lf_file)
    _, h_crlf, dup = preserve_raw(ws, crlf_file)
    assert h_lf != h_crlf
    assert dup is False


def test_binary_hashing_unchanged(ws, tmp_path):
    body = b"trailing spaces   \r\nand a BOM-free line\r\n"
    src = tmp_path / "r.md"
    src.write_bytes(body)
    path, raw_hash, _ = preserve_raw(ws, src)
    assert raw_hash == hash_bytes(body, binary=True)
    assert hash_file(path, binary=True) == raw_hash


# -- strict UTF-8 validation is unaffected --------------------------------

def test_invalid_utf8_still_rejected(ws, tmp_path):
    src = tmp_path / "bad.md"
    src.write_bytes(b"```yaml\r\nstatus: \xff\xfe\r\n```\r\n")
    text, defects = decode_raw(src)
    assert text is None
    assert defects[0].code == "invalid-response-encoding"


def test_crlf_bom_still_rejected_by_canonical_hashing(ws, tmp_path):
    """A BOM is still an integrity error; CRLF handling did not relax it."""
    from conclave.errors import IntegrityError
    from conclave.hashing import canonicalise
    with pytest.raises(IntegrityError, match="BOM"):
        canonicalise(b"\xef\xbb\xbf```yaml\r\nk: v\r\n```\r\n")


# -- end-to-end import -----------------------------------------------------

@pytest.mark.parametrize("newline", [LF, CRLF], ids=["lf", "crlf"])
def test_import_succeeds_for_both_line_endings(ws, exported, tmp_path, newline):
    """The blocker, stated as a test: a CRLF reply must import."""
    src = write_reply_bytes(tmp_path / "reply.md", exported, newline=newline)
    result = import_response(ws, src)
    assert result.status == "imported", [str(d) for d in result.defects]
    assert result.packet.provider == "claude"
    assert verify_handoff_content_hash(result.packet)


def test_crlf_and_lf_produce_equivalent_handoff_content(ws, exported, tmp_path):
    """Same reply, different editor — the parsed packet must be the same.

    Only the raw_response_hash differs, because the bytes genuinely differed.
    """
    lf_src = write_reply_bytes(tmp_path / "lf.md", exported, newline=LF)
    crlf_src = write_reply_bytes(tmp_path / "crlf.md", exported, newline=CRLF)

    lf_packet = import_response(ws, lf_src).packet
    crlf_packet = import_response(ws, crlf_src).packet

    assert lf_packet.raw_response_hash != crlf_packet.raw_response_hash

    ignore = {"raw_response_hash", "imported_at", "content_hash"}
    a = {k: v for k, v in lf_packet.to_serialisable().items() if k not in ignore}
    b = {k: v for k, v in crlf_packet.to_serialisable().items() if k not in ignore}
    assert a == b


def test_crlf_multiline_scalar_normalised_in_stored_packet(ws, exported, tmp_path):
    """A block scalar authored with CRLF must not carry CRs into the packet."""
    src = write_reply_bytes(tmp_path / "reply.md", exported, newline=CRLF)
    packet = import_response(ws, src).packet
    assert "\r" not in packet.output["body"]
    assert packet.output["body"] == "line one\nline two\n"


def test_stored_handoff_is_lf_from_crlf_source(ws, exported, tmp_path):
    src = write_reply_bytes(tmp_path / "reply.md", exported, newline=CRLF)
    result = import_response(ws, src)
    assert b"\r\n" not in result.handoff_path.read_bytes()


def test_no_fabrication_when_crlf_reply_is_malformed(ws, exported, tmp_path):
    """Line-ending tolerance must not become tolerance for bad content."""
    src = tmp_path / "reply.md"
    src.write_bytes(b"```yaml\r\nstatus: submitted\r\n```\r\n")   # missing every other field
    result = import_response(ws, src)
    assert result.status == "rejected"
    assert result.handoff_path is None
    assert "missing-required-field" in {d.code for d in result.defects}
    assert result.raw_path.read_bytes() == b"```yaml\r\nstatus: submitted\r\n```\r\n"


def test_crlf_provenance_still_verified(ws, exported, tmp_path):
    """A CRLF reply with a forged identifier is still rejected."""
    doc = ("```yaml\n" + yaml.safe_dump(
        response_body(exported, packet_content_hash="sha256:" + "0" * 64),
        sort_keys=False) + "```\n")
    src = tmp_path / "reply.md"
    src.write_bytes(doc.encode("utf-8").replace(LF, CRLF))
    result = import_response(ws, src)
    assert result.status == "rejected"
    assert "packet-hash-mismatch" in {d.code for d in result.defects}


def test_crlf_reply_flows_through_scope_review(ws, exported, tmp_path):
    src = write_reply_bytes(tmp_path / "reply.md", exported, newline=CRLF)
    result = import_response(ws, src)
    outcome = review_handoff(ws, result.handoff_path)
    assert outcome.review.scope_status == "within_scope"


# -- guard against the fixture pattern that hid the defect ----------------

def test_suite_does_not_rely_on_write_text_for_line_ending_tests():
    """This file must never CALL write_text() for a newline-sensitive fixture.

    write_text() translates newlines per platform, so such a fixture tests LF
    on Linux and CRLF on Windows. That is what let the v0.1.0 blocker ship.

    Checked by parsing the AST rather than searching text, so prose about
    write_text — including this docstring — does not trip it.
    """
    import ast
    from pathlib import Path

    tree = ast.parse(Path(__file__).read_bytes().decode("utf-8"))
    offenders = [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "write_text"
    ]
    assert offenders == [], (
        f"write_text() called at line(s) {offenders}; use write_bytes() so the "
        "fixture's line endings are explicit rather than platform-dependent"
    )
