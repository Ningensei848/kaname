"""Bind a complete Web artifact to the exact public content Git commit."""
from pathlib import Path

from techkb.publication import ExportError
from techkb.publication.git_snapshot import content_snapshot
from .artifact import load_artifact, install_artifact
from .validation import public_version_matches, snapshot_matches


def prepare_pages(checkout, commit, artifact, output):
    """Copy only a sealed nonfixture artifact with identical Git Note bytes."""
    source, compiled, destination = (Path(p).absolute() for p in (checkout, artifact, output))
    if (destination.is_relative_to(source) or source.is_relative_to(destination) or
            destination.is_relative_to(compiled) or compiled.is_relative_to(destination)):
        raise ExportError("pages_paths_overlap")
    manifest, original, _ = content_snapshot(source, commit)
    marker, files = load_artifact(compiled)
    if not public_version_matches(marker, commit):
        raise ExportError("pages_provenance_mismatch")
    if not snapshot_matches(marker, manifest, files, original):
        raise ExportError("pages_snapshot_mismatch")
    if not {"index.html", "about/snapshot.html"} <= files.keys():
        raise ExportError("missing_pages_entrypoint")
    result = install_artifact(compiled, destination)
    return {"status": "success", "output": result["output"], "content_commit": commit,
            "dataset_digest": marker["dataset_digest"], "artifact_digest": marker["artifact_digest"],
            "notes": len(manifest["notes"]), "unchanged": result["unchanged"]}
