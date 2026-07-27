"""Canonical byte form and content hashing.

This is the ONLY place canonicalisation and hashing are implemented. Every
other module imports from here. A second implementation would be a second
source of truth, and the hashes would diverge the first time the two drifted.

Canonical form for text:

    UTF-8
    no BOM
    LF newlines
    exactly one trailing newline (empty content stays empty)
    trailing whitespace PRESERVED

Trailing whitespace is deliberately not stripped. Two trailing spaces are a
hard line break in Markdown, and whitespace inside a fenced code block may be
significant. Canonicalisation must be lossless with respect to meaning; the
trailing-newline rule is the only whitespace normalisation that is safely so.

Hashes are computed on canonical bytes, never on working-tree bytes. This is
what makes an object's hash identical on Windows, macOS and Linux regardless
of how the checkout materialised line endings, and it is what lets a file
relayed through a chat window and saved by hand still verify.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from .errors import IntegrityError

BOM = b"\xef\xbb\xbf"
CANONICALISATION_ID = "kos-canonical-text-v1"
ALGORITHM = "sha256"


def canonicalise(raw: bytes) -> bytes:
    """Return the canonical byte form of text content.

    Raises IntegrityError on a BOM or on invalid UTF-8. Both are refusals
    rather than repairs: a BOM changes the bytes and therefore the hash, and
    silently stripping it would mean two contributors with different editors
    produce the same hash from different files.
    """
    if raw.startswith(BOM):
        raise IntegrityError(
            "content begins with a UTF-8 BOM; canonical form forbids it. "
            "Re-save the file as UTF-8 without BOM."
        )
    try:
        raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise IntegrityError(f"content is not valid UTF-8: {exc}") from exc

    out = raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    stripped = out.rstrip(b"\n")
    # Content that is empty, or consists only of newlines, canonicalises to
    # empty. There is exactly one canonical representation of "no content",
    # so a file of three blank lines hashes identically to an empty file.
    # Anything else ends with exactly one newline.
    return stripped + b"\n" if stripped else b""


def hash_bytes(raw: bytes, *, binary: bool = False) -> str:
    """Hash content. Text is canonicalised first; binary is hashed as-is."""
    payload = raw if binary else canonicalise(raw)
    return f"{ALGORITHM}:{hashlib.sha256(payload).hexdigest()}"


def hash_text(text: str) -> str:
    """Hash a Python string as canonical text."""
    return hash_bytes(text.encode("utf-8"))


def hash_file(path: Path, *, binary: bool = False) -> str:
    """Hash a file's content in canonical form."""
    return hash_bytes(Path(path).read_bytes(), binary=binary)


def write_canonical(path: Path, text: str) -> str:
    """Write text in canonical form and return its content hash.

    All CONCLAVE-authored files go through this. Writing bytes directly
    anywhere else risks emitting content whose hash does not match what a
    later read would compute.
    """
    path = Path(path)
    payload = canonicalise(text.encode("utf-8"))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return hash_bytes(payload)


def verify_file(path: Path, expected_hash: str, *, binary: bool = False) -> None:
    """Raise IntegrityError if a file's canonical hash differs from expected."""
    actual = hash_file(path, binary=binary)
    if actual != expected_hash:
        raise IntegrityError(
            f"content hash mismatch for {path}\n"
            f"  expected: {expected_hash}\n"
            f"  actual:   {actual}"
        )
