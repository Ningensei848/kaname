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
    model: str = "gemini-3.5-flash-lite"
    thinking_level: Literal["minimal", "low", "medium", "high"] = "minimal"
    max_calls_per_run: int = Field(default=30, ge=0)
    max_input_chars: int = Field(default=20000, gt=0)
    max_output_tokens: int = Field(default=2048, gt=0)
    retries: int = Field(default=3, ge=0, le=8)

class StorageConfig(StrictModel):
    bucket: str = ""
    store_raw_html: bool = False

class AppConfig(StrictModel):
    http: HTTPConfig = Field(default_factory=HTTPConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    prompt_file: str = "prompts/enrich.txt"
    tracking_parameters: list[str] = Field(default_factory=lambda: ["fbclid", "gclid"])
    categories: list[str] = Field(default_factory=lambda: ["ai-llm", "cloud", "cybersecurity", "software-development", "data", "hardware", "network", "web-platform", "standards-policy", "other"])

    @model_validator(mode="after")
    def categories_valid(self):
        if not self.categories or len(set(self.categories)) != len(self.categories):
            raise ValueError("categories must be nonempty and unique")
        return self

class Source(StrictModel):
    id: str = Field(pattern=r"^[a-zA-Z0-9_-]+$")
    name: str
    enabled: bool = True
    type: Literal["rss"] = "rss"
    feed_url: HttpUrl
    base_url: HttpUrl
    request_interval_seconds: float = Field(default=2, ge=0)
    store_full_text: bool = True
    store_raw_html: bool | None = None
    tags: list[str] = Field(default_factory=list)

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
