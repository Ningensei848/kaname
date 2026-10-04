import json
from types import SimpleNamespace as NS
import httpx
from google.genai import errors
from techkb.operations import cost_report
from techkb.audit import audit_state, audit_run


class BatchSDK:
    def __init__(self,standard):
        self.batches=self
        self.models=standard
        self.standard=standard
        self.created=[]; self.jobs={}; self.timeout=False; self.visible=True; self.reject=False
    def create(self,**kwargs):
        self.created.append(kwargs)
        if self.reject:
            raise errors.ClientError(400,{'error':{'message':'invalid batch'}})
        job=NS(name='batches/'+str(len(self.created)),display_name=kwargs['config'].display_name,
               model=kwargs['model'],state=NS(name='JOB_STATE_PENDING'),dest=None)
        self.jobs[job.name]=job
        if self.timeout:
            raise httpx.ReadTimeout('ambiguous submit')
        return job
    def get(self,name): return self.jobs[name]
    def list(self): return list(self.jobs.values()) if self.visible else []
    def finish(self,failed_keys=(),reverse=False):
        request=self.created[-1]; job=self.jobs['batches/'+str(len(self.created))]
        results=[]
        for item in request['src']:
            key=item.metadata['key']
            response=NS(text=self.standard.text,usage_metadata=NS(prompt_token_count=100,candidates_token_count=20,thoughts_token_count=5))
            results.append(NS(metadata={'key':key},error=NS(code=400) if key in failed_keys else None,response=response))
        job.state=NS(name='JOB_STATE_SUCCEEDED');job.dest=NS(inlined_responses=results[::-1] if reverse else results)


def setup(h):
    sdk=BatchSDK(h.sdk); h.gemini.client=sdk; h.app.llm.mode='batch'
    return sdk


def test_batch_submit_poll_save_and_standard_switch_without_double_charge(harness):
    h=harness; sdk=setup(h)
    first=h.pipeline.run()
    assert first.status=='success' and first.batch_submitted==1 and first.saved==0 and first.pending_after==1
    ledger=json.loads(h.store.read(h.store.list('state/batches/')[0]))
    assert 'Original text' not in json.dumps(ledger)
    submitted=sdk.created[0]['src'][0]
    assert 'Original text' in submitted.contents[0].parts[0].text
    assert submitted.config.thinking_config.thinking_level.name=='MINIMAL'
    assert submitted.config.response_json_schema['properties']['category']['enum']==h.app.categories
    assert cost_report(h.store,h.app)['pending_batch_items']==1
    h.app.llm.mode='standard'
    waiting=h.pipeline.run()
    assert waiting.batch_jobs_pending==1 and not h.sdk.calls and len(sdk.created)==1
    sdk.finish()
    settled=h.pipeline.run()
    assert settled.status=='success' and settled.batch_saved==1 and settled.saved==1 and settled.pending_after==0
    assert audit_state(h.store)['issues']==[]
    assert audit_run(h.store,settled.run_id,expected_success_before=0)['status']=='success'
    assert len(sdk.created)==1 and not h.sdk.calls
    assert h.pipeline.run().saved==0
    billing=[json.loads(h.store.read(n)) for n in h.store.list('runs/') if json.loads(h.store.read(n))['record_kind']=='batch_usage']
    assert len(billing)==1 and billing[0]['total_input_tokens']==100
    costs=cost_report(h.store,h.app)
    assert costs['uncertain_runs']==0
    assert len(h.store.list('state/receipts/'))==1


def test_ambiguous_creation_reconciles_existing_job(harness):
    h=harness; sdk=setup(h); sdk.timeout=True
    assert h.pipeline.run().status=='failed'
    assert len(sdk.created)==1
    sdk.visible=False
    assert h.pipeline.run().status=='failed'
    assert len(sdk.created)==1 and not h.sdk.calls
    sdk.visible=True; sdk.finish()
    assert h.pipeline.run().saved==1
    assert len(sdk.created)==1


def test_partial_reordered_results_keep_failed_item_pending(harness):
    h=harness; sdk=setup(h)
    h.fetcher.pages['https://example.com/b']=b'<article>Different article text</article>'
    assert h.pipeline.run().batch_submitted==2
    failed=sdk.created[0]['src'][0].metadata['key']; sdk.finish([failed],reverse=True)
    h.app.llm.max_calls_per_run=0
    result=h.pipeline.run()
    assert result.status=='failed' and result.batch_saved==1 and result.batch_failed==1 and result.pending_after==1
    assert audit_state(h.store)['issues']==[]
    assert len(sdk.created)==1


def test_batch_durability_failure_recovers_receipt_without_new_job(harness):
    h=harness; sdk=setup(h); h.pipeline.run(); sdk.finish()
    h.store.fail_prefix='notes/'
    assert h.pipeline.run().status=='failed'
    h.store.fail_prefix=None
    recovered=h.pipeline.run()
    assert recovered.saved==1 and recovered.recovered==1 and recovered.status=='success'
    assert len(sdk.created)==1 and not h.sdk.calls
    assert audit_state(h.store)['issues']==[]


def test_duplicate_response_keys_fail_closed(harness):
    h=harness; sdk=setup(h); h.pipeline.run(); sdk.finish()
    job=sdk.jobs['batches/1']; job.dest.inlined_responses*=2
    result=h.pipeline.run()
    assert result.status=='failed' and result.saved==0
    assert len(sdk.created)==1 and not h.sdk.calls


def test_definitive_batch_rejection_does_not_block_standard_collection(harness):
    h=harness; sdk=setup(h); sdk.reject=True
    assert h.pipeline.run().status=='failed'
    assert cost_report(h.store,h.app)['pending_batch_items']==0
    h.app.llm.mode='standard'
    assert h.pipeline.run().saved==1
    assert len(sdk.created)==1 and len(h.sdk.calls)==1
