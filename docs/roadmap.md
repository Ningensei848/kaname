# 確定バックログ — Deferred but Required

以下は採用済みの必須機能であり、任意の将来候補ではありません。
Phase 1の実環境受入完了後にPhase 2、その完了後にPhase 3へ着手します。
本ファイルはMVP完成後も削除しません。

## Phase 2
- [ ] Playwright Fetcher — RSSなし/JSサイトをsource設定から選択
- [ ] Main Content Extraction — source selectorと汎用本文抽出
- [ ] Deterministic Relevant Filter — include/exclude keyword・domain・category
- [ ] Gemini Batch API — standard/batch切替、standardを維持
- [ ] Obsidian Sync — `techkb sync --vault`、ローカル編集を保護
- [ ] Cost Management — 実測usageの日次/月次USD費用、予算通知手順
- [ ] Failure Notification — 連続失敗を識別、必要時Issue通知
- [ ] Raw HTML Lifecycle — sourceごとの保存期間・自動削除

## Phase 3
- [ ] Parallel Processing — parallel fetch/convert + single state writer
- [ ] Source Health Check — 最終成功・連続失敗・発見/処理件数
- [ ] Regression Corpus — 代表サイトfixtureと変換差分検出
- [ ] Knowledge Graph Quality — 表記揺れ・同義語・タグ・WikiLink品質評価

## 条件付きインフラ移行（上記の必須機能とは区別）
Actions実行時間・quota・数千記事/日・worker運用・durabilityが問題になった場合に
Cloud Run Jobs等を検討します。MVPではDB、Vector DB、複数LLMを導入しません。
