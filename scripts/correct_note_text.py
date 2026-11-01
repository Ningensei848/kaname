"""Preview or apply a hash-pinned correction without article or Gemini requests."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from kaname.config import load_config
from kaname.note_corrections import correct_note, load_plan
from kaname.publication.snapshot import ExportDirectorySnapshot
from kaname.storage import GCSStore


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', required=True)
    parser.add_argument('--output', required=True, help='new directory for validated preview')
    parser.add_argument('--state-dir', help='read-only local state snapshot')
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args(argv)
    store = None
    try:
        if args.apply and args.state_dir:
            raise ValueError('cannot apply to a read-only snapshot')
        if Path(args.output).exists() or Path(args.output).is_symlink():
            raise ValueError('preview output must be a new directory')
        plan = load_plan(args.plan)
        app, _ = load_config('config/app.yaml', 'config/sources.yaml')
        store = ExportDirectorySnapshot(args.state_dir) if args.state_dir else GCSStore(app.storage.bucket)
        result = correct_note(store, app, plan, apply=args.apply, output=args.output)
        if Path(args.output).is_dir():
            (Path(args.output) / 'result.json').write_text(json.dumps(result) + '\n')
        print(json.dumps(result))
        return int(result['status'] != 'success')
    except Exception as exc:
        print(json.dumps(dict(status='failed', error_type=type(exc).__name__)))
        return 1
    finally:
        if hasattr(store, 'close'):
            store.close()


if __name__ == '__main__':
    sys.exit(main())
