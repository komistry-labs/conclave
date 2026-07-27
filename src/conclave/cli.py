"""CONCLAVE command-line interface — Bootstrap 0.1.

All Bootstrap 0.1 commands are implemented. Each command states whether it
CREATES an immutable artifact, VERIFIES one, PROJECTS one into another form,
RECONCILES a gap, or merely DISPLAYS state.
"""

from __future__ import annotations

from pathlib import Path

import typer
import yaml

from . import __version__, ledger
from .council import review_task
from .errors import ConclaveError
from .handoff import import_response
from .models import SCHEMA_VERSION
from .reconcile import reconcile
from .relay import export_prompts
from .scope import review_handoff
from .taskpacket import (
    build_packet,
    build_revision,
    latest_version,
    list_tasks,
    list_versions,
    packet_path,
    read_packet,
    write_packet,
)
from .validation import Category, Severity, validate_packet_file
from .workspace import Workspace

app = typer.Typer(
    name="conclave",
    help=(
        "Coordinate multiple AI providers on Komistry OS work through manual relay.\n\n"
        "One instruction in, independent advisory responses out, structured review, "
        "human decision. CONCLAVE proposes and records; it never approves, ratifies, "
        "commissions or merges. Komistry OS is external and read-only."
    ),
    no_args_is_help=True,
    add_completion=False,
)

task_app = typer.Typer(
    help="Task Packets. Immutable once written; revision creates a new version.",
    no_args_is_help=True)
relay_app = typer.Typer(
    help="Manual relay. Export prompts to paste into providers; import their replies.",
    no_args_is_help=True)
scope_app = typer.Typer(
    help="Scope drift detection. Compares declared objects_touched against granted scope.",
    no_args_is_help=True)
council_app = typer.Typer(
    help="Council Review. Aggregates verified submissions for one Task Packet version.",
    no_args_is_help=True)
ledger_app = typer.Typer(
    help="Append-only hash-chained EVENT ledger (audit chain of governed events).",
    no_args_is_help=True)

app.add_typer(task_app, name="task")
app.add_typer(relay_app, name="relay")
app.add_typer(scope_app, name="scope")
app.add_typer(council_app, name="council")
app.add_typer(ledger_app, name="ledger")


def _fail(msg: str) -> None:
    typer.secho(f"error: {msg}", fg=typer.colors.RED, err=True)
    raise typer.Exit(code=1)


def _record(ws: Workspace, **kwargs) -> None:
    """Append a ledger event if a ledger exists.

    A ledger failure never destroys an artifact. The artifact is already
    written and immutable; rolling it back to keep the ledger tidy would
    trade real evidence for a neater record. Report the gap and let a
    reconciliation event close it later.
    """
    try:
        ledger.record_event(ws, **kwargs)
    except ConclaveError as exc:
        typer.echo("")
        typer.secho("LEDGER APPEND FAILED — the artifact was written and is preserved.",
                    fg=typer.colors.RED, bold=True)
        typer.echo(f"  {exc}")
        typer.secho("  Re-running this command will not help: the artifact already exists "
                    "and creation is refused.", fg=typer.colors.YELLOW)
        typer.secho("  Instead run:  conclave ledger verify   then   conclave ledger reconcile",
                    fg=typer.colors.YELLOW, bold=True)


def _ws() -> tuple[Workspace, dict]:
    try:
        ws = Workspace.find()
        return ws, ws.load_config()
    except ConclaveError as exc:
        _fail(str(exc))
        raise


def parse_object_ref(spec: str) -> dict:
    """Parse 'RA-001', 'RA-001#RA-001-PART-IV', 'RA-001@0.3.0', or both."""
    rest, _, version = spec.partition("@")
    object_id, _, section = rest.partition("#")
    if not object_id.strip():
        raise typer.BadParameter(f"empty object id in {spec!r}")
    return {
        "object_id": object_id.strip(),
        "section_id": section.strip() or None,
        "expected_version": version.strip() or None,
    }


def parse_provider(spec: str) -> dict:
    """Parse 'claude:governance_critic' or 'claude' (uses configured default)."""
    provider, _, role = spec.partition(":")
    if not provider.strip():
        raise typer.BadParameter(f"empty provider in {spec!r}")
    return {"provider": provider.strip(), "role": role.strip() or None}


# -- init / status ---------------------------------------------------------

