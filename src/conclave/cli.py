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
from .context import ContextSource, build_context_bundle, write_context_bundle
from .contextrelay import write_context_relay_export
from .concurrency import RetryPolicy, execute_concurrent, write_concurrent_outcome
from .decision import prepare_decision, read_instruction, record_decision
from .errors import ConclaveError
from .execution import execute_stage, read_run_record, write_run_record
from .handoff import import_response
from .models import SCHEMA_VERSION
from .orchestration import orchestrate_batch
from .reconcile import reconcile
from .relay import export_prompts
from .providers import EgressDecision, FixtureAdapter, read_egress_decision
from .routing import ProviderCapability, TokenBudget, build_route, write_route_plan
from .runhandoff import convert_run
from .scope import review_handoff
from .synthesis import execute_synthesis, synthesis_target
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
context_app = typer.Typer(
    help="Governed context bundles. Sealed, provenance-bearing, and write-once.",
    no_args_is_help=True)
route_app = typer.Typer(
    help="Adaptive provider route plans and token ceilings.",
    no_args_is_help=True)
run_app = typer.Typer(
    help="Execute one authorized route stage and preserve its normalized response.",
    no_args_is_help=True)
orchestrate_app = typer.Typer(
    help="Advance sealed execution evidence to a Council Review and explicit pause.",
    no_args_is_help=True)
identity_app = typer.Typer(
    help="Opt-in IDM verification modes. Identity never creates authority or membership.",
    no_args_is_help=True)
evidence_app = typer.Typer(
    help="Public signed-evidence coordination. No private-key or signing command exists.",
    no_args_is_help=True)

app.add_typer(task_app, name="task")
app.add_typer(relay_app, name="relay")
app.add_typer(scope_app, name="scope")
app.add_typer(council_app, name="council")
app.add_typer(ledger_app, name="ledger")
app.add_typer(context_app, name="context")
app.add_typer(route_app, name="route")
app.add_typer(run_app, name="run")
app.add_typer(orchestrate_app, name="orchestrate")
app.add_typer(identity_app, name="identity")
app.add_typer(evidence_app, name="evidence")


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


def parse_capability(spec: str) -> tuple[str, str]:
    provider, separator, role = spec.partition(":")
    if not separator or not provider.strip() or not role.strip():
        raise typer.BadParameter("capability must be provider:role")
    return provider.strip(), role.strip()


@context_app.command("create")
def context_create(
    task_id: str = typer.Argument(...),
    manifest: Path = typer.Option(..., "--manifest", "-m",
                                  help="YAML list or {sources: [...]} with source content."),
    version: int = typer.Option(1, "--version", "-v", min=1),
) -> None:
    """CREATE an immutable context bundle from an explicit source manifest."""
    ws, _ = _ws()
    try:
        packet = read_packet(ws, task_id, version)
        raw = yaml.safe_load(manifest.read_text(encoding="utf-8"))
        items = raw.get("sources") if isinstance(raw, dict) else raw
        if not isinstance(items, list):
            raise ConclaveError("context manifest must contain a sources list")
        sources = [ContextSource.seal(
            object_id=item["object_id"], status=item["status"],
            authority=item["authority"], classification=item["classification"],
            content=item["content"],
        ) for item in items]
        bundle = build_context_bundle(
            packet_ref=packet.ref, packet_content_hash=packet.content_hash or "",
            sources=sources,
        )
        path, created = write_context_bundle(ws, bundle)
    except (ConclaveError, OSError, KeyError, TypeError, ValueError) as exc:
        _fail(str(exc))
        return
    typer.echo(f"{'created' if created else 'unchanged'}: {path}")
    typer.echo(f"context hash: {bundle.content_hash}")
    if created:
        _record(
            ws, event_type="context_bundle_created", actor="conclave",
            authority_level="system", subject_refs=[packet.ref],
            artifact_hashes={"context_bundle": bundle.content_hash},
            payload={"source_artifact": path.relative_to(ws.root).as_posix()},
        )


@route_app.command("plan")
def route_plan(
    task_id: str = typer.Argument(...),
    risk: str = typer.Option(..., "--risk"),
    capability: list[str] = typer.Option(
        ..., "--capability", "-c", help="Repeat provider:role."),
    version: int = typer.Option(1, "--version", "-v", min=1),
    max_input_tokens: int = typer.Option(..., "--max-input-tokens", min=1),
    max_output_tokens: int = typer.Option(..., "--max-output-tokens", min=1),
) -> None:
    """CREATE a deterministic adaptive route plan. Makes no provider call."""
    ws, _ = _ws()
    try:
        packet = read_packet(ws, task_id, version)
        grouped: dict[str, set[str]] = {}
        for spec in capability:
            provider, role = parse_capability(spec)
            grouped.setdefault(provider, set()).add(role)
        capabilities = [
            ProviderCapability(provider=provider, roles=frozenset(roles))
            for provider, roles in sorted(grouped.items())
        ]
        plan = build_route(
            packet_ref=packet.ref, risk=risk, capabilities=capabilities,
            budget=TokenBudget(
                max_input_tokens=max_input_tokens,
                max_output_tokens=max_output_tokens,
            ),
        )
        path, created = write_route_plan(ws, plan)
    except (ConclaveError, OSError, TypeError, ValueError) as exc:
        _fail(str(exc))
        return
    typer.echo(f"{'created' if created else 'unchanged'}: {path}")
    for stage in plan.stages:
        typer.echo(f"  {stage.role}: {stage.provider}")
    if created:
        _record(
            ws, event_type="route_plan_created", actor="conclave",
            authority_level="system", subject_refs=[packet.ref],
            artifact_hashes={"route_plan": plan.content_hash},
            payload={"source_artifact": path.relative_to(ws.root).as_posix()},
        )


