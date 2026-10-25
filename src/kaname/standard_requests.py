"""Durable standard request reservations and response recovery, never API retries.

The raw article and API credentials are never persisted here. A response and
its original composition context let recovery finish without fetching again.
An unanswered reservation is held until an explicit, cost-bounded retry.
"""
import json
import re
from types import SimpleNamespace

from ._receipts import build_receipt
from .config import Source
from .gemini import Usage, validate_response
from .pending import Candidate
from .usage import FIELDS

PREFIX = 'state/standard-requests/'


class UnresolvedStandardRequest(RuntimeError):
    pass


def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True).encode()


class StandardRequests:
    def __init__(self, store, retry_content=None):
        self.store, self.retry_content = store, retry_content
        self.retried = False

    def write(self, record):
        self.store.write(PREFIX + record['content_sha256'] + '.json', encode(record), 'application/json')

    def load(self, name):
        data = self.store.read(name)
        record = json.loads(data or b'null')
        if (not isinstance(record, dict) or type(record.get('schema_version')) is not int or record['schema_version'] != 1 or
                not re.fullmatch(r'[0-9a-f]{64}', record.get('content_sha256', '')) or
                name != PREFIX + record['content_sha256'] + '.json' or
                not re.fullmatch(r'\d{8}T\d{6}Z-[0-9a-f]{8}', record.get('run_id', '')) or
                record.get('status') not in {'reserved', 'response', 'complete'} or
                not isinstance(record.get('context'), dict)):
            raise ValueError('invalid standard request record')
        return record

    def reserve(self, content, context, report):
        name = PREFIX + content + '.json'
        previous = self.store.read(name)
        if previous is not None:
            old = self.load(name)
            if content != self.retry_content or old['status'] == 'complete':
                raise UnresolvedStandardRequest()
            # Preserve each original request/billing identity before replacing
            # a held reservation. The GCS Store guards both writes by generation.
            history = 'state/standard-request-history/' + content + '/' + old['run_id'] + '.json'
            archived = self.store.read(history)
            if archived is not None and archived != encode(old):
                raise ValueError('conflicting standard request history')
            if archived is None:
                self.store.write(history, encode(old), 'application/json')
            self.retried = True
        elif content == self.retry_content:
            raise ValueError('retry requires an existing standard request')
        record = dict(schema_version=1, content_sha256=content, run_id=report.run_id,
                      status='reserved', context=context)
        self.write(record)
        return record

    def capture(self, record, gemini, report):
        if gemini.last_response is None:
            return
        record.update(status='response', response_text=gemini.last_response.text or '',
                      usage=dict(input_tokens=gemini.last_usage.input_tokens,
                                 output_tokens=gemini.last_usage.output_tokens,
                                 thinking_tokens=gemini.last_usage.thinking_tokens),
                      usage_record={key: getattr(report, key) for key in FIELDS})
        self.write(record)

    def complete(self, record):
        record['status'] = 'complete'
        self.write(record)

    def repair_usage(self, record):
        saved = record['usage_record']
        name = 'state/standard-usage/' + record['run_id'] + '.json'
        current = json.loads(self.store.read(name) or b'null')
        if (not isinstance(current, dict) or any(current.get(key) != saved.get(key) for key in
                ('run_id', 'started_at', 'llm_model', 'llm_mode', 'token_price'))):
            raise ValueError('conflicting standard request usage')
        # A later request in the same original run must never be rewound.
        if current['llm_calls'] > saved['llm_calls']:
            return
        counts = FIELDS[5:]
        if (current['llm_calls'] != saved['llm_calls'] or
                any(current[key] > saved[key] for key in counts)):
            raise ValueError('conflicting standard request usage totals')
        restored = dict(saved, schema_version=1, pending=False)
        if current != restored:
            self.store.write(name, encode(restored), 'application/json')

    def receipt(self, record, categories, compose_note):
        context = record['context']
        enrichment = validate_response(SimpleNamespace(text=record['response_text']), categories)
        return build_receipt(Candidate(**context['candidate']), Source.model_validate(context['source']),
            enrichment, '', context['canonical'], context['fetched_at'], context['raw_hash'],
            record['content_sha256'], context['model'], context['truncated'], context['authors'],
            Usage(**record['usage']), input_char_limit=context['input_char_limit'],
            source_word_count=context['source_word_count'], usage_run_id=record['run_id'],
            compose_note=compose_note, image_candidates=context['image_candidates'])

    def recover(self, categories, compose_note):
        records = [self.load(name) for name in self.store.list(PREFIX)]
        blocked = False
        for record in records:
            if record['status'] == 'complete':
                if self.store.read('state/receipts/' + record['content_sha256'] + '.json') is None:
                    raise ValueError('completed standard request missing receipt')
                continue
            if record['content_sha256'] == self.retry_content:
                continue
            if record['status'] == 'reserved':
                blocked = True
                continue
            self.repair_usage(record)
            target = 'state/receipts/' + record['content_sha256'] + '.json'
            existing = self.store.read(target)
            if existing is None:
                try:
                    receipt = self.receipt(record, categories, compose_note)
                except (ValueError, TypeError, KeyError):
                    # A rejected response cannot permit another charge, but it
                    # need not prevent recovery of other already-paid results.
                    blocked = True
                    continue
                self.store.write(target, encode(receipt), 'application/json')
            else:
                # A durable receipt preserves its original bytes across later
                # composer/config versions. Never recompute it on recovery.
                receipt = json.loads(existing)
                context = record['context']
                expected = dict(content_sha256=record['content_sha256'], raw_html_sha256=context['raw_hash'],
                    source_id=context['source']['id'], source_url=context['candidate']['url'],
                    canonical_url=context['canonical'], processed_at=context['fetched_at'], llm_model=context['model'])
                if (receipt.get('usage_run_id') != record['run_id'] or not isinstance(receipt.get('note'), str) or
                        any(receipt.get('row', {}).get(key) != value for key, value in expected.items())):
                    raise ValueError('conflicting standard request receipt')
            self.complete(record)
        return blocked or bool(self.legacy_pending_runs(records))

    def legacy_pending_runs(self, records):
        owned = {record['run_id'] for record in records}
        for name in self.store.list('state/standard-request-history/'):
            match = re.fullmatch(r'state/standard-request-history/[0-9a-f]{64}/(\d{8}T\d{6}Z-[0-9a-f]{8})\.json', name)
            if not match:
                raise ValueError('invalid standard request history identity')
            owned.add(match[1])
        # Old journals did not identify the article. An interrupted request
        # cannot be safely assigned to a hash or silently re-generated.
        pending = []
        for name in self.store.list('state/standard-usage/'):
            journal = json.loads(self.store.read(name) or b'null')
            if not isinstance(journal, dict):
                raise ValueError('invalid standard usage journal')
            if not journal.get('pending'):
                continue
            run_id = journal.get('run_id', '')
            if not re.fullmatch(r'\d{8}T\d{6}Z-[0-9a-f]{8}', run_id):
                raise ValueError('invalid standard usage identity')
            if run_id in owned:
                continue
            report = json.loads(self.store.read('runs/' + run_id[:4] + '/' + run_id[4:6] + '/' + run_id + '.json') or b'null')
            if not isinstance(report, dict) or report.get('llm_usage_unavailable', 1):
                pending.append(run_id)
        return sorted(pending)

    def status(self):
        records = [self.load(name) for name in self.store.list(PREFIX)]
        return dict(status='success', requests=[{key: record[key] for key in
            ('content_sha256', 'run_id', 'status')} for record in records if record['status'] != 'complete'],
            completed=sum(record['status'] == 'complete' for record in records),
            legacy_pending_runs=self.legacy_pending_runs(records))
