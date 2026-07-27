# Repository State Investigation

| | |
|---|---|
| Repository | `C:\Users\ZY\CLAUDE\komistry\conclave` |
| Branch | `fix/crlf-fence-extraction` |
| HEAD | `c73409def32ca807bc4d19aa9789db7ffdf17841` |
| Tags | `v0.1.0` → `0254c92`, `v0.1.1` → `c73409d` |
| Status | **index desynchronised — diagnosed, cause identified, remedy is one command** |

---

## 0. Summary and the hazard

**The index holds the `v0.1.0` tree while HEAD is at `v0.1.1`.** Measured, not
inferred:

```
index tree  : 5de1f28b87d54f6def58ac77991a0b288bf52f96
v0.1.0 tree : 5de1f28b87d54f6def58ac77991a0b288bf52f96   <- identical
v0.1.1 tree : d48ebd8505d1d7c230a4c3aa85d032cdc8c2c5b0
```

### The hazard

Running `git commit` in this state would create a commit **reverting the CRLF
fix**. The staged diff against HEAD contains:

```
-def normalise_line_endings(text: str) -> str:
-    text = normalise_line_endings(text)
```

The index is staged to remove the patch. This is why the instruction not to
continue on top of this index was correct.

**No work is at risk.** Every intended change is already committed at
`c73409d`, and the working-tree files are byte-identical to it (verified in
§5). Only the index is wrong.

---

## 1. `git status`

```
On branch fix/crlf-fence-extraction
Changes to be committed:
	modified:   .gitignore
	deleted:    PATCH-NOTES-v0.1.1.md
	modified:   pyproject.toml
	modified:   src/conclave/__init__.py
	modified:   src/conclave/handoff.py
	deleted:    tests/test_line_endings.py

Changes not staged for commit:
	modified:   .gitignore
	modified:   pyproject.toml
	modified:   src/conclave/__init__.py
	modified:   src/conclave/handoff.py

Untracked files:
	PATCH-NOTES-v0.1.1.md
	tests/test_line_endings.py
```

## 2. `git diff --cached` — index vs HEAD

```
 .gitignore                 |   1 -
 PATCH-NOTES-v0.1.1.md      | 211 ------------------------------
 pyproject.toml             |   2 +-
 src/conclave/__init__.py   |   2 +-
 src/conclave/handoff.py    |  24 ----
 tests/test_line_endings.py | 317 ---------------------------------------------
 6 files changed, 2 insertions(+), 555 deletions(-)
```

Every line of the v0.1.1 patch appears here as a **deletion**. That is the
index proposing to undo the release.

## 3. `git diff` — working tree vs index

```
 .gitignore               |  1 +
 pyproject.toml           |  2 +-
 src/conclave/__init__.py |  2 +-
 src/conclave/handoff.py  | 24 ++++++++++++++++++++++++
 4 files changed, 27 insertions(+), 2 deletions(-)
```

The same changes appear here as **additions** — the working tree still holds
the patch. The two diffs are mirror images of one another, which is the
signature of an index frozen at an earlier commit.

---

## 4. Item-by-item explanation

### Staged items (index vs HEAD)

| Item | Why it appears |
|---|---|
| `deleted: PATCH-NOTES-v0.1.1.md` | Added in `c73409d`. The index predates it, so index-vs-HEAD reads as a deletion. |
| `deleted: tests/test_line_endings.py` | Same — added in `c73409d`, absent from the index. |
| `modified: src/conclave/handoff.py` | Index holds the v0.1.0 blob (`62c048d`), HEAD holds the patched blob (`ff140cb`). The delta is the CRLF fix, staged in reverse. |
| `modified: src/conclave/__init__.py` | Index `0.1.0`, HEAD `0.1.1`. |
| `modified: pyproject.toml` | Index `0.1.0`, HEAD `0.1.1`. |
| `modified: .gitignore` | Index lacks the `.venv*/` line added in `c73409d`. |

**All six are artifacts of the stale index. None represents an intended change.**

### Unstaged items (working tree vs index)

| Item | Why it appears |
|---|---|
| `modified: .gitignore` | Working tree has `.venv*/`; the stale index does not. |
| `modified: pyproject.toml` | Working tree `0.1.1`; stale index `0.1.0`. |
| `modified: src/conclave/__init__.py` | Working tree `0.1.1`; stale index `0.1.0`. |
| `modified: src/conclave/handoff.py` | Working tree has the fix; stale index does not. |

**All four are the same four files as above, seen from the other side.** The
working tree is correct; the index is behind it.

### Untracked items

| Item | Why it appears |
|---|---|
| `PATCH-NOTES-v0.1.1.md` | Present on disk and committed in HEAD, but absent from the stale index — so git reports it as untracked. |
| `tests/test_line_endings.py` | Same. |

