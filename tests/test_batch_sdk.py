"""Exercise the pinned Google SDK wire conversion, not just a batches fake."""
import json
from pathlib import Path
import httpx
import pytest
from google import genai
from google.genai import types
from techkb.batch import BatchManager
from techkb.gemini import Gemini
from techkb.reporting import RunReport
from techkb.pending import Candidate
from techkb.audit import audit_state
from techkb.operations import cost_report
from techkb.models import ArticleEnrichment


def normalized_schema(schema):
    """Compare JSON schema constraints across SDK/protobuf field spellings."""
    if isinstance(schema, list):
        return [normalized_schema(item) for item in schema]
    if not isinstance(schema, dict):
        return schema
    names = {'additional_properties': 'additionalProperties', 'max_items': 'maxItems',
             'min_items': 'minItems', 'max_length': 'maxLength', 'min_length': 'minLength'}
    result = {names.get(key, key): normalized_schema(value) for key, value in schema.items()
              if key not in {'default', 'property_ordering', 'propertyOrdering'}}
    if isinstance(result.get('type'), str):
        result['type'] = result['type'].lower()
    return result


def test_real_sdk_serializes_batch_request_and_reads_inline_response(harness):
    h=harness; captured=[]; remote={}
    def handler(req):
        if req.method=='POST':
            body=json.loads(req.content); captured.append(body)
            remote.update(name='batches/mock',metadata={'displayName':body['batch']['displayName'],
                          'model':h.app.llm.model,'state':'BATCH_STATE_PENDING'})
        return httpx.Response(200,json=remote)
    client=genai.Client(api_key='test',http_options=types.HttpOptions(
        client_args={'transport':httpx.MockTransport(handler)},retry_options=types.HttpRetryOptions(attempts=1)))
    try:
        prompt = (Path(__file__).resolve().parents[1] / 'prompts/enrich.txt').read_text(encoding='utf-8')
        gemini=Gemini(h.app.llm,h.app.categories,prompt,'test',client=client)
        manager=BatchManager(h.store,gemini)
        images = [dict(image_id='img-1', url='https://example.com/diagram.png',
                       alt='Fixture diagram', caption='fixture text', context='fixture text')]
        item=manager.prepare(Candidate('now',h.source.id,'https://example.com/a'),h.source,'fixture text',
                             'https://example.com/a','a'*64,'b'*64,[],image_candidates=images)
        manager.submit([item],h.app,RunReport())
        request=captured[0]['batch']['inputConfig']['requests']['requests'][0]
        assert request['metadata']=={'key':'b'*64}
        assert 'responseJsonSchema' not in request['request']['generationConfig']
        assert request['request']['generationConfig']['responseSchema']['properties']['category']['enum']==h.app.categories
        schema = normalized_schema(request['request']['generationConfig']['responseSchema'])
        expected_schema = ArticleEnrichment.model_json_schema()
        image_definition = expected_schema.pop('$defs')['ImageSelection']
        expected_schema['properties']['images']['items'] = image_definition
        expected_schema['properties']['category']['enum'] = h.app.categories
        assert schema == normalized_schema(expected_schema)
        assert 'title_ja' in schema['required'] and schema['additionalProperties'] is False
        assert schema['properties']['images']['type'] == 'array'
        image_schema = schema['properties']['images']['items']
        assert image_schema['type'] == 'object'
        assert image_schema['required'] == ['image_id', 'after']
        assert image_schema['additionalProperties'] is False
        assert image_schema['properties']['image_id']['pattern'] == '^img-[1-9][0-9]*$'
        assert image_schema['properties']['after']['enum'] == [
            'summary', 'key_point_1', 'key_point_2', 'key_point_3', 'key_point_4', 'key_point_5', 'positioning']
        assert schema['properties']['images']['maxItems'] == 6
        assert '$ref' not in json.dumps(schema) and '$defs' not in schema
        assert request['request']['systemInstruction']['parts'] == [
            {'text': prompt + '\nカテゴリ候補: ' + ', '.join(h.app.categories)}]
        assert request['request']['generationConfig']['responseMimeType'] == 'application/json'
        assert request['request']['generationConfig']['maxOutputTokens'] == h.app.llm.max_output_tokens
        sent = request['request']['contents'][0]['parts'][0]['text']
        metadata = json.loads(sent)['metadata']
        assert metadata['image_candidates'] == [dict(image_id='img-1', alt='Fixture diagram',
                                                    caption='fixture text', context='fixture text')]
        assert images[0]['url'] not in sent
        thinking=request['request']['generationConfig']['thinkingConfig']
        assert thinking.get('thinkingLevel',thinking.get('thinking_level')).lower()=='minimal'
        response={'candidates':[{'content':{'role':'model','parts':[{'text':h.sdk.text}]}}],
                  'usageMetadata':{'promptTokenCount':100,'candidatesTokenCount':20,'thoughtsTokenCount':5}}
        remote['metadata'].update(state='BATCH_STATE_SUCCEEDED',output={'inlinedResponses':{'inlinedResponses':[
            {'metadata':{'key':'b'*64},'response':response}]}})
        fetched=client.batches.get(name='batches/mock')
        assert fetched.state.name=='JOB_STATE_SUCCEEDED'
        assert fetched.dest.inlined_responses[0].response.text==h.sdk.text
        assert fetched.dest.inlined_responses[0].response.usage_metadata.prompt_token_count==100
    finally:
        client.close()


