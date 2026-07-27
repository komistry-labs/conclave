"""Regression coverage for the workspace-isolation path check.

The v0.1.1 assertion searched serialised JSON for path substrings. That could
not work on Windows — `json.dumps` escapes every backslash — and it would also
have accepted `C:\\ws\\..\\..\\Windows` as being inside `C:\\ws`, because the
string starts with the root.

These tests pin both behaviours: escaping must be irrelevant, and containment
must be semantic. They run identically on every platform, because every path
here is a literal rather than something derived from the host filesystem.
"""

import json

import pytest

from pathcheck import classify, foreign_paths, is_within, iter_strings, looks_absolute

WIN_WS = r"C:\Users\ZY\AppData\Local\Temp\pytest-of-ZY\pytest-0\ws0"
POSIX_WS = "/tmp/pytest-of-arthur/pytest-0/ws0"


# -- traversal -------------------------------------------------------------

def test_iter_strings_walks_nested_structures():
    obj = {"a": ["x", {"b": ("y", "z")}], "c": {"d": "w"}}
    assert set(iter_strings(obj)) >= {"x", "y", "z", "w"}


def test_iter_strings_includes_dict_keys():
    """A path used as a key is still a recorded path."""
    assert WIN_WS in set(iter_strings({WIN_WS: "value"}))


def test_iter_strings_ignores_non_string_values():
    """Keys are strings and are yielded; numeric, boolean and null values are not."""
    yielded = set(iter_strings({"n": 1, "f": 1.5, "b": True, "z": None}))
    assert yielded == {"n", "f", "b", "z"}          # the keys
    assert not any(isinstance(v, (int, float, bool)) for v in yielded)


def test_iter_strings_from_bare_non_strings():
    assert set(iter_strings(1)) == set()
    assert set(iter_strings(None)) == set()
    assert set(iter_strings([1, 2.0, True, None])) == set()


def test_iter_strings_handles_deep_nesting():
    obj = {"l1": {"l2": {"l3": [{"l4": [WIN_WS]}]}}}
    assert WIN_WS in set(iter_strings(obj))


# -- candidate detection ---------------------------------------------------

@pytest.mark.parametrize("value", [
    "/tmp/x",
    "/",
    r"C:\Users",
    "C:/Users",
    r"D:\data\file.yaml",
    r"\\server\share\file",
])
def test_absolute_paths_detected(value):
    assert looks_absolute(value)


@pytest.mark.parametrize("value", [
    "sha256:abc123",                     # hash, has a colon
    "kos:decision:000005",               # canonical id, two colons
    "RA-001#RA-001-PART-IV",             # object ref with a separator
    "TP-draft-abc-0123456789@v1",        # packet ref
    "relative/path/file.md",             # relative
    r"relative\path\file.md",            # relative, Windows style
    "tasks/TP-x/v1.yaml",
    "",
    "C:",                                # drive with no separator
    "conclave-ledger/0.1.0",             # schema version
])
def test_non_paths_not_detected(value):
    assert not looks_absolute(value)
    assert classify(value, WIN_WS) == "not-a-path"


# -- Windows absolute paths ------------------------------------------------

def test_windows_path_inside_workspace():
    assert is_within(WIN_WS + r"\.conclave", WIN_WS)


def test_windows_workspace_root_itself_is_inside():
    assert is_within(WIN_WS, WIN_WS)


def test_windows_path_outside_workspace():
    assert not is_within(r"C:\Users\ZY\CLAUDE\komistry\KOS\architecture", WIN_WS)


def test_windows_forward_slashes_equivalent():
    assert is_within(WIN_WS.replace("\\", "/") + "/.conclave", WIN_WS)


def test_windows_case_insensitive():
    """Windows paths differing only in case are the same location."""
    assert is_within(WIN_WS.upper() + r"\.CONCLAVE", WIN_WS)


def test_windows_dotdot_escape_rejected():
    """Prefix matching would wrongly accept this; normalisation rejects it."""
    escaping = WIN_WS + r"\..\..\..\..\..\..\Windows\System32"
    assert escaping.startswith(WIN_WS)          # a naive check would pass
    assert not is_within(escaping, WIN_WS)      # semantics say otherwise


def test_windows_dotdot_that_stays_inside_is_accepted():
    assert is_within(WIN_WS + r"\sub\..\.conclave", WIN_WS)


def test_windows_redundant_separators_normalised():
    assert is_within(WIN_WS + r"\\.\\.conclave", WIN_WS)


def test_unc_path_outside_workspace():
    assert not is_within(r"\\fileserver\share\secrets", WIN_WS)


# -- POSIX absolute paths --------------------------------------------------

def test_posix_path_inside_workspace():
    assert is_within(POSIX_WS + "/.conclave", POSIX_WS)


def test_posix_workspace_root_itself_is_inside():
    assert is_within(POSIX_WS, POSIX_WS)


def test_posix_path_outside_workspace():
    assert not is_within("/home/arthur/KOS/architecture", POSIX_WS)


def test_posix_dotdot_escape_rejected():
    escaping = POSIX_WS + "/../../../../etc/passwd"
    assert escaping.startswith(POSIX_WS)
    assert not is_within(escaping, POSIX_WS)


def test_posix_case_sensitive():
    """POSIX paths differing in case are different locations."""
    assert not is_within(POSIX_WS.upper() + "/.conclave", POSIX_WS)


