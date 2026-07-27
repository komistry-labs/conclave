"""Workspace-isolation helpers for tests. Not a test module.

The invariant under test is that CONCLAVE never records or creates a path
outside the workspace it was given — in particular, never a path into the KOS
repository.

Checking that by searching serialised JSON is wrong, and was the v0.1.1 test
defect: `json.dumps` escapes backslashes, so a Windows path stored as
`C:\\Users\\...` appears in the JSON text as `C:\\\\Users\\\\...`. A substring
comparison against the escaped text can never match the unescaped workspace
root, and the assertion fails on Windows for reasons that have nothing to do
with path containment.

These helpers instead walk the structured object, inspect the actual string
values before any escaping, and compare normalised path semantics.

Normalisation matters beyond escaping. A prefix comparison would accept
`C:\\ws\\..\\..\\Windows` as being inside `C:\\ws`, because it starts with the
root. Normalising resolves it to `C:\\Windows`, which is correctly rejected.
"""

from __future__ import annotations

import ntpath
import posixpath
import re
from pathlib import PurePosixPath, PureWindowsPath
from typing import Any, Iterator

# `C:\`, `C:/`, `\\server\share`
_WINDOWS_DRIVE = re.compile(r"^[A-Za-z]:[\\/]")
_WINDOWS_UNC = re.compile(r"^\\\\[^\\]")


def iter_strings(obj: Any) -> Iterator[str]:
    """Yield every string in a nested structure, unescaped.

    Dictionary keys are walked as well as values: a path used as a key is
    still a recorded path.
    """
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for key, value in obj.items():
            yield from iter_strings(key)
            yield from iter_strings(value)
    elif isinstance(obj, (list, tuple, set)):
        for item in obj:
            yield from iter_strings(item)
    # numbers, bools and None carry no path


def looks_absolute(value: str) -> bool:
    """Is this plausibly an absolute path, in either syntax?

    Deliberately narrow. Strings such as `sha256:abc…`, `kos:decision:000005`
    and `RA-001#RA-001-PART-IV` contain colons or separators but are not paths,
    and must not be treated as candidates.
    """
    if not isinstance(value, str) or not value:
        return False
    return (
        value.startswith("/")
        or bool(_WINDOWS_DRIVE.match(value))
        or bool(_WINDOWS_UNC.match(value))
    )


def _flavour(value: str):
    """Which path syntax is this string written in?"""
    if _WINDOWS_DRIVE.match(value) or _WINDOWS_UNC.match(value):
        return PureWindowsPath
    if value.startswith("/"):
        return PurePosixPath
    return None


def _normalise(value: str, flavour) -> str:
    """Collapse `.`, `..` and redundant separators; fold case on Windows."""
    if flavour is PureWindowsPath:
        return ntpath.normcase(ntpath.normpath(value))
    return posixpath.normpath(value)


def is_within(candidate: str, root: Any) -> bool:
    """Does `candidate` resolve to a location inside `root`?

    Semantic containment, not string prefixing. Returns False when the two
    are written in different path syntaxes — a POSIX path recorded on a
    Windows run is foreign by definition and should be reported, not excused.
    """
    if not looks_absolute(candidate):
        return False

    root_text = str(root)
    candidate_flavour = _flavour(candidate)
    root_flavour = _flavour(root_text)

    if candidate_flavour is None or root_flavour is None:
        return False
    if candidate_flavour is not root_flavour:
        return False

    normalised_candidate = candidate_flavour(_normalise(candidate, candidate_flavour))
    normalised_root = candidate_flavour(_normalise(root_text, candidate_flavour))

    if normalised_candidate == normalised_root:
        return True
    return normalised_candidate.is_relative_to(normalised_root)


def classify(value: str, root: Any) -> str:
    """`not-a-path`, `inside` or `outside`."""
    if not looks_absolute(value):
        return "not-a-path"
    return "inside" if is_within(value, root) else "outside"


def foreign_paths(obj: Any, root: Any) -> list[str]:
    """Every absolute path in `obj` that does not resolve inside `root`.

    An empty list is the invariant holding.
    """
    return sorted(
        {s for s in iter_strings(obj) if looks_absolute(s) and not is_within(s, root)}
    )