@run_app.command("fixture")
def run_fixture(
    context_file: Path = typer.Option(..., "--context"),
    route_file: Path = typer.Option(..., "--route"),
    prompt_file: Path = typer.Option(..., "--prompt"),
    response_file: Path = typer.Option(..., "--response"),
    model: str = typer.Option("fixture-model", "--model"),
    stage_index: int = typer.Option(0, "--stage-index", min=0),
    estimated_input_tokens: int = typer.Option(..., "--estimated-input-tokens", min=0),
) -> None:
    """EXECUTE a local fixture adapter. No network or provider account is used."""
    from .context import read_context_bundle
    from .routing import read_route_plan

    ws, _ = _ws()
    try:
        bundle = read_context_bundle(context_file)
        plan = read_route_plan(route_file)
        task_id, version_text = bundle.packet_ref.rsplit("@v", 1)
        packet = read_packet(ws, task_id, int(version_text))
        stage = plan.stages[stage_index]
        adapter = FixtureAdapter(
            provider=stage.provider,
            response_text=response_file.read_text(encoding="utf-8"),
        )
        decision = EgressDecision(
            allowed=True,
            transports=frozenset({"fixture"}),
            classifications=frozenset(
                source.classification for source in bundle.sources
            ),
            authority="CONCLAVE",
            decision_ref="LOCAL-FIXTURE-NO-EGRESS",
        )
        record = execute_stage(
            packet=packet, bundle=bundle, plan=plan, stage_index=stage_index,
            adapter=adapter, decision=decision, model=model,
            prompt=prompt_file.read_text(encoding="utf-8"),
            estimated_input_tokens=estimated_input_tokens,
            prior_runs=[
                prior for prior in (
                    read_run_record(path) for path in ws.runs_dir.glob("*.yaml")
                )
                if prior.route_plan_hash == plan.content_hash
                and prior.stage_index < stage_index
            ],
        )
        path, created = write_run_record(ws, record)
    except (ConclaveError, OSError, IndexError, TypeError, ValueError) as exc:
        _fail(str(exc))
        return
    typer.echo(f"{'created' if created else 'unchanged'}: {path}")
    typer.echo(f"status: {record.status}")
    typer.echo(
        f"tokens: input={record.response.usage.input_tokens} "
        f"output={record.response.usage.output_tokens}"
    )
    if created:
        _record(
            ws, event_type="provider_run_captured", actor="conclave",
            authority_level="system", subject_refs=[record.packet_ref],
            artifact_hashes={"provider_run": record.content_hash},
            payload={
                "source_artifact": path.relative_to(ws.root).as_posix(),
                "provider": record.response.provider,
                "role": record.role,
                "status": record.status,
            },
        )


@run_app.command("live")
def run_live(
    context_file: Path = typer.Option(..., "--context"),
    route_file: Path = typer.Option(..., "--route"),
    prompt_file: Path = typer.Option(..., "--prompt"),
    egress_decision_file: Path = typer.Option(
        ..., "--egress-decision",
        help="Principal-authored D7 policy permitting this provider transport.",
    ),
    model: str = typer.Option(..., "--model"),
    stage_index: int = typer.Option(0, "--stage-index", min=0),
    estimated_input_tokens: int = typer.Option(
        ..., "--estimated-input-tokens", min=0
    ),
    timeout_seconds: float = typer.Option(120.0, "--timeout", min=1.0),
    identity_verification: str | None = typer.Option(
        None, "--identity-verification",
        help="Workspace-relative immutable identity verification record."),
    evidence_binding: str | None = typer.Option(
        None, "--evidence-binding",
        help="Workspace-relative signed evidence binding required in attested mode."),
) -> None:
    """EXECUTE one live provider stage after explicit D7 authorization."""
    from .context import read_context_bundle
    from .live_providers import ClaudeAdapter, GeminiAdapter, OpenAIAdapter
    from .routing import read_route_plan

    ws, config = _ws()
    try:
        bundle = read_context_bundle(context_file)
        plan = read_route_plan(route_file)
        task_id, version_text = bundle.packet_ref.rsplit("@v", 1)
        packet = read_packet(ws, task_id, int(version_text))
        stage = plan.stages[stage_index]
        decision = read_egress_decision(
            egress_decision_file, principal=config.get("principal", ""), workspace=ws,
            identity_verification_reference=identity_verification,
            signed_evidence_binding_reference=evidence_binding,
        )
        if stage.provider in {"adrian", "openai"}:
            adapter = OpenAIAdapter(
                provider=stage.provider, timeout_seconds=timeout_seconds
            )
        elif stage.provider == "claude":
            adapter = ClaudeAdapter(timeout_seconds=timeout_seconds)
        elif stage.provider == "gemini":
            adapter = GeminiAdapter(timeout_seconds=timeout_seconds)
        else:
            raise ConclaveError(
                f"no live adapter is registered for provider {stage.provider!r}"
            )
        record = execute_stage(
            packet=packet, bundle=bundle, plan=plan, stage_index=stage_index,
            adapter=adapter, decision=decision, model=model,
            prompt=prompt_file.read_text(encoding="utf-8"),
            estimated_input_tokens=estimated_input_tokens,
            prior_runs=[
                prior for prior in (
                    read_run_record(path) for path in ws.runs_dir.glob("*.yaml")
                )
                if prior.route_plan_hash == plan.content_hash
                and prior.stage_index < stage_index
            ],
        )
        path, created = write_run_record(ws, record)
    except (ConclaveError, OSError, IndexError, TypeError, ValueError) as exc:
        _fail(str(exc))
        return
    typer.echo(f"{'created' if created else 'unchanged'}: {path}")
    typer.echo(f"provider: {record.response.provider}")
    typer.echo(f"model: {record.response.model}")
    typer.echo(f"status: {record.status}")
    typer.echo(
        f"tokens: input={record.response.usage.input_tokens} "
        f"cached_input={record.response.usage.cached_input_tokens} "
        f"output={record.response.usage.output_tokens} "
        f"reasoning_output={record.response.usage.reasoning_output_tokens}"
    )
    if created:
        _record(
            ws, event_type="provider_run_captured", actor="conclave",
            authority_level="system", subject_refs=[record.packet_ref],
            artifact_hashes={"provider_run": record.content_hash},
            payload={
                "source_artifact": path.relative_to(ws.root).as_posix(),
                "provider": record.response.provider,
                "role": record.role,
                "status": record.status,
                "egress_decision_ref": decision.decision_ref,
            },
        )


