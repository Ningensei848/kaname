import yaml
from techkb.composer import compose, filename
from techkb.models import ArticleEnrichment
from techkb.pending import Candidate

def test_filename_safe_and_bounded():
    name = filename('a/b:c*?"<>|\\' + '日本語'*100, '2026-09-25', 'a'*64)
    assert all(c not in name for c in '/\\:*?"<>|')
    assert len(name.encode()) < 255 and name.endswith('_aaaaaaaaaaaa.md')

def test_yaml_and_wikilinks_are_safe(harness):
    e = ArticleEnrichment(title_ja='Title: "quoted"', summary_ja='a\n# injected', key_points=['point', 'point 2'],
        positioning_ja='position\n# injected', category='other', tags=['a b'],
        related_concepts=['A]]\n# heading|alias', 'Safe concept'], source_language='en')
    path, note = compose(Candidate('now', 'example', 'https://example.com/', title='Original: x'), harness.source,
        e, 'Body', 'https://example.com/', '2026-09-25T00:00:00Z', 'a'*64, 'b'*64, 'model', False,
        ['Alice Example'])
    front = yaml.safe_load(note.split('---', 2)[1])
    assert front['title'] == e.title_ja
    assert front['source'] == 'https://example.com/'
    assert front['author'] == ['[[Alice Example]]']
    assert front['published'] is None
    assert front['tags'][0] == 'clippings'
    assert '\n# injected' not in note
    assert '[[A]]' not in note
    assert '## 検索キーワード' in note
    assert '## 資料の位置づけ' in note
    assert '## 出典情報' in note
    assert '## 原文' not in note
    assert '\nBody\n' not in note
    assert '- Word count: 1' in note
    assert '- Author: Alice Example' in note
