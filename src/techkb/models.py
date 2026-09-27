from pydantic import BaseModel, ConfigDict, Field

class ArticleEnrichment(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    title_ja: str = Field(min_length=1, max_length=300)
    summary_ja: str = Field(min_length=1, max_length=1600)
    key_points: list[str] = Field(min_length=2, max_length=5)
    positioning_ja: str = Field(min_length=1, max_length=1200)
    category: str
    tags: list[str] = Field(max_length=8)
    related_concepts: list[str] = Field(min_length=2, max_length=6)
    source_language: str = Field(min_length=2, max_length=40)