def _indexed_values(values: list[str], *, label: str) -> dict[int, str]:
    parsed: dict[int, str] = {}
    for value in values:
        try:
            index_text, item = value.split(":", 1)
            index = int(index_text)
        except (ValueError, TypeError) as exc:
            raise ConclaveError(f"{label} must use STAGE:VALUE, got {value!r}") from exc
        if index < 0 or not item:
            raise ConclaveError(f"{label} must use a non-negative stage and non-empty value")
        if index in parsed:
            raise ConclaveError(f"{label} repeats stage {index}")
        parsed[index] = item
    return parsed


@run_app.command("concurrent-live")
def run_concurrent_live(
    context_file: Path = typer.Option(..., "--context"),
    route_file: Path = typer.Option(..., "--route"),
    egress_decision_file: Path = typer.Option(..., "--egress-decision"),
    stage_indices: list[int] = typer.Option(
        [], "--stage", min=0,
        help="Repeat stage index. Default: the first independent wave."),
    model_specs: list[str] = typer.Option(
        ..., "--model", help="Repeat STAGE:MODEL."),
    prompt_specs: list[str] = typer.Option(
        ..., "--prompt", help="Repeat STAGE:FILE."),
    estimate_specs: list[str] = typer.Option(
        ..., "--estimated-input", help="Repeat STAGE:TOKENS."),
    max_workers: int = typer.Option(3, "--max-workers", min=1, max=8),
    max_attempts: int = typer.Option(1, "--max-attempts", min=1, max=3),
    fail_fast: bool = typer.Option(False, "--fail-fast"),
    timeout_seconds: float = typer.Option(120.0, "--timeout", min=1.0),
    identity_verification: str | None = typer.Option(
        None, "--identity-verification"),
    evidence_binding: str | None = typer.Option(None, "--evidence-binding"),
) -> None:
    """EXECUTE an isolated lead/critic/verifier wave concurrently.

    A synthesizer is never admitted. Failed provider attempts may have unknown
    billable usage; the batch record states when token totals are incomplete.
    """
    from .context import read_context_bundle
    from .live_providers import ClaudeAdapter, GeminiAdapter, OpenAIAdapter
    from .routing import read_route_plan

    ws, config = _ws()
    try:
        bundle = read_context_bundle(context_file)
        plan = read_route_plan(route_file)
        task_id, version_text = bundle.packet_ref.rsplit("@v", 1)
        packet = read_packet(ws, task_id, int(version_text))
        decision = read_egress_decision(
            egress_decision_file, principal=config.get("principal", ""), workspace=ws,
            identity_verification_reference=identity_verification,
            signed_evidence_binding_reference=evidence_binding,
        )
        if stage_indices:
            indices = tuple(sorted(stage_indices))
        else:
            indices = tuple(
                index for index, stage in enumerate(plan.stages)
                if stage.independent and stage.role != "synthesizer"
            )
        models = _indexed_values(model_specs, label="--model")
        prompt_paths = _indexed_values(prompt_specs, label="--prompt")
        estimate_text = _indexed_values(estimate_specs, label="--estimated-input")
        try:
            estimates = {index: int(value) for index, value in estimate_text.items()}
        except ValueError as exc:
            raise ConclaveError("--estimated-input values must be integers") from exc
        prompts = {
            index: Path(path).read_text(encoding="utf-8")
            for index, path in prompt_paths.items()
        }
        existing_selected = sorted({
            run.stage_index
            for run in (
                read_run_record(path) for path in ws.runs_dir.glob("*.yaml")
            )
            if run.route_plan_hash == plan.content_hash
            and run.stage_index in indices
        })
        if existing_selected:
            raise ConclaveError(
                "refusing duplicate provider calls: this Route Plan already has "
                f"captured runs for selected stages {existing_selected}"
            )
        adapters = {}
        for index in indices:
            stage = plan.stages[index]
            if stage.provider in {"adrian", "openai"}:
                adapters[index] = OpenAIAdapter(
                    provider=stage.provider, timeout_seconds=timeout_seconds
                )
            elif stage.provider == "claude":
                adapters[index] = ClaudeAdapter(timeout_seconds=timeout_seconds)
            elif stage.provider == "gemini":
                adapters[index] = GeminiAdapter(timeout_seconds=timeout_seconds)
            else:
                raise ConclaveError(
                    f"no live adapter is registered for provider {stage.provider!r}"
                )
        prior_runs = tuple(
            sorted(
                (
                    run for run in (
                        read_run_record(path) for path in ws.runs_dir.glob("*.yaml")
                    )
                    if run.route_plan_hash == plan.content_hash
                    and run.stage_index < indices[0]
                ),
                key=lambda run: run.stage_index,
            )
        )
        outcome = execute_concurrent(
            packet=packet, bundle=bundle, plan=plan, stage_indices=indices,
            adapters=adapters, decisions={index: decision for index in indices},
            models=models, prompts=prompts, estimated_input_tokens=estimates,
            prior_runs=prior_runs, max_workers=max_workers,
            retry_policy=RetryPolicy(max_attempts=max_attempts), fail_fast=fail_fast,
        )
        stored = write_concurrent_outcome(ws, outcome)
    except (ConclaveError, OSError, IndexError, TypeError, ValueError) as exc:
        _fail(str(exc))
        return

    for run, (path, created) in zip(outcome.runs, stored.run_paths):
        if created:
            _record(
                ws, event_type="provider_run_captured", actor="conclave",
                authority_level="system", subject_refs=[run.packet_ref],
                artifact_hashes={"provider_run": run.content_hash},
                payload={
                    "source_artifact": path.relative_to(ws.root).as_posix(),
                    "provider": run.response.provider, "role": run.role,
                    "status": run.status, "egress_decision_ref": run.egress_decision_ref,
                    "execution_mode": "concurrent-independent-wave",
                },
            )
    if stored.batch_created:
        _record(
            ws, event_type="execution_batch_recorded", actor="conclave",
            authority_level="system", subject_refs=[outcome.record.packet_ref],
            artifact_hashes={
                "execution_batch": outcome.record.content_hash,
                "route_plan": outcome.record.route_plan_hash,
                "context_bundle": outcome.record.context_bundle_hash,
                "task_packet": outcome.record.task_packet_hash,
            },
            payload={
                "source_artifact": stored.batch_path.relative_to(ws.root).as_posix(),
                "batch_id": outcome.record.batch_id,
                "status": outcome.record.status,
                "stage_indices": list(outcome.record.stage_indices),
                "usage_complete": outcome.record.usage_complete,
            },
        )

    typer.secho(
        f"CONCURRENT WAVE {outcome.record.status.upper()}",
        fg=(typer.colors.GREEN if outcome.record.status == "completed"
            else typer.colors.YELLOW), bold=True,
    )
    for result in outcome.record.stage_results:
        typer.echo(
            f"  stage {result.stage_index} {result.provider}:{result.role} "
            f"{result.status} attempts={result.attempts}"
        )
    typer.echo(
        f"  tokens: input={outcome.record.wave_input_tokens} "
        f"output={outcome.record.wave_output_tokens} "
        f"usage_complete={str(outcome.record.usage_complete).lower()}"
    )
    typer.echo(f"  batch: {stored.batch_path}")
    if outcome.record.status != "completed":
        raise typer.Exit(code=1)


