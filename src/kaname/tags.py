"""Reviewed aliases for Web tags. Stored Notes and WikiLink policy stay intact."""
import re
import unicodedata

TAG_ALIASES = {
    'ai-agent': ('ai-egent', 'ai-agents', 'AI agent', 'AI agents', 'AIエージェント'),
    'llm': ('large language model', 'large language models', '大規模言語モデル'),
    'rag': ('retrieval-augmented generation', 'retrieval augmented generation', '検索拡張生成'),
    'c-plus-plus': ('C++', 'C plus plus', 'cplusplus'),
    'c-sharp': ('C#', 'C sharp', 'csharp'),
}


def spelling(value):
    # Preserve meaningful symbols and tag hierarchy: C/C++/C#, cloud/security.
    return re.sub(r'\s+', '-', unicodedata.normalize('NFKC', value).lower().strip())


def alias_map():
    return {spelling(alias): canonical for canonical, aliases in TAG_ALIASES.items()
            for alias in (canonical, *aliases)}


def canonical_tag(value):
    key = spelling(value)
    return alias_map().get(key, key)


def canonical_tags(values):
    return sorted({canonical_tag(value) for value in values})
