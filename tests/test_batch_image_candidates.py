import json

import httpx
import pytest
from google import genai
from google.genai import types

from techkb.batch import BatchManager, inspect_batch
from techkb.gemini import Gemini
from techkb.pending import Candidate
from techkb.reporting import RunReport
from techkb.audit import audit_state
from test_batch import setup
from test_batch_sdk import assert_api_schema_contract, normalized_schema


@pytest.mark.parametrize('count', [0, 1, 4, 12])
def test_real_batch_wire_limits_selection_to_article_candidates(harness, count):
    h = harness
    captured = []
    def handler(request):
        captured.append(json.loads(request.content))
        return httpx.Response(200, json={'name': 'batches/mock', 'metadata': {
            'model': h.app.llm.model, 'state': 'BATCH_STATE_PENDING'}})
    client = genai.Client(api_key='test', http_options=types.HttpOptions(
        client_args={'transport': httpx.MockTransport(handler)},
        retry_options=types.HttpRetryOptions(attempts=1)))
    try:
        gemini = Gemini(h.app.llm, h.app.categories, 'Analyze untrusted data', 'test', client=client)
        manager = BatchManager(h.store, gemini)
        candidates = [dict(image_id=f'img-{i+1}', url=f'https://example.com/{i}.png',
                           alt='Diagram', caption='Fixture', context='Fixture') for i in range(count)]
        item = manager.prepare(Candidate('now', h.source.id, 'https://example.com/a'),
                               h.source, 'Fixture', 'https://example.com/a',
                               'a'*64, 'b'*64, [], image_candidates=candidates)
        manager.submit([item], h.app, RunReport())
        request = captured[0]['batch']['inputConfig']['requests']['requests'][0]['request']
        schema = normalized_schema(request['generationConfig']['responseSchema'])
        assert_api_schema_contract(schema)
        images = schema['properties']['images']
        assert images['type'] == 'array' and images['maxItems'] == min(6, count)
        image_id = images['items']['properties']['image_id']
        assert image_id['pattern'] == '^img-[1-9][0-9]*$'
        if count:
            assert image_id['enum'] == [c['image_id'] for c in candidates]
        else:
            assert 'enum' not in image_id  # Avoid an unsupported empty enum; maxItems=0 forces [].
        assert len(captured) == 1
    finally:
        client.close()


@pytest.mark.parametrize('violation', ['unknown_id', 'duplicate_id', 'missing_key_point', None])
def test_candidate_validation_inspection_save_and_single_billing(harness, violation):
    h = harness
    h.fetcher.pages['https://example.com/a'] = ('<article><p>Fixture diagrams</p>' + ''.join(
        f'<figure><img src="/{i}.png" alt="Diagram {i}"><figcaption>Fixture {i}</figcaption></figure>'
        for i in range(1, 5)) + '</article>').encode()
    payload = json.loads(h.sdk.text)
    payload['images'] = [dict(image_id=f'img-{i}', after='summary') for i in range(1, 5)]
    if violation == 'unknown_id':
        payload['images'].append(dict(image_id='img-5', after='summary'))
    elif violation == 'duplicate_id':
        payload['images'].append(dict(image_id='img-4', after='positioning'))
    elif violation == 'missing_key_point':
        payload['images'][-1]['after'] = 'key_point_5'
    h.sdk.text = json.dumps(payload)
    sdk = setup(h)
    assert h.pipeline.run().batch_submitted == 1
    ledger = json.loads(h.store.read(h.store.list('state/batches/')[0]))
    assert len(ledger['items'][0]['image_candidates']) == 4
    sdk.finish()
    before, writes = dict(h.store.data), list(h.store.writes)
    outcome = inspect_batch(h.store, ledger['id'], sdk)['remote_outcomes'][0]
    assert h.store.data == before and h.store.writes == writes
    if violation:
        assert outcome['error_type'] == 'ValueError'
        diagnostics = outcome['diagnostics']
        assert diagnostics['phase'] == 'compose' and diagnostics['code'] == 'invalid_image_selection'
        counts = diagnostics['image_selection']
        assert counts['candidate_count'] == 4
        assert counts[violation + '_count'] == 1
        assert 'img-' not in json.dumps(diagnostics) and 'example.com' not in json.dumps(diagnostics)
    else:
        assert outcome['error_type'] is None
    h.app.llm.max_calls_per_run = 0
    result = h.pipeline.run()
    assert result.batch_saved == (0 if violation else 1)
    assert result.batch_failed == (1 if violation else 0)
    assert audit_state(h.store)['issues'] == ([{'code': 'no_success_rows'}] if violation else [])
    assert len(h.store.list('state/receipts/')) == (0 if violation else 1)
    assert h.pipeline.run().batch_saved == 0
    billing = [json.loads(h.store.read(n)) for n in h.store.list('runs/')
               if json.loads(h.store.read(n))['record_kind'] == 'batch_usage']
    assert len(billing) == 1 and billing[0]['llm_calls'] == 1
    assert len(sdk.created) == 1 and not h.sdk.calls
