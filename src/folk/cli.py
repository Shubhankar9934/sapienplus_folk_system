"""FOLK AI Council command-line entry point.

Subcommands are wired up incrementally as layers land. For now it exposes
``info`` so the install can be smoke-tested.
"""

from __future__ import annotations

import argparse
import functools

from folk import __version__
from folk.config import get_settings
from folk.utils.lock import RunLockError, run_lock
from folk.utils.logging import get_logger


def _locked(label: str):
    """Decorate a CLI command so it holds the exclusive run lock while it runs.

    Prevents two mutating commands (which share ``outputs/folk.sqlite`` and the
    ``outputs/`` directory) from clobbering each other's published outputs.
    """
    def deco(fn):
        @functools.wraps(fn)
        def wrapper(args: argparse.Namespace) -> int:
            log = get_logger()
            try:
                with run_lock(get_settings().outputs_dir, label):
                    return fn(args)
            except RunLockError as exc:
                log.error(str(exc))
                return 1
        return wrapper
    return deco

# Stale output artifacts wiped on a fresh run/reset (inputs + folk.sqlite are kept).
_OUTPUT_GLOBS = ("folk_*.json", "folk_*.xlsx", "folk_*.txt", "folk_run_log.jsonl",
                 "index.json", "run_summary.txt")


def _reset_state(repos, clean_outputs: bool = True) -> None:
    """Wipe persisted state so the next run starts from scratch.

    Drops and recreates all DB tables (profiles, references, validations,
    audits, evidence, and the resume checkpoint). Using drop/create rather than
    deleting the SQLite file avoids file-lock issues on Windows. Optionally
    removes stale report artifacts so old runs do not linger in outputs/.
    """
    log = get_logger()
    repos.db.drop_all()
    repos.db.create_all()
    log.info("Reset: dropped and recreated all database tables (checkpoint cleared).")

    if not clean_outputs:
        return
    outputs_dir = get_settings().outputs_dir
    removed = 0
    for pattern in _OUTPUT_GLOBS:
        for path in outputs_dir.glob(pattern):
            path.unlink()
            removed += 1
    # Per-country docs directory.
    countries_dir = outputs_dir / "countries"
    if countries_dir.exists():
        for path in countries_dir.glob("*.json"):
            path.unlink()
            removed += 1
    log.info(f"Reset: removed {removed} stale output artifact(s) from {outputs_dir}.")


def _cmd_info(_: argparse.Namespace) -> int:
    log = get_logger()
    settings = get_settings()
    log.info(f"FOLK AI Council v{__version__}")
    log.info(f"Provider mode: {settings.provider_mode}")
    log.info(f"Dataset: {settings.dataset_path}")
    log.info(f"Prompts: {settings.prompts_path}")
    log.info(f"Database: {settings.database_url}")
    return 0


def _cmd_calibrate(_: argparse.Namespace) -> int:
    from folk.pipeline.pipeline import Pipeline

    log = get_logger()
    result = Pipeline().calibration_run()
    log.info(f"Calibration run passed={result.passed}; anchors={result.anchor_results}")
    for note in result.notes:
        log.warning(note)
    return 0 if result.passed else 1


@_locked("reset")
def _cmd_reset(args: argparse.Namespace) -> int:
    """Wipe the database (and, by default, stale output artifacts)."""
    from folk.storage.repositories import Repositories

    log = get_logger()
    _reset_state(Repositories(), clean_outputs=not args.keep_outputs)
    log.info("Reset complete. Next run will start from scratch.")
    return 0


