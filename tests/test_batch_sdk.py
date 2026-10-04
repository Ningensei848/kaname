"""Exercise the pinned Google SDK wire conversion, not just a batches fake."""
import json
import httpx
from google import genai
from google.genai import types
from techkb.batch import BatchManager
from techkb.gemini import Gemini
from techkb.reporting import RunReport
from techkb.pending import Candidate


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
        gemini=Gemini(h.app.llm,h.app.categories,'Analyze data','test',client=client)
        manager=BatchManager(h.store,gemini)
        item=manager.prepare(Candidate('now',h.source.id,'https://example.com/a'),h.source,'fixture text',
                             'https://example.com/a','a'*64,'b'*64,[])
        manager.submit([item],h.app,RunReport())
        request=captured[0]['batch']['inputConfig']['requests']['requests'][0]
        assert request['metadata']=={'key':'b'*64}
        assert request['request']['generationConfig']['responseJsonSchema']['properties']['category']['enum']==h.app.categories
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
