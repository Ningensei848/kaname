"""Pure failure plans and explicit, deduplicated GitHub Issue publishing."""
from collections import defaultdict
import hashlib
import json
import re

import httpx

from .costs import cost_report
from .run_history import history


def failure_events(reports,notifications,source_ids):
    streak, first = defaultdict(int), {}
    for run in reports:
        if run.get('dry_run') or run.get('record_kind') == 'batch_usage':
            continue
        failed={f['source_id'] or 'collector' for f in run['failures']}
        # Legacy reports cannot establish completion of enabled sources.
        completed = set(run.get('source_completed_ids', []))
        covered = completed | {'collector'} | failed
        for source_id in covered:
            if source_id in failed:
                if not streak[source_id]:
                    first[source_id]=run['run_id']
                streak[source_id]+=1
            elif (source_id == 'collector' and run['status'] == 'success') or source_id in completed:
                streak[source_id]=0
    events=[dict(kind='failure',key='failure-'+sid+'-'+first[sid],source_id=sid,consecutive_failures=count)
            for sid,count in sorted(streak.items()) if count>=notifications.consecutive_failures and sid in {*source_ids, 'collector'}]
    return events


def notification_plan(store,app,source_ids):
    events = failure_events(history(store), app.notifications, source_ids)
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
            if event['kind'] == 'publication':
                title = 'TechKB: 収集・公開workflowの失敗'
            else:
                title=('TechKB: '+event['source_id']+' の連続失敗' if event['kind']=='failure' else 'TechKB: '+event['period']+' 予算到達')
            body=marker+'\n\n'+json.dumps(event,ensure_ascii=False,indent=2)+'\n\nREADMEの復旧・費用確認手順を参照してください。'
            response=client.post(base,headers=headers,json={'title':title,'body':body})
            response.raise_for_status(); existing.append(response.json()); created+=1
        return dict(status='success',created=created,existing=len(events)-created)
    finally:
        if own:
            client.close()