@pytest.mark.parametrize("failure", [None, 'missing_title', 'missing_title_and_invalid_images', 'invalid_images'])
def test_real_sdk_result_passes_through_settle_and_billing(harness, failure):
    h = harness
    remote = {}
    posts = []
    mismatched_title = json.loads(h.sdk.text)
    if failure in {'missing_title', 'missing_title_and_invalid_images'}:
        mismatched_title['PRIVATE_EXTRA_FIELD'] = mismatched_title.pop('title_ja')
    if failure in {'missing_title_and_invalid_images', 'invalid_images'}:
        mismatched_title['images'] = ['PRIVATE_IMAGE_VALUE'] * 3
    def handler(req):
        if req.method == 'POST':
            body = json.loads(req.content)
            posts.append(body)
            key = body['batch']['inputConfig']['requests']['requests'][0]['metadata']['key']
            response = {'candidates': [{'content': {'role': 'model', 'parts': [
                {'text': h.sdk.text if failure is None else json.dumps(mismatched_title)}]}, 'finishReason': 'STOP'}],
                'usageMetadata': {'promptTokenCount': 100, 'candidatesTokenCount': 20, 'thoughtsTokenCount': 5}}
            remote.update(name='batches/mock', metadata={'displayName': body['batch']['displayName'],
                'model': h.app.llm.model, 'state': 'BATCH_STATE_SUCCEEDED',
                'output': {'inlinedResponses': {'inlinedResponses': [{'metadata': {'key': key}, 'response': response}]}}})
        return httpx.Response(200, json=remote)
    client = genai.Client(api_key='test', http_options=types.HttpOptions(
        client_args={'transport': httpx.MockTransport(handler)}, retry_options=types.HttpRetryOptions(attempts=1)))
    h.gemini.client = client
    h.app.llm.mode = 'batch'
    try:
        assert h.pipeline.run().batch_submitted == 1
        h.app.llm.mode = 'standard'
        h.app.llm.max_calls_per_run = 0
        report = h.pipeline.run()
        if failure is None:
            assert report.status == 'success' and report.batch_saved == 1
            assert audit_state(h.store)['issues'] == []
        else:
            assert report.status == 'failed' and report.batch_failed == 1 and report.saved == 0
            assert report.failures[0]['error_type'] == 'ValidationError'
            assert report.failures[0]['diagnostics']['finish_reason'] == 'STOP'
            assert report.failures[0]['diagnostics']['phase'] == 'validation'
            expected = [{'field': '$', 'code': 'extra_forbidden'}, {'field': 'title_ja', 'code': 'missing'}]
            if failure == 'missing_title_and_invalid_images':
                expected.insert(1, {'field': 'images', 'code': 'model_type'})
            if failure == 'invalid_images':
                expected = [{'field': 'images', 'code': 'model_type'}]
                assert report.failures[0]['diagnostics']['images_shape'] == {
                    'type': 'array', 'count': 3, 'items': [{'type': 'string'}] * 3, 'omitted_items': 0}
                assert h.store.list('state/receipts/') == []
                assert audit_state(h.store)['success_rows'] == 0
            assert report.failures[0]['diagnostics']['validation_errors'] == expected
            assert 'PRIVATE' not in report.to_bytes().decode()
        billing = [json.loads(h.store.read(name)) for name in h.store.list('runs/')
                   if json.loads(h.store.read(name))['record_kind'] == 'batch_usage']
        assert len(billing) == 1 and billing[0]['total_input_tokens'] == 100
        before = cost_report(h.store, h.app)
        h.pipeline.run()
        assert cost_report(h.store, h.app) == before
        assert len(posts) == 1
    finally:
        client.close()


@pytest.mark.parametrize('with_images', [False, True])
def test_standard_and_batch_wire_payload_preserve_same_content_and_schema_constraints(harness, with_images):
    """Compare both real SDK serializers with the same article and metadata."""
    h = harness
    sent = {}
    def handler(req):
        body = json.loads(req.content)
        if req.url.path.endswith(':generateContent'):
            sent['standard'] = body
            return httpx.Response(200, json={'candidates': [{'content': {'role': 'model', 'parts': [{'text': h.sdk.text}]}}]})
        sent['batch'] = body['batch']['inputConfig']['requests']['requests'][0]['request']
        return httpx.Response(200, json={'name': 'batches/mock', 'metadata': {'state': 'BATCH_STATE_PENDING'}})
    client = genai.Client(api_key='test', http_options=types.HttpOptions(
        client_args={'transport': httpx.MockTransport(handler)}, retry_options=types.HttpRetryOptions(attempts=1)))
    try:
        gemini = Gemini(h.app.llm, h.app.categories, Path('prompts/enrich.txt').read_text(), 'test', client=client)
        manager = BatchManager(h.store, gemini)
        markdown = 'Exact input including Japanese 日本語 and <untrusted> data.'
        from techkb._standard import StandardRequest
        candidate = Candidate('now', h.source.id, 'https://example.com/a', title='日本語の候補')
        images = [dict(image_id='img-1', url='https://example.com/figure.png', alt='Fixture',
                       caption='Caption', context='Exact input')] if with_images else []
        authors = ['Fixture Author']
        item = manager.prepare(candidate, h.source, markdown, 'https://example.com/a',
                               'a'*64, 'b'*64, authors, image_candidates=images)
        request = StandardRequest(h.store, gemini, RunReport(llm_calls=1))
        request.enrich(candidate, h.source, markdown, False, authors, image_candidates=images)
        manager.submit([item], h.app, RunReport())
        standard_config = sent['standard']['generationConfig']
        batch_config = sent['batch']['generationConfig']
        standard_schema = standard_config.pop('responseJsonSchema')
        batch_schema = batch_config.pop('responseSchema')
        assert 'responseSchema' not in standard_config and 'responseJsonSchema' not in batch_config
        assert normalized_schema(standard_schema) == normalized_schema(batch_schema)
        assert sent['standard'] == sent['batch']
    finally:
        client.close()
