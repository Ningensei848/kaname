import json
from decimal import Decimal
from types import SimpleNamespace
import httpx
import pytest
from techkb.operations import cost_report,notification_plan,publish_issues
from techkb.lifecycle import configure_lifecycle


def report(h,index,day='2026-10-01',failed=False,**extra):
    data=dict(run_id=f'{day.replace("-","")}T000000Z-{index:08x}',started_at=day+'T00:00:00+00:00',
              status='failed' if failed else 'success',dry_run=False,llm_model=h.app.llm.model,
              source_ids=[h.source.id],total_input_tokens=1000000,total_output_tokens=1000000,
              total_thinking_tokens=1000000,llm_usage_unavailable=0,
              failures=[dict(source_id=h.source.id)] if failed else [])|extra
    h.store.data['runs/'+data['run_id']+'.json']=json.dumps(data).encode()
    return data


def test_costs_usage_thinking_price_snapshot_and_budget(harness):
    h=harness
    one=report(h,1,token_price={'input_usd_per_million':0.3,'output_usd_per_million':2.5})
    h.app.costs.prices[h.app.llm.model]['standard'].input_usd_per_million=999
    # Historical rate is fixed; duplicate copy does not double bill.
    h.store.data['runs/copy.json']=json.dumps(one).encode()
    report(h,2,llm_mode='batch'); report(h,3,day='2026-09-30')
    h.app.costs.daily_budget_usd=5
    result=cost_report(h.store,h.app,'2026-10-01')
    assert Decimal(result['daily_usd']['2026-10-01'])==Decimal('7.95')
    assert Decimal(result['monthly_usd']['2026-10'])==Decimal('7.95')
    assert result['alerts'][0]['kind']=='budget'


def test_unknown_usage_is_partial_and_invalid_report_is_rejected(harness):
    h=harness
    report(h,1,llm_usage_unavailable=1)
    assert cost_report(h.store,h.app,'2026-10-01')['status']=='partial'
    report(h,2,total_input_tokens=-1)
    with pytest.raises(ValueError): cost_report(h.store,h.app)


def test_failure_streak_recovery_and_incident_key(harness):
    h=harness
    for i in range(3): report(h,i,failed=True)
    first=notification_plan(h.store,h.app,[h.source.id])
    assert first[0]['consecutive_failures']==3
    report(h,3,failed=True)
    assert notification_plan(h.store,h.app,[h.source.id])[0]['key']==first[0]['key']
    report(h,4)
    assert notification_plan(h.store,h.app,[h.source.id])==[]


def test_issue_notifications_deduplicate_closed_incident(harness):
    issues=[]; posts=[]
    def handler(req):
        if req.method=='GET': return httpx.Response(200,json=issues)
        body=json.loads(req.content); posts.append(body)
        issues.append(body|{'state':'closed'})
        return httpx.Response(201,json=issues[-1])
    client=httpx.Client(transport=httpx.MockTransport(handler))
    events=[dict(kind='failure',key='stable',source_id='example',consecutive_failures=3)]
    assert publish_issues(events,'owner/repo','secret',client)['created']==1
    assert publish_issues(events,'owner/repo','secret',client)['created']==0
    assert len(posts)==1 and 'secret' not in posts[0]['body']


def test_raw_lifecycle_preserves_other_rules_and_guards_generation(harness):
    old={'action':{'type':'Delete'},'condition':{'age':90,'matchesPrefix':['other/']}}
    class Bucket:
        lifecycle_rules=[old]
        metageneration=7
        calls=[]
        def patch(self,**kwargs): self.calls.append(kwargs)
    b=Bucket(); store=SimpleNamespace(bucket=b); harness.source.raw_retention_days=14
    plan=configure_lifecycle(store,[harness.source])
    assert not plan['applied'] and b.lifecycle_rules==[old]
    assert plan['rules'][1]['condition']==dict(age=14,matchesPrefix=['raw/example/'])
    assert configure_lifecycle(store,[harness.source],apply=True)['applied']
    assert b.calls==[dict(if_metageneration_match=7)]
    assert not configure_lifecycle(store,[harness.source],apply=True)['changed']
