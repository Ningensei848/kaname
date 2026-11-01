from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

class ImageSelection(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    image_id: str = Field(pattern=r"^img-[1-9][0-9]*$")
    after: Literal["summary", "key_point_1", "key_point_2", "key_point_3", "key_point_4", "key_point_5", "positioning"]

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
    images: list[ImageSelection] = Field(default_factory=list, max_length=6)
