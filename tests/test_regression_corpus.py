"""Reviewable golden corpus plus invariants independent of golden generation."""
import importlib.util
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('regression_corpus', ROOT / 'scripts/regression_corpus.py')
corpus = importlib.util.module_from_spec(spec); spec.loader.exec_module(corpus)

@pytest.mark.parametrize('case', corpus.cases(), ids=lambda case: case['id'])
def test_reviewed_body_and_image_candidates(case):
    assert corpus.check(case) == []
    markdown, images = corpus.project(case)
    assert markdown.strip() and len(markdown) < 20000
    if case['source_id'] == 'google-research':
        for noise in ('Changing navigation outside', 'Related posts'):
            assert noise not in markdown
        assert len(images) == 8 and 'Article conclusion.' in markdown
        assert 'Last topic explanation.' in markdown
    elif case['source_id'] == 'github-blog':
        # Existing GitHub configuration converts the whole page. Freeze that
        # behavior explicitly; corpus acceptance is not a selector change.
        assert 'Navigation links' in markdown
        assert len(images) == 1 and 'measured limitations' in markdown
        assert images[0]['alt'] == 'SDK architecture'
    elif case['source_id'] == 'google-deepmind':
        assert 'Article introduction.' in markdown and 'Article conclusion.' in markdown
        for noise in ('outside article', 'Related posts', 'unwanted()'):
            assert noise not in markdown
        assert len(images) == 1 and images[0]['alt'] == 'Method diagram'


def test_changes_show_a_reviewable_diff(monkeypatch):
    case = corpus.cases()[0]
    markdown, images = corpus.project(case)
    monkeypatch.setattr(corpus, 'project', lambda _: (markdown + '\nUnexpected navigation', images[:-1]))
    diff = '\n'.join(corpus.check(case))
    assert '+Unexpected navigation' in diff and 'Image candidates changed' in diff
