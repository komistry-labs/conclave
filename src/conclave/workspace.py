"""CONCLAVE workspace layout and configuration.

The workspace is a local directory holding tasks, relay files, council review
packets, ledger entries and run records. It is deliberately OUTSIDE any
governed repository: CONCLAVE must function without modifying Komistry OS.

A workspace may record a `kos_repository` path for read-only inspection in a
later increment. Nothing in CONCLAVE writes to it.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import yaml

from .errors import WorkspaceError

WORKSPACE_DIRNAME = ".conclave"
CONFIG_FILENAME = "config.yaml"
BOOTSTRAP_VERSION = "0.1.0"

SUBDIRS = (
    "tasks",
    "relay/outbox",
    "relay/inbox",
    "scope",
    "council",
    "ledger",
    "runs",
)


def utcnow() -> str:
    """ISO 8601, UTC, second precision. One timestamp format everywhere."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


@dataclass(frozen=True)
class Workspace:
    root: Path

    # -- locations ---------------------------------------------------------

    @property
    def config_path(self) -> Path:
        return self.root / CONFIG_FILENAME

    @property
    def tasks_dir(self) -> Path:
        return self.root / "tasks"

    @property
    def outbox_dir(self) -> Path:
        return self.root / "relay" / "outbox"

    @property
    def inbox_dir(self) -> Path:
        return self.root / "relay" / "inbox"

    @property
    def council_dir(self) -> Path:
        return self.root / "council"

    @property
    def ledger_dir(self) -> Path:
        return self.root / "ledger"

    @property
    def ledger_path(self) -> Path:
        return self.ledger_dir / "ledger.jsonl"

    @property
    def runs_dir(self) -> Path:
        return self.root / "runs"

    # -- config ------------------------------------------------------------

    def load_config(self) -> dict:
        if not self.config_path.exists():
            raise WorkspaceError(
                f"no CONCLAVE workspace config at {self.config_path}. "
                "Run 'conclave init' first."
            )
        return yaml.safe_load(self.config_path.read_text(encoding="utf-8")) or {}

    def task_dir(self, task_id: str) -> Path:
        return self.tasks_dir / task_id

    # -- discovery ---------------------------------------------------------

    @classmethod
    def find(cls, start: Path | None = None) -> "Workspace":
        """Locate the nearest workspace, walking upward from `start`.

        Honours CONCLAVE_HOME when set, which keeps tests hermetic and lets an
        operator run against a specific workspace without changing directory.
        """
        env = os.environ.get("CONCLAVE_HOME")
        if env:
            ws = cls(Path(env).expanduser().resolve())
            if not ws.config_path.exists():
                raise WorkspaceError(
                    f"CONCLAVE_HOME is set to {ws.root} but no workspace exists there."
                )
            return ws

        here = (start or Path.cwd()).resolve()
        for candidate in (here, *here.parents):
            probe = candidate / WORKSPACE_DIRNAME
            if (probe / CONFIG_FILENAME).exists():
                return cls(probe)
        raise WorkspaceError(
            "no CONCLAVE workspace found in this directory or any parent. "
            "Run 'conclave init' to create one."
        )

    @classmethod
    def create(
        cls,
        parent: Path,
        *,
        principal: str,
        kos_repository: str | None = None,
        force: bool = False,
    ) -> "Workspace":
        """Create a workspace under `parent`/.conclave."""
        root = Path(parent).resolve() / WORKSPACE_DIRNAME
        ws = cls(root)

        if ws.config_path.exists() and not force:
            raise WorkspaceError(
                f"workspace already exists at {root}. Use --force to reinitialise "
                "configuration (existing tasks, ledger and runs are left intact)."
            )

        for sub in SUBDIRS:
            (root / sub).mkdir(parents=True, exist_ok=True)

        config = {
            "bootstrap_version": BOOTSTRAP_VERSION,
            "created_at": utcnow(),
            "principal": principal,
            "authority": {
                "constitutional_authority": principal,
                "agents_may_propose": True,
                "agents_may_merge": False,
            },
            "kos_repository": kos_repository,
            "kos_access": "read-only",
            "providers": {
                "adrian": {
                    "display_name": "Adrian (ChatGPT)",
                    "transport": "manual-relay",
                    "default_role": "institutional_architect",
                    "authority_level": "advisory",
                },
                "claude": {
                    "display_name": "Claude",
                    "transport": "manual-relay",
                    "default_role": "governance_critic",
                    "authority_level": "advisory",
                },
                "gemini": {
                    "display_name": "Gemini",
                    "transport": "manual-relay",
                    "default_role": "external_verifier",
                    "authority_level": "advisory",
                },
            },
            "hashing": {
                "algorithm": "sha256",
                "canonicalisation": "kos-canonical-text-v1",
            },
        }

        ws.config_path.write_bytes(
            yaml.safe_dump(config, sort_keys=False, allow_unicode=True).encode("utf-8")
        )
        return ws
