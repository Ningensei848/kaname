"""Durable asynchronous inline batches. No article bodies in the local ledger."""
from dataclasses import asdict
import json
import hashlib
import re
from types import SimpleNamespace
from google.genai import types, errors
from pydantic import ValidationError
from .composer import compose, word_count
from ._receipts import build_receipt
from .gemini import response_usage, validate_response
from .pending import Candidate
from .models import ArticleEnrichment
from .reporting import RunReport, now


def failure_diagnostics(exc, phase, response):
    """Only structural error codes; never response text, values or error messages."""
    details = {"phase": phase}
    codes = {"category outside configured vocabulary": "category_not_allowed",
             "empty or oversized enrichment item": "invalid_enrichment_item",
             "batch item failed or missing": "batch_response_unavailable"}
    if isinstance(exc, ValueError) and exc.args and isinstance(exc.args[0], str):
        code = codes.get(exc.args[0])
        if code:
            details["code"] = code
    if isinstance(exc, ValidationError):
        # Extra-field locations and JSON parser context can contain input data.
        # Retain only known schema field names and Pydantic's structural codes.
        issues = set()
        for error in exc.errors(include_url=False, include_context=False, include_input=False):
            location = error["loc"]
            field = location[0] if location and location[0] in ArticleEnrichment.model_fields else "$"
            code = error["type"]
            if re.fullmatch(r"[a-z0-9_]{1,80}", code):
                issues.add((field, code))
        details["validation_errors"] = [dict(field=field, code=code) for field, code in sorted(issues)]
    if response is not None:
        try:
            details["text_present"] = bool(response.text)
        except Exception:
            details["text_present"] = False
        candidates = getattr(response, "candidates", None) or []
        if candidates:
            reason = getattr(candidates[0], "finish_reason", None)
            reason = getattr(reason, "name", None)
            if isinstance(reason, str) and re.fullmatch(r"[A-Z_]{1,64}", reason):
                details["finish_reason"] = reason
    return details


def inspect_batch(store, batch_id, client=None):
    """Read a completed or active ledger; optionally GET its existing API result."""
    if not re.fullmatch(r'\d{8}T\d{6}Z-[0-9a-f]{8}', batch_id or ''):
        raise ValueError('invalid batch ID')
    data = store.read('state/batches/' + batch_id + '.json')
    if data is None:
        raise ValueError('batch ledger missing')
    job = json.loads(data)
    if job['id'] != batch_id:
        raise ValueError('batch ledger identity mismatch')
    # Keep article metadata, Note text, hashes and API resource names private.
    result = dict(status='success', batch_id=batch_id, ledger_status=job['status'],
                  items=len(job['items']), remote_inspected=client is not None,
                  recorded_errors=[outcome['error'] for outcome in job.get('outcomes', [])])
    if client is None:
        return result
    if not job.get('name'):
        raise ValueError('batch has no bound job to inspect')
    remote = client.batches.get(name=job['name'])
    result['remote_state'] = remote.state.name if remote.state else ''
    responses = (remote.dest.inlined_responses if remote.dest else None) or []
    expected = {item['ch'] for item in job['items']}
    by_key = {}
    for response in responses:
        key = (response.metadata or {}).get('key')
        if key not in expected or key in by_key:
            raise ValueError('unknown or duplicate batch response key')
        by_key[key] = response
    result['returned_items'] = len(responses)
    result['remote_outcomes'] = []
    if result['remote_state'] not in {'JOB_STATE_SUCCEEDED', 'JOB_STATE_FAILED', 'JOB_STATE_CANCELLED', 'JOB_STATE_EXPIRED'}:
        return result
    for number, item in enumerate(job['items'], 1):
        response = by_key.get(item['ch'])
        content = response.response if response and not response.error else None
        outcome = dict(item=number, error_type=None)
        try:
            if content is None:
                raise ValueError('batch item failed or missing')
            validate_response(content, job['categories'])
        except Exception as exc:
            outcome['error_type'] = type(exc).__name__
            outcome['diagnostics'] = failure_diagnostics(exc, 'validation' if content is not None else 'response', content)
        result['remote_outcomes'].append(outcome)
    return result


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
                    phase = 'response'
                    try:
                        if response is None:
                            raise ValueError('batch item failed or missing')
                        phase = 'validation'
                        enrichment=validate_response(response,job['categories'])
                        phase = 'compose'
                        candidate=Candidate(**item['candidate']); source=SimpleNamespace(**item['source'])
                        fetched_at=now()
                        outcome['receipt']=build_receipt(candidate,source,enrichment,'',item['canon'],fetched_at,
                                                         item['rh'],item['ch'],job['model'],item['truncated'],
                                                         item['authors'],usage,input_char_limit=job['input_char_limit'],
                                                         source_word_count=item['word_count'],compose_note=compose)
                    except Exception as exc:
                        outcome['error']=type(exc).__name__
                        outcome['diagnostics']=failure_diagnostics(exc, phase, response)
                    outcomes.append(outcome)
                job['outcomes']=outcomes; job['settled_at']=now()
                job['billing_run_id']=job['settled_at'][:19].replace('-','').replace(':','')+'Z-'+hashlib.sha256(('batch:'+job['id']).encode()).hexdigest()[:8]
                for outcome in outcomes:
                    if outcome['receipt']:
                        outcome['receipt']['usage_run_id'] = job['billing_run_id']
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
                    billed.fail_recorded('batch_result',item['source']['id'],item['candidate']['url'],
                                         outcome['error'],outcome.get('diagnostics'))
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
                    report.fail_recorded('batch_result',item['source']['id'],item['candidate']['url'],
                                         outcome['error'],outcome.get('diagnostics'))
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