@app.command()
def init(
    path: Path = typer.Option(Path("."), "--path", "-p", help="Directory to create .conclave/ in"),
    principal: str = typer.Option(..., "--principal", help="Human constitutional authority."),
    kos_repository: str = typer.Option(None, "--kos-repository",
                                       help="KOS working tree for READ-ONLY inspection."),
    force: bool = typer.Option(False, "--force", help="Reinitialise config; data untouched."),
) -> None:
    """CREATE a CONCLAVE workspace. Writes .conclave/ and its config."""
    try:
        ws = Workspace.create(path, principal=principal, kos_repository=kos_repository, force=force)
    except ConclaveError as exc:
        _fail(str(exc))
        return
    typer.secho(f"workspace created: {ws.root}", fg=typer.colors.GREEN)
    typer.echo(f"  principal        : {principal}")
    typer.echo("  providers        : adrian, claude, gemini (manual relay)")
    typer.echo("  agents may merge : no")
    typer.echo(f"  kos repository   : {kos_repository or 'not configured'}"
               f"{' (read-only)' if kos_repository else ''}")


@app.command()
def status() -> None:
    """DISPLAY workspace state. Read-only; creates nothing."""
    ws, config = _ws()
    tasks = list_tasks(ws)
    outbox = list(ws.outbox_dir.glob("*.md")) if ws.outbox_dir.exists() else []
    inbox = list(ws.inbox_dir.glob("*")) if ws.inbox_dir.exists() else []
    entries = (
        sum(1 for ln in ws.ledger_path.read_text(encoding="utf-8").splitlines() if ln.strip())
        if ws.ledger_path.exists() else 0
    )

    typer.secho(f"CONCLAVE Bootstrap {config.get('bootstrap_version', '?')}", bold=True)
    typer.echo(f"  workspace     : {ws.root}")
    typer.echo(f"  principal     : {config.get('principal', '?')}")
    typer.echo(f"  kos repository: {config.get('kos_repository') or 'not configured'} "
               f"({config.get('kos_access', 'read-only')})")
    typer.echo("")
    typer.echo(f"  tasks         : {len(tasks)}")
    for t in tasks:
        versions = list_versions(ws, t)
        vs = ", ".join(f"v{v}" for v in versions) or "no packets"
        typer.echo(f"      - {t}  [{vs}]")
    typer.echo(f"  relay outbox  : {len(outbox)} prompt(s)")
    typer.echo(f"  relay inbox   : {len(inbox)} response(s)")
    typer.echo(f"  ledger entries: {entries}")


# -- task ------------------------------------------------------------------

@task_app.command("create")
def task_create(
    objective: str = typer.Option(..., "--objective", "-o", help="What this task is to achieve."),
    target: list[str] = typer.Option(None, "--target", "-t",
                                     help="Target object, may be modified. Repeatable. "
                                          "Format: ID[#SECTION][@VERSION]"),
    read_only: list[str] = typer.Option(None, "--read-only", "-r",
                                        help="Readable, NOT modifiable. Repeatable."),
    prohibited: list[str] = typer.Option(None, "--prohibited", "-x",
                                         help="Must not be read or modified. Repeatable."),
    provider: list[str] = typer.Option(None, "--provider", "-P",
                                       help="PROVIDER[:ROLE]. Repeatable."),
    constraint: list[str] = typer.Option(None, "--constraint", "-c", help="Repeatable."),
    criterion: list[str] = typer.Option(None, "--criterion", "-a",
                                        help="Acceptance criterion. Repeatable."),
    egress: str = typer.Option("relay-only", "--egress",
                               help="relay-only | non-constitutional | all"),
    interpreted: str = typer.Option(None, "--interpreted", help="Interpreted objective."),
    created_by: str = typer.Option(None, "--created-by", help="Defaults to workspace principal."),
) -> None:
    """CREATE a version-1 Task Packet. Immutable once written."""
    ws, config = _ws()

    providers_cfg = config.get("providers", {})
    assignments = []
    for spec in provider or []:
        parsed = parse_provider(spec)
        role = parsed["role"] or providers_cfg.get(parsed["provider"], {}).get(
            "default_role", "contributor"
        )
        assignments.append({"provider": parsed["provider"], "role": role})

    try:
        packet = build_packet(
            objective=objective,
            created_by=created_by or config.get("principal", "unknown"),
            target_objects=[parse_object_ref(s) for s in (target or [])],
            read_only_objects=[parse_object_ref(s) for s in (read_only or [])],
            prohibited_objects=[parse_object_ref(s) for s in (prohibited or [])],
            assigned_providers=assignments,
            egress={"policy": egress},
            constraints=list(constraint or []),
            acceptance_criteria=list(criterion or []),
            interpreted_objective=interpreted,
        )
        path = write_packet(ws, packet)
    except ConclaveError as exc:
        _fail(str(exc))
        return
    except Exception as exc:  # pydantic and parsing errors
        _fail(str(exc))
        return

    typer.secho(f"created {packet.ref}", fg=typer.colors.GREEN)
    typer.echo(f"  file        : {path}")
    typer.echo(f"  content_hash: {packet.content_hash}")
    typer.echo(f"  targets     : {len(packet.target_objects)}  "
               f"read-only: {len(packet.read_only_objects)}  "
               f"prohibited: {len(packet.prohibited_objects)}")
    typer.echo(f"  providers   : {', '.join(a.provider for a in packet.assigned_providers) or 'none'}")
    _record(ws, event_type="task_packet_created",
            subject_refs=[packet.ref],
            artifact_hashes={"task_packet": packet.content_hash},
            payload={"task_id": packet.task_id, "version": packet.version,
                     "path": str(path.relative_to(ws.root)),
                     "created_by": packet.created_by,
                     "target_count": len(packet.target_objects),
                     "providers": [a.provider for a in packet.assigned_providers]})

    typer.echo("")
    typer.secho("run 'conclave validate' before relay export.", fg=typer.colors.BRIGHT_BLACK)


