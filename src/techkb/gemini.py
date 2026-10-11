from dataclasses import dataclass
from copy import deepcopy
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
        # Send the image object at items directly, so the generation constraint
        # does not depend on the API resolving this nested definition reference.
        definitions = schema.pop("$defs")
        schema["properties"]["images"]["items"] = definitions.pop("ImageSelection")
        if definitions:
            schema["$defs"] = definitions
        schema["properties"]["category"]["enum"] = self.categories
        image_ids = list(dict.fromkeys(candidate["image_id"] for candidate in
                                       metadata.get("image_candidates", ())))
        image_schema = schema["properties"]["images"]
        image_schema["maxItems"] = min(image_schema["maxItems"], len(image_ids))
        if image_ids:
            image_schema["items"]["properties"]["image_id"]["enum"] = image_ids
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


def batch_response_schema(schema):
    """Express closed objects using the Developer API's Schema field subset.

    responseSchema has no additionalProperties. Requiring every known property
    and bounding the property count closes the object without that unsupported
    field. In Batch, images is therefore required (use [] for no selection).
    Local ArticleEnrichment validation remains the final acceptance boundary.
    """
    result = deepcopy(schema)
    def close_objects(node):
        if "additionalProperties" in node:
            if node.pop("additionalProperties") is not False:
                raise ValueError("batch schema requires closed objects")
            properties = node["properties"]
            node["required"] = list(properties)
            node["minProperties"] = node["maxProperties"] = len(properties)
        for child in node.get("properties", {}).values():
            close_objects(child)
        if "items" in node:
            close_objects(node["items"])
    close_objects(result)
    return result


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
