import argparse
import json
import logging
import os
from pathlib import Path
from .config import load_config
from .converter import Converter
from .fetcher import Fetcher
from .gemini import Gemini
from .pipeline import Pipeline
from .storage import GCSStore, DirectorySnapshot
from .audit import audit_state
from .metadata_refresh import MetadataRefresh

def main(argv=None):
    parser = argparse.ArgumentParser(description="TechKB deterministic RSS knowledge collector")
    parser.add_argument("command", choices=["run", "validate-config", "dry-run", "audit-state", "refresh-metadata"])
    parser.add_argument("--config", default="config/app.yaml")
    parser.add_argument("--sources", default="config/sources.yaml")
    parser.add_argument("--state-dir", help="read-only local snapshot; dry-run, audit-state or refresh-metadata only")
    parser.add_argument("--apply", action="store_true", help="apply refresh-metadata changes")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    # Vendor debug/request logs can contain secrets and content.
    for name in ("httpx", "httpcore", "google", "markitdown"):
        logging.getLogger(name).setLevel(logging.CRITICAL)
    fetcher = gemini = None
    try:
        app, sources = load_config(args.config, args.sources)
        if args.state_dir and args.command not in {"dry-run", "audit-state", "refresh-metadata"}:
            raise ValueError("--state-dir is only for dry-run, audit-state or refresh-metadata")
        if args.apply and args.command != "refresh-metadata":
            raise ValueError("--apply is only for refresh-metadata")
        if args.apply and args.state_dir:
            raise ValueError("--apply cannot write a local snapshot")
        if args.command == "audit-state":
            if args.state_dir and not Path(args.state_dir).is_dir():
                raise ValueError("snapshot directory does not exist")
            store = DirectorySnapshot(args.state_dir) if args.state_dir else GCSStore(app.storage.bucket)
            result = audit_state(store)
            print(json.dumps(result, ensure_ascii=False))
            return 0 if result["status"] == "success" else 1
        if args.command == "refresh-metadata":
            if args.state_dir and not Path(args.state_dir).is_dir():
                raise ValueError("snapshot directory does not exist")
            store = DirectorySnapshot(args.state_dir) if args.state_dir else GCSStore(app.storage.bucket)
            fetcher = Fetcher(app.http)
            result = MetadataRefresh(store, fetcher, sources).run(apply=args.apply)
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
        fetcher = Fetcher(app.http)
        if not dry:
            gemini = Gemini(app.llm, app.categories, prompt, os.environ["GEMINI_API_KEY"])
        report = Pipeline(app, sources, store, fetcher, Converter(), gemini).run(dry_run=dry)
        return 0 if report.status == "success" else 1
    except Exception as exc:
        # Do not print exception text: SDK errors may contain sensitive payloads.
        logging.error("startup/config failure: %s; check configuration, credentials and README", type(exc).__name__)
        return 1
    finally:
        if fetcher:
            fetcher.close()
        if gemini:
            gemini.close()