@task_app.command("revise")
def task_revise(
    task_id: str = typer.Argument(..., help="Task to revise."),
    reason: str = typer.Option(..., "--reason", help="Why this revision exists."),
    objective: str = typer.Option(None, "--objective", help="Replacement objective."),
    target: list[str] = typer.Option(None, "--target", "-t", help="REPLACES the target set."),
    read_only: list[str] = typer.Option(None, "--read-only", "-r", help="REPLACES the read-only set."),
    prohibited: list[str] = typer.Option(None, "--prohibited", "-x", help="REPLACES the prohibited set."),
    clear_targets: bool = typer.Option(False, "--clear-targets", help="Set the target set to empty."),
    clear_read_only: bool = typer.Option(False, "--clear-read-only", help="Set the read-only set to empty."),
    clear_prohibited: bool = typer.Option(False, "--clear-prohibited", help="Set the prohibited set to empty."),
) -> None:
    """CREATE the next version as a new immutable packet. The predecessor is untouched."""
    ws, _ = _ws()
    version = latest_version(ws, task_id)
    if version is None:
        _fail(f"no packets found for task {task_id!r}")
        return

    # An omitted option and a requested empty set are different intentions and
    # must not be conflated. --clear-* is the unambiguous way to say "empty".
    for name, items, clear in (
        ("--target", target, clear_targets),
        ("--read-only", read_only, clear_read_only),
        ("--prohibited", prohibited, clear_prohibited),
    ):
        if items and clear:
            _fail(f"{name} and its --clear form are mutually exclusive")
            return

    previous = read_packet(ws, task_id, version)
    changes: dict = {}
    if objective is not None:
        changes["objective"] = objective
    if clear_targets:
        changes["target_objects"] = []
    elif target:
        changes["target_objects"] = [parse_object_ref(s) for s in target]
    if clear_read_only:
        changes["read_only_objects"] = []
    elif read_only:
        changes["read_only_objects"] = [parse_object_ref(s) for s in read_only]
    if clear_prohibited:
        changes["prohibited_objects"] = []
    elif prohibited:
        changes["prohibited_objects"] = [parse_object_ref(s) for s in prohibited]

    if not changes:
        _fail("a revision must change something")
        return

    try:
        revision = build_revision(previous, reason=reason, changes=changes)
        path = write_packet(ws, revision)
    except ConclaveError as exc:
        _fail(str(exc))
        return

    typer.secho(f"created {revision.ref}", fg=typer.colors.GREEN)
    typer.echo(f"  supersedes  : {revision.supersedes}  (unchanged on disk)")
    typer.echo(f"  file        : {path}")
    typer.echo(f"  content_hash: {revision.content_hash}")

    _record(ws, event_type="task_packet_revised",
            subject_refs=[revision.ref],
            artifact_hashes={"task_packet": revision.content_hash},
            payload={"task_id": revision.task_id, "version": revision.version,
                     "supersedes": revision.supersedes,
                     "revision_reason": revision.revision_reason,
                     "path": str(path.relative_to(ws.root))})


@task_app.command("list")
def task_list() -> None:
    """DISPLAY tasks and their packet versions. Read-only."""
    ws, _ = _ws()
    tasks = list_tasks(ws)
    if not tasks:
        typer.echo("no tasks")
        return
    for t in tasks:
        versions = list_versions(ws, t)
        typer.echo(f"{t}")
        for v in versions:
            try:
                p = read_packet(ws, t, v)
                typer.echo(f"   v{v}  {p.created_at}  {p.objective[:60]}")
            except Exception as exc:
                typer.secho(f"   v{v}  UNREADABLE: {exc}", fg=typer.colors.RED)


