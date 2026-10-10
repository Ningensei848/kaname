"""Synthetic compact Notes. No network, credentials, or production state."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from techkb.composer import compose
from techkb.config import Source
from techkb.models import ArticleEnrichment
from techkb.pending import Candidate
from techkb.publication import export_notes, sha256
from techkb.state import INDEX_COLUMNS, encode_tsv


class FixtureStore:
    def __init__(self):
        self.data = {}
    def read(self, name):
        return self.data.get(name)
    def list(self, prefix):
        return sorted(name for name in self.data if name.startswith(prefix))


def make_fixture(output):
    store, rows = FixtureStore(), []
    fixtures = [
        ("LLMの評価を小さく始める", "fixture-research", "Research Studio（架空）", "ai-llm",
         "モデルの比較は、実際の仕事に近い小さな評価セットから。変化を追える基準を先に用意します。",
         ["評価する用途と成功条件を先に決める", "少数の代表例で品質・費用・速度を比較する", "プロンプトとモデルの版を記録する"], False),
        ("失敗から再実行できるバッチ設計", "fixture-engineering", "Engineering Journal（架空）", "software-development",
         "ジョブを提出して終わりにせず、保存までを見届ける。状態と利用量を残すことで、失敗後も安全に再開できます。",
         ["提出と結果取込みの状態を分けて記録する", "再提出の前に既存ジョブを照合する", "保存の完了と利用量をそれぞれ確認する"], True),
        ("検索から知識にたどり着く", "fixture-research", "Research Studio（架空）", "data",
         "検索結果を読み直せる短いNoteへ。出典と文脈を残すことで、発見した情報を次の学習につなげます。",
         ["要約から原典へ戻れるようにする", "同じ知識を日付・出典・カテゴリから探す", "生成された知識と人の判断を分けて扱う"], False),
    ]
    for n, (title, source_id, publisher, category, summary, points, truncated) in enumerate(fixtures):
        at = f"2026-10-0{n + 1}T09:00:00Z"
        url = f"https://example.com/fixture/{n + 1}"
        source = Source(id=source_id, name=publisher, feed_url="https://example.com/feed", base_url="https://example.com")
        enrichment = ArticleEnrichment(title_ja=title, summary_ja=summary, key_points=points,
            positioning_ja="このNoteは画面検証のための架空データです。実在の記事の要約ではありません。",
            category=category, tags=[category, "preview"],
            related_concepts=[fixtures[(n+1) % len(fixtures)][0], "知識の育て方"], source_language="ja")
        images = []
        if n == 0:
            from techkb.models import ImageSelection
            enrichment.images = [ImageSelection(image_id='img-1', after='key_point_1')]
            images = [dict(image_id='img-1', url='https://images.example.com/evaluation.png', alt='評価の流れ')]
        digest, raw = sha256(title.encode()), sha256(("synthetic:" + title).encode())
        name, note = compose(Candidate(at, source_id, url, title=title), source, enrichment,
            "Synthetic fixture only.", url, at, raw, digest, "fixture-model", truncated, input_char_limit=20000,
            image_candidates=images)
        row = dict(processed_at=at, source_id=source_id, source_url=url, canonical_url=url, published_at="",
            raw_html_sha256=raw, content_sha256=digest, status="success", note_object=name,
            llm_model="fixture-model", input_tokens=0, output_tokens=0, thinking_tokens=0,
            llm_input_truncated=str(truncated).lower())
        rows.append({k: str(row[k]) for k in INDEX_COLUMNS})
        store.data[name] = note.encode()
        store.data[f"state/receipts/{digest}.json"] = json.dumps(dict(row=row, note=note), ensure_ascii=False).encode()
    store.data["state/index/2026-10.tsv"] = encode_tsv(rows, INDEX_COLUMNS)
    return export_notes(store, output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parent / ".cache/fixture-snapshot")
    output = parser.parse_args().output
    output.parent.mkdir(parents=True, exist_ok=True)
    print(json.dumps(make_fixture(output), ensure_ascii=False))
