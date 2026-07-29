"""Tests for workspace creation, discovery and configuration."""

import pytest
import yaml

from conclave.errors import WorkspaceError
from conclave.workspace import SUBDIRS, Workspace


def test_create_makes_all_subdirs(tmp_path):
    ws = Workspace.create(tmp_path, principal="Arthur")
    for sub in SUBDIRS:
        assert (ws.root / sub).is_dir(), f"missing {sub}"


def test_create_writes_config(tmp_path):
    ws = Workspace.create(tmp_path, principal="Arthur")
    config = yaml.safe_load(ws.config_path.read_text(encoding="utf-8"))
    assert config["principal"] == "Arthur"
    assert config["bootstrap_version"] == "0.3.0"


def test_agents_may_not_merge_by_default(tmp_path):
    """Directive: no AI agent merges. This must be the default, not an option."""
    ws = Workspace.create(tmp_path, principal="Arthur")
    config = ws.load_config()
    assert config["authority"]["agents_may_merge"] is False
    assert config["authority"]["agents_may_propose"] is True


def test_all_providers_are_advisory(tmp_path):
    ws = Workspace.create(tmp_path, principal="Arthur")
    providers = ws.load_config()["providers"]
    assert set(providers) == {"adrian", "claude", "gemini"}
    for name, spec in providers.items():
        assert spec["authority_level"] == "advisory", name
        assert spec["transport"] == "manual-relay", name


def test_kos_access_is_read_only(tmp_path):
    ws = Workspace.create(tmp_path, principal="Arthur", kos_repository="/some/KOS")
    config = ws.load_config()
    assert config["kos_repository"] == "/some/KOS"
    assert config["kos_access"] == "read-only"


def test_kos_repository_optional(tmp_path):
    ws = Workspace.create(tmp_path, principal="Arthur")
    assert ws.load_config()["kos_repository"] is None


def test_create_refuses_to_overwrite(tmp_path):
    Workspace.create(tmp_path, principal="Arthur")
    with pytest.raises(WorkspaceError, match="already exists"):
        Workspace.create(tmp_path, principal="Someone Else")


def test_force_reinitialises_config_but_keeps_data(tmp_path):
    ws = Workspace.create(tmp_path, principal="Arthur")
    (ws.tasks_dir / "KOS-TEST-001").mkdir(parents=True)
    ws2 = Workspace.create(tmp_path, principal="Arthur", force=True)
    assert (ws2.tasks_dir / "KOS-TEST-001").exists()


# -- discovery -------------------------------------------------------------

def test_find_from_workspace_parent(tmp_path, monkeypatch):
    monkeypatch.delenv("CONCLAVE_HOME", raising=False)
    Workspace.create(tmp_path, principal="Arthur")
    assert Workspace.find(tmp_path).root == (tmp_path / ".conclave").resolve()


def test_find_walks_upward(tmp_path, monkeypatch):
    monkeypatch.delenv("CONCLAVE_HOME", raising=False)
    Workspace.create(tmp_path, principal="Arthur")
    deep = tmp_path / "a" / "b" / "c"
    deep.mkdir(parents=True)
    assert Workspace.find(deep).root == (tmp_path / ".conclave").resolve()


def test_find_raises_when_absent(tmp_path, monkeypatch):
    monkeypatch.delenv("CONCLAVE_HOME", raising=False)
    with pytest.raises(WorkspaceError, match="no CONCLAVE workspace"):
        Workspace.find(tmp_path)


def test_conclave_home_env_overrides(tmp_path, monkeypatch):
    ws = Workspace.create(tmp_path, principal="Arthur")
    monkeypatch.setenv("CONCLAVE_HOME", str(ws.root))
    elsewhere = tmp_path / "unrelated"
    elsewhere.mkdir()
    assert Workspace.find(elsewhere).root == ws.root


def test_conclave_home_pointing_nowhere_raises(tmp_path, monkeypatch):
    monkeypatch.setenv("CONCLAVE_HOME", str(tmp_path / "nothing-here"))
    with pytest.raises(WorkspaceError, match="CONCLAVE_HOME"):
        Workspace.find(tmp_path)


def test_load_config_raises_without_init(tmp_path):
    with pytest.raises(WorkspaceError, match="conclave init"):
        Workspace(tmp_path / ".conclave").load_config()
