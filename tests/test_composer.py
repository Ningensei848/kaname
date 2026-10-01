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


def test_truncation_notice_preserves_summary_and_records_limit(harness):
    e = ArticleEnrichment(title_ja='Title', summary_ja='要約', key_points=['point', 'point 2'],
        positioning_ja='position', category='other', tags=['tag'],
        related_concepts=['Concept', 'Other concept'], source_language='en')
    args = (Candidate('now', 'example', 'https://example.com/', title='Original'),
            harness.source, e, 'Body', 'https://example.com/',
            '2026-09-25T00:00:00Z', 'a'*64, 'b'*64, 'model')
    for truncated in (False, True):
        _, note = compose(*args, truncated, input_char_limit=20000)
        front = yaml.safe_load(note.split('---', 2)[1])
        assert front['llm_input_max_chars'] == 20000
        assert front['llm_input_truncated'] is truncated
        assert front['description'] == '要約'
        assert ('> [!warning] 要約対象の制限' in note) is truncated
        if truncated:
            assert '先頭20,000文字だけを要約' in note
            assert note.index('[!warning]') < note.index('[!abstract]')
        assert '> 要約' in note
