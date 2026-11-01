"""Shared public snapshot codes, paths, bytes and distribution metadata."""
import hashlib
import json
from pathlib import PurePosixPath
import re


class ExportError(ValueError):
    """Only a fixed code is safe to print; never include Note text or URLs."""


# Distribution-only metadata: preserve blob bytes even with core.autocrlf.
PUBLIC_ATTRIBUTES = b"* -text -filter -ident -working-tree-encoding\n"


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


def object_path(name, prefix, suffix):
    path = PurePosixPath(name)
    if (not name.startswith(prefix) or str(path) != name or ".." in path.parts or
            path.suffix != suffix or re.search(r'[\\\x00-\x1f\x7f]', name)):
        raise ExportError("invalid_object_path")
    return path


def reject_symlinks(path):
    if any(part.is_symlink() for part in (path, *path.parents)):
        raise ExportError("symlink_path")


PUBLIC_README = ("# kaname generated Notes\n\n"
                 "LLMが生成した技術記事の要約です。正確性は出典で確認してください。\n"
                 "記事原文・運用台帳・人力Vaultは含みません。元記事の権利は各権利者に帰属します。\n\n"
                 "manifest.jsonのNote ID・SHA-256・dataset digestで同じ版を照合できます。\n"
                 "Git submoduleではcommitを固定して参照し、更新は利用側で明示してください。\n"
                 "生成領域の変更を強制reset/cleanせず、人の注釈は領域外に保持してください。\n").encode()


def digest_matches(data, expected):
    return sha256(data) == expected


def digest_value(value):
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None