@run_app.command("handoff")
def run_handoff(
    run_file: Path = typer.Argument(..., help="Sealed Provider Run YAML."),
    scope: bool = typer.Option(
        True, "--scope/--no-scope", help="Create the existing Scope Review immediately."),
) -> None:
    """PROJECT a completed Provider Run into a validated Handoff Packet."""
    ws, _ = _ws()
    try:
        result = convert_run(ws, run_file)
        scope_outcome = review_handoff(ws, result.handoff_path) if scope else None
    except (ConclaveError, OSError, TypeError, ValueError) as exc:
        _fail(str(exc))
        return
    typer.echo(
        f"{'created' if result.created else 'unchanged'} handoff: "
        f"{result.handoff_path}"
    )
    typer.echo(f"raw response: {result.raw_path}")
    if result.created:
        packet = result.packet
        _record(
            ws, event_type="provider_response_preserved",
            actor=packet.provider, authority_level="advisory_agent",
            artifact_hashes={"raw_response": packet.raw_response_hash},
            payload={
                "raw_file": result.raw_path.name,
                "source_run": Path(run_file).name,
                "note": "normalized provider response text captured by sealed Run Record",
            },
        )
        _record(
            ws, event_type="handoff_packet_imported",
            actor=packet.provider, authority_level="advisory_agent",
            subject_refs=[packet.packet_ref],
            artifact_hashes={
                "handoff_packet": packet.content_hash,
                "raw_response": packet.raw_response_hash,
                "prompt": packet.prompt_hash,
                "provider_run": packet.run_record_hash,
            },
            payload={
                "provider": packet.provider, "role": packet.role,
                "submission_status": packet.status,
                "recommended_next_action": packet.recommended_next_action,
                "declared_objects_touched": sorted(packet.touched_keys()),
                "handoff_file": result.handoff_path.name,
                "source_run": Path(run_file).name,
                "note": "projected from a verified completed Provider Run",
            },
        )
    if scope_outcome:
        typer.echo(
            f"{'created' if scope_outcome.created else 'unchanged'} scope: "
            f"{scope_outcome.path}"
        )
        if scope_outcome.created:
            review = scope_outcome.review
            _record(
                ws, event_type="scope_review_created",
                subject_refs=[review.task_packet_ref],
                artifact_hashes={
                    "scope_review": review.content_hash,
                    "handoff_packet": review.handoff_packet_hash,
                    "task_packet": review.task_packet_hash,
                },
                payload={
                    "provider": review.provider,
                    "evaluator_schema": review.schema_version,
                    "scope_status": review.scope_status,
                    "violation_count": review.violation_count,
                    "source_artifact": scope_outcome.path.relative_to(ws.root).as_posix(),
                    "note": "an evaluator result under the named schema; it does "
                            "not itself authorise remediation",
                },
            )


