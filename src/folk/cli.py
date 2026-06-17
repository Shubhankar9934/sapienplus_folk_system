"""FOLK AI Council command-line entry point.

Subcommands are wired up incrementally as layers land. For now it exposes
``info`` so the install can be smoke-tested.
"""

from __future__ import annotations

import argparse

from folk import __version__
from folk.config import get_settings
from folk.utils.logging import get_logger


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


def _cmd_run(args: argparse.Namespace) -> int:
    from folk.export.exporter import Exporter
    from folk.pipeline.pipeline import Pipeline

    log = get_logger()
    pipeline = Pipeline()
    isos = [s.strip().upper() for s in args.isos.split(",")] if args.isos else None
    report = pipeline.run(isos=isos, limit=args.limit, resume=not args.no_resume)
    paths = Exporter(pipeline.repos).export_all(report)
    log.info(f"Run complete: {report.total_countries} countries; "
             f"{len(report.human_review_queue)} flagged for review.")
    for name, path in paths.items():
        log.info(f"  {name}: {path}")
    return 0


def _cmd_export(_: argparse.Namespace) -> int:
    from folk.export.exporter import Exporter
    from folk.pipeline.pipeline import Pipeline

    log = get_logger()
    pipeline = Pipeline()
    report = pipeline.finalize()
    paths = Exporter(pipeline.repos).export_all(report)
    for name, path in paths.items():
        log.info(f"  {name}: {path}")
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
    p_run.add_argument("--no-resume", action="store_true", help="Ignore checkpoint and reprocess.")
    p_run.set_defaults(func=_cmd_run)

    p_exp = sub.add_parser("export", help="Re-run global pass + export from current DB.")
    p_exp.set_defaults(func=_cmd_export)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
