"""Public export API; load Note/renderer dependencies only when requested.

Importing common byte contracts must also work without site-packages.
"""
from importlib import import_module


_EXPORTS = {
    'ExportError': ('common', 'ExportError'),
    'PUBLIC_ATTRIBUTES': ('common', 'PUBLIC_ATTRIBUTES'),
    'PUBLIC_README': ('common', 'PUBLIC_README'),
    'sha256': ('common', 'sha256'),
    'json_bytes': ('common', 'json_bytes'),
    'object_path': ('common', 'object_path'),
    'reject_symlinks': ('common', 'reject_symlinks'),
    'UniqueLoader': ('note', 'UniqueLoader'),
    'unique_mapping': ('note', 'unique_mapping'),
    'FRONTMATTER': ('note', 'FRONTMATTER'),
    'FIELDS': ('note', 'FIELDS'),
    'SECRET': ('note', 'SECRET'),
    'UNSAFE': ('note', 'UNSAFE'),
    'reject_secrets': ('note', 'reject_secrets'),
    'note_frontmatter': ('note', 'note_frontmatter'),
    'instant': ('note', 'instant'),
    'plain_inline': ('note', 'plain_inline'),
    'validate_note': ('note', 'validate_note'),
    'ExportDirectorySnapshot': ('snapshot', 'ExportDirectorySnapshot'),
    'CheckedReads': ('snapshot', 'CheckedReads'),
    'index_catalog': ('snapshot', 'index_catalog'),
    'snapshot_files': ('snapshot', 'snapshot_files'),
    'load_snapshot': ('snapshot', 'load_snapshot'),
    'existing_matches': ('install', 'existing_matches'),
    'export_notes': ('export', 'export_notes'),
    'content_snapshot': ('git_snapshot', 'content_snapshot'),
}
__all__ = list(_EXPORTS)


def __getattr__(name):
    if name not in _EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module, attribute = _EXPORTS[name]
    value = getattr(import_module(f".{module}", __name__), attribute)
    globals()[name] = value
    return value
