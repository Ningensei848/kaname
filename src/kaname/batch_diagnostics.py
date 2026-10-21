"""Structural generation diagnostics shared by standard and Batch; no I/O."""
import json
import re
from google.genai import errors
from pydantic import ValidationError
from .models import ArticleEnrichment


def image_response_shape(response):
    """Describe only JSON types of the known image fields, never input values."""
    try:
        payload = json.loads(response.text or "")
    except (ValueError, TypeError, AttributeError):
        return None
    if not isinstance(payload, dict) or "images" not in payload:
        return None
    def kind(value):
        return {dict: "object", list: "array", str: "string", bool: "boolean",
                int: "number", float: "number", type(None): "null"}[type(value)]
    images = payload["images"]
    shape = {"type": kind(images)}
    if isinstance(images, list):
        shape["count"] = len(images)
        shape["items"] = []
        for item in images[:6]:
            detail = {"type": kind(item)}
            if isinstance(item, dict):
                detail["fields"] = {key: kind(item[key]) for key in ("image_id", "after") if key in item}
                detail["unknown_fields"] = len(item.keys() - {"image_id", "after"})
            shape["items"].append(detail)
        shape["omitted_items"] = max(0, len(images) - 6)
    return shape


def image_selection_diagnostics(response, candidates):
    """Count selection violations without exposing IDs or response values."""
    payload = json.loads(response.text)
    selections = payload.get("images", [])
    known = {candidate["image_id"] for candidate in candidates}
    ids = [selection["image_id"] for selection in selections]
    return dict(candidate_count=len(known), selection_count=len(ids),
                unknown_id_count=sum(image_id not in known for image_id in ids),
                duplicate_id_count=len(ids) - len(set(ids)),
                missing_key_point_count=sum(
                    selection["after"].startswith("key_point_") and
                    int(selection["after"][-1]) > len(payload["key_points"])
                    for selection in selections))


def failure_diagnostics(exc, phase, response, *, image_candidates=None):
    """Only structural error codes; never response text, values or error messages."""
    details = {"phase": phase}
    if isinstance(exc, errors.APIError):
        if type(exc.code) is int and 100 <= exc.code <= 599:
            details["http_status"] = exc.code
        if isinstance(exc.status, str) and exc.status in {"INVALID_ARGUMENT", "UNAUTHENTICATED", "PERMISSION_DENIED", "NOT_FOUND",
                          "RESOURCE_EXHAUSTED", "FAILED_PRECONDITION", "INTERNAL", "UNAVAILABLE"}:
            details["api_status"] = exc.status
        # Never retain API messages: field paths may contain request data.
        message = exc.message if isinstance(exc.message, str) else ""
        names = re.findall(r'Unknown name "([A-Za-z_][A-Za-z0-9_]*)"', message)
        if names:
            details["code"] = "unknown_api_field"
            known = {"additionalProperties", "minProperties", "maxProperties", "minLength", "maxLength",
                     "minItems", "maxItems", "propertyOrdering", "pattern", "default", "title", "type"}
            canonical = [re.sub(r"_([a-z])", lambda match: match[1].upper(), name) for name in names]
            details["schema_fields"] = sorted(set(canonical) & known)
            details["unknown_field_count"] = sum(name not in known for name in canonical)
    codes = {"category outside configured vocabulary": "category_not_allowed",
             "empty or oversized enrichment item": "invalid_enrichment_item",
             "batch item failed or missing": "batch_response_unavailable",
             "invalid_image_selection": "invalid_image_selection",
             "invalid_image_url": "invalid_image_url"}
    if isinstance(exc, ValueError) and exc.args and isinstance(exc.args[0], str):
        code = codes.get(exc.args[0])
        if code:
            details["code"] = code
    if isinstance(exc, ValidationError):
        # Extra-field locations and JSON parser context can contain input data.
        # Retain only known schema field names and Pydantic's structural codes.
        issues = set()
        for error in exc.errors(include_url=False, include_context=False, include_input=False):
            location = error["loc"]
            field = location[0] if location and location[0] in ArticleEnrichment.model_fields else "$"
            code = error["type"]
            if re.fullmatch(r"[a-z0-9_]{1,80}", code):
                issues.add((field, code))
        details["validation_errors"] = [dict(field=field, code=code) for field, code in sorted(issues)]
    if response is not None:
        if phase == 'compose' and image_candidates is not None:
            details['image_selection'] = image_selection_diagnostics(response, image_candidates)
        shape = image_response_shape(response)
        if shape is not None:
            details["images_shape"] = shape
        try:
            details["text_present"] = bool(response.text)
        except Exception:
            details["text_present"] = False
        candidates = getattr(response, "candidates", None) or []
        if candidates:
            reason = getattr(candidates[0], "finish_reason", None)
            reason = getattr(reason, "name", None)
            if isinstance(reason, str) and re.fullmatch(r"[A-Z_]{1,64}", reason):
                details["finish_reason"] = reason
    return details
