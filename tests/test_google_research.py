"""Regression for Google Research's body sections and separate media blocks.

The fixture uses synthetic text and the DOM structure observed on GlucoFM;
no original article text or image binaries are copied into the repository.
"""
import json
from pathlib import Path

import pytest
import yaml

from techkb.config import load_config
from techkb.converter import Converter
from techkb.extraction import extract_main
from techkb.html_cleaner import clean_html
from techkb.images import article_images
from techkb.normalize import normalize_markdown
from techkb.state import State
from test_batch import setup


ROOT = Path(__file__).resolve().parents[1]
URL = "https://example.com/a"


@pytest.fixture
def google_article():
    _, sources = load_config(ROOT / "config/app.yaml", ROOT / "config/sources.yaml")
    source = next(source for source in sources if source.id == "google-research")
    raw = (ROOT / "tests/fixtures/google_research_article.html").read_bytes()
    # Reproduce a page whose navigation consumes the input budget before the body.
    raw = raw.replace(b"Changing navigation outside article",
                      b"Changing navigation outside article " * 1000)
    return source, raw


def test_google_body_keeps_all_sections_and_figures_within_input_budget(google_article):
    source, raw = google_article
    app, _ = load_config(ROOT / "config/app.yaml", ROOT / "config/sources.yaml")
    legacy = normalize_markdown(Converter().convert(clean_html(raw)))
    assert len(legacy) > app.llm.max_input_chars
    assert article_images(raw, URL, legacy[:app.llm.max_input_chars]) == []

    extracted = extract_main(raw, source.content_selector)
    markdown = normalize_markdown(Converter().convert(clean_html(extracted)))
    assert len(markdown) < app.llm.max_input_chars
    for text in ("Article introduction.", "First topic explanation.",
                 "Middle topic explanation.", "Last topic explanation.", "Article conclusion."):
        assert text in markdown
    assert "outside article" not in markdown and "Related posts" not in markdown
    images = article_images(extracted, URL, markdown[:app.llm.max_input_chars])
    assert [image["url"] for image in images] == [
        f"https://example.com/figure-{number}.png" for number in range(1, 9)]
    for number in range(1, 9):
        assert f"Caption for diagram {number}." in markdown


@pytest.mark.parametrize("mode", ["standard", "batch"])
def test_google_body_reaches_llm_and_late_image_reaches_note(harness, google_article, mode):
    h = harness
    source, raw = google_article
    h.source.extract_main = source.extract_main
    h.source.content_selector = source.content_selector
    h.fetcher.pages[URL] = raw
    response = json.loads(h.sdk.text)
    response["images"] = [{"image_id": "img-8", "after": "summary"}]
    h.sdk.text = json.dumps(response)

    if mode == "batch":
        sdk = setup(h)
        assert h.pipeline.run().batch_submitted == 1
        content = json.loads(sdk.created[0]["src"][0].contents[0].parts[0].text)
        sdk.finish()
        h.app.llm.max_calls_per_run = 0
        assert h.pipeline.run().batch_saved == 1
        assert len(sdk.created) == 1 and not h.sdk.calls
    else:
        assert h.pipeline.run().saved == 1
        content = json.loads(h.sdk.calls[0]["contents"])
        assert len(h.sdk.calls) == 1

    assert "outside article" not in content["article_markdown"]
    assert "Article conclusion." in content["article_markdown"]
    assert len(content["metadata"]["image_candidates"]) == 8
    assert [image["caption"] for image in content["metadata"]["image_candidates"]] == [
        f"Caption for diagram {number}." for number in range(1, 9)]
    assert "figure-8.png" not in json.dumps(content)
    row = State(h.store).rows[0]
    note = h.store.read(row["note_object"]).decode()
    metadata = yaml.safe_load(note.split("---", 2)[1])
    assert metadata["llm_input_truncated"] is False
    assert metadata["article_images"][0]["url"] == "https://example.com/figure-8.png"
    assert "> 本文に基づく要約です。\n\n![Body diagram 8]" in note

    # Navigation updates must not turn the same body into another paid request.
    h.fetcher.pages[URL] = raw.replace(b"Changing navigation", b"Updated navigation")
    assert h.pipeline.run().content_duplicates == 1
    if mode == "batch":
        assert len(sdk.created) == 1
    else:
        assert len(h.sdk.calls) == 1


def test_google_missing_body_remains_pending_without_llm(harness, google_article):
    h = harness
    source, raw = google_article
    h.source.extract_main = source.extract_main
    h.source.content_selector = source.content_selector
    h.fetcher.pages[URL] = raw.replace(b"blog-detail-wrapper", b"changed-body-wrapper")
    result = h.pipeline.run()
    assert result.status == "failed" and result.pending_after == 1
    assert not h.sdk.calls
    assert not h.store.list("notes/")
