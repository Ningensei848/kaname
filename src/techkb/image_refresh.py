"""Reviewed, targeted image additions without re-enrichment or index changes."""
import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
import yaml

from .composer import image_block, place_images
from .converter import Converter
from .extraction import extract_main
from .html_cleaner import canonical_url, clean_html
from .images import article_images, image_url
from .models import ImageSelection
from .normalize import normalize_markdown, normalize_url
from .publication.common import json_bytes, object_path, sha256
from .publication.note import instant, note_frontmatter, validate_note
from .publication.snapshot import CheckedReads, index_catalog
from .state import INDEX_COLUMNS, decode_tsv


class RepairImage(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    url: str
    after: str

    @field_validator("url")
    @classmethod
    def valid_url(cls, value):
        return image_url(value)

    @field_validator("after")
    @classmethod
    def valid_placement(cls, value):
        return ImageSelection(image_id="img-1", after=value).after


class ImageRepairPlan(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    schema_version: int = Field(ge=1, le=1)
    note_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    expected_note_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_markdown_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    images: list[RepairImage] = Field(min_length=1, max_length=6)

    @model_validator(mode="after")
    def unique_urls(self):
        if len({image.url for image in self.images}) != len(self.images):
            raise ValueError("duplicate_image")
        return self


def load_plan(path):
    data = Path(path).read_bytes()
    if len(data) > 20_000:
        raise ValueError("oversized_image_plan")
    return ImageRepairPlan.model_validate_json(data)


def add_images(data, images):
    text, match, meta = note_frontmatter(data)
    if "article_images" in meta:
        raise ValueError("images_already_present")
    addition = yaml.safe_dump({"article_images": images}, allow_unicode=True, sort_keys=False)
    front = text[:match.end() - 4] + addition + "---\n"
    return (front + place_images(text[match.end():], images)).encode()


def original_bytes(data):
    """Undo only this operation's appended field and registered image blocks."""
    text, match, meta = note_frontmatter(data)
    images = meta.get("article_images")
    if not images:
        raise ValueError("missing_repaired_images")
    addition = yaml.safe_dump({"article_images": images}, allow_unicode=True, sort_keys=False)
    front = text[:match.end() - 4]
    if not front.endswith(addition):
        raise ValueError("changed_repaired_frontmatter")
    body = text[match.end():]
    for image in images:
        block = image_block(image)
        if body.count(block) != 1:
            raise ValueError("changed_repaired_images")
        body = body.replace(block, "", 1)
    return (front[:-len(addition)] + "---\n" + body).encode()


def repair_images(store, fetcher, sources, app, plan, *, apply=False, output=None):
    result = dict(status="failed", apply=apply, note_id=plan.note_id,
                  planned=0, updated=0, unchanged=0)
    stage = "validate"
    try:
        reader = CheckedReads(store)
        indexes = index_catalog(store)
        candidates = []
        for name in indexes:
            for row in decode_tsv(reader.read(name), INDEX_COLUMNS[:12]):
                if row["status"] != "success":
                    continue
                identity = [row["source_id"], normalize_url(row["canonical_url"], app.tracking_parameters)]
                note_id = sha256(json.dumps(identity, ensure_ascii=False, separators=(",", ":")).encode())
                if note_id == plan.note_id:
                    candidates.append(row)
        if not candidates:
            raise ValueError("unknown_note")
        row = max(candidates, key=lambda r: (instant(r["processed_at"]), r["content_sha256"]))
        note_name = row["note_object"]
        object_path(note_name, "notes/", ".md")
        object_path("state/receipts/" + row["content_sha256"] + ".json", "state/receipts/", ".json")
        receipt_name = f"state/receipts/{row['content_sha256']}.json"
        note_data = reader.read(note_name)
        receipt = json.loads(reader.read(receipt_name))
        if (not isinstance(receipt, dict) or not isinstance(receipt.get("row"), dict) or
                not isinstance(receipt.get("note"), str) or
                any(str(receipt["row"].get(k, "")) != v for k, v in row.items())):
            raise ValueError("receipt_mismatch")
        plan_hash = sha256(json_bytes(plan.model_dump()))
        proof = receipt.get("image_repair")
        resume = proof is not None
        if resume:
            refreshed = receipt["note"].encode()
            if (not isinstance(proof, dict) or
                    proof != {"plan_sha256": plan_hash,
                              "previous_note_sha256": plan.expected_note_sha256,
                              "note_sha256": sha256(refreshed)}):
                raise ValueError("different_image_repair")
            validate_note(refreshed, row, app.tracking_parameters, app.categories)
            original = original_bytes(refreshed)
            if sha256(original) != plan.expected_note_sha256 or note_data not in (original, refreshed):
                raise ValueError("changed_note")
        else:
            if sha256(note_data) != plan.expected_note_sha256 or receipt["note"].encode() != note_data:
                raise ValueError("changed_note")
            validate_note(note_data, row, app.tracking_parameters, app.categories)
            source = next(source for source in sources if source.id == row["source_id"])
            if not source.enabled:
                raise ValueError("disabled_source")
            stage = "fetch"
            fetched = fetcher.page(row["source_url"], source)
            if canonical_url(fetched.content, fetched.url, app.tracking_parameters) != row["canonical_url"]:
                raise ValueError("changed_canonical")
            body = (extract_main(fetched.content, source.content_selector)
                    if source.extract_main or source.content_selector else fetched.content)
            markdown = normalize_markdown(Converter().convert(clean_html(body)))
            if sha256(markdown.encode()) != plan.source_markdown_sha256:
                raise ValueError("changed_source")
            available = {image["url"]: image for image in article_images(
                body, fetched.url, markdown[:app.llm.max_input_chars])}
            images = []
            for selected in plan.images:
                if selected.url not in available:
                    raise ValueError("unavailable_image")
                image = available[selected.url]
                images.append(dict(image_id=image["image_id"], url=image["url"],
                                   alt=image["alt"], after=selected.after))
            stage = "compose"
            refreshed = add_images(note_data, images)
            validate_note(refreshed, row, app.tracking_parameters, app.categories)
            if original_bytes(refreshed) != note_data:
                raise ValueError("changed_summary")
            receipt["note"] = refreshed.decode()
            receipt["image_repair"] = dict(plan_sha256=plan_hash,
                                           previous_note_sha256=plan.expected_note_sha256,
                                           note_sha256=sha256(refreshed))
        result.update(before_sha256=plan.expected_note_sha256, after_sha256=sha256(refreshed),
                      images=len(note_frontmatter(refreshed)[2]["article_images"]))
        result["planned"] = int(note_data != refreshed)
        result["unchanged"] = int(note_data == refreshed)
        stage = "recheck"
        reader.verify(indexes)
        if output is not None:
            stage = "preview"
            destination = Path(output)
            destination.mkdir(parents=True, exist_ok=False)
            (destination / f"{plan.note_id}.md").write_bytes(refreshed)
        if apply and note_data != refreshed:
            stage = "receipt_save"
            if not resume:
                # The durable receipt is the exact recipe for resuming this pair.
                store.write(receipt_name, json_bytes(receipt), "application/json")
            stage = "note_save"
            store.write(note_name, refreshed, "text/markdown; charset=utf-8")
            result["updated"] = 1
        result["status"] = "success"
    except Exception as exc:
        result.update(stage=stage, error_type=type(exc).__name__)
    return result