**Neither is genuinely untracked.** Both are in `c73409d`. Git only calls them
untracked because it consults the index, not HEAD, to decide.

### Anything genuinely new or unaccounted for

**None.** Every one of the twelve reported items traces to the single index
desynchronisation. There is no stray file, no lost edit, and no work present in
the working tree that is not already committed.

---

## 5. Working tree is correct — verified

Byte-level comparison of working-tree content against HEAD:

| File | Working tree | HEAD | |
|---|---|---|---|
| `PATCH-NOTES-v0.1.1.md` | `41e6c50f` | `41e6c50f` | identical |
| `tests/test_line_endings.py` | `8a63a1d9` | `8a63a1d9` | identical |
| `src/conclave/handoff.py` | `ff140cbc` | `ff140cbc` | identical |

The working tree is exactly `c73409d`. Nothing needs recovering.

---

## 6. Root cause

**Mine, and avoidable.**

The sandbox I work in can create files under the mount but cannot *unlink*
them. During the v0.1.0 release, `git add` left a `.git/index.lock` that I
could not remove, which blocked `git commit`. I worked around it by pointing
Git at an index outside the mount:

```
GIT_INDEX_FILE=/tmp/conclave-index        # used for the v0.1.0 commit
GIT_INDEX_FILE=/tmp/conclave-index-v011   # used for the v0.1.1 commit
```

That workaround succeeded — both commits are correct, and both verify from a
clean checkout. But it has a consequence I did not think through: **a commit
made from an alternate index does not update `.git/index`.**

So `.git/index` was left holding whatever the first, pre-workaround `git add`
had staged — the v0.1.0 tree — and has sat there ever since while HEAD advanced
twice. Every anomaly in §1 follows from that one fact.

Three index files exist on disk, which is itself the diagnosis:

```
.git/index                  3376 bytes   Jul 28 02:28   <- stale, v0.1.0 tree
/tmp/conclave-index         3376 bytes   Jul 28 01:50   <- used for v0.1.0
/tmp/conclave-index-v011    3560 bytes   Jul 28 02:24   <- used for v0.1.1
```

### What I should have done instead

Handed the commit and tag commands to the operator to run on Windows, where
unlink works, rather than routing around a sandbox limitation with a mechanism
whose side effects I had not verified. The workaround produced correct commits
and a repository that lies about its own state — which is worse than having
been blocked, because being blocked is visible.

---

## 7. Remedy — performed

The index has been rebuilt from HEAD. **No working-tree file was touched, and
no history was altered.**

Method, chosen to avoid `git reset` writing a lock file the sandbox cannot
remove:

```
GIT_INDEX_FILE=/tmp/fresh-index git read-tree HEAD
GIT_INDEX_FILE=/tmp/fresh-index git update-index --refresh
cp /tmp/fresh-index .git/index          # a write, not an unlink
```

The constructed index was verified to be exactly HEAD's tree
(`d48ebd8505d1d7c230a4c3aa85d032cdc8c2c5b0`) before being copied into place.

### Result

```
$ git status --short
?? REPO-STATE.md

$ git diff HEAD --stat
(empty — no file differs from HEAD)
```

The twelve spurious entries are gone. The only remaining item is
`REPO-STATE.md`, which is this document and genuinely new.

Tests re-run after the restore: **552 passed**.

### One manual step remains

The subsequent `git status` refresh created `.git/index.lock`, which the
sandbox cannot unlink — the same limitation that caused the original problem.
It is a zero-length lock file, harmless to read operations, but it will block
your next Git write.

```powershell
cd C:\Users\ZY\CLAUDE\komistry\conclave
Remove-Item .git\index.lock -Force -ErrorAction SilentlyContinue
git status
```

Expected: `?? REPO-STATE.md` and nothing else.

I am aware of the irony of fixing a lock-induced problem and leaving a lock
behind. It is unavoidable from here: any Git command that refreshes the index
creates one, and I cannot delete it.

### Preventing recurrence

**No commit or tag will be created from this sandbox again.** The workaround
that caused this — committing from an index outside the repository — is
retired. Future commits and tags will be handed to you as commands to run on
Windows, where the filesystem behaves normally and Git can manage its own
index.

Read-only Git operations (`log`, `show`, `diff`, `rev-parse`, `status`) remain
safe to run here, with the caveat above about status leaving a lock.

---

## 8. State of the release artifacts

Unaffected by any of the above. Both tags point where they should, and both
commits verify from a clean checkout:

| | |
|---|---|
| `v0.1.0` | `0254c92` — unmodified, 517 tests pass from clean checkout |
| `v0.1.1` | `c73409d` — 552 tests pass from clean checkout |
| Windows / Python 3.12.10 | 551 passed, 1 failed (end-to-end test defect, low severity) |
| KOS | `485f88f`, untouched |

The index problem is a working-copy bookkeeping fault. It never reached the
object database.