@_locked("run")
def _cmd_run(args: argparse.Namespace) -> int:
    from folk.export.exporter import Exporter
    from folk.pipeline.pipeline import Pipeline

    log = get_logger()
    pipeline = Pipeline()
    if args.fresh:
        _reset_state(pipeline.repos)
    isos = [s.strip().upper() for s in args.isos.split(",")] if args.isos else None
    # Completed countries (DB profile + output file both present) are always
    # skipped on a re-run; use --fresh to wipe state and reprocess everything.
    report = pipeline.run(isos=isos, limit=args.limit, resume=True)
    full_exports = bool(getattr(args, "full_exports", False)) or get_settings().full_exports
    exporter = Exporter(pipeline.repos)
    paths = exporter.export_all(report, full_exports=full_exports)
    if getattr(args, "audit", False):
        audit_paths = exporter.export_audit()
        paths.update(audit_paths)
    # "this run" = ISOs targeted by this invocation; "corpus" = everything in the
    # DB (the accumulate model republishes the whole corpus on every export).
    this_run = len(pipeline.run_isos)
    log.info(f"Run complete: processed {this_run} this run; "
             f"{report.total_countries} total in corpus "
             f"(fully autonomous, no human review).")
    for name, path in paths.items():
        log.info(f"  {name}: {path}")
    return 0


@_locked("export")
def _cmd_export(args: argparse.Namespace) -> int:
    from folk.export.exporter import Exporter
    from folk.pipeline.pipeline import Pipeline

    log = get_logger()
    pipeline = Pipeline()
    report = pipeline.finalize()
    full_exports = bool(getattr(args, "full_exports", False)) or get_settings().full_exports
    paths = Exporter(pipeline.repos).export_all(report, full_exports=full_exports)
    for name, path in paths.items():
        log.info(f"  {name}: {path}")
    return 0


@_locked("quality")
def _cmd_quality(_: argparse.Namespace) -> int:
    """Recompute Phase 2 analytics from the stored DB and re-emit reports."""
    from folk.export.exporter import Exporter
    from folk.pipeline.pipeline import Pipeline

    log = get_logger()
    pipeline = Pipeline()
    report = pipeline.finalize()
    exporter = Exporter(pipeline.repos)
    q = report.research_quality
    if q:
        log.info(f"Research quality grade: {q.overall_grade}")
        log.info(f"  narrative_fail={q.narrative_failure_pct}% judge_disagree={q.judge_disagreement_pct}%")
        log.info(f"  anchor_compliance={q.anchor_compliance_pct}% "
                 f"external_pearson={q.external_correlation.get('mean_abs_pearson')}")
    if report.counterfactual:
        log.info(f"Counterfactual: {report.counterfactual.verdict}")
    log.info(f"  research_quality_json: {exporter.export_research_quality_json(report)}")
    log.info(f"  research_quality_txt: {exporter.export_research_quality_txt(report)}")
    log.info(f"  external_validation_json: {exporter.export_external_validation_json(report)}")
    log.info(f"  council_impact_json: {exporter.export_council_impact_json(report)}")
    log.info(f"  agent_contribution_json: {exporter.export_agent_contribution_json(report)}")
    log.info(f"  council_diversity_json: {exporter.export_council_diversity_json()}")
    log.info(f"  decision_explanations_json: {exporter.export_decision_explanations_json()}")
    return 0


def _cmd_research(args: argparse.Namespace) -> int:
    """Validate each provider's native web-search capability (no fallback)."""
    from folk.research.errors import ConfigurationError
    from folk.research.factory import ResearchFactory
    from folk.research.validation import plan_seats

    log = get_logger()
    factory = ResearchFactory()
    try:
        availability, assignment, diversity, _ = plan_seats(factory=factory)
    except ConfigurationError as exc:
        log.error(f"Research capability validation FAILED: {exc}")
        return 1
    for provider, ok in availability.available.items():
        log.info(f"  {provider}: {'AVAILABLE' if ok else 'UNAVAILABLE'} "
                 f"- {availability.reasons.get(provider)}")
    log.info(f"Seat assignment: {assignment.assignments} "
             f"(slot fallback: {assignment.used_slot_fallback})")
    log.info(f"Provider diversity: {diversity.provider_diversity} "
             f"(penalty {diversity.confidence_penalty}) - {diversity.note}")
    return 0


