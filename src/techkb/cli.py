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
from .distribution import publish_snapshot
from ._cli_arguments import parse_args, validate_args


class _Dependencies:
    """Create only requested clients and retain ownership until command completion."""

    def __init__(self, args):
        self.args = args
        self.app = None
        self.fetcher = self.gemini = None

    def store(self, *, public=False):
        if self.args.state_dir:
            if public:
                return ExportDirectorySnapshot(self.args.state_dir)
            # Preserve dry-run's existing snapshot semantics.
            if self.args.command != "dry-run" and not Path(self.args.state_dir).is_dir():
                raise ValueError("snapshot directory does not exist")
            return DirectorySnapshot(self.args.state_dir)
        return GCSStore(self.app.storage.bucket)

    def http(self):
        self.fetcher = Fetcher(self.app.http)
        return self.fetcher

    def articles(self):
        # Own the HTTP client even if constructing its browser adapter fails.
        self.fetcher = SourceFetcher(self.http())
        return self.fetcher

    def llm(self, prompt=""):
        self.gemini = Gemini(self.app.llm, self.app.categories, prompt, os.environ["GEMINI_API_KEY"])
        return self.gemini

    def close(self):
        try:
            if self.fetcher:
                self.fetcher.close()
        finally:
            if self.gemini:
                self.gemini.close()


def _json_result(result, *, ensure_ascii=False, status_exit=False):
    print(json.dumps(result, ensure_ascii=ensure_ascii))
    return 0 if not status_exit or result["status"] == "success" else 1


def main(argv=None):
    args = parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    # Vendor debug/request logs can contain secrets and content.
    for name in ("httpx", "httpcore", "google", "google_genai", "markitdown"):
        logging.getLogger(name).setLevel(logging.CRITICAL)
    dependencies = _Dependencies(args)
    try:
        app, sources = load_config(args.config, args.sources)
        validate_args(args, app)
        dependencies.app = app
        if args.command == "publish-notes":
            if not args.public_snapshot or not args.distribution_repo:
                raise ValueError("publish-notes requires public snapshot and local bare repository")
            return _json_result(publish_snapshot(args.public_snapshot, args.distribution_repo))
        if args.command == "export-notes":
            if not args.output:
                raise ValueError("export-notes requires --output")
            store = dependencies.store(public=True)
            result = export_notes(store, args.output, app.tracking_parameters, app.categories, args.exclude_note_id)
            return _json_result(result)
        if args.command == "batch-inspect":
            if not args.batch_id:
                raise ValueError("batch-inspect requires --batch-id")
            if not re.fullmatch(r"\d{8}T\d{6}Z-[0-9a-f]{8}", args.batch_id):
                raise ValueError("invalid batch ID")
            if args.remote and not os.environ.get("GEMINI_API_KEY"):
                raise ValueError("GEMINI_API_KEY is required for remote inspection")
            store = dependencies.store()
            if args.remote:
                dependencies.llm()
            result = inspect_batch(store, args.batch_id, dependencies.gemini.client if dependencies.gemini else None)
            return _json_result(result)
        if args.command == "batch-status":
            store = dependencies.store()
            manager = BatchManager(store, None)
            return _json_result(dict(status="success", jobs=[dict(id=j['id'],name=j['name'],status=j['status'],items=len(j['items'])) for _,j in manager.jobs]), ensure_ascii=True)
        if args.command in {"cost-report", "notify", "raw-lifecycle"}:
            store = dependencies.store()
            if args.command == "cost-report":
                result = cost_report(store, app, args.as_of)
            elif args.command == "raw-lifecycle":
                result = configure_lifecycle(store, sources, apply=args.apply)
            else:
                events = notification_plan(store, app, [s.id for s in sources if s.enabled])
                result = (publish_issues(events, app.notifications.github_repository, os.environ.get("GITHUB_TOKEN", ""))
                          if args.apply else dict(status="success", events=events, applied=False))
            return _json_result(result)
        if args.command == "sync":
            if not args.vault:
                raise ValueError("sync requires --vault")
            store = dependencies.store()
            result = sync_vault(store, args.vault, dry_run=args.dry_run)
            return _json_result(result, ensure_ascii=True, status_exit=True)
        if args.command in {"audit-state", "audit-run"}:
            store = dependencies.store()
            result = (audit_state(store) if args.command == "audit-state" else
                      audit_run(store, args.run_id, app.llm.max_calls_per_run, args.expected_success_before))
            return _json_result(result, status_exit=True)
        if args.command == "refresh-metadata":
            store = dependencies.store()
            fetcher = dependencies.http()
            result = MetadataRefresh(store, fetcher, sources, app.tracking_parameters).run(apply=args.apply)
            return _json_result(result, status_exit=True)
        if args.command == "batch-bind":
            if not args.batch_id or not args.job_name:
                raise ValueError("batch-bind requires --batch-id and --job-name")
            if not re.fullmatch(r"\d{8}T\d{6}Z-[0-9a-f]{8}", args.batch_id):
                raise ValueError("invalid batch ID")
            if not os.environ.get("GEMINI_API_KEY"):
                raise ValueError("GEMINI_API_KEY is required")
            store = dependencies.store()
            BatchManager(store, dependencies.llm()).bind(args.batch_id, args.job_name)
            return _json_result(dict(status="success", bound=True), ensure_ascii=True)
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
        store = dependencies.store()
        fetcher = dependencies.articles()
        gemini = dependencies.llm(prompt) if not dry else None
        report = Pipeline(app, sources, store, fetcher, Converter(), gemini).run(dry_run=dry)
        return 0 if report.status == "success" else 1
    except ExportError as exc:
        return _json_result(dict(status="failed", code=str(exc)), ensure_ascii=True, status_exit=True)
    except Exception as exc:
        # Do not print exception text: SDK errors may contain sensitive payloads.
        logging.error("startup/config failure: %s; check configuration, credentials and README", type(exc).__name__)
        return 1
    finally:
        dependencies.close()
