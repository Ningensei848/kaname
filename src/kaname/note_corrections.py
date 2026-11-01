"""Hash-pinned source-reviewed text edits; no HTTP, LLM or billing mutation."""
from datetime import date
import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator
import yaml

from .publication.common import json_bytes, object_path, sha256
from .publication.identity import note_identity
from .publication.note import correction_trailer, instant, note_frontmatter, validate_note
from .publication.snapshot import CheckedReads, index_catalog
from .state import INDEX_COLUMNS, decode_tsv


class TextEdit(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    old: str = Field(min_length=1, max_length=2000)
    new: str = Field(min_length=1, max_length=2000)
    expected_occurrences: int = Field(ge=1, le=20)


class NoteCorrectionPlan(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    schema_version: int = Field(ge=1, le=1)
    note_id: str = Field(pattern=r'^[0-9a-f]{64}$')
    expected_note_sha256: str = Field(pattern=r'^[0-9a-f]{64}$')
    expected_text_sha256: str = Field(pattern=r'^[0-9a-f]{64}$')
    source: str = Field(min_length=1, max_length=2000)
    checked_at: str
    source_published: str | None = None
    edits: list[TextEdit] = Field(min_length=1, max_length=10)

    @field_validator('checked_at', 'source_published')
    @classmethod
    def valid_date(cls, value):
        if value is None:
            return value
        if date.fromisoformat(value).isoformat() != value:
            raise ValueError('invalid review date')
        return value


def plan_payload(plan):
    # Keep hashes of existing text-only plans stable when adding optional fields.
    return plan.model_dump(exclude_none=True)


def load_plan(path):
    data = Path(path).read_bytes()
    if len(data) > 30_000:
        raise ValueError('oversized correction plan')
    return NoteCorrectionPlan.model_validate_json(data)


def load_intent(name, data):
    record = json.loads(data)
    if (not isinstance(record, dict) or set(record) != {'schema_version', 'status', 'plan'} or
            type(record['schema_version']) is not int or record['schema_version'] != 1 or
            record['status'] not in {'pending', 'complete'}):
        raise ValueError('invalid correction intent')
    plan = NoteCorrectionPlan.model_validate(record['plan'])
    if name != 'state/note-corrections/' + plan.note_id + '.json':
        raise ValueError('invalid correction identity')
    return record, plan


def correction_intents(store):
    for name in store.list('state/note-corrections/'):
        record, plan = load_intent(name, store.read(name))
        yield name, record, plan


def recover_note_corrections(store, app):
    for _, record, plan in list(correction_intents(store)):
        if record['status'] == 'pending' and correct_note(store, app, plan, apply=True)['status'] != 'success':
            raise ValueError('note correction recovery failed')


def corrected_note(original, row, app, plan):
    if sha256(original) != plan.expected_note_sha256:
        raise ValueError('changed note')
    meta = validate_note(original, row, app.tracking_parameters, app.categories)
    if meta['canonical_url'] != plan.source:
        raise ValueError('changed source')
    text = original.decode()
    for edit in plan.edits:
        if text.count(edit.old) != edit.expected_occurrences or edit.old == edit.new:
            raise ValueError('changed edit occurrence')
        text = text.replace(edit.old, edit.new)
    if sha256(text.encode()) != plan.expected_text_sha256:
        raise ValueError('changed proposed text')
    _, match, updated = note_frontmatter(text.encode())
    immutable = set(meta) - {'title', 'description'}
    if plan.source_published is not None:
        if updated.get('published') != plan.source_published or meta['published'] == plan.source_published:
            raise ValueError('changed source publication date')
        immutable.remove('published')
    if any(updated.get(k) != meta[k] for k in immutable) or set(updated) != set(meta):
        raise ValueError('changed immutable metadata')
    # Search terms establish graph relations; a text correction does not alter
    # that declaration, image definitions, source provenance or billing identity.
    def keywords(value):
        return value.partition('\n\n## 検索キーワード\n\n')[2].partition('\n\n## 資料の位置づけ\n\n')[0]
    if keywords(text) != keywords(original.decode()):
        raise ValueError('changed search keywords')
    revisions = list(meta.get('note_corrections', []))
    body = text[match.end():]
    if revisions:
        trailer = correction_trailer(revisions)
        if not body.endswith(trailer):
            raise ValueError('changed correction trailer')
        body = body[:-len(trailer)]
    revision = dict(plan_sha256=sha256(json_bytes(plan_payload(plan))),
                    previous_note_sha256=plan.expected_note_sha256,
                    checked_at=plan.checked_at, reviewer_kind='automated_assistant')
    if plan.source_published is not None:
        revision.update(published_before=meta['published'], published_after=plan.source_published)
    revisions.append(revision)
    updated['note_corrections'] = revisions
    result = ('---\n' + yaml.safe_dump(updated, allow_unicode=True, sort_keys=False) +
              '---\n' + body + correction_trailer(revisions)).encode()
    validate_note(result, row, app.tracking_parameters, app.categories)
    return result


def correct_note(store, app, plan, *, apply=False, output=None):
    result = dict(status='failed', apply=apply, note_id=plan.note_id, planned=0, updated=0, unchanged=0)
    stage = 'validate'
    try:
        reader, indexes = CheckedReads(store), index_catalog(store)
        rows = [row for name in indexes for row in decode_tsv(reader.read(name), INDEX_COLUMNS[:12])
                if row['status'] == 'success' and
                note_identity(row['source_id'], row['canonical_url'], app.tracking_parameters)[1] == plan.note_id]
        if not rows:
            raise ValueError('unknown note')
        row = max(rows, key=lambda r: (instant(r['processed_at']), r['content_sha256']))
        name = row['note_object']
        object_path(name, 'notes/', '.md')
        receipt_name = 'state/receipts/' + row['content_sha256'] + '.json'
        object_path(receipt_name, 'state/receipts/', '.json')
        note_data, receipt_data = reader.read(name), reader.read(receipt_name)
        receipt = json.loads(receipt_data)
        if (not isinstance(receipt, dict) or not isinstance(receipt.get('row'), dict) or
                not isinstance(receipt.get('note'), str) or
                any(str(receipt['row'].get(k, '')) != value for k, value in row.items())):
            raise ValueError('conflicting receipt')
        plan_hash = sha256(json_bytes(plan_payload(plan)))
        intent_name = 'state/note-corrections/' + plan.note_id + '.json'
        intent = dict(schema_version=1, status='pending', plan=plan_payload(plan))
        previous_intent = store.read(intent_name)
        if previous_intent is not None:
            saved, saved_plan = load_intent(intent_name, previous_intent)
            if saved['status'] == 'pending' and saved_plan != plan:
                raise ValueError('another correction is pending')
        history = f'state/note-correction-history/{plan.note_id}/{plan.expected_note_sha256}.json'
        proof = receipt.get('note_correction', {})
        resume = isinstance(proof, dict) and proof.get('plan_sha256') == plan_hash
        if resume:
            original_receipt = reader.read(history)
            previous = json.loads(original_receipt)
            original = previous['note'].encode()
            if previous['row'] != receipt['row']:
                raise ValueError('changed correction history')
        else:
            original_receipt, original = receipt_data, note_data
            if receipt['note'].encode() != original:
                raise ValueError('changed note or receipt')
        proposed = corrected_note(original, row, app, plan)
        expected = dict(plan_sha256=plan_hash, previous_note_sha256=plan.expected_note_sha256,
                        note_sha256=sha256(proposed), previous_receipt_sha256=sha256(original_receipt),
                        history=history)
        if resume:
            if proof != expected or receipt['note'].encode() != proposed or note_data not in (original, proposed):
                raise ValueError('changed resumed correction')
        else:
            receipt.update(note=proposed.decode(), note_correction=expected)
        result.update(before_sha256=plan.expected_note_sha256, after_sha256=sha256(proposed),
                      planned=int(note_data != proposed), unchanged=int(note_data == proposed))
        archived = store.read(history)
        if archived is not None and archived != original_receipt:
            raise ValueError('conflicting correction history')
        stage = 'recheck'
        reader.verify(indexes)
        if output is not None:
            stage = 'preview'
            destination = Path(output)
            destination.mkdir(parents=True, exist_ok=False)
            (destination / (plan.note_id + '.md')).write_bytes(proposed)
        if apply and note_data != proposed:
            stage = 'history_save'
            if archived is None:
                store.write(history, original_receipt, 'application/json')
            stage = 'intent_save'
            if previous_intent != json_bytes(intent):
                store.write(intent_name, json_bytes(intent), 'application/json')
            stage = 'receipt_save'
            if not resume:
                store.write(receipt_name, json_bytes(receipt), 'application/json')
            stage = 'note_save'
            store.write(name, proposed, 'text/markdown; charset=utf-8')
            result['updated'] = 1
        if apply:
            stage = 'intent_complete'
            pending_intent = json_bytes(intent)
            intent['status'] = 'complete'
            current_intent = store.read(intent_name)
            if current_intent not in (None, pending_intent, json_bytes(intent)):
                raise ValueError('changed correction intent')
            if current_intent != json_bytes(intent):
                store.write(intent_name, json_bytes(intent), 'application/json')
        result['status'] = 'success'
    except Exception as exc:
        result.update(stage=stage, error_type=type(exc).__name__)
    return result
