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
        usage = response.usage_metadata
        if usage:
            self.last_usage_available = True
            self.last_usage = Usage(usage.prompt_token_count or 0, usage.candidates_token_count or 0, usage.thoughts_token_count or 0)
        # Validation is intentionally outside the retry loop.
        result = ArticleEnrichment.model_validate_json(response.text or "")
        if result.category not in self.categories:
            raise ValueError("category outside configured vocabulary")
        for values in (result.key_points, result.technical_insights, result.tags, result.related_concepts):
            if any(not value.strip() or len(value) > 2000 for value in values):
                raise ValueError("empty or oversized enrichment item")
        return result

    def close(self):
        self.client.close()
