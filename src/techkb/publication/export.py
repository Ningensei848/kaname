"""Read-only export with a last-write completion manifest."""
import os
from pathlib import Path

from .common import ExportError, reject_symlinks
from .snapshot import ExportDirectorySnapshot, snapshot_files
from .install import install_snapshot


def export_notes(store, output, tracking=(), categories=None, exclude_ids=()):
    root = Path(output).absolute()
    reject_symlinks(root)
    if isinstance(store, ExportDirectorySnapshot) and root.resolve().is_relative_to(store.root.resolve()):
        raise ExportError("output_inside_snapshot")
    if not root.parent.is_dir():
        raise ExportError("missing_output_parent")
    if not all(hasattr(os, flag) for flag in ("O_DIRECTORY", "O_NOFOLLOW")):
        raise ExportError("unsupported_filesystem")
    files, digest = snapshot_files(store, tracking, categories, exclude_ids)
    result = dict(status="success", dataset_digest=digest, notes=len(files) - 2, output=str(root))
    return dict(result, unchanged=install_snapshot(root, files))
