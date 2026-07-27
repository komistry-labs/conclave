# CONCLAVE v0.1.2 — Test Patch

| | |
|---|---|
| Type | **test-only patch** |
| Based on | `v0.1.1` @ `c73409d` — unmodified, tag not moved |
| Branch | `fix/windows-path-invariant-test` |
| Defect | Windows-incompatible assertion in `tests/test_end_to_end.py` |
| Severity | low |
| **Runtime impact** | **none — no production code changed** |
| Tests | 552 → **620** |

---

## 1. What each patch fixed

| Release | Fixed | Kind |
|---|---|---|
| `v0.1.0` | — | initial release |
| `v0.1.1` | **CRLF fence extraction** — `relay import` was inoperable on Windows | **runtime blocker** |
| `v0.1.2` | **a Windows-incompatible test assertion** | **test defect only** |

**v0.1.1 fixed the CRLF runtime blocker. v0.1.2 fixes only a test assertion.**
The two are unrelated beyond both surfacing on Windows.

The Windows / Python 3.12.10 run of `v0.1.1` reported **551 passed, 1 failed**.
The single failure was this assertion. The runtime fix was already validated by
the other 551.

## 2. Defect

`tests/test_end_to_end.py`, in the workspace-isolation invariant:

```python
for path_value in [v for v in json.dumps(e).split('"')
                   if v.startswith("/") or ":\\" in v]:
    assert str(ws) in path_value or path_value.startswith("/sessions"), path_value
```

The check searched **serialised JSON text** for the workspace root as a
substring.

## 3. Root cause

`json.dumps` escapes every backslash. A Windows path stored as a value:

```
value in the event : C:\Users\ZY\AppData\...\ws0\.conclave
text in the JSON   : C:\\Users\\ZY\\AppData\\...\\ws0\\.conclave
```

The assertion then compared the **unescaped** `str(ws)` against the **escaped**
text. That comparison cannot succeed on Windows, no matter how correct the
underlying behaviour is. On Linux it passed only because POSIX paths contain no
backslashes to escape.

The assertion was testing JSON serialisation, not path containment.

### A second, latent flaw

Even with escaping handled, substring matching is the wrong test. It would have
accepted:

```
C:\...\ws0\..\..\..\CLAUDE\komistry\KOS
```

as inside the workspace, because the string starts with the workspace root —
while the path resolves into the KOS repository. The old assertion could not
have caught the exact violation the invariant exists to prevent.

**The invariant was weaker than it appeared, on every platform.** That is the
more serious half of this defect, and it is why the replacement compares
normalised path semantics rather than adding an unescaping step.

## 4. Fix

New test helper `tests/pathcheck.py` — **not** a test module, no production code:

