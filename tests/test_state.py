import pytest
from conftest import MemoryStore
from techkb.state import State, encode_tsv, decode_tsv, INDEX_COLUMNS
from techkb.pending import Candidate, COLUMNS, merge_pending

def test_all_months_loaded():
    s = MemoryStore()
    for month in ("2025-12", "2026-01", "2026-09"):
        row = dict.fromkeys(INDEX_COLUMNS, "")
        row.update(processed_at=month + "-01", status="success", raw_html_sha256="a"*64, content_sha256="b"*64)
        s.write(f"state/index/{month}.tsv", encode_tsv([row], INDEX_COLUMNS))
    assert len(State(s).rows) == 3

def test_tsv_quotes_tabs_newlines_unicode():
    c = Candidate("now", "s", "https://example.com/", title='日本語\t"quoted"\nline')
    assert decode_tsv(encode_tsv([c.row()], COLUMNS), COLUMNS) == [c.row()]

def test_corrupt_state_fails_closed():
    with pytest.raises(ValueError):
        decode_tsv(b"wrong\theader\n", COLUMNS)

def test_pending_normalized_and_oldest_first():
    old = Candidate("2026-01-01", "s", "https://example.com/a#old")
    new = Candidate("2026-02-01", "s", "https://example.com/a?utm_source=x")
    merged = merge_pending([old], [new])
    assert len(merged) == 1 and merged[0].discovered_at == old.discovered_at
