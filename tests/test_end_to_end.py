"""End-to-end Bootstrap 0.1 workflow inside a temporary clean workspace.

Exercises the CLI itself, in order, and asserts every Bootstrap 0.1 invariant.
Nothing outside tmp_path is touched; there is no KOS repository anywhere in
this test, which is itself part of the point.
"""

import json

import pytest
import yaml
from pathcheck import foreign_paths
from typer.testing import CliRunner

from conclave.cli import app

runner = CliRunner()


def run(*args, cwd, expect=0):
    import os
    prev = os.getcwd()
    os.chdir(cwd)
    try:
        result = runner.invoke(app, list(args))
    finally:
        os.chdir(prev)
    assert result.exit_code == expect, (
        f"`conclave {' '.join(args)}` exited {result.exit_code}, expected {expect}\n"
        f"{result.output}\n{result.exception}"
    )
    return result


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    monkeypatch.delenv("CONCLAVE_HOME", raising=False)
    return tmp_path


def reply(path, *, packet_ref, packet_hash, provider, role, touches, action="revise",
          status="submitted", findings=(), unresolved=()):
    body = {
        "handoff_packet": "handoff-packet/0.1.0",
        "packet_ref": packet_ref, "packet_content_hash": packet_hash,
        "provider": provider, "role": role, "status": status,
        "objects_touched": [
            {"object_id": o.split("#")[0],
             "section_id": (o.split("#")[1] if "#" in o else None), "action": a}
            for o, a in touches
        ],
        "output": {"type": "critique", "summary": f"{provider} summary", "body": "body"},
        "findings": list(findings), "assumptions": [], "abstentions": [],
        "unresolved": list(unresolved), "evidence_used": [],
        "recommended_next_action": action,
    }
    path.write_text("Here is my response.\n\n```yaml\n" +
                    yaml.safe_dump(body, sort_keys=False) + "```\n", encoding="utf-8")
    return path


