"""Optional estimated per-run cap; no network token-counting requests."""
from decimal import Decimal


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
