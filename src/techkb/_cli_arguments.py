"""CLI parsing and cross-command argument validation; no client construction."""

import argparse
from decimal import Decimal
from .budget import validate_budget


def parse_args(argv):
    parser = argparse.ArgumentParser(description="TechKB deterministic RSS knowledge collector")
    parser.add_argument("command", choices=["run", "validate-config", "dry-run", "audit-state", "audit-run", "refresh-metadata", "sync", "cost-report", "source-health", "graph-quality", "notify", "raw-lifecycle", "batch-status", "batch-bind", "batch-inspect", "export-notes", "publish-notes"])
    parser.add_argument("--config", default="config/app.yaml")
    parser.add_argument("--sources", default="config/sources.yaml")
    parser.add_argument("--state-dir", help="read-only local snapshot for inspection, dry-run, sync and export")
    parser.add_argument("--output", help="new public snapshot directory; export-notes only")
    parser.add_argument("--exclude-note-id", action="append", default=[], help="withdraw stable Note ID; export-notes only")
    parser.add_argument("--public-snapshot", help="validated public snapshot; publish-notes or graph-quality")
    parser.add_argument("--details", action="store_true", help="include public terms/Note IDs in graph-quality report")
    parser.add_argument("--distribution-repo", help="local bare repository; publish-notes only (no remote push)")
    parser.add_argument("--apply", action="store_true", help="apply metadata/lifecycle changes or publish notifications")
    parser.add_argument("--run-id", help="persisted report to compare; audit-run only")
    parser.add_argument("--expected-success-before", type=int, help="success index baseline; audit-run only")
    parser.add_argument("--vault", help="Obsidian vault directory; sync only")
    parser.add_argument("--dry-run", action="store_true", help="preview sync without Note writes")
    parser.add_argument("--as-of", help="UTC date for cost-report: YYYY-MM-DD")
    parser.add_argument("--batch-id", help="ledger ID; batch-bind or batch-inspect only")
    parser.add_argument("--remote", action="store_true", help="GET the existing Batch result; batch-inspect only")
    parser.add_argument("--job-name", help="matching Gemini job resource name; batch-bind only")
    parser.add_argument("--llm-mode", choices=["standard", "batch"], help="override configured mode for run/dry-run")
    parser.add_argument("--max-calls", type=int, help="run limit; increases require a standard --max-cost-usd cap")
    parser.add_argument("--max-cost-usd", type=Decimal, help="estimated standard generation cost cap for this run; stops on uncertain usage")
    return parser.parse_args(argv)


def validate_args(args, app):
    if (args.llm_mode or args.max_calls is not None) and args.command not in {"run", "dry-run"}:
        raise ValueError("LLM overrides require run or dry-run")
    if args.llm_mode:
        app.llm.mode=args.llm_mode
    if args.max_cost_usd is not None:
        if args.command != "run":
            raise ValueError("--max-cost-usd requires standard run")
        validate_budget(app, args.max_cost_usd)
    if args.max_calls is not None:
        if args.max_calls < 0 or (args.max_cost_usd is None and args.max_calls > app.llm.max_calls_per_run):
            raise ValueError("increasing --max-calls requires a standard cost cap")
        app.llm.max_calls_per_run=args.max_calls
    if args.state_dir and args.command not in {"dry-run", "audit-state", "audit-run", "refresh-metadata", "sync", "cost-report", "source-health", "notify", "batch-status", "batch-inspect", "export-notes"}:
        raise ValueError("--state-dir requires a command supporting read-only snapshots")
    if args.apply and args.command not in {"refresh-metadata", "notify", "raw-lifecycle"}:
        raise ValueError("--apply requires refresh-metadata, notify or raw-lifecycle")
    if args.apply and args.state_dir and args.command != "notify":
        raise ValueError("--apply cannot write a local snapshot")
    if (args.run_id or args.expected_success_before is not None) and args.command != "audit-run":
        raise ValueError("report arguments require audit-run")
    if (args.vault or args.dry_run) and args.command != "sync":
        raise ValueError("vault arguments require sync")
    if args.as_of and args.command != "cost-report":
        raise ValueError("--as-of requires cost-report")
    if args.batch_id and args.command not in {"batch-bind", "batch-inspect"}:
        raise ValueError("batch ID requires batch-bind or batch-inspect")
    if args.job_name and args.command != "batch-bind":
        raise ValueError("job name requires batch-bind")
    if args.remote and args.command != "batch-inspect":
        raise ValueError("--remote requires batch-inspect")
    if (args.output or args.exclude_note_id) and args.command != "export-notes":
        raise ValueError("export arguments require export-notes")
    if args.public_snapshot and args.command not in {"publish-notes", "graph-quality"}:
        raise ValueError("public snapshot requires publish-notes or graph-quality")
    if args.distribution_repo and args.command != "publish-notes":
        raise ValueError("distribution repository requires publish-notes")
    if args.details and args.command != "graph-quality":
        raise ValueError("--details requires graph-quality")
