# バックログと着手順

最新の要求は[ADR-0001](adr/0001-generated-content-module-and-pages.md)です。
旧Phase 1→2→3の一律の着手制約を改め、公開生成NoteのGit配布/Pagesを優先します。
これまで採用した品質・復旧機能は残し、実装済みと本番受入済みを区別します。

## 今回優先する配布・Web

- [x] 新要求と旧仕様の衝突をADRに記録し、現行文書と履歴を分離。
- [x] 成功Noteの決定的export、安定Note ID、manifest、整合性/公開内容検査。offline検証済み。
- [ ] 実GCSのexport受入。既存成功Noteのみを読取り、無書込み/追加生成0を照合。
- [x] 共通snapshotを使うWeb preview。Quartz 5.0.0/plugin固定、架空Noteと実Chromiumで検証。
- [ ] `content`branchの完全snapshot配布、再実行/競合、submodule互換性。
- [ ] 同じ生成Note群のGit/Pages初回公開とhash/commit/digest照合。
- [ ] 成功収集後の日次公開と、収集/配布/deployそれぞれの障害通知。

この順の成果物と完了条件は[実装計画](implementation-plan.md)にあります。
人力Vaultのrepo/公開/プラグイン設定はこのバックログへ含めません。

## 現行コレクタの修正・受入

- [x] F1: 互換syncの最終確認後の編集消失を防ぐ。PR #98。
- [x] F2: Batchの元例外と安全な診断を保持し、既存結果をGETで検査。PR #97。
- [ ] F4/F5: usage部分欠落と中断後の費用復旧。日次公開の自動化拡張前に優先。
- [ ] F6: 未処理sourceの失敗streakを維持。
- [ ] F3: browser resource/robots redirectの通信前policy。本番有効化前に対処。
- [x] F7: 状態/schema/通知に関する現行文書の旧説明を改訂。
- [ ] 実Batchの成功結果保存、再実行、audit/costの本番受入。後続standard成功と混同しない。

## 既存機能の位置づけ

| 機能 | 状態 |
|---|---|
| 公開snapshot export | 読取り専用CLI、39件のoffline検証。実GCSの受入は未完了 |
| Web preview | 公開境界24テストと架空Noteのbrowser受入。実NoteのPages公開は未完了 |
| Playwright/HTML一覧、本文抽出、決定的filter | 実装済み、sourceごとのopt-in。browserのF3と実source受入は残る |
| 非同期Gemini Batch | 実装/fixture検証済み。成功保存の本番受入は残る |
| Obsidian直接sync | 編集保護を取込済み。新標準はGit/submodule、直接syncは互換用途 |
| Cost management | 推計/予算通知は実装済み。F4/F5とinvoice照合は残る |
| Failure notification | 日次Issue通知は実装・承認済み。F6と追加通知範囲は残る |
| Raw lifecycle | plan/管理者applyは実装済み。未設定sourceへの本番適用は必須でない |

## 継続する後続の必須項目

- [ ] Parallel Processing — parallel fetch/convert + single state writer。
- [ ] Source Health Check — 最終成功・連続失敗・発見/処理件数。
- [ ] Regression Corpus — 代表サイトfixtureと変換差分検出。
- [ ] Knowledge Graph Quality — 表記揺れ・同義語・タグ・WikiLink品質評価。

大規模化でActionsの時間/quotaやdurabilityが問題になった場合にCloud Run Jobs等を再検討します。
DB/Vector DB/複数LLMへの移行は、今回の配布・Webの前提ではありません。
