from copy import deepcopy

import pytest
from bs4 import BeautifulSoup

from kaname_web.validation import artifact_path
from listing_acceptance import audit_listings
from kaname.publication import ExportError, export_notes
from kaname.site import PAGE_SIZE, load_snapshot, project_content


@pytest.fixture
def library(harness, tmp_path):
    harness.pipeline.run()
    root = tmp_path / 'snapshot'
    export_notes(harness.store, root)
    return load_snapshot(root)


@pytest.mark.parametrize('count', [0, 1, 24, 25, 48, 49])
def test_all_collections_are_complete_ordered_and_bounded(library, count):
    manifest, files, metadata = deepcopy(library)
    seed = manifest['notes'][0]
    meta = metadata[seed['id']]
    original = files[seed['path']]
    manifest['notes'] = []
    for n in range(count):
        ident = f'{n:064x}'
        entry = dict(seed, id=ident, path=f'notes/{ident}.md')
        manifest['notes'].append(entry)
        files[entry['path']] = original
        metadata[ident] = dict(meta)
    before = dict(files)
    projected = project_content(manifest, files, metadata)
    parsed = {name[:-3] + '.html': BeautifulSoup(data, 'html.parser') for name, data in projected.items()}
    pages = max(1, (count + PAGE_SIZE - 1) // PAGE_SIZE)
    assert audit_listings(manifest, parsed) == (4 if count else 2) * pages
    assert len(parsed['index.html'].select('a.note-card')) == min(count, PAGE_SIZE)
    assert all(artifact_path(name) for name in parsed)
    assert files == before
    if pages > 1:
        broken = deepcopy(parsed)
        del broken['page/2.html']
        with pytest.raises(ExportError, match='missing_listing_page'):
            audit_listings(manifest, broken)
        parsed['page/2.html'].select_one('.note-card')['href'] = '../notes/' + seed['id']
        with pytest.raises(ExportError, match='listing_membership_mismatch'):
            audit_listings(manifest, parsed)


@pytest.mark.parametrize('path', ['page/1.html', 'page/02.html', 'page/-2.html', 'page/2/private.html',
                                  'browse/unknown/page/2.html', 'static/arbitrary.js'])
def test_pagination_does_not_expand_the_private_output_boundary(path):
    assert not artifact_path(path)
