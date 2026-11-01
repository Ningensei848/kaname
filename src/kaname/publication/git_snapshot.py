"""Verify public snapshot bytes against a clean, fixed Git commit."""
import os
from pathlib import Path
import re
import subprocess

from ..distribution import README
from .common import ExportError, PUBLIC_README, PUBLIC_ATTRIBUTES, reject_symlinks
from .snapshot import load_snapshot


def content_snapshot(checkout, commit):
    root = Path(checkout).absolute()
    reject_symlinks(root)
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ExportError("invalid_content_commit")
    if not (root / ".git").is_dir() or (root / ".git").is_symlink():
        raise ExportError("content_checkout_required")
    env = {k: os.environ[k] for k in ("PATH", "HOME", "LANG", "LC_ALL", "TMPDIR") if k in os.environ}
    env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull, GIT_TERMINAL_PROMPT="0")
    def git(*args):
        result = subprocess.run(["git", "--git-dir=" + str(root / ".git"), "--work-tree=" + str(root),
            "-c", "core.hooksPath=" + os.devnull, "-c", "core.fsmonitor=false", *args],
            env=env, capture_output=True, timeout=30)
        if result.returncode:
            raise ExportError("content_git_failed")
        return result.stdout
    def head():
        if git("rev-parse", "--verify", "HEAD^{commit}").strip().decode("ascii") != commit:
            raise ExportError("content_commit_mismatch")
        if git("status", "--porcelain=v1", "--untracked-files=all", "--ignored"):
            raise ExportError("dirty_content_checkout")
    head()
    manifest, files, metadata = load_snapshot(root)
    captured = dict(files, **{"README.md": (root / "README.md").read_bytes(),
                             ".gitattributes": (root / ".gitattributes").read_bytes()})
    if captured["README.md"] not in {PUBLIC_README, README} or captured[".gitattributes"] != PUBLIC_ATTRIBUTES:
        raise ExportError("invalid_distribution_metadata")
    tracked = set()
    for item in git("ls-tree", "-rz", "--full-tree", commit).split(b"\0"):
        if not item:
            continue
        try:
            header, name = item.split(b"\t", 1)
            mode, kind, oid = header.decode("ascii").split()
            name = name.decode("utf-8")
        except (ValueError, UnicodeError):
            raise ExportError("invalid_content_tree") from None
        if mode != "100644" or kind != "blob" or name not in captured:
            raise ExportError("invalid_content_tree")
        if git("cat-file", "blob", oid) != captured[name]:
            raise ExportError("content_blob_mismatch")
        tracked.add(name)
    if tracked != captured.keys():
        raise ExportError("invalid_content_tree")
    head()
    return manifest, files, metadata
