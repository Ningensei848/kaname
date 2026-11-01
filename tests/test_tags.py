import pytest
import yaml

from kaname.tags import canonical_tag, canonical_tags
from kaname.publication import export_notes
from kaname.site import load_snapshot, project_content


@pytest.mark.parametrize('term', ['ai-egent', 'AIエージェント', 'ai-agent', 'AI agents', 'ＡＩ－ＡＧＥＮＴ'])
def test_reviewed_aliases_share_a_tag(term):
    assert canonical_tag(term) == 'ai-agent'


def test_normalization_preserves_distinct_symbols_and_hierarchy():
    assert canonical_tags(['C', 'C++', 'C#', 'GraphRAG', 'RAG', 'cloud/security', 'cloud-security']) == [
        'c', 'c-plus-plus', 'c-sharp', 'cloud-security', 'cloud/security', 'graphrag', 'rag']
    assert canonical_tags(['LLM', '大規模言語モデル', 'ｌｌｍ']) == ['llm']


def test_only_web_projection_changes_not_stored_snapshot(harness, tmp_path):
    harness.pipeline.run()
    root = tmp_path / 'snapshot'
    export_notes(harness.store, root)
    manifest, files, metadata = load_snapshot(root)
    before = dict(files)
    digest = manifest['dataset_digest']
    entry = manifest['notes'][0]
    metadata[entry['id']]['tags'] = ['AIエージェント', 'ai-egent', 'AI-agent']
    projected = project_content(manifest, files, metadata)
    front = yaml.safe_load(projected[entry['path']].decode().split('---', 2)[1])
    assert front['tags'] == ['ai-agent']
    assert files == before and manifest['dataset_digest'] == digest


def test_new_notes_canonicalize_before_symbol_sanitizing(harness):
    from kaname.publication import note_frontmatter
    import json
    enrichment = json.loads(harness.sdk.text)
    enrichment['tags'] = ['C', 'C++', 'C#', 'ai-egent', 'AIエージェント']
    harness.sdk.text = json.dumps(enrichment, ensure_ascii=False)
    result = harness.pipeline.run()
    assert result.saved == 1
    meta = note_frontmatter(harness.store.read(harness.store.list('notes/')[0]))[2]
    assert {'c', 'c-plus-plus', 'c-sharp', 'ai-agent'} <= set(meta['tags'])
    assert meta['tags'].count('ai-agent') == 1