def test_posix_sibling_with_shared_prefix_rejected():
    """`/tmp/ws0-other` must not count as inside `/tmp/ws0`."""
    assert not is_within(POSIX_WS + "-other/file", POSIX_WS)


def test_windows_sibling_with_shared_prefix_rejected():
    assert not is_within(WIN_WS + r"-other\file", WIN_WS)


# -- cross-syntax ----------------------------------------------------------

def test_posix_candidate_against_windows_root_is_foreign():
    assert not is_within("/etc/passwd", WIN_WS)


def test_windows_candidate_against_posix_root_is_foreign():
    assert not is_within(r"C:\Windows\System32", POSIX_WS)


# -- escaping is irrelevant ------------------------------------------------

def test_escaped_backslashes_do_not_break_containment():
    """The v0.1.1 defect, stated directly.

    A Windows path survives a JSON round trip unchanged as a *value*; only its
    serialised text is escaped. Containment must be judged on the value.
    """
    event = {"subject_refs": [WIN_WS + r"\.conclave"]}
    restored = json.loads(json.dumps(event))
    assert restored["subject_refs"][0] == event["subject_refs"][0]
    assert foreign_paths(restored, WIN_WS) == []


def test_serialised_text_contains_doubled_backslashes():
    """Confirms the escaping the old assertion tripped over is real."""
    text = json.dumps({"p": WIN_WS})
    assert "\\\\" in text
    assert WIN_WS not in text          # the unescaped root is absent from the text
    assert foreign_paths({"p": WIN_WS}, WIN_WS) == []   # yet containment holds


def test_literal_double_backslash_in_a_value_is_still_handled():
    """A value that genuinely contains doubled separators, not JSON escaping."""
    doubled = WIN_WS + r"\\.conclave\\file.yaml"
    assert is_within(doubled, WIN_WS)


# -- JSON-sensitive characters --------------------------------------------

@pytest.mark.parametrize("value", [
    'quote " inside',
    "backslash \\ inside",
    "newline \n inside",
    "tab \t inside",
    "carriage \r return",
    "unicode — ✓ é 日本語",
    "control \u0001 char",
    "brace { and } and [ ]",
    "colon : and comma ,",
])
def test_json_sensitive_values_are_not_mistaken_for_paths(value):
    assert not looks_absolute(value)
    assert foreign_paths({"note": value}, WIN_WS) == []


def test_json_sensitive_characters_survive_traversal():
    payload = {'a "quoted" key': "value \\ with \n specials"}
    assert set(iter_strings(payload)) == {'a "quoted" key', "value \\ with \n specials"}


def test_path_with_spaces_and_unicode():
    p = WIN_WS + r"\a folder\naïve file.md"
    assert is_within(p, WIN_WS)
    assert foreign_paths({"p": p}, WIN_WS) == []


# -- external paths must still fail ---------------------------------------

@pytest.mark.parametrize("intruder", [
    r"C:\Users\ZY\CLAUDE\komistry\KOS\architecture\decisions\ADR-0001.md",
    r"C:\Windows\System32\config",
    r"D:\somewhere\else",
    r"\\server\share\kos",
    "/home/arthur/KOS/README.md",
    "/etc/shadow",
])
def test_external_path_is_reported(intruder):
    root = WIN_WS if looks_absolute(intruder) and intruder[1:2] == ":" or intruder.startswith("\\\\") else POSIX_WS
    assert foreign_paths({"subject_refs": [intruder]}, root) == [intruder]


def test_kos_path_inside_an_event_is_caught():
    """The invariant that matters: a KOS path must never reach a ledger event."""
    event = {
        "event_type": "task_packet_created",
        "sequence": 3,
        "subject_refs": [WIN_WS + r"\.conclave"],
        "payload": {
            "path": "tasks/TP-x/v1.yaml",
            "kos_repository": r"C:\Users\ZY\CLAUDE\komistry\KOS",
        },
    }
    assert foreign_paths(event, WIN_WS) == [r"C:\Users\ZY\CLAUDE\komistry\KOS"]


def test_intruder_nested_deep_is_still_found():
    event = {"payload": {"a": [{"b": {"c": ["/etc/passwd"]}}]}}
    assert foreign_paths(event, POSIX_WS) == ["/etc/passwd"]


def test_multiple_intruders_all_reported_and_sorted():
    event = {"payload": ["/etc/passwd", "/etc/hosts", POSIX_WS + "/ok"]}
    assert foreign_paths(event, POSIX_WS) == ["/etc/hosts", "/etc/passwd"]


def test_clean_event_reports_nothing():
    event = {
        "event_type": "workspace_genesis",
        "subject_refs": [POSIX_WS + "/.conclave"],
        "artifact_hashes": {"manifest": "sha256:" + "a" * 64},
        "payload": {"principal": "Arthur", "kos_repository": None,
                    "path": "tasks/TP-x/v1.yaml"},
    }
    assert foreign_paths(event, POSIX_WS) == []


# -- classify --------------------------------------------------------------

@pytest.mark.parametrize("value,root,expected", [
    (WIN_WS + r"\.conclave", WIN_WS, "inside"),
    (r"C:\elsewhere", WIN_WS, "outside"),
    ("sha256:abc", WIN_WS, "not-a-path"),
    (POSIX_WS + "/x", POSIX_WS, "inside"),
    ("/etc/passwd", POSIX_WS, "outside"),
])
def test_classify(value, root, expected):
    assert classify(value, root) == expected
