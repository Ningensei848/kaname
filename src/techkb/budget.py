"""Optional estimated run/UTC period caps; no token-counting API requests."""
from decimal import Decimal
from datetime import datetime, timezone
import os


def aggregate_limits_enabled(app):
    return any(value is not None for value in
               (app.costs.generation_daily_limit_usd, app.costs.generation_monthly_limit_usd))


def validate_generation_mode(app):
    if aggregate_limits_enabled(app) and app.llm.mode != 'standard':
        raise ValueError('aggregate generation limits require standard mode')


def generation_allowance(store, app, started_at):
    """Read-only UTC period allowance; uncertain accounting cannot permit work."""
    validate_generation_mode(app)
    if not aggregate_limits_enabled(app):
        return None
    if hasattr(store, 'read_snapshot'):
        with store.read_snapshot(('runs/', 'state/standard-usage/', 'state/batches/'),
                                 cache_dir=os.environ.get('TECHKB_READ_CACHE')) as snapshot:
            return _period_allowance(snapshot, app, started_at)
    return _period_allowance(store, app, started_at)


def _period_allowance(store, app, started_at):
    from .costs import merge_standard_usage, standard_usage, estimate_costs, pending_batch_items
    from .run_history import history
    def utc_day(stamp):
        value = datetime.fromisoformat(stamp)
        if value.tzinfo is None:
            raise ValueError('generation budget requires timezone-aware usage')
        return value.astimezone(timezone.utc).date()
    day = utc_day(started_at)
    start = day.replace(day=1) if app.costs.generation_monthly_limit_usd is not None else day
    reports = history(store)
    billing, _ = merge_standard_usage(reports, standard_usage(store))
    active = {key: run for key, run in billing.items()
              if start <= utc_day(run['started_at']) <= day}
    daily, monthly, uncertain, legacy, _ = estimate_costs(active, app, day)
    original_price_missing = any(not run.get('dry_run') and
        (run.get('llm_calls') or run.get('batch_submitted')) and
        ('token_price' not in run or run['token_price'] is None) for run in active.values())
    pending = pending_batch_items(store, reports)
    periods = {}
    for period, key, spent, limit in (
        ('daily', day.isoformat(), daily[day.isoformat()], app.costs.generation_daily_limit_usd),
        ('monthly', day.isoformat()[:7], monthly[day.isoformat()[:7]], app.costs.generation_monthly_limit_usd),
    ):
        if limit is not None:
            cap = Decimal(str(limit))
            periods[period] = dict(key=key, spent_usd=str(spent), limit_usd=str(cap),
                                   remaining_usd=str(max(Decimal(0), cap - spent)))
    blocked = bool(uncertain or legacy or original_price_missing or pending)
    remaining = min(Decimal(value['remaining_usd']) for value in periods.values())
    return dict(status='blocked' if blocked else 'ready', timezone='UTC', periods=periods,
                remaining_usd=str(remaining),
                reason='aggregate_usage_uncertain' if blocked else 'aggregate_limit_reached' if not remaining else None)


def validate_budget(app, limit):
    limit = Decimal(limit)
    if not limit.is_finite() or limit <= 0 or app.llm.mode != "standard":
        raise ValueError("cost cap requires positive finite USD and standard mode")
    if app.llm.model not in app.costs.prices or "standard" not in app.costs.prices[app.llm.model]:
        raise ValueError("cost cap requires configured token prices")
    return limit


def token_cost(price, inputs, outputs):
    return (Decimal(str(price.input_usd_per_million)) * inputs +
            Decimal(str(price.output_usd_per_million)) * outputs) / Decimal(1000000)


def measured_cost(report, price):
    return token_cost(price, report.total_input_tokens,
                      report.total_output_tokens + report.total_thinking_tokens)


def request_reserve(gemini, metadata, markdown, price):
    content, config = gemini.request(metadata, markdown)
    # UTF-8 bytes conservatively estimate text tokens. Include system/schema,
    # model and 1024 framing tokens. Double output for thinking, and reserve
    # every configured HTTP attempt, even though failed-attempt usage is unknown.
    inputs = len((content + config.model_dump_json(exclude_none=True) +
                  gemini.config.model).encode("utf-8")) + 1024
    return token_cost(price, inputs, 2 * gemini.config.max_output_tokens) * (gemini.config.retries + 1)
