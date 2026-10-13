"""Choose fixed Git or verified restored Release input without cloud clients."""
from techkb.publication.git_snapshot import content_snapshot
from techkb.release_bundle import release_input


def public_input(content, commit, release_receipt=None):
    if release_receipt is None:
        return content_snapshot(content, commit)
    return release_input(content, commit, release_receipt)