@task_app.command("show")
def task_show(
    task_id: str = typer.Argument(...),
    version: int = typer.Option(None, "--version", "-v", help="Defaults to latest."),
) -> None:
    """DISPLAY a Task Packet verbatim. Read-only."""
    ws, _ = _ws()
    v = version or latest_version(ws, task_id)
    if v is None:
        _fail(f"no packets found for task {task_id!r}")
        return
    path = packet_path(ws, task_id, v)
    if not path.exists():
        _fail(f"no packet at {path}")
        return
    typer.echo(path.read_text(encoding="utf-8"))


# -- validate --------------------------------------------------------------

@app.command()
def validate(
    task_id: str = typer.Argument(None, help="Task to validate. Omit to validate all."),
    version: int = typer.Option(None, "--version", "-v", help="Defaults to latest."),
    strict: bool = typer.Option(False, "--strict", help="Treat warnings as failures."),
) -> None:
    """Validate Task Packets. Reports schema, semantic and governance findings separately.

    Never repairs. A packet that fails validation is reported and left alone.
    """
    ws, config = _ws()

    targets: list[tuple[str, int]] = []
    if task_id:
        v = version or latest_version(ws, task_id)
        if v is None:
            _fail(f"no packets found for task {task_id!r}")
            return
        targets.append((task_id, v))
    else:
        for t in list_tasks(ws):
            for v in list_versions(ws, t):
                targets.append((t, v))

    if not targets:
        typer.echo("no packets to validate")
        return

    total_errors = 0
    total_warnings = 0
    governance_violations = 0

    for tid, v in targets:
        path = packet_path(ws, tid, v)
        report = validate_packet_file(path, config)
        ref = f"{tid}@v{v}"

        if report.ok and not report.warnings:
            typer.secho(f"PASS  {ref}", fg=typer.colors.GREEN)
            continue

        colour = typer.colors.RED if not report.ok else typer.colors.YELLOW
        typer.secho(f"{'FAIL' if not report.ok else 'WARN'}  {ref}", fg=colour, bold=True)

        for category in (Category.SCHEMA, Category.SEMANTIC, Category.GOVERNANCE):
            items = report.by_category(category)
            if not items:
                continue
            typer.echo(f"    {category.value}:")
            for f in items:
                c = typer.colors.RED if f.severity is Severity.ERROR else typer.colors.YELLOW
                loc = f" ({f.location})" if f.location else ""
                typer.secho(f"      [{f.severity.value}] {f.code}{loc}", fg=c)
                typer.echo(f"          {f.message}")

        total_errors += len(report.errors)
        total_warnings += len(report.warnings)
        if report.has_governance_violation:
            governance_violations += 1

    typer.echo("")
    typer.echo(f"{len(targets)} packet(s): {total_errors} error(s), {total_warnings} warning(s)")
    if governance_violations:
        typer.secho(
            f"{governance_violations} packet(s) contain GOVERNANCE violations. "
            "These are authority-boundary failures and are not for an agent to resolve.",
            fg=typer.colors.RED, bold=True,
        )

    if total_errors or (strict and total_warnings):
        raise typer.Exit(code=1)


# -- stubs -----------------------------------------------------------------

