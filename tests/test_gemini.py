import httpx
from pydantic import ValidationError
import pytest

def test_timeout_is_never_replayed(harness):
    h = harness
    h.sdk.error = httpx.ReadTimeout("test")
    with pytest.raises(httpx.ReadTimeout):
        h.gemini.enrich({}, "body")
    assert len(h.sdk.calls) == 1

def test_invalid_category_no_retry(harness):
    h = harness
    h.sdk.text = h.sdk.text.replace('ai-llm', 'made-up')
    with pytest.raises(ValueError):
        h.gemini.enrich({}, "body")
    assert len(h.sdk.calls) == 1
