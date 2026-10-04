from pathlib import Path
from typing import Literal
import os
import yaml
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

class HTTPConfig(StrictModel):
    timeout_seconds: float = Field(default=20, gt=0)
    retries: int = Field(default=3, ge=0, le=8)
    user_agent: str = "TechKnowledgeCollector/0.1"
    max_response_bytes: int = Field(default=10_000_000, gt=0)

class LLMConfig(StrictModel):
    mode: Literal["standard", "batch"] = "standard"
    model: str = "gemini-3.5-flash-lite"
    thinking_level: Literal["minimal", "low", "medium", "high"] = "minimal"
    max_calls_per_run: int = Field(default=30, ge=0)
    max_input_chars: int = Field(default=20000, gt=0)
    max_output_tokens: int = Field(default=2048, gt=0)
    retries: int = Field(default=3, ge=0, le=8)

class StorageConfig(StrictModel):
    bucket: str = ""
    store_raw_html: bool = False

class TokenPrice(StrictModel):
    input_usd_per_million: float = Field(ge=0, allow_inf_nan=False)
    output_usd_per_million: float = Field(ge=0, allow_inf_nan=False)

class CostConfig(StrictModel):
    prices: dict[str, dict[Literal["standard", "batch"], TokenPrice]] = Field(default_factory=lambda: {
        "gemini-3.5-flash-lite": {
            "standard": TokenPrice(input_usd_per_million=0.30, output_usd_per_million=2.50),
            "batch": TokenPrice(input_usd_per_million=0.15, output_usd_per_million=1.25)}})
    daily_budget_usd: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    monthly_budget_usd: float | None = Field(default=None, gt=0, allow_inf_nan=False)

class NotificationConfig(StrictModel):
    consecutive_failures: int = Field(default=3, ge=1)
    github_repository: str = Field(default="", pattern=r"^$|^[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+$")

class AppConfig(StrictModel):
    http: HTTPConfig = Field(default_factory=HTTPConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    costs: CostConfig = Field(default_factory=CostConfig)
    notifications: NotificationConfig = Field(default_factory=NotificationConfig)
    prompt_file: str = "prompts/enrich.txt"
    tracking_parameters: list[str] = Field(default_factory=lambda: ["fbclid", "gclid"])
    categories: list[str] = Field(default_factory=lambda: ["ai-llm", "cloud", "cybersecurity", "software-development", "data", "hardware", "network", "web-platform", "standards-policy", "other"])

    @model_validator(mode="after")
    def categories_valid(self):
        if not self.categories or len(set(self.categories)) != len(self.categories):
            raise ValueError("categories must be nonempty and unique")
        return self

class RelevantFilter(StrictModel):
    include_keywords: list[str] = Field(default_factory=list)
    exclude_keywords: list[str] = Field(default_factory=list)
    include_domains: list[str] = Field(default_factory=list)
    exclude_domains: list[str] = Field(default_factory=list)
    include_categories: list[str] = Field(default_factory=list)
    exclude_categories: list[str] = Field(default_factory=list)

class Source(StrictModel):
    id: str = Field(pattern=r"^[a-zA-Z0-9_-]+$")
    name: str
    enabled: bool = True
    type: Literal["rss", "html"] = "rss"
    feed_url: HttpUrl | None = None
    listing_url: HttpUrl | None = None
    link_selector: str | None = None
    fetcher: Literal["http", "playwright"] = "http"
    render_selector: str | None = None
    resource_domains: list[str] = Field(default_factory=list)
    max_browser_requests: int = Field(default=40, ge=1, le=200)
    extract_main: bool = False
    content_selector: str | None = None
    category: str = ""
    relevant_filter: RelevantFilter = Field(default_factory=RelevantFilter)
    raw_retention_days: int | None = Field(default=None, ge=1)
    base_url: HttpUrl
    request_interval_seconds: float = Field(default=2, ge=0)
    store_raw_html: bool | None = None
    tags: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def discovery_valid(self):
        if self.type == "rss" and not self.feed_url:
            raise ValueError("RSS requires feed_url")
        if self.type == "html" and (not self.listing_url or not self.link_selector):
            raise ValueError("HTML discovery requires listing_url and link_selector")
        return self

class SourceConfig(StrictModel):
    sources: list[Source]

    @model_validator(mode="after")
    def unique_ids(self):
        if len({s.id for s in self.sources}) != len(self.sources):
            raise ValueError("source ids must be unique")
        return self

def load_config(app_path: str, sources_path: str):
    app = AppConfig.model_validate(yaml.safe_load(Path(app_path).read_text()))
    sources = SourceConfig.model_validate(yaml.safe_load(Path(sources_path).read_text()))
    app.storage.bucket = os.environ.get("GCS_BUCKET") or app.storage.bucket
    return app, sources.sources
