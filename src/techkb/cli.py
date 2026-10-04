import argparse
import json
import logging
import os
import re
from pathlib import Path
from .config import load_config
from .converter import Converter
from .fetcher import Fetcher
from .browser_fetcher import SourceFetcher
from .gemini import Gemini
from .pipeline import Pipeline
from .storage import GCSStore, DirectorySnapshot
from .audit import audit_state, audit_run
from .metadata_refresh import MetadataRefresh
from .sync import sync_vault
from .operations import cost_report, notification_plan, publish_issues
from .lifecycle import configure_lifecycle
from .batch import BatchManager, inspect_batch
from .publication import export_notes, ExportDirectorySnapshot, ExportError

def main(argv=None):
    parser = argparse.ArgumentParser(description="TechKB deterministic RSS knowledge collector")
    parser.add_argument("command", choices=["run", "validate-config", "dry-run", "audit-state", "audit-run", "refresh-metadata", "sync", "cost-report", "notify", "raw-lifecycle", "batch-status", "batch-bind", "batch-inspect", "export-notes"])
    parser.add_argument("--config", default="config/app.yaml")
    parser.add_argument("--sources", default="config/sources.yaml")
    parser.add_argument("--state-dir", help="read-only local snapshot for inspection, dry-run, sync and export")
    parser.add_argument("--output", help="new public snapshot directory; export-notes only")
    parser.add_argument("--exclude-note-id", action="append", default=[], help="withdraw stable Note ID; export-notes only")
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
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    # Vendor debug/request logs can contain secrets and content.
    for name in ("httpx", "httpcore", "google", "google_genai", "markitdown"):
        logging.getLogger(name).setLevel(logging.CRITICAL)
    fetcher = gemini = None
    try:
        app, sources = load_config(args.config, args.sources)
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
        if args.command == "export-notes":
            if not args.output:
                raise ValueError("export-notes requires --output")
            store = ExportDirectorySnapshot(args.state_dir) if args.state_dir else GCSStore(app.storage.bucket)
            result = export_notes(store, args.output, app.tracking_parameters, app.categories, args.exclude_note_id)
            print(json.dumps(result, ensure_ascii=False))
            return 0
        if args.command == "batch-inspect":
            if not args.batch_id:
                raise ValueError("batch-inspect requires --batch-id")
            if not re.fullmatch(r"\d{8}T\d{6}Z-[0-9a-f]{8}", args.batch_id):
                raise ValueError("invalid batch ID")
            if args.state_dir and not Path(args.state_dir).is_dir():
                raise ValueError("snapshot directory does not exist")
            if args.remote and not os.environ.get("GEMINI_API_KEY"):
                raise ValueError("GEMINI_API_KEY is required for remote inspection")
            store = DirectorySnapshot(args.state_dir) if args.state_dir else GCSStore(app.storage.bucket)
            if args.remote:
                gemini = Gemini(app.llm, app.categories, "", os.environ["GEMINI_API_KEY"])
            result = inspect_batch(store, args.batch_id, gemini.client if gemini else None)
            print(json.dumps(result, ensure_ascii=False))
            return 0
        if args.command == "batch-status":
            if args.state_dir and not Path(args.state_dir).is_dir():
                raise ValueError("snapshot directory does not exist")
            store = DirectorySnapshot(args.state_dir) if args.state_dir else GCSStore(app.storage.bucket)
            manager = BatchManager(store, None)
            print(json.dumps(dict(status="success", jobs=[dict(id=j['id'],name=j['name'],status=j['status'],items=len(j['items'])) for _,j in manager.jobs])))
            return 0
        if args.command in {"cost-report", "notify", "raw-lifecycle"}:
            if args.state_dir and not Path(args.state_dir).is_dir():
                raise ValueError("snapshot directory does not exist")
            store = DirectorySnapshot(args.state_dir) if args.state_dir else GCSStore(app.storage.bucket)
            if args.command == "cost-report":
                result = cost_report(store, app, args.as_of)
            elif args.command == "raw-lifecycle":
                result = configure_lifecycle(store, sources, apply=args.apply)
            else:
                events = notification_plan(store, app, [s.id for s in sources if s.enabled])
                result = (publish_issues(events, app.notifications.github_repository, os.environ.get("GITHUB_TOKEN", ""))
                          if args.apply else dict(status="success", events=events, applied=False))
            print(json.dumps(result, ensure_ascii=False))
            return 0
        if args.command == "sync":
            if not args.vault:
                raise ValueError("sync requires --vault")
            if args.state_dir and not Path(args.state_dir).is_dir():
                raise ValueError("snapshot directory does not exist")
            store = DirectorySnapshot(args.state_dir) if args.state_dir else GCSStore(app.storage.bucket)
            result = sync_vault(store, args.vault, dry_run=args.dry_run)
            print(json.dumps(result))
            return 0 if result["status"] == "success" else 1
        if args.command in {"audit-state", "audit-run"}:
            if args.state_dir and not Path(args.state_dir).is_dir():
                raise ValueError("snapshot directory does not exist")
            store = DirectorySnapshot(args.state_dir) if args.state_dir else GCSStore(app.storage.bucket)
            result = (audit_state(store) if args.command == "audit-state" else
                      audit_run(store, args.run_id, app.llm.max_calls_per_run, args.expected_success_before))
            print(json.dumps(result, ensure_ascii=False))
            return 0 if result["status"] == "success" else 1
        if args.command == "refresh-metadata":
            if args.state_dir and not Path(args.state_dir).is_dir():
                raise ValueError("snapshot directory does not exist")
            store = DirectorySnapshot(args.state_dir) if args.state_dir else GCSStore(app.storage.bucket)
            fetcher = Fetcher(app.http)
            result = MetadataRefresh(store, fetcher, sources, app.tracking_parameters).run(apply=args.apply)
            print(json.dumps(result, ensure_ascii=False))
            return 0 if result["status"] == "success" else 1
        prompt_path = Path(app.prompt_file)
        if not prompt_path.is_absolute():
            prompt_path = Path(args.config).resolve().parent.parent / prompt_path
        prompt = prompt_path.read_text(encoding="utf-8")
        if args.command == "validate-config":
            print(f"Configuration valid: {len(sources)} sources; model={app.llm.model}")
            return 0
        dry = args.command == "dry-run"
        if not dry and not os.environ.get("GEMINI_API_KEY"):
            raise ValueError("GEMINI_API_KEY is required")
        store = DirectorySnapshot(args.state_dir) if args.state_dir else GCSStore(app.storage.bucket)
        fetcher = SourceFetcher(Fetcher(app.http))
        if not dry:
            gemini = Gemini(app.llm, app.categories, prompt, os.environ["GEMINI_API_KEY"])
        if args.command == "batch-bind":
            if not args.batch_id or not args.job_name:
                raise ValueError("batch-bind requires --batch-id and --job-name")
            BatchManager(store, gemini).bind(args.batch_id, args.job_name)
            print(json.dumps(dict(status="success",bound=True)))
            return 0
        report = Pipeline(app, sources, store, fetcher, Converter(), gemini).run(dry_run=dry)
        return 0 if report.status == "success" else 1
    except ExportError as exc:
        print(json.dumps(dict(status="failed", code=str(exc))))
        return 1
    except Exception as exc:
        # Do not print exception text: SDK errors may contain sensitive payloads.
        logging.error("startup/config failure: %s; check configuration, credentials and README", type(exc).__name__)
        return 1
    finally:
        if fetcher:
            fetcher.close()
        if gemini:
            gemini.close()
