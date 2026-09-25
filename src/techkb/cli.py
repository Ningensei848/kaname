import argparse
import logging
import os
from pathlib import Path
from .config import load_config
from .converter import Converter
from .fetcher import Fetcher
from .gemini import Gemini
from .pipeline import Pipeline
from .storage import GCSStore, DirectorySnapshot

def main(argv=None):
    parser = argparse.ArgumentParser(description="TechKB deterministic RSS knowledge collector")
    parser.add_argument("command", choices=["run", "validate-config", "dry-run"])
    parser.add_argument("--config", default="config/app.yaml")
    parser.add_argument("--sources", default="config/sources.yaml")
    parser.add_argument("--state-dir", help="read-only local state snapshot; dry-run only")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    # Vendor debug/request logs can contain secrets and content.
    for name in ("httpx", "httpcore", "google", "markitdown"):
        logging.getLogger(name).setLevel(logging.CRITICAL)
    fetcher = gemini = None
    try:
        app, sources = load_config(args.config, args.sources)
        prompt_path = Path(app.prompt_file)
        if not prompt_path.is_absolute():
            prompt_path = Path(args.config).resolve().parent.parent / prompt_path
        prompt = prompt_path.read_text(encoding="utf-8")
        if args.command == "validate-config":
            print(f"Configuration valid: {len(sources)} sources; model={app.llm.model}")
            return 0
        dry = args.command == "dry-run"
        if args.state_dir and not dry:
            raise ValueError("--state-dir is only for dry-run")
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
