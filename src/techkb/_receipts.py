"""Pure Note and index-row construction shared by standard and Batch."""
from .composer import compose


def build_receipt(candidate, source, enrichment, markdown, canonical, fetched_at,
                  raw_hash, content_hash, model, truncated, authors, usage, *,
                  input_char_limit, source_word_count=None, usage_run_id=None,
                  compose_note=compose):
    note_object, note = compose_note(candidate, source, enrichment, markdown, canonical,
                                     fetched_at, raw_hash, content_hash, model, truncated, authors,
                                     input_char_limit=input_char_limit,
                                     source_word_count=source_word_count)
    row = dict(processed_at=fetched_at, source_id=source.id, source_url=candidate.url,
               canonical_url=canonical, published_at=candidate.published_at,
               raw_html_sha256=raw_hash, content_sha256=content_hash, status="success",
               note_object=note_object, llm_model=model, input_tokens=usage.input_tokens,
               output_tokens=usage.output_tokens, thinking_tokens=usage.thinking_tokens,
               llm_input_truncated=str(truncated).lower())
    receipt = {"row": row, "note": note}
    if usage_run_id is not None:
        receipt["usage_run_id"] = usage_run_id
    return receipt
