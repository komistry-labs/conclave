"""Tests for canonical form and content hashing.

The idempotence and cross-platform tests matter most. A canonicalisation that
is not idempotent yields different hashes on repeated application, which would
corrupt the ledger chain silently rather than loudly.
"""

import pytest

from conclave.errors import IntegrityError
from conclave.hashing import (
    canonicalise,
    hash_bytes,
    hash_file,
    hash_text,
    verify_file,
    write_canonical,
)


# -- line endings ----------------------------------------------------------

def test_crlf_and_lf_produce_identical_hashes():
    """The whole point: a Windows checkout must hash like a Linux one."""
    assert hash_bytes(b"line one\r\nline two\r\n") == hash_bytes(b"line one\nline two\n")


def test_lone_cr_normalised():
    assert canonicalise(b"a\rb\r") == b"a\nb\n"


def test_mixed_endings_normalised():
    assert canonicalise(b"a\r\nb\nc\rd") == b"a\nb\nc\nd\n"


# -- trailing newline ------------------------------------------------------

def test_missing_trailing_newline_added():
    assert canonicalise(b"no newline") == b"no newline\n"


def test_multiple_trailing_newlines_collapsed():
    assert canonicalise(b"text\n\n\n\n") == b"text\n"


def test_empty_stays_empty():
    assert canonicalise(b"") == b""


def test_only_newlines_collapses_to_empty():
    assert canonicalise(b"\n\n\n") == b""


# -- whitespace preservation ----------------------------------------------

def test_trailing_whitespace_preserved():
    """Two trailing spaces are a hard line break in Markdown. Do not strip."""
    assert canonicalise(b"hard break  \nnext\n") == b"hard break  \nnext\n"


def test_interior_blank_lines_preserved():
    assert canonicalise(b"a\n\n\nb\n") == b"a\n\n\nb\n"


def test_leading_whitespace_preserved():
    assert canonicalise(b"    indented\n") == b"    indented\n"


# -- refusals --------------------------------------------------------------

def test_bom_is_rejected_not_stripped():
    with pytest.raises(IntegrityError, match="BOM"):
        canonicalise(b"\xef\xbb\xbfhello\n")


def test_invalid_utf8_rejected():
    with pytest.raises(IntegrityError, match="UTF-8"):
        canonicalise(b"\xff\xfe invalid")


def test_valid_multibyte_utf8_accepted():
    raw = "café — naïve ✓\n".encode("utf-8")
    assert canonicalise(raw) == raw


# -- idempotence -----------------------------------------------------------

@pytest.mark.parametrize(
    "raw",
    [
        b"", b"\n", b"\n\n\n", b"a", b"a\n", b"a\r\nb", b"trailing  \n",
        b"  leading\r\n\r\n", "unicode ✓\r\n".encode("utf-8"),
    ],
)
def test_canonicalise_is_idempotent(raw):
    once = canonicalise(raw)
    assert canonicalise(once) == once


# -- hashing ---------------------------------------------------------------

def test_hash_format():
    h = hash_text("hello")
    assert h.startswith("sha256:")
    assert len(h) == len("sha256:") + 64


def test_hash_is_deterministic():
    assert hash_text("same input") == hash_text("same input")


def test_different_content_different_hash():
    assert hash_text("a") != hash_text("b")


def test_binary_is_not_canonicalised():
    """Binary must hash as-is; normalising CRLF in a PNG would corrupt it."""
    raw = b"\x89PNG\r\n\x1a\n\x00\x01"
    assert hash_bytes(raw, binary=True) != hash_bytes(b"\x89PNG\n\x1a\n\x00\x01", binary=True)


def test_binary_bom_bytes_not_rejected():
    assert hash_bytes(b"\xef\xbb\xbf\x00\x01", binary=True)


# -- files -----------------------------------------------------------------

def test_write_canonical_normalises_on_disk(tmp_path):
    p = tmp_path / "out.md"
    returned = write_canonical(p, "written\r\nwith crlf\r\n\r\n\r\n")
    assert p.read_bytes() == b"written\nwith crlf\n"
    assert returned == hash_file(p)


def test_write_canonical_creates_parents(tmp_path):
    p = tmp_path / "deep" / "nested" / "f.md"
    write_canonical(p, "x")
    assert p.exists()


def test_hash_file_matches_hash_bytes(tmp_path):
    p = tmp_path / "f.md"
    p.write_bytes(b"content\r\n")
    assert hash_file(p) == hash_bytes(b"content\n")


def test_verify_file_passes_on_match(tmp_path):
    p = tmp_path / "f.md"
    h = write_canonical(p, "stable")
    verify_file(p, h)


def test_verify_file_raises_on_mismatch(tmp_path):
    p = tmp_path / "f.md"
    write_canonical(p, "original")
    with pytest.raises(IntegrityError, match="hash mismatch"):
        verify_file(p, "sha256:" + "0" * 64)


def test_file_written_crlf_still_verifies(tmp_path):
    """A file saved by hand on Windows must still verify against its hash.

    This is the relay case: content leaves Git, is pasted into a chat window,
    saved by an editor that writes CRLF, and must still hash to the same value.
    """
    p = tmp_path / "relayed.md"
    expected = hash_text("relayed content\nsecond line\n")
    p.write_bytes(b"relayed content\r\nsecond line\r\n")
    verify_file(p, expected)
