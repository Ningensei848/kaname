from copy import deepcopy

from kaname.graph_quality import shared_keyword_links
from kaname.publication import export_notes
from kaname.publication.snapshot import load_snapshot
from kaname.site import project_content


def snapshot(values):
    entries, files = [], {}
    for number, terms in enumerate(values):
        note_id = f'{number:064x}'
        path = 'notes/' + note_id + '.md'
        entries.append(dict(id=note_id, path=path))
        files[path] = ('---\ntitle: Fixture\n---\n\n# Fixture\n\n## 検索キーワード\n\n' +
                       '\n'.join('- [[' + term + ']]' for term in terms) +
                       '\n\n## 資料の位置づけ\n\nFixture').encode()
    return dict(notes=entries), files


def test_two_declared_keywords_are_required_and_one_keyword_does_not_link():
    manifest, files = snapshot([['LLM', 'Redis', 'C++'],
                                ['大規模言語モデル', 'Redis', 'C#'], ['Redis', 'C++']])
    result = shared_keyword_links(manifest, files)
    a, b, c = [entry['id'] for entry in manifest['notes']]
    assert result[a] == [dict(note_id=b, terms=['llm', 'redis']), dict(note_id=c, terms=['c++', 'redis'])]
    assert result[b] == [dict(note_id=a, terms=['llm', 'redis'])]
    assert result[c] == [dict(note_id=a, terms=['c++', 'redis'])]


def test_common_generic_and_repeated_keywords_cannot_manufacture_edges():
    manifest, files = snapshot([['Gemini', 'DeepMind', 'AI', 'Redis', 'Redis']] * 4)
    assert all(not links for links in shared_keyword_links(manifest, files).values())
    manifest, files = snapshot([['Redis', 'Redis', 'LLM', '大規模言語モデル'], ['Redis']])
    assert all(not links for links in shared_keyword_links(manifest, files).values())


def test_links_are_bounded_deterministic_and_have_no_self_or_removed_notes():
    manifest, files = snapshot([['Redis', 'Valkey']] * 4 + [['Unique' + str(i)] for i in range(36)])
    result = shared_keyword_links(manifest, files)
    assert sum(map(len, result.values())) == 12
    assert all(len(links) <= 3 and all(link['note_id'] != source for link in links)
               for source, links in result.items())
    manifest['notes'].reverse()
    assert shared_keyword_links(manifest, files) == result
    removed = manifest['notes'].pop()['id']
    assert all(link['note_id'] != removed for links in shared_keyword_links(manifest, files).values() for link in links)


def test_frequency_limit_never_rounds_above_ten_percent():
    manifest, files = snapshot([['Redis', 'Valkey']] * 4 + [['Unique' + str(i)] for i in range(27)])
    assert all(not links for links in shared_keyword_links(manifest, files).values())


def test_projection_adds_only_verified_public_links_without_changing_snapshot(harness, tmp_path):
    h = harness
    h.fetcher.pages['https://example.com/b'] = b'<article>A different public article</article>'
    assert h.pipeline.run().saved == 2
    root = tmp_path / 'snapshot'
    export_notes(h.store, root)
    manifest, files, metadata = load_snapshot(root)
    before = deepcopy((manifest, files, metadata))
    projected = project_content(manifest, files, metadata)
    assert (manifest, files, metadata) == before
    for entry in manifest['notes']:
        target = next(other['id'] for other in manifest['notes'] if other['id'] != entry['id'])
        assert ('class="shared-keyword-note" href="' + target + '"').encode() in projected[entry['path']]