@orchestrate_app.command("batch")
def orchestrate_batch_command(
    batch_file: Path = typer.Argument(
        ..., exists=True, dir_okay=False, help="Sealed Execution Batch YAML."),
) -> None:
    """PROJECT a completed batch through Handoff, Scope, and Council stages."""
    ws, _ = _ws()
    try:
        outcome = orchestrate_batch(ws, batch_file)
    except (ConclaveError, OSError, TypeError, ValueError) as exc:
        _fail(str(exc))
        return

    for conversion, scope in zip(outcome.conversions, outcome.scopes):
        packet = conversion.packet
        if conversion.created:
            _record(
                ws, event_type="provider_response_preserved",
                actor=packet.provider, authority_level="advisory_agent",
                artifact_hashes={"raw_response": packet.raw_response_hash},
                payload={
                    "raw_file": conversion.raw_path.name,
                    "source_run": next(
                        stage.run_file for stage in outcome.record.processed_stages
                        if stage.handoff_content_hash == packet.content_hash
                    ),
                    "note": "normalized provider response text captured by sealed Run Record",
                },
            )
            _record(
                ws, event_type="handoff_packet_imported",
                actor=packet.provider, authority_level="advisory_agent",
                subject_refs=[packet.packet_ref],
                artifact_hashes={
                    "handoff_packet": packet.content_hash,
                    "raw_response": packet.raw_response_hash,
                    "prompt": packet.prompt_hash,
                    "provider_run": packet.run_record_hash,
                },
                payload={
                    "provider": packet.provider, "role": packet.role,
                    "submission_status": packet.status,
                    "recommended_next_action": packet.recommended_next_action,
                    "declared_objects_touched": sorted(packet.touched_keys()),
                    "handoff_file": conversion.handoff_path.name,
                    "source_run": next(
                        stage.run_file for stage in outcome.record.processed_stages
                        if stage.handoff_content_hash == packet.content_hash
                    ),
                    "note": "projected from a verified completed Provider Run",
                },
            )
        if scope.created:
            review = scope.review
            _record(
                ws, event_type="scope_review_created",
                subject_refs=[review.task_packet_ref],
                artifact_hashes={
                    "scope_review": review.content_hash,
                    "handoff_packet": review.handoff_packet_hash,
                    "task_packet": review.task_packet_hash,
                },
                payload={
                    "provider": review.provider,
                    "evaluator_schema": review.schema_version,
                    "scope_status": review.scope_status,
                    "violation_count": review.violation_count,
                    "source_artifact": scope.path.relative_to(ws.root).as_posix(),
                    "note": "an evaluator result under the named schema; it does not "
                            "itself authorise remediation",
                },
            )

    council = outcome.council.review
    if outcome.council.created:
        _record(
            ws, event_type="council_review_created",
            subject_refs=[council.task_packet_ref, council.council_review_id],
            artifact_hashes={
                "council_review": council.content_hash,
                "task_packet": council.task_packet_hash,
                **({"route_plan": council.route_plan_hash}
                   if council.route_plan_hash else {}),
            },
            payload={
                "council_review_id": council.council_review_id,
                "review_status": council.review_status,
                "submission_count": len(council.submissions),
                "missing_providers": council.missing_providers,
                "governance_alert_count": len(council.governance_alerts),
                "selection_basis": council.selection_basis,
                "yaml_file": outcome.council.yaml_path.name,
                "markdown_file": outcome.council.markdown_path.name,
                "note": "a review artifact was produced; this asserts nothing about "
                        "whether its recommendations were accepted",
            },
        )
    if outcome.created:
        _record(
            ws, event_type="orchestration_recorded",
            subject_refs=[outcome.record.packet_ref, outcome.record.council_review_id],
            artifact_hashes={
                "orchestration": outcome.record.content_hash,
                "execution_batch": outcome.record.execution_batch_hash,
                "council_review": outcome.record.council_review_hash,
                "route_plan": outcome.record.route_plan_hash,
                "task_packet": outcome.record.task_packet_hash,
            },
            payload={
                "source_artifact": outcome.path.relative_to(ws.root).as_posix(),
                "orchestration_id": outcome.record.orchestration_id,
                "pause_state": outcome.record.pause_state,
                "action_execution_allowed": False,
            },
        )

    colour = (
        typer.colors.GREEN
        if outcome.record.pause_state == "awaiting_human_decision"
        else typer.colors.YELLOW
    )
    typer.secho(
        f"ORCHESTRATION PAUSED: {outcome.record.pause_state.upper()}",
        fg=colour, bold=True,
    )
    typer.echo(f"  stages processed : {len(outcome.record.processed_stages)}")
    typer.echo(f"  council status   : {outcome.record.council_review_status}")
    typer.echo(f"  council review   : {outcome.council.yaml_path}")
    typer.echo(f"  record           : {outcome.path}")
    typer.echo("  action execution : not authorised")


def _record_synthesis_outcome(ws: Workspace, outcome) -> None:
    run = outcome.run
    if outcome.run_created:
        _record(
            ws, event_type="provider_run_captured", actor="conclave",
            authority_level="system", subject_refs=[run.packet_ref],
            artifact_hashes={"provider_run": run.content_hash},
            payload={
                "source_artifact": outcome.run_path.relative_to(ws.root).as_posix(),
                "provider": run.response.provider, "role": run.role,
                "status": run.status, "egress_decision_ref": run.egress_decision_ref,
                "execution_mode": "sequential-synthesizer",
            },
        )
    conversion = outcome.conversion
    if conversion.created:
        packet = conversion.packet
        _record(
            ws, event_type="provider_response_preserved",
            actor=packet.provider, authority_level="advisory_agent",
            artifact_hashes={"raw_response": packet.raw_response_hash},
            payload={
                "raw_file": conversion.raw_path.name,
                "source_run": outcome.run_path.name,
                "note": "sequential synthesizer response captured by sealed Run Record",
            },
        )
        _record(
            ws, event_type="handoff_packet_imported",
            actor=packet.provider, authority_level="advisory_agent",
            subject_refs=[packet.packet_ref],
            artifact_hashes={
                "handoff_packet": packet.content_hash,
                "raw_response": packet.raw_response_hash,
                "prompt": packet.prompt_hash,
                "provider_run": packet.run_record_hash,
            },
            payload={
                "provider": packet.provider, "role": packet.role,
                "submission_status": packet.status,
                "recommended_next_action": packet.recommended_next_action,
                "declared_objects_touched": sorted(packet.touched_keys()),
                "handoff_file": conversion.handoff_path.name,
                "source_run": outcome.run_path.name,
                "note": "projected from the verified sequential synthesizer Run",
            },
        )
    if outcome.scope.created:
        review = outcome.scope.review
        _record(
            ws, event_type="scope_review_created",
            subject_refs=[review.task_packet_ref],
            artifact_hashes={
                "scope_review": review.content_hash,
                "handoff_packet": review.handoff_packet_hash,
                "task_packet": review.task_packet_hash,
            },
            payload={
                "provider": review.provider,
                "evaluator_schema": review.schema_version,
                "scope_status": review.scope_status,
                "violation_count": review.violation_count,
                "source_artifact": outcome.scope.path.relative_to(ws.root).as_posix(),
                "note": "an evaluator result; it does not authorise remediation",
            },
        )
    council = outcome.council.review
    if outcome.council.created:
        _record(
            ws, event_type="council_review_created",
            subject_refs=[council.task_packet_ref, council.council_review_id],
            artifact_hashes={
                "council_review": council.content_hash,
                "task_packet": council.task_packet_hash,
                "route_plan": council.route_plan_hash,
            },
            payload={
                "council_review_id": council.council_review_id,
                "review_status": council.review_status,
                "submission_count": len(council.submissions),
                "missing_providers": council.missing_providers,
                "governance_alert_count": len(council.governance_alerts),
                "selection_basis": council.selection_basis,
                "yaml_file": outcome.council.yaml_path.name,
                "markdown_file": outcome.council.markdown_path.name,
                "note": "a post-synthesis review; no recommendation was accepted",
            },
        )
    if outcome.created:
        record = outcome.record
        _record(
            ws, event_type="synthesis_continuation_recorded",
            subject_refs=[record.packet_ref, record.council_review_id],
            artifact_hashes={
                "synthesis_continuation": record.content_hash,
                "source_orchestration": record.source_orchestration_hash,
                "provider_run": record.synthesis_run_hash,
                "council_review": record.council_review_hash,
                "route_plan": record.route_plan_hash,
                "task_packet": record.task_packet_hash,
            },
            payload={
                "source_artifact": outcome.path.relative_to(ws.root).as_posix(),
                "continuation_id": record.continuation_id,
                "pause_state": record.pause_state,
                "action_execution_allowed": False,
            },
        )


