from dataclasses import dataclass
import json
import time
import httpx
from google import genai
from google.genai import types, errors
from .models import ArticleEnrichment

@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    thinking_tokens: int = 0

class Gemini:
    def __init__(self, config, categories, prompt, api_key, client=None, sleep=time.sleep):
        self.config, self.categories, self.prompt = config, categories, prompt
        self.client = client or genai.Client(api_key=api_key, http_options=types.HttpOptions(
            timeout=60000, retry_options=types.HttpRetryOptions(attempts=1)))
        self.sleep = sleep
        self.attempts = 0
        self.last_usage = Usage()
        self.last_usage_available = False

    def enrich(self, metadata, markdown):
        self.last_usage = Usage()
        self.last_usage_available = False
        content, config = self.request(metadata, markdown)
        for attempt in range(self.config.retries + 1):
            self.attempts += 1
            try:
                response = self.client.models.generate_content(model=self.config.model, contents=content, config=config)
                break
            except (errors.APIError, httpx.TimeoutException, httpx.NetworkError) as exc:
                code = getattr(exc, "code", None)
                retryable = isinstance(exc, (httpx.TimeoutException, httpx.NetworkError)) or code == 429 or (isinstance(code, int) and 500 <= code < 600)
                if not retryable or attempt == self.config.retries:
                    raise
                self.sleep(min(2**attempt, 30))
        self.last_usage, self.last_usage_available = response_usage(response)
        return validate_response(response, self.categories)

    def request(self, metadata, markdown):
        schema = ArticleEnrichment.model_json_schema()
        schema["properties"]["category"]["enum"] = self.categories
        config = types.GenerateContentConfig(
            system_instruction=self.prompt + "\nカテゴリ候補: " + ", ".join(self.categories),
            response_mime_type="application/json", response_json_schema=schema,
            max_output_tokens=self.config.max_output_tokens,
            thinking_config=types.ThinkingConfig(thinking_level=self.config.thinking_level),
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )
        content = json.dumps({"metadata": metadata, "article_markdown": markdown[:self.config.max_input_chars]}, ensure_ascii=False)
        return content, config

    def close(self):
        self.client.close()


def response_usage(response):
    usage = getattr(response, "usage_metadata", None)
    if usage is None:
        return Usage(), False
    counts = [getattr(usage, name, None) for name in
              ("prompt_token_count", "candidates_token_count", "thoughts_token_count")]
    # A missing count is unknown, not a measured zero. The SDK defines total
    # as prompt + candidates + tool-use prompt + thoughts; total equality can
    # establish zero thoughts without inventing a missing billed quantity.
    total = getattr(usage, "total_token_count", None)
    if (counts[2] is None and all(type(v) is int and v >= 0 for v in counts[:2]) and
            type(total) is int and total == sum(counts[:2])):
        counts[2] = 0
    complete = all(type(value) is int and value >= 0 for value in counts)
    known = [value if type(value) is int and value >= 0 else 0 for value in counts]
    return Usage(*known), complete


def validate_response(response, categories):
    result = ArticleEnrichment.model_validate_json(response.text or "")
    if result.category not in categories:
        raise ValueError("category outside configured vocabulary")
    for values in (result.key_points, result.tags, result.related_concepts):
        if any(not value.strip() or len(value) > 2000 for value in values):
            raise ValueError("empty or oversized enrichment item")
    return result
