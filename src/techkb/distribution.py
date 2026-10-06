"""Publish a complete validated snapshot to a local bare content branch.

No working tree, remote push, credentials, collection, or Vault operations.
Only the content ref is advanced, with a compare-and-swap final update.
"""
import os
from pathlib import Path
import re
import subprocess
import tempfile

from .publication import ExportError, PUBLIC_README, PUBLIC_ATTRIBUTES, reject_symlinks
from .site import load_snapshot


REF = "refs/heads/content"
README = PUBLIC_README + (
    "\n旧形式の打切りNoteは、上限文字数と本文の注意表示が保存されていない場合があります。\n"
    "`llm_input_truncated: true`を確認し、記事全体は原典で確認してください。\n"
    "Web版はこの場合に上限値未記録の注意を表示します。元Noteのbytesは変更しません。\n"
).encode()


class Git:
    def __init__(self, repository):
        self.root = Path(repository).absolute()
        reject_symlinks(self.root)
        if not self.root.is_dir():
            raise ExportError("missing_distribution_repository")
        if (self.root / ".git").exists() or (self.root / ".git").is_symlink():
            raise ExportError("bare_distribution_repository_required")
        self.env = {k: os.environ[k] for k in ("PATH", "HOME", "LANG", "LC_ALL", "TMPDIR") if k in os.environ}
        self.env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull, GIT_TERMINAL_PROMPT="0")
        self.prefix = ["git", "--git-dir=" + str(self.root), "-c", "core.hooksPath=" + os.devnull,
                       "-c", "commit.gpgsign=false", "-c", "user.name=kaname",
                       "-c", "user.email=kaname@users.noreply.github.com"]
        if self.call("rev-parse", "--is-bare-repository").strip() != b"true":
            raise ExportError("bare_distribution_repository_required")
        if self.call("rev-parse", "--show-object-format").strip() != b"sha1":
            raise ExportError("unsupported_git_object_format")
        if self.call("symbolic-ref", "-q", REF, absent=True) is not None:
            raise ExportError("symbolic_distribution_ref")

    def call(self, *args, data=None, absent=False, code="distribution_git_failed"):
        result = subprocess.run([*self.prefix, *args], input=data, capture_output=True,
                                env=self.env, timeout=30)
        if result.returncode:
            if absent and result.returncode == 1:
                return None
            raise ExportError(code)
        return result.stdout

    def head(self):
        raw = self.call("rev-parse", "--verify", "--quiet", REF, absent=True)
        if raw is None:
            return None
        oid = raw.strip().decode("ascii")
        if not re.fullmatch(r"[0-9a-f]{40}", oid) or self.call("cat-file", "-t", oid).strip() != b"commit":
            raise ExportError("invalid_distribution_ref")
        return oid


def previous_snapshot(git, commit):
    """Reject a code/private/malformed branch before reading its blobs."""
    objects = {}
    listing = git.call("ls-tree", "-rz", "--full-tree", commit)
    for item in listing.split(b"\0"):
        if not item:
            continue
        try:
            header, raw_name = item.split(b"\t", 1)
            mode, kind, oid = header.decode("ascii").split()
            name = raw_name.decode("utf-8")
        except (ValueError, UnicodeError):
            raise ExportError("invalid_distribution_tree") from None
        if (mode != "100644" or kind != "blob" or not re.fullmatch(r"[0-9a-f]{40}", oid) or
                (name not in {"README.md", "manifest.json", ".gitattributes"} and not re.fullmatch(r"notes/[0-9a-f]{64}\.md", name))):
            raise ExportError("invalid_distribution_tree")
        objects[name] = oid
    if not {"README.md", "manifest.json"} <= objects.keys():
        raise ExportError("invalid_distribution_tree")
    with tempfile.TemporaryDirectory(prefix="kaname-previous-distribution-") as temporary:
        root = Path(temporary)
        for name, oid in objects.items():
            data = git.call("cat-file", "blob", oid)
            if name == "README.md" and data not in {PUBLIC_README, README}:
                raise ExportError("unrecognized_distribution_readme")
            if name == ".gitattributes" and data != PUBLIC_ATTRIBUTES:
                raise ExportError("invalid_distribution_attributes")
            path = root / name; path.parent.mkdir(exist_ok=True); path.write_bytes(data)
        return load_snapshot(root)[0]


def publish_snapshot(snapshot, repository):
    """Capture validated public files and atomically advance only content."""
    root, source = Path(repository).absolute(), Path(snapshot).absolute()
    if root.is_relative_to(source) or source.is_relative_to(root):
        raise ExportError("distribution_paths_overlap")
    manifest, captured, _ = load_snapshot(source)
    # Never import a caller's README, .git, untracked files, hooks or config.
    files = dict(captured, **{"README.md": README, ".gitattributes": PUBLIC_ATTRIBUTES})
    git = Git(root)
    parent = git.head()
    if parent:
        previous_snapshot(git, parent)
    blobs = {}
    for name, data in sorted(files.items()):
        blobs[name] = git.call("hash-object", "-w", "--stdin", data=data).strip().decode("ascii")
    root_entries = []
    notes = []
    for name, oid in sorted(blobs.items()):
        entry = f"100644 blob {oid}\t{Path(name).name}\0".encode()
        (notes if name.startswith("notes/") else root_entries).append(entry)
    if notes:
        tree = git.call("mktree", "-z", data=b"".join(notes)).strip().decode("ascii")
        root_entries.append(f"040000 tree {tree}\tnotes\0".encode())
    tree = git.call("mktree", "-z", data=b"".join(root_entries)).strip().decode("ascii")
    result = dict(status="success", branch="content", dataset_digest=manifest["dataset_digest"],
                  notes=len(manifest["notes"]), tree=tree)
    if parent and git.call("rev-parse", parent + "^{tree}").strip().decode("ascii") == tree:
        # A concurrent update invalidates even an otherwise unchanged result.
        if git.head() != parent:
            raise ExportError("distribution_ref_conflict")
        return dict(result, commit=parent, unchanged=True)
    args = ["commit-tree", tree]
    if parent:
        args += ["-p", parent]
    message = f"Publish Note snapshot {manifest['dataset_digest']}\n".encode()
    commit = git.call(*args, data=message).strip().decode("ascii")
    # On interruption or conflict only unreachable objects remain; no index,
    # working tree, other refs, or previous content commit are overwritten.
    git.call("update-ref", "--no-deref", REF, commit, parent or "0" * 40, code="distribution_ref_conflict")
    return dict(result, commit=commit, unchanged=False)