@relay_app.command("export")
def relay_export(
    task_id: str = typer.Argument(..., help="Task to export."),
    version: int = typer.Option(None, "--version", "-v", help="Defaults to latest."),
    provider: list[str] = typer.Option(None, "--provider", "-P",
                                       help="Limit to these providers. Repeatable."),
    force: bool = typer.Option(False, "--force",
                               help="Replace an existing, differing prompt. Requires --reason."),
    reason: str = typer.Option(None, "--reason",
                               help="Why the existing prompt is being replaced. Recorded."),
) -> None:
    """CREATE one independent prompt file per assigned provider.

    Refuses to export a packet with any validation error. The Task Packet is
    never modified.
    """
    ws, config = _ws()
    v = version or latest_version(ws, task_id)
    if v is None:
        _fail(f"no packets found for task {task_id!r}")
        return

    path = packet_path(ws, task_id, v)
    report = validate_packet_file(path, config)

    if not report.ok:
        typer.secho(f"refusing to export {task_id}@v{v}: packet has "
                    f"{len(report.errors)} validation error(s)", fg=typer.colors.RED, bold=True)
        for f in report.errors:
            typer.secho(f"  [{f.category.value}] {f.code}"
                        f"{f' (' + f.location + ')' if f.location else ''}", fg=typer.colors.RED)
            typer.echo(f"      {f.message}")
        typer.echo("")
        typer.echo("run 'conclave validate' for the full report.")
        raise typer.Exit(code=1)

    # Warnings do not block export, but governance and egress warnings concern
    # authority boundaries and are surfaced separately so they cannot be lost
    # in a wall of routine output.
    needs_confirmation = [
        f for f in report.warnings
        if f.category is Category.GOVERNANCE or (f.location or "").startswith("egress")
    ]
    other_warnings = [f for f in report.warnings if f not in needs_confirmation]

    if needs_confirmation:
        typer.echo("")
        typer.secho("GOVERNANCE / EGRESS WARNINGS — confirm before pasting anything "
                    "into a provider:", fg=typer.colors.YELLOW, bold=True)
        for f in needs_confirmation:
            typer.secho(f"  {f.code}{f' (' + f.location + ')' if f.location else ''}",
                        fg=typer.colors.YELLOW, bold=True)
            typer.echo(f"      {f.message}")
        typer.echo("")

    for f in other_warnings:
        typer.secho(f"  warning: {f.code} — {f.message}", fg=typer.colors.YELLOW)

    packet = read_packet(ws, task_id, v)
    try:
        results = export_prompts(ws, packet, config,
                                 providers=list(provider) if provider else None,
                                 force=force, reason=reason,
                                 authority=config.get("principal"))
    except ConclaveError as exc:
        _fail(str(exc))
        return

    typer.echo("")
    typer.secho(f"{packet.ref}", bold=True)
    typer.echo(f"  content_hash: {packet.content_hash}")
    typer.echo("")

    refused = 0
    for r in results:
        if r.status == "created":
            typer.secho(f"  exported  {r.provider:<10} {r.path.name}", fg=typer.colors.GREEN)
        elif r.status == "replaced":
            typer.secho(f"  REPLACED  {r.provider:<10} {r.path.name}",
                        fg=typer.colors.YELLOW, bold=True)
            typer.echo(f"            {r.detail} — recorded with reason")
        elif r.status == "unchanged":
            typer.secho(f"  unchanged {r.provider:<10} {r.path.name}",
                        fg=typer.colors.BRIGHT_BLACK)
        else:
            refused += 1
            typer.secho(f"  REFUSED   {r.provider:<10} {r.path.name}", fg=typer.colors.RED)
            typer.echo(f"            {r.detail}")

    for r in results:
        if r.status == "created":
            _record(ws, event_type="relay_prompt_exported",
                    subject_refs=[packet.ref],
                    artifact_hashes={"task_packet": packet.content_hash,
                                     "prompt": r.prompt_hash},
                    payload={"provider": r.provider, "role": r.role,
                             "prompt_file": r.path.name})
        elif r.status == "replaced":
            _record(ws, event_type="relay_prompt_replaced",
                    subject_refs=[packet.ref],
                    artifact_hashes={"task_packet": packet.content_hash,
                                     "prompt": r.prompt_hash},
                    payload={"provider": r.provider, "role": r.role,
                             "prompt_file": r.path.name,
                             "replacement_reason": reason,
                             "replacement_authority": config.get("principal")})

    typer.echo("")
    typer.echo(f"outbox: {ws.outbox_dir}")
    typer.echo("Open each file, paste it into that provider, save the reply for import.")
    typer.secho("Do not show one provider another's prompt or response.",
                fg=typer.colors.BRIGHT_BLACK)

    if refused:
        raise typer.Exit(code=1)