def _show_synthesis_outcome(ws: Workspace, outcome) -> None:
    _record_synthesis_outcome(ws, outcome)
    colour = (
        typer.colors.GREEN
        if outcome.record.pause_state == "awaiting_human_decision"
        else typer.colors.YELLOW
    )
    typer.secho(
        f"SYNTHESIS PAUSED: {outcome.record.pause_state.upper()}",
        fg=colour, bold=True,
    )
    typer.echo(f"  synthesizer     : {outcome.record.synthesizer_provider}")
    typer.echo(f"  council status  : {outcome.record.council_review_status}")
    typer.echo(f"  council review  : {outcome.council.yaml_path}")
    typer.echo(f"  continuation    : {outcome.path}")
    typer.echo("  human decision  : required")
    typer.echo("  action execution: not authorised")


@orchestrate_app.command("synthesize-fixture")
def orchestrate_synthesize_fixture(
    source_file: Path = typer.Argument(
        ..., exists=True, dir_okay=False,
        help="Stored orchestration paused for sequential synthesis.",
    ),
    instruction_file: Path = typer.Option(..., "--instruction", exists=True),
    response_file: Path = typer.Option(..., "--response", exists=True),
    model: str = typer.Option("fixture-model", "--model"),
    estimated_input_tokens: int = typer.Option(
        ..., "--estimated-input-tokens", min=0
    ),
) -> None:
    """EXECUTE a local sequential synthesizer fixture and rebuild Council review."""
    ws, _ = _ws()
    try:
        _, provider = synthesis_target(ws, source_file)
        adapter = FixtureAdapter(
            provider=provider,
            response_text=response_file.read_text(encoding="utf-8"),
        )
        decision = EgressDecision(
            allowed=True, transports=frozenset({"fixture"}),
            classifications=frozenset(
                {"public", "internal", "restricted", "constitutional"}
            ),
            authority="CONCLAVE", decision_ref="LOCAL-FIXTURE-NO-EGRESS",
        )
        outcome = execute_synthesis(
            ws=ws, source_file=source_file, adapter=adapter, decision=decision,
            model=model,
            operator_instruction=instruction_file.read_text(encoding="utf-8"),
            estimated_input_tokens=estimated_input_tokens,
        )
    except (ConclaveError, OSError, IndexError, TypeError, ValueError) as exc:
        _fail(str(exc))
        return
    _show_synthesis_outcome(ws, outcome)


@orchestrate_app.command("synthesize-live")
def orchestrate_synthesize_live(
    source_file: Path = typer.Argument(
        ..., exists=True, dir_okay=False,
        help="Stored orchestration paused for sequential synthesis.",
    ),
    instruction_file: Path = typer.Option(..., "--instruction", exists=True),
    egress_decision_file: Path = typer.Option(..., "--egress-decision", exists=True),
    model: str = typer.Option(..., "--model"),
    estimated_input_tokens: int = typer.Option(
        ..., "--estimated-input-tokens", min=0
    ),
    timeout_seconds: float = typer.Option(120.0, "--timeout", min=1.0),
    identity_verification: str | None = typer.Option(
        None, "--identity-verification"),
    evidence_binding: str | None = typer.Option(None, "--evidence-binding"),
) -> None:
    """EXECUTE the one governed live synthesizer stage, then pause for Arthur."""
    from .live_providers import ClaudeAdapter, GeminiAdapter, OpenAIAdapter

    ws, config = _ws()
    try:
        _, provider = synthesis_target(ws, source_file)
        decision = read_egress_decision(
            egress_decision_file, principal=config.get("principal", ""), workspace=ws,
            identity_verification_reference=identity_verification,
            signed_evidence_binding_reference=evidence_binding,
        )
        if provider in {"adrian", "openai"}:
            adapter = OpenAIAdapter(provider=provider, timeout_seconds=timeout_seconds)
        elif provider == "claude":
            adapter = ClaudeAdapter(timeout_seconds=timeout_seconds)
        elif provider == "gemini":
            adapter = GeminiAdapter(timeout_seconds=timeout_seconds)
        else:
            raise ConclaveError(
                f"no live adapter is registered for synthesizer {provider!r}"
            )
        outcome = execute_synthesis(
            ws=ws, source_file=source_file, adapter=adapter, decision=decision,
            model=model,
            operator_instruction=instruction_file.read_text(encoding="utf-8"),
            estimated_input_tokens=estimated_input_tokens,
        )
    except (ConclaveError, OSError, IndexError, TypeError, ValueError) as exc:
        _fail(str(exc))
        return
    _show_synthesis_outcome(ws, outcome)


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


