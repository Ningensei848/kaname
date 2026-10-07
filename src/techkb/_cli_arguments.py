"""CLI parsing and cross-command argument validation; no client construction."""

import argparse


def parse_args(argv):
    parser = argparse.ArgumentParser(description="TechKB deterministic RSS knowledge collector")
    parser.add_argument("command", choices=["run", "validate-config", "dry-run", "audit-state", "audit-run", "refresh-metadata", "sync", "cost-report", "notify", "raw-lifecycle", "batch-status", "batch-bind", "batch-inspect", "export-notes", "publish-notes"])
    parser.add_argument("--config", default="config/app.yaml")
    parser.add_argument("--sources", default="config/sources.yaml")
    parser.add_argument("--state-dir", help="read-only local snapshot for inspection, dry-run, sync and export")
    parser.add_argument("--output", help="new public snapshot directory; export-notes only")
    parser.add_argument("--exclude-note-id", action="append", default=[], help="withdraw stable Note ID; export-notes only")
    parser.add_argument("--public-snapshot", help="validated public snapshot; publish-notes only")
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
    parser.add_argument("--max-calls", type=int, help="reduce run limit (0..configured limit)")
    return parser.parse_args(argv)


def validate_args(args, app):
    if (args.llm_mode or args.max_calls is not None) and args.command not in {"run", "dry-run"}:
        raise ValueError("LLM overrides require run or dry-run")
    if args.llm_mode:
        app.llm.mode=args.llm_mode
    if args.max_calls is not None:
        if not 0 <= args.max_calls <= app.llm.max_calls_per_run:
            raise ValueError("--max-calls must reduce the configured limit")
        app.llm.max_calls_per_run=args.max_calls
    if args.state_dir and args.command not in {"dry-run", "audit-state", "audit-run", "refresh-metadata", "sync", "cost-report", "notify", "batch-status", "batch-inspect", "export-notes"}:
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
    if (args.public_snapshot or args.distribution_repo) and args.command != "publish-notes":
        raise ValueError("distribution arguments require publish-notes")