@relay_app.command("import")
def relay_import(
    response_file: Path = typer.Argument(..., help="Saved provider response."),
    prompt_hash: str = typer.Option(None, "--prompt-hash",
                                    help="Disambiguate when a prompt was replaced."),
) -> None:
    """CREATE a sealed Handoff Packet from a provider response.

    The raw response is preserved before parsing and is never altered,
    whatever the outcome.
    """
    ws, _ = _ws()
    try:
        result = import_response(ws, response_file, prompt_hash=prompt_hash)
    except ConclaveError as exc:
        _fail(str(exc))
        return

    typer.echo(f"raw response preserved: {result.raw_path.name}")
    typer.echo(f"  raw_response_hash: {result.raw_hash}")
    typer.echo("")

    if result.status != "duplicate":
        _record(ws, event_type="provider_response_preserved",
                actor=result.packet.provider if result.packet else "unknown-provider",
                authority_level="advisory_agent",
                artifact_hashes={"raw_response": result.raw_hash},
                payload={"raw_file": result.raw_path.name,
                         "note": "the exact bytes received, before parsing"})

    if result.status == "duplicate":
        typer.secho(f"DUPLICATE — {result.defects[0].message}.", fg=typer.colors.YELLOW)
        if result.handoff_path:
            typer.echo(f"  existing handoff: {result.handoff_path.name}")
        if result.repair_path:
            typer.echo(f"  existing repair : {result.repair_path.name}")
        typer.echo("  nothing was overwritten.")
        raise typer.Exit(code=0)

    if result.status == "rejected":
        typer.secho(f"REJECTED — {len(result.defects)} defect(s). No Handoff Packet created.",
                    fg=typer.colors.RED, bold=True)
        for d in result.defects:
            typer.secho(f"  {d.code}{f' ({d.location})' if d.location else ''}",
                        fg=typer.colors.RED)
            typer.echo(f"      {d.message}")
        typer.echo("")
        typer.echo(f"repair request written: {result.repair_path}")
        typer.echo("Send it to the same provider and import the corrected reply.")
        typer.secho("The rejected response is preserved unaltered and was not repaired.",
                    fg=typer.colors.BRIGHT_BLACK)
        _record(ws, event_type="provider_response_rejected",
                artifact_hashes={"raw_response": result.raw_hash},
                payload={"raw_file": result.raw_path.name,
                         "repair_file": result.repair_path.name if result.repair_path else None,
                         "defect_codes": sorted({d.code for d in result.defects}),
                         "note": "rejected at import; no Handoff Packet was created"})
        raise typer.Exit(code=1)

    p = result.packet
    typer.secho(f"imported {p.provider} response to {p.packet_ref}", fg=typer.colors.GREEN)
    typer.echo(f"  handoff     : {result.handoff_path.name}")
    typer.echo(f"  role        : {p.role}")
    typer.echo(f"  status      : {p.status}")
    typer.echo(f"  findings    : {len(p.findings)}")
    typer.echo(f"  unresolved  : {len(p.unresolved)}")
    typer.echo(f"  abstentions : {len(p.abstentions)}")
    typer.echo(f"  next action : {p.recommended_next_action}")
    typer.echo(f"  objects_touched: {sorted(p.touched_keys()) or 'none declared'}")
    _record(ws, event_type="handoff_packet_imported",
            actor=p.provider, authority_level="advisory_agent",
            subject_refs=[p.packet_ref],
            artifact_hashes={"handoff_packet": p.content_hash,
                             "raw_response": p.raw_response_hash,
                             "prompt": p.prompt_hash},
            payload={"provider": p.provider, "role": p.role,
                     "submission_status": p.status,
                     "recommended_next_action": p.recommended_next_action,
                     "declared_objects_touched": sorted(p.touched_keys()),
                     "handoff_file": result.handoff_path.name,
                     "note": "passed import validation; this asserts nothing about "
                             "whether its findings are correct"})

    typer.echo("")
    typer.secho("scope drift is not adjudicated in this build.",
                fg=typer.colors.BRIGHT_BLACK)


@scope_app.command("review")
def scope_review(
    handoff_file: Path = typer.Argument(None, help="Handoff Packet. Omit to review all."),
) -> None:
    """CREATE a sealed Scope Review comparing declared objects_touched against granted scope.\n\n    Idempotent: an existing attestation is verified and returned unchanged.\n    """
    ws, _ = _ws()

    if handoff_file:
        targets = [Path(handoff_file)]
    else:
        targets = sorted(ws.inbox_dir.glob("*.yaml"))
    if not targets:
        typer.echo("no handoff packets to review")
        return

    expansions = 0
    for path in targets:
        try:
            outcome = review_handoff(ws, path)
        except ConclaveError as exc:
            typer.secho(f"ERROR  {path.name}", fg=typer.colors.RED, bold=True)
            typer.echo(f"       {exc}")
            expansions += 1
            continue

        review, out_path = outcome.review, outcome.path
        suffix = "" if outcome.created else "  (existing attestation, unchanged)"

        # Recorded before display output, so a piped/truncated run cannot lose it.
        if outcome.created:
            _record(ws, event_type="scope_review_created",
                    subject_refs=[review.task_packet_ref],
                    artifact_hashes={"scope_review": review.content_hash,
                                     "handoff_packet": review.handoff_packet_hash,
                                     "task_packet": review.task_packet_hash},
                    payload={"provider": review.provider,
                             "evaluator_schema": review.schema_version,
                             "scope_status": review.scope_status,
                             "violation_count": review.violation_count,
                             "review_file": out_path.name,
                             "note": "an evaluator result under the named schema; it does "
                                     "not itself authorise remediation"})

        if review.scope_status == "within_scope":
            typer.secho(f"within_scope  {review.provider:<9} {review.task_packet_ref}{suffix}",
                        fg=typer.colors.GREEN)
        else:
            expansions += 1
            typer.secho(f"EXPANSION     {review.provider:<9} {review.task_packet_ref}{suffix}",
                        fg=typer.colors.RED, bold=True)

        for r in review.object_results:
            colour = typer.colors.GREEN if r.allowed else typer.colors.RED
            typer.secho(f"    {r.classification:<21} {r.key}  [{r.action}]", fg=colour)
            if not r.allowed:
                typer.echo(f"        {r.reason}")

        if review.scope_status == "expansion_detected":
            typer.echo("")
            typer.secho("    scope_status: expansion_detected", fg=typer.colors.RED, bold=True)
            typer.secho("    human_review_required: true", fg=typer.colors.RED, bold=True)

        typer.echo(f"    review: {out_path.name}")
        typer.echo("")


    typer.secho("Evaluated declared objects_touched only. Provider prose was not parsed, "
                "so undeclared work is not detected here.", fg=typer.colors.BRIGHT_BLACK)

    if expansions:
        raise typer.Exit(code=1)