def test_full_bootstrap_workflow(workspace):
    ws = workspace
    conclave = ws / ".conclave"

    # 1. workspace init
    run("init", "--principal", "Arthur", cwd=ws)
    assert (conclave / "config.yaml").exists()
    config = yaml.safe_load((conclave / "config.yaml").read_text(encoding="utf-8"))
    assert config["authority"]["agents_may_merge"] is False
    assert config["kos_access"] == "read-only"
    assert config["kos_repository"] is None

    # 2. ledger init — genesis on an empty workspace
    run("ledger", "init", cwd=ws)
    events = [json.loads(l) for l in
              (conclave / "ledger" / "ledger.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [e["event_type"] for e in events] == ["workspace_genesis",
                                                 "workspace_snapshot_attested"]
    assert events[1]["payload"]["artifact_count"] == 0

    # 3. task create
    run("task", "create",
        "-o", "Draft RA-001 Part I",
        "-t", "RA-001#RA-001-PART-I",
        "-r", "ADR-0002",
        "-x", "KOS-CONSTITUTION",
        "-P", "claude:governance_critic",
        "-P", "gemini:external_verifier",
        "-c", "do not rename approved Reasoning Architectures",
        "-a", "constitutional grounding stated explicitly",
        cwd=ws)
    task_dirs = list((conclave / "tasks").iterdir())
    assert len(task_dirs) == 1
    task_id = task_dirs[0].name
    packet = yaml.safe_load((task_dirs[0] / "v1.yaml").read_text(encoding="utf-8"))
    packet_hash = packet["content_hash"]

    # 4. validate
    run("validate", cwd=ws)

    # 5. relay export — one independent prompt per provider
    run("relay", "export", task_id, cwd=ws)
    prompts = sorted((conclave / "relay" / "outbox").glob("*.md"))
    assert len(prompts) == 2
    texts = {p.name.split("__")[2]: p.read_text(encoding="utf-8") for p in prompts}
    assert "gemini" not in texts["claude"]
    assert "claude" not in texts["gemini"]
    for provider, text in texts.items():
        assert packet_hash in text
        assert f"{task_id}@v1" in text
        assert "objects_touched" in text

    # 6. responses imported
    reply(ws / "claude.md", packet_ref=f"{task_id}@v1", packet_hash=packet_hash,
          provider="claude", role="governance_critic",
          touches=[("RA-001#RA-001-PART-I", "proposed_change"), ("ADR-0002", "cited")],
          findings=[{"key": "EVIDENCE-STATES", "finding_id": "F-001", "severity": "high",
                     "dimension": "epistemic-integrity", "claim": "states conflated"}],
          unresolved=[{"id": "U-CONSTITUTION", "note": "grounding unverifiable"}])
    reply(ws / "gemini.md", packet_ref=f"{task_id}@v1", packet_hash=packet_hash,
          provider="gemini", role="external_verifier", action="accept",
          touches=[("ADR-0002", "proposed_change"), ("RA-009", "cited")])

    run("relay", "import", "claude.md", cwd=ws)
    run("relay", "import", "gemini.md", cwd=ws)
    assert len(list((conclave / "relay" / "inbox").glob("*.yaml"))) == 2
    assert len(list((conclave / "relay" / "inbox" / "raw").glob("*"))) == 2

    # raw bytes preserved exactly
    for name in ("claude.md", "gemini.md"):
        original = (ws / name).read_bytes()
        assert any(p.read_bytes() == original
                   for p in (conclave / "relay" / "inbox" / "raw").glob("*"))

    # 7. scope review — gemini violated read-only and touched an undeclared object
    run("scope", "review", cwd=ws, expect=1)
    reviews = {yaml.safe_load(p.read_text(encoding="utf-8"))["provider"]:
               yaml.safe_load(p.read_text(encoding="utf-8"))
               for p in (conclave / "scope").glob("*.yaml")}
    assert reviews["claude"]["scope_status"] == "within_scope"
    assert reviews["gemini"]["scope_status"] == "expansion_detected"
    assert reviews["gemini"]["human_review_required"] is True
    assert {r["classification"] for r in reviews["gemini"]["object_results"]} == {
        "read_only_modified", "undeclared_expansion"}

    # 8. council review
    run("council", "review", task_id, cwd=ws)
    council_yaml = next((conclave / "council").glob("*.yaml"))
    council_md = council_yaml.with_suffix(".md")
    review = yaml.safe_load(council_yaml.read_text(encoding="utf-8"))
    md = council_md.read_text(encoding="utf-8")

    assert review["review_status"] == "blocked_by_governance"
    assert review["human_decision_required"] is True
    assert review["decision_block"] == {"decision": "pending", "decided_by": None,
                                        "decided_at": None, "rationale": None,
                                        "authorised_actions": []}
    assert review["missing_providers"] == []
    assert any(a["kind"] == "scope_violation" for a in review["governance_alerts"])
    assert review["content_hash"] in md
    assert review["council_review_id"] in md
    assert "has not approved, ratified, commissioned or merged anything" in md

    # structural comparison found the real disagreement, not a prose guess
    kinds = {d["kind"] for d in review["structural_disagreements"]}
    assert "recommended_next_action" in kinds
    assert "accept_versus_dissent" in kinds

    # 9. ledger verify
    result = run("ledger", "verify", cwd=ws)
    assert "chain verified" in result.output

    events = [json.loads(l) for l in
              (conclave / "ledger" / "ledger.jsonl").read_text(encoding="utf-8").splitlines()]
    types = [e["event_type"] for e in events]
    for expected in ("workspace_genesis", "task_packet_created", "relay_prompt_exported",
                     "provider_response_preserved", "handoff_packet_imported",
                     "scope_review_created", "council_review_created"):
        assert expected in types, expected

    # -- invariants --------------------------------------------------------

    # KOS remains external and untouched.
    #
    # A crude "the string KOS never appears" check is not the invariant and
    # would be wrong: KOS-CONSTITUTION is a legitimate object identifier in a
    # scope grant, and the snapshot's own exclusion note names KOS by design.
    # What matters is that no KOS *content* was read and no path outside the
    # workspace was recorded or created.
    #
    # Containment is checked on the structured event, not on serialised JSON.
    # See tests/pathcheck.py for why searching json.dumps() output cannot work.
    assert config["kos_repository"] is None
    for e in events:
        for value in (e.get("artifact_hashes") or {}).values():
            assert value.startswith("sha256:")
        strays = foreign_paths(e, ws)
        assert strays == [], (
            f"event {e['event_type']} (seq {e['sequence']}) records path(s) "
            f"outside the workspace: {strays}"
        )
    snapshot = next(e for e in events if e["event_type"] == "workspace_snapshot_attested")
    assert "the KOS repository" in snapshot["payload"]["excludes"][0]
    # every attested artifact lives inside the workspace
    for entries in snapshot["payload"]["classes"].values():
        for entry in entries:
            assert not entry["path"].startswith(("/", "..")), entry["path"]

    # only files under tmp_path exist; nothing was written elsewhere
    assert set(p.name for p in ws.iterdir()) <= {
        ".conclave", "claude.md", "gemini.md"}

    # no agent holds merge or approval authority
    for a in packet["assigned_providers"]:
        assert a["may_merge"] is False
        assert a["authority_level"] == "advisory"
    for e in events:
        assert e["authority_level"] in ("system", "advisory_agent", "human_principal")
        if e["authority_level"] == "advisory_agent":
            assert e["event_type"] in ("provider_response_preserved",
                                       "handoff_packet_imported",
                                       "provider_response_rejected")

    # every stored hash verifies
    from conclave.council import CouncilReview, verify_council_content_hash
    from conclave.handoff import HandoffPacket, verify_handoff_content_hash
    from conclave.scope import ScopeReview, verify_review_content_hash
    from conclave.taskpacket import verify_content_hash
    from conclave.models import TaskPacket

    assert verify_content_hash(TaskPacket.model_validate(packet))
    for p in (conclave / "relay" / "inbox").glob("*.yaml"):
        assert verify_handoff_content_hash(
            HandoffPacket.model_validate(yaml.safe_load(p.read_text(encoding="utf-8"))))
    for p in (conclave / "scope").glob("*.yaml"):
        assert verify_review_content_hash(
            ScopeReview.model_validate(yaml.safe_load(p.read_text(encoding="utf-8"))))
    assert verify_council_content_hash(CouncilReview.model_validate(review))

    # canonical packets immutable — recreating the same task is refused
    run("task", "create", "-o", "Draft RA-001 Part I", "-t", "RA-001#RA-001-PART-I",
        "-P", "claude", cwd=ws, expect=1)

    # idempotency where specified
    before = (conclave / "ledger" / "ledger.jsonl").read_bytes()
    run("relay", "export", task_id, cwd=ws)
    run("scope", "review", cwd=ws, expect=1)
    run("council", "review", task_id, cwd=ws)
    run("relay", "import", "claude.md", cwd=ws)
    assert (conclave / "ledger" / "ledger.jsonl").read_bytes() == before
    assert len(list((conclave / "council").glob("*.yaml"))) == 1
    assert len(list((conclave / "scope").glob("*.yaml"))) == 2

    run("ledger", "verify", cwd=ws)


def test_rejected_response_remains_auditable(workspace):
    ws = workspace
    conclave = ws / ".conclave"
    run("init", "--principal", "Arthur", cwd=ws)
    run("ledger", "init", cwd=ws)

    bad = ws / "bad.md"
    bad.write_bytes(b"no yaml block here at all\n")
    run("relay", "import", "bad.md", cwd=ws, expect=1)

    raws = list((conclave / "relay" / "inbox" / "raw").glob("*"))
    repairs = list((conclave / "relay" / "inbox" / "repair").glob("*"))
    assert len(raws) == 1 and len(repairs) == 1
    assert raws[0].read_bytes() == b"no yaml block here at all\n"
    assert list((conclave / "relay" / "inbox").glob("*.yaml")) == []

    events = [json.loads(l) for l in
              (conclave / "ledger" / "ledger.jsonl").read_text(encoding="utf-8").splitlines()]
    assert "provider_response_rejected" in [e["event_type"] for e in events]
    run("ledger", "verify", cwd=ws)


def test_reconciliation_closes_a_ledger_gap(workspace):
    """Artifacts created before ledger init are bridged, then reconciled."""
    ws = workspace
    conclave = ws / ".conclave"
    run("init", "--principal", "Arthur", cwd=ws)

    run("task", "create", "-o", "Work done before the ledger existed",
        "-t", "RA-001", "-P", "claude:governance_critic", cwd=ws)
    task_id = next((conclave / "tasks").iterdir()).name
    run("relay", "export", task_id, cwd=ws)
    assert not (conclave / "ledger" / "ledger.jsonl").exists()

    run("ledger", "init", cwd=ws)
    result = run("ledger", "reconcile", cwd=ws)
    assert "task_packet_created" in result.output
    assert "relay_prompt_exported" in result.output

    events = [json.loads(l) for l in
              (conclave / "ledger" / "ledger.jsonl").read_text(encoding="utf-8").splitlines()]
    reconciled = [e for e in events if e["payload"].get("reconciled")]
    assert len(reconciled) == 2
    for e in reconciled:
        assert e["payload"]["reconciliation_reason"]

    run("ledger", "verify", cwd=ws)
    before = (conclave / "ledger" / "ledger.jsonl").read_bytes()
    run("ledger", "reconcile", cwd=ws)
    assert (conclave / "ledger" / "ledger.jsonl").read_bytes() == before


def test_no_command_reports_itself_unimplemented(workspace):
    ws = workspace
    run("init", "--principal", "Arthur", cwd=ws)
    for args in (["--help"], ["task", "--help"], ["relay", "--help"],
                 ["scope", "--help"], ["council", "--help"], ["ledger", "--help"]):
        out = run(*args, cwd=ws).output
        assert "not implemented" not in out.lower()
    assert "decision ledger" not in run("ledger", "--help", cwd=ws).output.lower()
