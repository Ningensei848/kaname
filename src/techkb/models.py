from pydantic import BaseModel, ConfigDict, Field

class ArticleEnrichment(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    title_ja: str = Field(min_length=1, max_length=300)
    summary_ja: str = Field(min_length=1, max_length=1600)
    key_points: list[str] = Field(max_length=7)
    technical_insights: list[str] = Field(max_length=5)
    category: str
    tags: list[str] = Field(max_length=8)
    related_concepts: list[str] = Field(max_length=8)
    source_language: str = Field(min_length=2, max_length=40)
