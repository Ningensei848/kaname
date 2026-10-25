"""Read-only keyword/tag quality evaluation of a validated public snapshot.

Normalization is an evaluation proposal, not a rewrite or a linking policy.
Keep punctuation meaningful and resolve only a unique public title.
"""
from collections import Counter, defaultdict
import re
import unicodedata

from .publication.note import note_frontmatter
from .wikilinks import GENERIC


NORMALIZER_VERSION = 1
# Reviewed technical synonyms. No stemming, fuzzy matching or inferred aliases.
SYNONYMS = (
    ("LLM", "large language model", "large language models", "大規模言語モデル"),
    ("RAG", "retrieval-augmented generation", "retrieval augmented generation", "検索拡張生成"),
)


def spelling_key(value):
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


def term_key(value):
    key = spelling_key(value)
    for group in SYNONYMS:
        if key in {spelling_key(term) for term in group}:
            return spelling_key(group[0])
    return key


def keyword_terms(data):
    """Inspect the compact keyword section, excluding provenance and images."""
    text, match, _ = note_frontmatter(data)
    body = text[match.end():]
    section = body.split("\n\n## 検索キーワード\n\n", 1)[1].split(
        "\n\n## 資料の位置づけ\n\n", 1)[0]
    return re.findall(r"^- \[\[([^\[\]\n]+)\]\]$", section, re.MULTILINE)


def resolution(candidates, note_id):
    if len(candidates) > 1:
        return "ambiguous"
    if not candidates:
        return "unresolved"
    return "self" if note_id in candidates else "resolved"


def shared_keyword_links(manifest, files):
    """Bounded Note links justified by at least two declared search keywords.

    This is a separate relation from a concept resolving to a defining article.
    Terms appearing in more than 10% of the edition (minimum three Notes) do
    not establish a relation. No titles, body substrings or tag guesses enter it.
    """
    terms = {entry['id']: {term_key(term) for term in keyword_terms(files[entry['path']])
             if len(term_key(term)) >= 3 and term_key(term) not in GENERIC}
             for entry in manifest['notes']}
    frequency = Counter(term for values in terms.values() for term in values)
    maximum = max(3, len(terms) // 10)
    members = defaultdict(set)
    for note_id, values in terms.items():
        for term in values:
            if 2 <= frequency[term] <= maximum:
                members[term].add(note_id)
    result = {}
    for note_id in sorted(terms):
        candidates = defaultdict(set)
        for term in terms[note_id]:
            for other in members.get(term, set()) - {note_id}:
                candidates[other].add(term)
        ranked = sorted((other for other, shared in candidates.items() if len(shared) >= 2),
                        key=lambda other: (-len(candidates[other]),
                            sum(frequency[term] for term in candidates[other]), other))
        result[note_id] = [dict(note_id=other, terms=sorted(candidates[other])) for other in ranked[:3]]
    return result


def graph_quality(manifest, files, metadata, *, details=False):
    titles, proposed_titles = defaultdict(set), defaultdict(set)
    variants = {"tags": defaultdict(set), "keywords": defaultdict(set)}
    occurrences = Counter(tags=0, keywords=0)
    duplicates = Counter(tags=0, keywords=0)
    exact, proposed = Counter(), Counter()
    edges, proposed_edges = set(), set()
    findings = []
    entries = sorted(manifest["notes"], key=lambda e: e["id"])
    for entry in entries:
        titles[entry["title"]].add(entry["id"])
        proposed_titles[term_key(entry["title"])].add(entry["id"])
    for entry in entries:
        note_id = entry["id"]
        terms = keyword_terms(files[entry["path"]])
        for kind, values in (("tags", metadata[note_id]["tags"]), ("keywords", terms)):
            keys = [term_key(value) for value in values]
            occurrences[kind] += len(values)
            duplicates[kind] += len(keys) - len(set(keys))
            for value, key in zip(values, keys):
                variants[kind][key].add(value)
        for term in terms:
            current = resolution(titles[term], note_id)
            candidate = resolution(proposed_titles[term_key(term)], note_id)
            exact[current] += 1
            proposed[candidate] += 1
            if current == "resolved":
                edges.add((note_id, next(iter(titles[term]))))
            if candidate == "resolved":
                proposed_edges.add((note_id, next(iter(proposed_titles[term_key(term)]))))
            if details:
                findings.append(dict(note_id=note_id, term=term, current=current, proposed=candidate))
    counts = lambda values: {key: values[key] for key in ("resolved", "self", "unresolved", "ambiguous")}
    groups = {kind: [dict(key=key, spellings=sorted(values))
                     for key, values in sorted(by_key.items()) if len(values) > 1]
              for kind, by_key in variants.items()}
    result = dict(status="success", normalizer_version=NORMALIZER_VERSION,
                  dataset_digest=manifest["dataset_digest"], notes=len(entries),
                  occurrences=dict(occurrences), normalized_duplicates=dict(duplicates),
                  variant_groups={kind: len(values) for kind, values in groups.items()},
                  current_links=counts(exact), proposed_links=counts(proposed),
                  current_edges=len(edges), proposed_edges=len(proposed_edges),
                  ambiguous_title_groups=sum(len(ids) > 1 for ids in proposed_titles.values()),
                  applied=False)
    shared = shared_keyword_links(manifest, files)
    result['shared_keyword_edges'] = sum(map(len, shared.values()))
    result['shared_keyword_notes'] = sum(bool(links) for links in shared.values())
    if details:
        result["variants"] = groups
        result["links"] = findings
        result['shared_keyword_links'] = shared
    return result
