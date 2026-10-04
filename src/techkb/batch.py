"""Durable asynchronous inline batches. No article bodies in the local ledger."""
from dataclasses import asdict
import json
import hashlib
import re
from types import SimpleNamespace
from google.genai import types, errors
from .composer import compose, word_count
from .gemini import response_usage, validate_response
from .pending import Candidate
from .reporting import RunReport, now


class BatchManager:
    def __init__(self, store, gemini):
        self.store, self.gemini = store, gemini
        self.jobs = []
        for name in store.list('state/batches/'):
            data = store.read(name)
            if data is None:
                raise ValueError('batch ledger missing')
            ledger = json.loads(data)
            if ledger['status'] != 'complete':
                self.jobs.append((name, ledger))

    def active_hashes(self):
        return {item['ch'] for _, job in self.jobs if job['status'] != 'complete' for item in job['items']}

    def persist(self, name, job):
        self.store.write(name,json.dumps(job,ensure_ascii=False).encode(),'application/json')

    def prepare(self,candidate,source,markdown,canon,rh,ch,authors):
        metadata=dict(title=candidate.title[:1000],source=source.name,authors=authors,
                      published_at=candidate.published_at,llm_input_truncated=len(markdown)>self.gemini.config.max_input_chars)
        content,config=self.gemini.request(metadata,markdown)
        request=types.InlinedRequest(contents=[types.Content(role='user',parts=[types.Part(text=content)])],
                                     config=config,metadata={'key':ch})
        item=dict(candidate=candidate.row(),source=dict(id=source.id,name=source.name,tags=source.tags),
                  canon=canon,rh=rh,ch=ch,authors=authors,word_count=word_count(markdown),
                  truncated=metadata['llm_input_truncated'],status='pending')
        return item,request

    def submit(self, prepared, app, report):
        if not prepared:
            return
        # Body size includes structured config, Unicode encoding and SDK metadata.
        requests=[request for _,request in prepared]
        if sum(len(request.model_dump_json().encode()) for request in requests)>19_000_000:
            raise ValueError('inline batch exceeds conservative size limit')
        key=report.run_id
        price=app.costs.prices.get(app.llm.model,{}).get('batch')
        job=dict(id=key,status='submitting',display_name='techkb-'+key,name=None,model=app.llm.model,
                 categories=app.categories,input_char_limit=app.llm.max_input_chars,created_at=now(),
                 token_price=price.model_dump() if price else None,items=[item for item,_ in prepared])
        name='state/batches/'+key+'.json'
        # A timeout after this reservation must never trigger blind resubmission.
        self.persist(name,job)
        self.jobs.append((name,job))
        try:
            created=self.gemini.client.batches.create(model=app.llm.model,src=requests,
                                                    config=types.CreateBatchJobConfig(display_name=job['display_name']))
        except errors.APIError as exc:
            if exc.code in {400, 401, 403, 404, 422}:
                # A definitive request rejection has not created a paid job. Do
                # not let it freeze standard collection behind an ambiguous lock.
                job['status']='complete'; job['submission_rejected']=True
                job['error_type']=type(exc).__name__; self.persist(name,job)
            raise
        if not created.name:
            raise ValueError('batch job name unavailable')
        job['name']=created.name; job['status']='submitted'
        self.persist(name,job)
        report.batch_submitted+=len(prepared)

    def bind(self,ledger_id,job_name):
        if not re.fullmatch(r'\d{8}T\d{6}Z-[0-9a-f]{8}',ledger_id):
            raise ValueError('invalid batch ID')
        match=[(name,job) for name,job in self.jobs if job['id']==ledger_id]
        if len(match)!=1 or match[0][1]['name']:
            raise ValueError('batch is not awaiting reconciliation')
        name,job=match[0]
        remote=self.gemini.client.batches.get(name=job_name)
        if remote.display_name!=job['display_name'] or (remote.model and remote.model.removeprefix('models/')!=job['model']):
            raise ValueError('batch does not match reservation')
        job['name']=remote.name; job['status']='submitted'; self.persist(name,job)

    def settle(self, save_receipt, state, dedupe, report, done):
        for name,job in self.jobs:
            if job['status']=='complete':
                continue
            if not job['name']:
                # Only exact display-name reconciliation is allowed after ambiguous create.
                matches=[remote for remote in self.gemini.client.batches.list()
                         if remote.display_name==job['display_name']]
                if len(matches)!=1:
                    raise ValueError('ambiguous batch submission; inspect batch and use batch-bind')
                self.bind(job['id'],matches[0].name)
            if 'outcomes' not in job:
                remote=self.gemini.client.batches.get(name=job['name'])
                state_name=remote.state.name if remote.state else ''
                if state_name not in {'JOB_STATE_SUCCEEDED','JOB_STATE_FAILED','JOB_STATE_CANCELLED','JOB_STATE_EXPIRED'}:
                    report.batch_jobs_pending+=1; continue
                responses=(remote.dest.inlined_responses if remote.dest else None) or []
                by_key={}
                expected={item['ch'] for item in job['items']}
                for result in responses:
                    key=(result.metadata or {}).get('key')
                    if key not in expected or key in by_key:
                        raise ValueError('unknown or duplicate batch response key')
                    by_key[key]=result
                outcomes=[]
                for item in job['items']:
                    result=by_key.get(item['ch'])
                    response=result.response if result and not result.error else None
                    usage,available=response_usage(response)
                    outcome=dict(ch=item['ch'],usage=asdict(usage),usage_available=available,error=None,receipt=None)
                    try:
                        if response is None:
                            raise ValueError('batch item failed or missing')
                        enrichment=validate_response(response,job['categories'])
                        candidate=Candidate(**item['candidate']); source=SimpleNamespace(**item['source'])
                        fetched_at=now()
                        obj,note=compose(candidate,source,enrichment,'',item['canon'],fetched_at,item['rh'],item['ch'],
                                         job['model'],item['truncated'],item['authors'],
                                         input_char_limit=job['input_char_limit'],source_word_count=item['word_count'])
                        row=dict(processed_at=fetched_at,source_id=source.id,source_url=candidate.url,
                                 canonical_url=item['canon'],published_at=candidate.published_at,raw_html_sha256=item['rh'],
                                 content_sha256=item['ch'],status='success',note_object=obj,llm_model=job['model'],
                                 input_tokens=usage.input_tokens,output_tokens=usage.output_tokens,
                                 thinking_tokens=usage.thinking_tokens,llm_input_truncated=str(item['truncated']).lower())
                        outcome['receipt']={'row':row,'note':note}
                    except Exception as exc:
                        outcome['error']=type(exc).__name__
                    outcomes.append(outcome)
                job['outcomes']=outcomes; job['settled_at']=now()
                job['billing_run_id']=job['settled_at'][:19].replace('-','').replace(':','')+'Z-'+hashlib.sha256(('batch:'+job['id']).encode()).hexdigest()[:8]
                # Persist compact outcomes before writing cost report or Note/index.
                self.persist(name,job)
            billed=RunReport(run_id=job['billing_run_id'],started_at=job['settled_at'],llm_model=job['model'],llm_mode='batch',
                             record_kind='batch_usage',
                             token_price=job['token_price'],llm_calls=len(job['items']),
                             source_ids=sorted({item['source']['id'] for item in job['items']}))
            for item,outcome in zip(job['items'],job['outcomes'],strict=True):
                if item['ch']!=outcome['ch']:
                    raise ValueError('batch outcome identity mismatch')
                usage=outcome['usage']
                billed.total_input_tokens+=usage['input_tokens']; billed.total_output_tokens+=usage['output_tokens']
                billed.total_thinking_tokens+=usage['thinking_tokens']
                billed.llm_usage_unavailable+=not outcome['usage_available']
                if outcome['error']:
                    billed.llm_failed+=1
                    billed.fail('batch_result',item['source']['id'],item['candidate']['url'],ValueError())
                else:
                    billed.llm_processed+=1
            billed.finish()
            # Stable ID/path ensures polling/recovery never double counts costs.
            self.store.write('runs/'+job['settled_at'][:4]+'/'+job['settled_at'][5:7]+'/'+job['billing_run_id']+'.json',
                             billed.to_bytes(),'application/json')
            for item,outcome in zip(job['items'],job['outcomes'],strict=True):
                if item['status']=='done':
                    continue
                if outcome['error']:
                    report.batch_failed+=1
                    report.fail('batch_result',item['source']['id'],item['candidate']['url'],ValueError())
                else:
                    if item['ch'] not in dedupe.content:
                        self.store.write('state/receipts/'+item['ch']+'.json',
                                         json.dumps(outcome['receipt'],ensure_ascii=False).encode(),'application/json')
                        save_receipt(outcome['receipt'],state,dedupe,report)
                        report.batch_saved+=1
                    done.add(item['candidate']['url'])
                item['status']='done'
                self.persist(name,job)
            job['status']='complete'; self.persist(name,job)
