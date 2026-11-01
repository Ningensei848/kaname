"""Pure candidate completion and stop decisions; no clients or persistence."""

DURABILITY_STAGES = frozenset({'receipt_save', 'note_or_index_save', 'raw_save', 'usage_reserve', 'usage_save',
                              'standard_request_reserve', 'standard_response_save'})


def partition_known(candidates, known, enabled):
    remaining, skipped = [], []
    for candidate in candidates:
        target = skipped if candidate.source_id in enabled and known.contains(candidate) else remaining
        target.append(candidate)
    return remaining, skipped


def completed_sources(feed_urls, candidates, done):
    return sorted(source for source in feed_urls
                  if (feed_urls[source] | {c.url for c in candidates if c.source_id == source}) <= done)


def failure_stop_reason(stage, cost_limited):
    if cost_limited and stage in {'llm', 'compose'}:
        return 'generation_failed'
    return 'durability' if stage in DURABILITY_STAGES else None


def batch_submission_allowed(failures):
    return not any(failure['stage'] in DURABILITY_STAGES for failure in failures)
