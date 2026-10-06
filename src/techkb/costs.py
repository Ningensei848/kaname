"""Read-only cost inputs and pure usage reconciliation and price calculation."""
from collections import defaultdict
from datetime import date, datetime, timezone
from decimal import Decimal
import json
import re

from .config import TokenPrice
from .run_history import history
from .usage import FIELDS


def standard_usage(store):
    """Read checkpoints lazily, preserving their original validation order."""
    for name in store.list('state/standard-usage/'):
        yield name, json.loads(store.read(name))


def merge_standard_usage(reports, checkpoints):
    """Use the original run identity and let final reports cover checkpoints."""
    billing = {run['run_id']: run for run in reports}
    incomplete_standard_runs = 0
    for name, record in checkpoints:
        if (set(record) != {*FIELDS, 'schema_version', 'pending'} or type(record['schema_version']) is not int or record['schema_version'] != 1 or
                type(record['pending']) is not bool or record['llm_mode'] != 'standard' or
                not re.fullmatch(r'\d{8}T\d{6}Z-[0-9a-f]{8}', record['run_id']) or
                name != 'state/standard-usage/' + record['run_id'] + '.json'):
            raise ValueError('invalid standard usage checkpoint')
        for key in ('llm_calls', 'llm_http_attempts', 'llm_usage_unavailable',
                    'total_input_tokens', 'total_output_tokens', 'total_thinking_tokens'):
            if type(record[key]) is not int or record[key] < 0:
                raise ValueError('invalid standard usage count')
        existing = billing.get(record['run_id'])
        if existing and any(existing.get(k) != record[k] for k in ('started_at', 'llm_model', 'llm_mode', 'token_price')):
            raise ValueError('conflicting usage identity')
        if existing:
            if not record['pending'] and any(existing[k] != record[k] for k in
                    ('total_input_tokens', 'total_output_tokens', 'total_thinking_tokens', 'llm_calls')):
                raise ValueError('conflicting usage totals')
            continue  # A final report also covers a failed checkpoint write.
        if record['pending']:
            record = dict(record)
            record['llm_usage_unavailable'] += 1
            incomplete_standard_runs += 1
        # Original run ID is the common accounting identity, not an extra bill.
        billing[record['run_id']] = record
    return billing, incomplete_standard_runs


def estimate_costs(billing, app, day):
    """Calculate UTC totals and alerts using each run's recorded price."""
    daily, monthly, uncertain, legacy = defaultdict(Decimal), defaultdict(Decimal), 0, 0
    for run in billing.values():
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
    return daily, monthly, uncertain, legacy, alerts


def pending_batch_items(store, reports):
    known = {r['run_id'] for r in reports}
    pending_batch_items = 0
    for name in store.list('state/batches/'):
        job = json.loads(store.read(name))
        if not job.get('submission_rejected') and job.get('billing_run_id') not in known:
            pending_batch_items += len(job['items'])
    return pending_batch_items


def cost_report(store, app, as_of=None):
    day = date.fromisoformat(as_of) if as_of else datetime.now(timezone.utc).date()
    reports = history(store)
    billing, incomplete_standard_runs = merge_standard_usage(reports, standard_usage(store))
    daily, monthly, uncertain, legacy, alerts = estimate_costs(billing, app, day)
    pending_batch_items_count = pending_batch_items(store, reports)
    return dict(status='partial' if uncertain or pending_batch_items_count else 'success',as_of=day.isoformat(),timezone='UTC',
                daily_usd={k:str(v) for k,v in sorted(daily.items())}, monthly_usd={k:str(v) for k,v in sorted(monthly.items())},
                uncertain_runs=uncertain, incomplete_standard_runs=incomplete_standard_runs, pending_batch_items=pending_batch_items_count, legacy_model_assumptions=legacy, alerts=alerts)