@council_app.command("review")
def council_review(
    task_id: str = typer.Argument(..., help="Task to aggregate."),
    version: int = typer.Option(None, "--version", "-v", help="Defaults to latest."),
) -> None:
    """CREATE a Council Review Packet (canonical YAML) and PROJECT it to Markdown.\n\n    Idempotent for an unchanged source set.\n    """
    ws, _ = _ws()
    v = version or latest_version(ws, task_id)
    if v is None:
        _fail(f"no packets found for task {task_id!r}")
        return

    try:
        outcome = review_task(ws, task_id, v)
    except ConclaveError as exc:
        _fail(str(exc))
        return

    r = outcome.review

    # Recorded before any display output. If the operator pipes this command
    # into `head`, SIGPIPE terminates the process mid-write — and an event
    # appended after the printing would simply be lost.
    if outcome.created:
        _record(ws, event_type="council_review_created",
                subject_refs=[r.task_packet_ref, r.council_review_id],
                artifact_hashes={"council_review": r.content_hash,
                                 "task_packet": r.task_packet_hash},
                payload={"council_review_id": r.council_review_id,
                         "review_status": r.review_status,
                         "submission_count": len(r.submissions),
                         "missing_providers": r.missing_providers,
                         "governance_alert_count": len(r.governance_alerts),
                         "yaml_file": outcome.yaml_path.name,
                         "markdown_file": outcome.markdown_path.name,
                         "note": "a review artifact was produced; this asserts nothing "
                                 "about whether its recommendations were accepted"})

    colour = {
        "ready_for_human_review": typer.colors.GREEN,
        "incomplete": typer.colors.YELLOW,
        "blocked_by_governance": typer.colors.RED,
        "ambiguous_submissions": typer.colors.RED,
    }[r.review_status]

    typer.secho(f"{r.review_status.upper()}", fg=colour, bold=True)
    typer.echo(f"  council_review_id: {r.council_review_id}")
    typer.echo(f"  content_hash     : {r.content_hash}")
    if not outcome.created:
        typer.secho("  (existing review, unchanged source set)", fg=typer.colors.BRIGHT_BLACK)
    typer.echo("")

    typer.echo(f"  submissions : {len(r.submissions)} of {len(r.providers_expected)} expected")
    if r.missing_providers:
        typer.secho(f"  missing     : {', '.join(r.missing_providers)}", fg=typer.colors.YELLOW)
    typer.echo(f"  agreements  : {len(r.structural_agreements)}")
    typer.echo(f"  disagreements: {len(r.structural_disagreements)}")
    typer.echo(f"  findings    : {len(r.consolidated_findings)}")
    typer.echo(f"  unresolved  : {len(r.unresolved_items)}")

    if r.governance_alerts:
        typer.echo("")
        typer.secho(f"  GOVERNANCE ALERTS ({len(r.governance_alerts)}):",
                    fg=typer.colors.RED, bold=True)
        for a in r.governance_alerts:
            typer.secho(f"    {a['kind']}  {a.get('provider', '')} {a.get('object', '')}".rstrip(),
                        fg=typer.colors.RED)

    typer.echo("")
    typer.echo(f"  yaml    : {outcome.yaml_path.name}   (authoritative)")
    typer.echo(f"  markdown: {outcome.markdown_path.name}  (projection)")
    typer.echo("")
    typer.secho("  decision: pending — reserved for the constitutional authority.",
                fg=typer.colors.BRIGHT_BLACK)
    typer.secho("  CONCLAVE has not approved, ratified, commissioned or merged anything.",
                fg=typer.colors.BRIGHT_BLACK)