@relay_app.command("export-context")
def relay_export_context(
    context_file: Path = typer.Option(..., "--context",
                                      help="Sealed Context Bundle YAML."),
    route_file: Path = typer.Option(..., "--route",
                                    help="Sealed Route Plan YAML."),
    instruction_file: Path = typer.Option(..., "--instruction",
                                          help="Provider instruction text."),
    stage_index: int = typer.Option(0, "--stage-index", min=0),
) -> None:
    """CREATE one sealed, stage-bound prompt for governed manual relay.

    The full Context Bundle is projected into the prompt locally. This command
    makes no provider API call and never includes another provider's response.
    """
    from .context import read_context_bundle
    from .routing import read_route_plan

    ws, config = _ws()
    try:
        bundle = read_context_bundle(context_file)
        plan = read_route_plan(route_file)
        task_id, version_text = bundle.packet_ref.rsplit("@v", 1)
        packet = read_packet(ws, task_id, int(version_text))
        instruction = instruction_file.read_text(encoding="utf-8")
        record, prompt_path, manifest_path, created = write_context_relay_export(
            ws=ws,
            packet=packet,
            bundle=bundle,
            plan=plan,
            stage_index=stage_index,
            instruction=instruction,
            config=config,
        )
    except (ConclaveError, OSError, TypeError, ValueError) as exc:
        _fail(str(exc))
        return

    status = "created" if created else "unchanged"
    typer.secho(f"{status}: {prompt_path}", fg=typer.colors.GREEN)
    typer.echo(f"manifest: {manifest_path}")
    typer.echo(f"packet:   {record.packet_ref}  {record.packet_content_hash}")
    typer.echo(f"context:  {record.context_bundle_hash}")
    typer.echo(f"route:    {record.route_plan_hash}")
    typer.echo(
        f"stage:    {record.stage_index}  {record.provider}:{record.role}"
    )
    typer.echo(f"prompt:   {record.prompt_hash}")
    typer.echo("No provider API call was made.")

    if created:
        _record(
            ws,
            event_type="context_relay_prompt_exported",
            actor="conclave",
            authority_level="system",
            subject_refs=[record.packet_ref],
            artifact_hashes={
                "task_packet": record.packet_content_hash,
                "context_bundle": record.context_bundle_hash,
                "route_plan": record.route_plan_hash,
                "prompt": record.prompt_hash,
                "context_relay_manifest": record.content_hash,
            },
            payload={
                "provider": record.provider,
                "role": record.role,
                "stage_index": record.stage_index,
                "prompt_file": prompt_path.relative_to(ws.root).as_posix(),
                "source_artifact": manifest_path.relative_to(ws.root).as_posix(),
                "transport": "manual-relay",
            },
        )


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
    route: Path = typer.Option(
        None, "--route", help="Optional sealed Route Plan for stage-aware selection."),
) -> None:
    """CREATE a Council Review Packet (canonical YAML) and PROJECT it to Markdown.\n\n    Idempotent for an unchanged source set.\n    """
    ws, _ = _ws()
    v = version or latest_version(ws, task_id)
    if v is None:
        _fail(f"no packets found for task {task_id!r}")
        return

    try:
        outcome = review_task(ws, task_id, v, route_path=route)
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
                                 "task_packet": r.task_packet_hash,
                                 **({"route_plan": r.route_plan_hash}
                                    if r.route_plan_hash else {})},
                payload={"council_review_id": r.council_review_id,
                         "review_status": r.review_status,
                         "submission_count": len(r.submissions),
                         "missing_providers": r.missing_providers,
                         "governance_alert_count": len(r.governance_alerts),
                         "selection_basis": r.selection_basis,
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


@council_app.command("record-decision")
def council_record_decision(
    instruction_file: Path = typer.Argument(
        ..., exists=True, dir_okay=False,
        help="Strict principal-authored authority-decision instruction YAML."),
    identity_verification: str | None = typer.Option(
        None, "--identity-verification"),
    evidence_binding: str | None = typer.Option(None, "--evidence-binding"),
) -> None:
    """RECORD a human decision as a separate immutable, hash-bound artifact.

    Requires an initialised, healthy ledger and exact entry of the configured
    workspace principal. There is deliberately no non-interactive bypass.
    """
    ws, config = _ws()
    try:
        instruction = read_instruction(instruction_file)
        candidate = prepare_decision(ws, instruction)
    except ConclaveError as exc:
        _fail(str(exc))
        return

    principal = config.get("principal")
    typer.secho("AUTHORITY DECISION CANDIDATE", bold=True)
    typer.echo(f"  council review : {candidate.council_review_id}")
    typer.echo(f"  review hash    : {candidate.council_review_hash}")
    typer.echo(f"  task packet    : {candidate.task_packet_ref}")
    typer.echo(f"  decision       : {candidate.decision}")
    typer.echo(f"  decided by     : {candidate.decided_by}")
    typer.echo(f"  actions        : {len(candidate.authorised_actions)}")
    typer.echo(f"  candidate hash : {candidate.content_hash}")
    typer.echo("")
    typer.secho(
        "This confirmation is a local operator ceremony, not cryptographic "
        "identity proof.", fg=typer.colors.YELLOW
    )
    confirmation = typer.prompt(
        f"Type the exact workspace principal {principal!r} to record this decision"
    )

    try:
        outcome = record_decision(
            ws, instruction, confirmed_principal=confirmation, prepared=candidate,
            identity_verification_reference=identity_verification,
            signed_evidence_binding_reference=evidence_binding,
        )
    except ConclaveError as exc:
        # If the artifact was written but the ledger append failed, it is kept.
        # Re-running this command and reconfirming retries the idempotent event.
        existing = list(ws.decisions_dir.glob("*.yaml")) if ws.decisions_dir.exists() else []
        if existing:
            typer.secho(
                "DECISION ARTIFACT MAY BE PRESERVED; LEDGER RECORDING DID NOT COMPLETE.",
                fg=typer.colors.RED, bold=True,
            )
            typer.echo(f"  {exc}")
            typer.secho(
                "  Verify the ledger, then rerun this exact command and reconfirm.",
                fg=typer.colors.YELLOW,
            )
            raise typer.Exit(code=1)
        _fail(str(exc))
        return

    typer.secho(
        "DECISION RECORDED" if outcome.created else "DECISION ALREADY RECORDED",
        fg=typer.colors.GREEN, bold=True,
    )
    typer.echo(f"  decision id : {outcome.record.decision_id}")
    typer.echo(f"  content hash: {outcome.record.content_hash}")
    typer.echo(f"  yaml        : {outcome.yaml_path}")
    typer.echo(f"  markdown    : {outcome.markdown_path}")
    typer.echo("")
    typer.secho(
        "The Council Review remains immutable with decision: pending; this separate "
        "record is authoritative.", fg=typer.colors.BRIGHT_BLACK,
    )


@identity_app.command("show-mode")
def identity_show_mode() -> None:
    """DISPLAY the explicit workspace identity mode; missing legacy state is local."""
    from .gating import identity_mode

    ws, _ = _ws()
    try:
        mode = identity_mode(ws)
    except ConclaveError as exc:
        _fail(str(exc))
        return
    typer.echo(mode)


@identity_app.command("import-binding")
def identity_import_binding(
    source: Path = typer.Argument(..., exists=True, dir_okay=False),
) -> None:
    """IMPORT a public actor-binding claim; this does not establish a PASS."""
    from .gating import import_actor_binding

    ws, config = _ws()
    principal = config.get("principal")
    confirmation = typer.prompt(
        f"Type the exact workspace principal {principal!r} to import this binding claim"
    )
    try:
        binding, path, created = import_actor_binding(
            ws, source, confirmed_principal=confirmation
        )
    except ConclaveError as exc:
        _fail(str(exc))
        return
    typer.echo(f"{'created' if created else 'unchanged'}: {path}")
    typer.echo(f"actor: {binding.actor_id}")
    typer.echo("status: awaiting-verification")


@identity_app.command("set-mode")
def identity_set_mode(
    mode: str = typer.Argument(..., help="local, verify, or attested"),
) -> None:
    """STRENGTHEN identity enforcement after exact principal confirmation."""
    from .gating import MODE_ORDER, set_identity_mode

    ws, config = _ws()
    if mode not in MODE_ORDER:
        _fail(f"unsupported identity mode {mode!r}")
        return
    principal = config.get("principal")
    confirmation = typer.prompt(
        f"Type the exact workspace principal {principal!r} to set identity mode {mode!r}"
    )
    try:
        selected, changed = set_identity_mode(
            ws, mode, confirmed_principal=confirmation  # type: ignore[arg-type]
        )
    except ConclaveError as exc:
        _fail(str(exc))
        return
    typer.echo(f"{'updated' if changed else 'unchanged'}: {selected}")


@evidence_app.command("record-receipt")
def evidence_record_receipt(
    binding: str = typer.Option(..., "--binding"),
    identity_verification: str = typer.Option(..., "--identity-verification"),
) -> None:
    """RECORD receipt of verified evidence; this is not approval or authority."""
    from .gating import record_evidence_receipt

    ws, config = _ws()
    principal = config.get("principal")
    confirmation = typer.prompt(
        f"Type the exact workspace principal {principal!r} to record evidence receipt"
    )
    try:
        event, created = record_evidence_receipt(
            ws,
            signed_evidence_binding_reference=binding,
            identity_verification_reference=identity_verification,
            confirmed_principal=confirmation,
        )
    except ConclaveError as exc:
        _fail(str(exc))
        return
    typer.echo(f"{'recorded' if created else 'unchanged'}: {event['event_id']}")
    typer.echo("authority_effect: none")


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


@ledger_app.command("prepare-checkpoint")
def ledger_prepare_checkpoint() -> None:
    """CREATE an immutable unsigned checkpoint candidate for external attestation."""
    from .checkpoint import prepare_ledger_checkpoint

    ws, _ = _ws()
    try:
        checkpoint, path, created = prepare_ledger_checkpoint(ws)
    except ConclaveError as exc:
        _fail(str(exc))
        return
    typer.echo(f"{'created' if created else 'unchanged'}: {path}")
    typer.echo(f"content_hash: {checkpoint.content_hash}")
    typer.echo("status: unsigned-candidate; CONCLAVE did not sign anything")


@ledger_app.command("record-signed-checkpoint")
def ledger_record_signed_checkpoint(
    checkpoint: str = typer.Option(..., "--checkpoint"),
    identity_verification: str = typer.Option(..., "--identity-verification"),
    evidence_binding: str = typer.Option(..., "--evidence-binding"),
) -> None:
    """RECORD an externally attested checkpoint after all 19C gates pass."""
    from .checkpoint import record_signed_checkpoint

    ws, config = _ws()
    principal = config.get("principal")
    confirmation = typer.prompt(
        f"Type the exact workspace principal {principal!r} to record this checkpoint"
    )
    try:
        event, created = record_signed_checkpoint(
            ws,
            checkpoint_reference=checkpoint,
            identity_verification_reference=identity_verification,
            signed_evidence_binding_reference=evidence_binding,
            confirmed_principal=confirmation,
        )
    except ConclaveError as exc:
        _fail(str(exc))
        return
    typer.echo(f"{'recorded' if created else 'unchanged'}: {event['event_id']}")
    typer.echo("authority_effect: none")


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
