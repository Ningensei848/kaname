"""Exclusive snapshot install with an anchored, last-write completion marker."""
import os
from pathlib import Path, PurePosixPath
import tempfile

from .common import ExportError, reject_symlinks


def existing_matches(root, files):
    actual = set()
    for path in root.rglob("*"):
        reject_symlinks(path)
        if path.is_file():
            actual.add(path.relative_to(root).as_posix())
        elif not path.is_dir():
            raise ExportError("invalid_output")
        elif path.relative_to(root).as_posix() != "notes":
            raise ExportError("output_conflict")
    return actual == files.keys() and all((root / name).read_bytes() == data for name, data in files.items())


def install_snapshot(root, files):
    if root.exists():
        if root.is_dir() and existing_matches(root, files):
            return True
        raise ExportError("output_conflict")
    with tempfile.TemporaryDirectory(prefix=".kaname-export-", dir=root.parent) as staging:
        stage = Path(staging)
        for name, data in files.items():
            path = stage / name
            path.parent.mkdir(exist_ok=True)
            with path.open("xb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
        reject_symlinks(root)
        # mkdir is exclusive even when another process creates an empty target.
        # An interrupted install has no manifest and must never be published.
        root.mkdir()
        # Anchor writes to directory descriptors so replacing notes/ with a
        # symlink cannot redirect publication into somebody else's directory.
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        root_fd = os.open(root, flags)
        notes_fd = None
        try:
            os.mkdir("notes", dir_fd=root_fd)
            notes_fd = os.open("notes", flags, dir_fd=root_fd)
            for name in sorted(files):
                if name == "manifest.json":
                    continue
                target_fd = notes_fd if name.startswith("notes/") else root_fd
                os.link(stage / name, PurePosixPath(name).name, dst_dir_fd=target_fd)
            os.fsync(notes_fd)
            os.fsync(root_fd)
            reject_symlinks(root / "notes")
            if (root.stat().st_ino != os.fstat(root_fd).st_ino or
                    (root / "notes").stat().st_ino != os.fstat(notes_fd).st_ino):
                raise ExportError("output_changed")
            os.link(stage / "manifest.json", "manifest.json", dst_dir_fd=root_fd)
            os.fsync(root_fd)
        finally:
            if notes_fd is not None:
                os.close(notes_fd)
            os.close(root_fd)
    return False