@ledger_app.command("init")
def ledger_init() -> None:
    """CREATE the ledger: genesis plus one snapshot attesting existing artifacts."""
    ws, config = _ws()
    try:
        events = ledger.initialise(ws, config)
    except ConclaveError as exc:
        _fail(str(exc))
        return

    if len(events) > 2:
        typer.secho("ledger already initialised; nothing changed", fg=typer.colors.YELLOW)
    else:
        typer.secho("ledger initialised", fg=typer.colors.GREEN)
    snapshot = next((e for e in events if e["event_type"] == "workspace_snapshot_attested"), None)
    typer.echo(f"  entries    : {len(ledger.read_raw_lines(ws))}")
    typer.echo(f"  chain hash : {ledger.chain_hash(ws)}")
    if snapshot:
        typer.echo(f"  attested   : {snapshot['payload'].get('artifact_count', 0)} "
                   "pre-existing artifact(s)")
        typer.echo("")
        typer.secho("  Snapshot records that these artifacts existed with these hashes at "
                    "snapshot time.", fg=typer.colors.BRIGHT_BLACK)
        typer.secho("  It asserts nothing about when they were created or in what order. "
                    "No history was fabricated.", fg=typer.colors.BRIGHT_BLACK)


@ledger_app.command("verify")
def ledger_verify() -> None:
    """Verify the ledger hash chain from genesis. Never repairs."""
    ws, _ = _ws()
    report = ledger.verify(ws)

    typer.echo(f"entries          : {report.entry_count}")
    typer.echo(f"final chain hash : {report.final_chain_hash or '—'}")
    typer.echo("")

    if report.ok:
        typer.secho("chain verified", fg=typer.colors.GREEN, bold=True)
        typer.echo("  genesis position and uniqueness  ok")
        typer.echo("  contiguous sequence              ok")
        typer.echo("  previous-hash linkage            ok")
        typer.echo("  entry hashes                     ok")
        typer.echo("  event id uniqueness              ok")
        typer.echo("  required fields                  ok")
        typer.echo("  authority vocabulary             ok")
        return

    typer.secho(f"VERIFICATION FAILED — {len(report.defects)} defect(s)",
                fg=typer.colors.RED, bold=True)
    for d in report.defects:
        typer.secho(f"  {d.code}" + (f" [line {d.line}]" if d.line else ""),
                    fg=typer.colors.RED)
        typer.echo(f"      {d.message}")
    typer.echo("")
    typer.secho("The ledger has NOT been repaired. Nothing was rewritten.",
                fg=typer.colors.BRIGHT_BLACK)
    raise typer.Exit(code=1)


@ledger_app.command("reconcile")
def ledger_reconcile() -> None:
    """Append operational events for artifacts that have none.

    Reconstructs only what immutable artifact metadata establishes. Refuses
    ambiguous reconstruction. Never infers human decisions.
    """
    ws, _ = _ws()
    try:
        report = reconcile(ws)
    except ConclaveError as exc:
        _fail(str(exc))
        return

    typer.echo(f"created         : {len(report.created)}")
    typer.echo(f"already recorded: {len(report.already_recorded)}")
    typer.echo(f"unresolved      : {len(report.unresolved)}")
    typer.echo("")

    for e in report.created:
        unknown = " (original time unknown)" if e["payload"].get(
            "original_event_time_unknown") else ""
        typer.secho(f"  + {e['event_type']:<28} {e['payload'].get('source_artifact', '')}"
                    f"{unknown}", fg=typer.colors.GREEN)

    if report.unresolved:
        typer.echo("")
        typer.secho("UNRESOLVED — not reconstructed, and not guessed at:",
                    fg=typer.colors.YELLOW, bold=True)
        for u in report.unresolved:
            typer.secho(f"  {u.source}", fg=typer.colors.YELLOW)
            typer.echo(f"      {u.reason}")

    if report.created:
        typer.echo("")
        typer.secho("Reconciled events record that an artifact existed. Their sequence "
                    "numbers reflect", fg=typer.colors.BRIGHT_BLACK)
        typer.secho("when they were reconciled, not when the operations occurred.",
                    fg=typer.colors.BRIGHT_BLACK)

    typer.echo("")
    typer.echo(f"chain hash: {ledger.chain_hash(ws)}")


@ledger_app.command("show")
def ledger_show(limit: int = typer.Option(20, "--limit", "-n")) -> None:
    """Display recent ledger entries. Read-only; creates nothing."""
    ws, _ = _ws()
    events = ledger.read_events(ws)
    if not events:
        typer.echo("ledger is empty; run 'conclave ledger init'")
        return
    for e in events[-limit:]:
        typer.echo(f"{e['sequence']:>4}  {e['recorded_at']}  {e['event_type']:<28} "
                   f"{e['actor']:<10} {e['authority_level']}")


@app.command()
def version() -> None:
    """Print the CONCLAVE version and schema version."""
    typer.echo(f"conclave {__version__}")
    typer.echo(f"schema  {SCHEMA_VERSION}")


if __name__ == "__main__":
    app()
