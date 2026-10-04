"""Build a verified, immutable public artifact without production clients."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import yaml

WEB = Path(__file__).resolve().parent
sys.path.insert(0, str(WEB.parent / "src"))
from techkb.publication import ExportError, json_bytes, reject_symlinks
from techkb.site import load_snapshot, project_content, seal_artifact, install_artifact


def build(snapshot, output=None, fixture=False, content_commit=None):
    if output is not None and Path(output).absolute().is_relative_to(Path(snapshot).absolute()):
        raise ExportError("output_inside_snapshot")
    manifest, files, metadata = load_snapshot(snapshot)
    projected = project_content(manifest, files, metadata, fixture, content_commit)
    cache = WEB / ".cache"
    reject_symlinks(cache)
    engine = cache / "engine"
    reject_symlinks(engine)
    if not (engine / ".kaname-cache").is_file():
        raise ExportError("setup_required")
    config = yaml.safe_load((engine / "quartz.config.yaml").read_bytes())
    pins = json.loads((WEB / "quartz.lock.json").read_bytes())
    if ({p["source"] for p in config["plugins"]} != {"./plugins/" + name for name in pins["plugins"]} or
            config["configuration"]["ignorePatterns"] != [] or
            config["configuration"]["analytics"] is not None or
            config["configuration"]["theme"]["fontOrigin"] != "local"):
        raise ExportError("unsafe_builder_config")
    lock_path = cache / ".build.lock"
    with lock_path.open("x"):
        try:
            with tempfile.TemporaryDirectory(prefix="build-", dir=cache) as temporary:
                staging = Path(temporary)
                content, compiled = staging / "content", staging / "compiled"
                content.mkdir()
                for name, data in projected.items():
                    path = content / name
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(data)
                # The builder gets no inherited API/GCS/GitHub credentials.
                env = {key: os.environ[key] for key in ("PATH", "HOME", "TMPDIR", "LANG", "LC_ALL") if key in os.environ}
                env["NO_COLOR"] = "1"
                result = subprocess.run(["node", str(engine / "quartz/bootstrap-cli.mjs"), "build",
                    "-d", str(content), "-o", str(compiled), "--concurrency", "1"], cwd=engine,
                    env=env, capture_output=True, timeout=180)
                if result.returncode:
                    raise ExportError("quartz_build_failed")
                marker = seal_artifact(compiled, manifest, files, fixture, content_commit)
                if output is None:
                    parent = WEB / "public"
                    reject_symlinks(parent)
                    parent.mkdir(exist_ok=True)
                    output = parent / marker["artifact_digest"]
                result = install_artifact(compiled, output)
            pointer = cache / "last-build.json"
            reject_symlinks(pointer)
            fd, pointer_name = tempfile.mkstemp(prefix="last-build-", suffix=".tmp", dir=cache)
            temporary_pointer = Path(pointer_name)
            with os.fdopen(fd, "wb") as stream:
                stream.write(json_bytes(dict(output=result["output"])))
                stream.flush(); os.fsync(stream.fileno())
            os.replace(temporary_pointer, pointer)
            return {key: result[key] for key in ("output", "artifact_digest", "dataset_digest", "fixture", "unchanged")}
        finally:
            lock_path.unlink()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--content-commit")
    args = parser.parse_args()
    try:
        result = build(args.snapshot or WEB / ".cache/fixture-snapshot", args.output,
            fixture=args.snapshot is None, content_commit=args.content_commit)
        print(json.dumps(result, ensure_ascii=False))
    except ExportError as exc:
        print(json.dumps(dict(status="failed", error=str(exc))), file=sys.stderr); sys.exit(1)
    except Exception:
        print('{"status":"failed","error":"web_build_failed"}', file=sys.stderr); sys.exit(1)
