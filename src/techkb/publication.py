"""Read-only, deterministic export of validated compact Notes.

The manifest is the completion marker, installed only after all complete files.
No collection clients, storage writes, or human Vault operations are used here.
"""
import hashlib
import csv
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import tempfile
from datetime import datetime, timezone
from urllib.parse import unquote, urlsplit

import yaml

from .composer import concept, inline, code_span
from .normalize import normalize_url
from .state import INDEX_COLUMNS, decode_tsv
# Compatibility entrypoints retain the existing publication imports.
from ._publication_common import (ExportError, PUBLIC_ATTRIBUTES, PUBLIC_README,
                                  sha256, json_bytes, object_path, reject_symlinks)
from ._public_note import (UniqueLoader, unique_mapping, FRONTMATTER, FIELDS, SECRET, UNSAFE,
                           reject_secrets, note_frontmatter, instant, plain_inline, validate_note)
from ._publication_snapshot import (ExportDirectorySnapshot, CheckedReads, index_catalog, snapshot_files)
from ._snapshot_install import existing_matches, install_snapshot as _install_snapshot


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
    return dict(result, unchanged=_install_snapshot(root, files))