| Function | Purpose |
|---|---|
| `iter_strings(obj)` | walk the structured object, yielding unescaped string values and dict keys |
| `looks_absolute(s)` | narrow detection of POSIX (`/…`), Windows drive (`C:\`, `C:/`) and UNC (`\\server\share`) syntax |
| `is_within(candidate, root)` | normalised containment — collapses `.`, `..` and redundant separators; folds case on Windows only |
| `classify(value, root)` | `not-a-path` / `inside` / `outside` |
| `foreign_paths(obj, root)` | every absolute path not resolving inside `root` |

The assertion becomes:

```python
strays = foreign_paths(e, ws)
assert strays == [], (
    f"event {e['event_type']} (seq {e['sequence']}) records path(s) "
    f"outside the workspace: {strays}"
)
```

Structured traversal, actual values, semantic comparison. Escaping is now
irrelevant by construction rather than by compensation.

### `/sessions` exception removed

It was never required, and this was verified rather than assumed. A full
workflow was run and every absolute string in every ledger event inventoried:

```
absolute-looking strings found in events:
  INSIDE   /sessions/…/tmpq7merzxq/.conclave
count: 1
```

The only absolute path is the workspace root itself, recorded in
`subject_refs`. In the sandbox `tmp_path` already lives under `/sessions`, so
the workspace check covered it. The exception was noise and has been dropped —
which also removes a sandbox-specific detail from a portable test.

### Cross-syntax paths

A POSIX path appearing on a Windows run, or vice versa, is reported as foreign
rather than excused. Such a path could not have come from the workspace and
should be visible.

## 5. Regression coverage — 68 new tests

`tests/test_path_invariant.py`. Every path is a literal, so the tests behave
identically on all platforms.

| Area | Covered |
|---|---|
| Traversal | nesting, dict keys, tuples, non-string values, bare scalars |
| Windows absolute paths | inside, outside, root itself, forward slashes, case-insensitivity, UNC |
| POSIX absolute paths | inside, outside, root itself, case-sensitivity |
| Escaped backslashes | JSON round trip preserves the value; serialised text is doubled; containment still holds |
| JSON-sensitive characters | quotes, backslashes, newlines, tabs, CR, control chars, unicode, braces, colons — none mistaken for a path |
| External paths that must fail | KOS paths, `C:\Windows`, other drives, UNC shares, `/etc/shadow` |
| `..` traversal | escaping rejected even though the string starts with the root; staying inside accepted |
| Sibling prefixes | `/tmp/ws0-other` correctly rejected against `/tmp/ws0` |
| Non-paths | `sha256:…`, `kos:decision:…`, `RA-001#…`, packet refs, relative paths |

Two tests pin the defect directly: one asserts the serialised text contains
doubled backslashes and does **not** contain the unescaped root, while
containment still holds; another asserts that a `..`-escaping path passes a
naive `startswith` check and is nonetheless rejected.

## 6. Files changed

| File | Change |
|---|---|
| `tests/pathcheck.py` | **new** — helper module, ~120 lines |
| `tests/test_path_invariant.py` | **new** — 68 regression tests |
| `tests/test_end_to_end.py` | assertion replaced; one import added |
| `PATCH-NOTES-v0.1.2.md` | **new** |
| `src/conclave/__init__.py` | version → `0.1.2` |
| `pyproject.toml` | version → `0.1.2` |

**No file under `src/conclave/` changed except the version string.**

## 7. Test results

| Suite | Python 3.10.12 (Linux) | Python 3.12.10 (Windows) |
|---|---|---|
| `v0.1.1` | 552 passed | 551 passed, **1 failed** |
| `v0.1.2` | **620 passed** | **620 passed** |

All 552 v0.1.1 tests still pass, plus 68 new ones. **Both platforms green.**

### Environment note — not a CONCLAVE defect

The first Windows attempt produced 367 errors, all identical:

```
PermissionError: [WinError 5] Access is denied:
  'C:\Users\ZY\AppData\Local\Temp\pytest-of-ZY'
```

Every error occurred in pytest's `tmp_path` fixture *before any CONCLAVE code
ran*. The suite could not create temporary directories at all.

Resolved by directing pytest elsewhere:

```powershell
$BaseTemp = "C:\Users\ZY\CLAUDE\komistry\conclave\.pytest-tmp"
Remove-Item $BaseTemp -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path $BaseTemp | Out-Null
.\.venv312\Scripts\python.exe -m pytest -q --basetemp="$BaseTemp"
```

**Likely cause:** `pytest-of-ZY` was created by an earlier run in an elevated
shell — one was used for the long-path registry change during setup — leaving
it owned by the Administrator context and unwritable to the normal user. Once
that directory exists with restrictive ownership, every subsequent non-elevated
run fails on it.

**Suggested permanent fix**, so `--basetemp` is not needed indefinitely:

```powershell
Remove-Item "$env:LOCALAPPDATA\Temp\pytest-of-ZY" -Recurse -Force
```

pytest will recreate it under the correct ownership on the next run. If removal
is refused, the elevated-ownership hypothesis is confirmed and it can be
deleted from an Administrator shell.

`.pytest-tmp/` has been added to `.gitignore`.

## 8. Compatibility

**No runtime behaviour changed.** The only non-test change is a version string.

- no schema version changed — `task-packet/0.1.0`, `handoff-packet/0.1.0`,
  `scope-review/0.1.0`, `council-review/0.1.0`, `conclave-ledger/0.1.0`
- no hashing change — every hash computed under v0.1.1 is reproduced exactly
- no authority change — the decision block, advisory constraints and ledger
  authority vocabulary are untouched
- no provenance change
- no ledger change — chains written under v0.1.0 or v0.1.1 verify unchanged
- no artifact semantics change
- no migration required

A `v0.1.1` installation and a `v0.1.2` installation produce byte-identical
artifacts from identical inputs.

## 9. Why this is not a runtime defect

The failing assertion tested a property that **held**. CONCLAVE was not
recording paths outside the workspace on Windows; the test could not tell,
because it was reading escaped JSON text.

No production code was changed, and none was needed. Per the classification
issued with this work, runtime changes were authorised only if a distinct
runtime defect were independently demonstrated. None was found, and none is
claimed.

The investigation did surface that the invariant was weaker than intended on
**all** platforms (§3), but that is a weakness in the test, not in the runtime.

## 10. Not included

- **Phase 1A** — not begun
- **Increment 8** — not begun; design proposal unchanged
- **KOS** — untouched, `485f88f`
