"""Read-only run history, cost estimates, failure plans and explicit Issue publishing."""
from collections import defaultdict
from datetime import date, datetime, timezone
from decimal import Decimal
import hashlib
import json
import re
import httpx
from .config import TokenPrice


def history(store):
    reports = {}
    for name in store.list('runs/'):
        if not name.endswith('.json'):
            continue
        raw = store.read(name)
        if raw is None:
            raise ValueError('run disappeared')
        report = json.loads(raw)
        run_id = report['run_id']
        if not re.fullmatch(r'\d{8}T\d{6}Z-[0-9a-f]{8}',run_id):
            raise ValueError('invalid run identifier')
        datetime.fromisoformat(report['started_at'])
        if run_id in reports and reports[run_id] != report:
            raise ValueError('conflicting duplicate report')
        reports[run_id]=report
    return sorted(reports.values(), key=lambda r: (r['started_at'],r['run_id']))


def cost_report(store, app, as_of=None):
    day = date.fromisoformat(as_of) if as_of else datetime.now(timezone.utc).date()
    daily, monthly, uncertain, legacy = defaultdict(Decimal), defaultdict(Decimal), 0, 0
    reports = history(store)
    for run in reports:
        if run.get('dry_run'):
            continue
        stamp = datetime.fromisoformat(run['started_at']).astimezone(timezone.utc).date().isoformat()
        if stamp > day.isoformat():
            continue
        model = run.get('llm_model') or app.llm.model
        if not run.get('llm_model'):
            legacy += 1
        if 'token_price' in run:
            raw_price = run['token_price']
            price = TokenPrice.model_validate(raw_price) if raw_price is not None else None
        else:
            price = app.costs.prices.get(model,{}).get(run.get('llm_mode','standard'))
        counts=[]
        for key in ('total_input_tokens','total_output_tokens','total_thinking_tokens','llm_usage_unavailable'):
            count=run[key]
            if type(count) is not int or count<0:
                raise ValueError('invalid token count')
            counts.append(count)
        inp,out,thinking,unknown=counts
        if unknown or (price is None and (inp or out or thinking or run.get('llm_calls') or run.get('batch_submitted'))):
            uncertain += 1
        value = ((Decimal(inp)*Decimal(str(price.input_usd_per_million)) +
                  Decimal(out+thinking)*Decimal(str(price.output_usd_per_million))) / Decimal(1_000_000)
                 if price else Decimal(0))
        daily[stamp] += value
        monthly[stamp[:7]] += value
    daily_value=daily[day.isoformat()]; month_value=monthly[day.isoformat()[:7]]
    alerts=[]
    for period,value,limit in [('daily',daily_value,app.costs.daily_budget_usd),('monthly',month_value,app.costs.monthly_budget_usd)]:
        if limit is not None and value >= Decimal(str(limit)):
            alerts.append(dict(kind='budget',key=period+'-'+(day.isoformat() if period=='daily' else day.isoformat()[:7]),
                               period=period,estimated_usd=str(value),budget_usd=str(limit)))
    known = {r['run_id'] for r in reports}
    pending_batch_items = 0
    for name in store.list('state/batches/'):
        job = json.loads(store.read(name))
        if job.get('billing_run_id') not in known:
            pending_batch_items += len(job['items'])
    return dict(status='partial' if uncertain or pending_batch_items else 'success',as_of=day.isoformat(),timezone='UTC',
                daily_usd={k:str(v) for k,v in sorted(daily.items())}, monthly_usd={k:str(v) for k,v in sorted(monthly.items())},
                uncertain_runs=uncertain, pending_batch_items=pending_batch_items, legacy_model_assumptions=legacy, alerts=alerts)


def notification_plan(store,app,source_ids):
    streak, first = defaultdict(int), {}
    for run in history(store):
        if run.get('dry_run') or run.get('record_kind') == 'batch_usage':
            continue
        failed={f['source_id'] or 'collector' for f in run['failures']}
        covered=set(run.get('source_ids',source_ids)) | {'collector'} | failed
        for source_id in covered:
            if source_id in failed:
                if not streak[source_id]:
                    first[source_id]=run['run_id']
                streak[source_id]+=1
            elif run['status']=='success' or (source_id!='collector' and 'collector' not in failed):
                streak[source_id]=0
    events=[dict(kind='failure',key='failure-'+sid+'-'+first[sid],source_id=sid,consecutive_failures=count)
            for sid,count in sorted(streak.items()) if count>=app.notifications.consecutive_failures]
    return events + cost_report(store,app)['alerts']


def publish_issues(events,repository,token,client=None):
    if not re.fullmatch(r'[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+', repository) or not token:
        raise ValueError('notification repository and GITHUB_TOKEN required')
    own=client is None
    client=client or httpx.Client(timeout=20,trust_env=False,follow_redirects=False)
    headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json',
             'X-GitHub-Api-Version':'2022-11-28'}
    base='https://api.github.com/repos/'+repository+'/issues'
    try:
        existing=[]
        # Include closed issues so an acknowledged incident does not reopen on every run.
        for page in range(1,101):
            response=client.get(base,headers=headers,params={'state':'all','per_page':100,'page':page})
            response.raise_for_status(); items=response.json(); existing.extend(items)
            if len(items)<100:
                break
        else:
            raise ValueError('Issue pagination limit; refusing duplicate notifications')
        created=0
        for event in events:
            marker='<!-- techkb-alert:'+hashlib.sha256(event['key'].encode()).hexdigest()+' -->'
            if any(marker in (item.get('body') or '') for item in existing):
                continue
            title=('TechKB: '+event['source_id']+' の連続失敗' if event['kind']=='failure' else 'TechKB: '+event['period']+' 予算到達')
            body=marker+'\n\n'+json.dumps(event,ensure_ascii=False,indent=2)+'\n\nREADMEの復旧・費用確認手順を参照してください。'
            response=client.post(base,headers=headers,json={'title':title,'body':body})
            response.raise_for_status(); existing.append(response.json()); created+=1
        return dict(status='success',created=created,existing=len(events)-created)
    finally:
        if own:
            client.close()