def _cmd_api(args: argparse.Namespace) -> int:
    """Serve the exported outputs over HTTP for the frontend."""
    try:
        import uvicorn
    except ImportError:
        log = get_logger()
        log.error("uvicorn is not installed. Run: pip install -e \".[api]\"")
        return 1

    log = get_logger()
    log.info(f"Starting FOLK API on http://{args.host}:{args.port} "
             f"(docs at /docs)")
    uvicorn.run(
        "folk.api.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )
    return 0


@_locked("report")
def _cmd_report(args: argparse.Namespace) -> int:
    """Re-emit the evidence/intelligence/website reports from the stored DB."""
    from folk.export.exporter import Exporter
    from folk.storage.repositories import Repositories

    log = get_logger()
    exporter = Exporter(Repositories())
    log.info(f"  specialist_evidence_packs_json: {exporter.export_specialist_evidence_packs_json()}")
    log.info(f"  evidence_intelligence_json: {exporter.export_evidence_intelligence_json()}")
    log.info(f"  country_intelligence_json: {exporter.export_country_intelligence_reports_json()}")
    log.info(f"  country_intelligence_md: {exporter.export_country_intelligence_markdown()}")
    log.info(f"  website_cards_json: {exporter.export_website_cards_json()}")
    log.info(f"  provider_reports_json: {exporter.export_provider_reports_json()}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="folk", description="FOLK AI Council")
    parser.add_argument("--version", action="version", version=f"folk {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_info = sub.add_parser("info", help="Show resolved configuration.")
    p_info.set_defaults(func=_cmd_info)

    p_cal = sub.add_parser("calibrate", help="Pre-batch calibration run (anchors + references).")
    p_cal.set_defaults(func=_cmd_calibrate)

    p_run = sub.add_parser("run", help="Process countries end-to-end and export.")
    p_run.add_argument("--isos", help="Comma-separated ISO3 subset.", default=None)
    p_run.add_argument("--limit", type=int, default=None, help="Process at most N countries.")
    p_run.add_argument("--no-resume", action="store_true",
                       help="Deprecated no-op: completed countries are always skipped on re-run; "
                            "use --fresh to wipe state and reprocess everything.")
    p_run.add_argument("--fresh", action="store_true",
                       help="Wipe DB, checkpoint, and stale outputs before running.")
    p_run.add_argument("--full-exports", action="store_true", dest="full_exports",
                       help="Also write the legacy aggregate JSON/Excel deliverables.")
    p_run.add_argument("--audit", action="store_true",
                       help="Also write outputs/audit/*.csv: full score-formation, "
                            "specialist participation, clamp summary, and LLM-vs-integrator traces.")
    p_run.set_defaults(func=_cmd_run)

    p_reset = sub.add_parser("reset", help="Wipe DB, checkpoint, and stale output artifacts.")
    p_reset.add_argument("--keep-outputs", action="store_true",
                         help="Clear the database only; leave output files in place.")
    p_reset.set_defaults(func=_cmd_reset)

    p_exp = sub.add_parser("export", help="Re-run global pass + export from current DB.")
    p_exp.add_argument("--full-exports", action="store_true", dest="full_exports",
                       help="Also write the legacy aggregate JSON/Excel deliverables.")
    p_exp.set_defaults(func=_cmd_export)

    p_q = sub.add_parser("quality", help="Recompute Phase 2 analytics + research-quality report.")
    p_q.set_defaults(func=_cmd_quality)

    p_research = sub.add_parser(
        "research", help="Validate provider-native web-search capability (no fallback).")
    p_research.add_argument("--validate", action="store_true",
                            help="Probe each provider and assign specialist seats.")
    p_research.set_defaults(func=_cmd_research)

    p_report = sub.add_parser(
        "report", help="Re-emit evidence/intelligence/website reports from the DB.")
    p_report.set_defaults(func=_cmd_report)

    p_api = sub.add_parser("api", help="Serve exported outputs over HTTP for the frontend.")
    p_api.add_argument("--host", default="127.0.0.1", help="Bind host (default 127.0.0.1).")
    p_api.add_argument("--port", type=int, default=8000, help="Bind port (default 8000).")
    p_api.add_argument("--reload", action="store_true", help="Auto-reload on code changes.")
    p_api.set_defaults(func=_cmd_api)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
