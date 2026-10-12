# バックログと着手順

最新の要求は[ADR-0001](adr/0001-generated-content-module-and-pages.md)です。
旧Phase 1→2→3の一律の着手制約を改め、公開生成NoteのGit配布/Pagesを優先します。
これまで採用した品質・復旧機能は残し、実装済みと本番受入済みを区別します。

## 今回優先する配布・Web

- [x] 新要求と旧仕様の衝突をADRに記録し、現行文書と履歴を分離。
- [x] 成功Noteの決定的export、安定Note ID、manifest、整合性/公開内容検査。offline検証済み。
- [x] 実GCSのexport受入。117件、無書込み/追加生成0を照合。
- [x] 共通snapshotを使うWeb preview。Quartz 5.0.0/plugin固定、架空Noteと実Chromiumで検証。
- [x] `content`branchの完全snapshot配布、再実行/競合、一時submodule互換性。初回117件を公開。
- [x] 同じ生成Note群のPages初回公開。117件の固定Git版を公開し、公開URLの元Markdown hashを照合。
- [x] 成功収集後の日次公開と、収集/audit/export/配布/deployの障害通知を実装。公開専用runで117件の実更新と配信hash照合を受入。[日次公開](daily-publication.md)へ記録。

この順の成果物と完了条件は[実装計画](implementation-plan.md)にあります。
人力Vaultのrepo/公開/プラグイン設定はこのバックログへ含めません。

## 現行コレクタの修正・受入

- [x] F1: 互換syncの最終確認後の編集消失を防ぐ。PR #98。
- [x] F2: Batchの元例外と安全な診断を保持し、既存結果をGETで検査。PR #97。
- [x] F4/F5: usage部分欠落と中断後の費用復旧。元の日付/単価維持と二重計上防止を障害注入で検証。
- [x] F6: 未処理sourceの失敗streakを維持。明示的完了だけでreset。
- [x] F3: browser resource/robots redirectの各hopを通信前に検査。許可外hostへのDNS/HTTP要求0を検証。
- [x] F7: 状態/schema/通知に関する現行文書の旧説明を改訂。
- [x] 実Batchの3画像入りNote 1件を保存/公開、課金1回と追加生成0の再実行・audit/cost/Git/Pagesを本番受入。#94をClose。

## 既存機能の位置づけ

| 機能 | 状態 |
|---|---|
| 公開snapshot export | 読取り専用CLI、旧形式互換を含む43件のoffline検証。実GCSの117件を受入 |
| Git配布 | 公開内容のみのbare出版、15テスト。初回117件をcontent branchへ公開 |
| Web preview | 公開境界24テスト、架空/実Noteのbrowser受入。117件の初回Pages deploy/公開URL hash照合は受入済み |
| Playwright/HTML一覧、本文抽出、決定的filter | 実装済み、sourceごとのopt-in。F3は修正済み。実source受入は残る |
| 非同期Gemini Batch | 実Note 1件/画像3件の保存・公開、課金1回・追加生成0の再実行を本番受入済み |
| Obsidian直接sync | 編集保護を取込済み。新標準はGit/submodule、直接syncは互換用途 |
| Cost management | 推計/予算通知は実装済み。F4/F5は修正・offline検証済み。invoice照合は残る |
| Failure notification | 日次Issue通知は実装・承認済み。F6修正済み。公開stage通知・重複抑止をoffline検証済み |
| Raw lifecycle | plan/管理者applyは実装済み。未設定sourceへの本番適用は必須でない |

## 継続する後続の必須項目

- [x] Parallel Processing — 最大2件のfetch/convert先行処理、入力順の課金・状態更新、host間隔/robotsの排他を回帰検証。
- [x] Source Health Check — 読取り専用`source-health` CLIのJSONで最終成功・連続失敗・source別発見/保存件数・pendingを表示。旧runの件数不明はnull。運用手順を参照。
- [x] Regression Corpus — 有効7 source・8レイアウトの合成fixture・本文/画像goldenと差分検出CLI、offline回帰。
- [x] Knowledge Graph Quality — 読取り専用CLI、良い/悪い16例・27件、固定実content125 Noteを評価。検索語612件未解決・表記群各3組と元hash不変を確認。[評価と限界](graph-quality.md)。

大規模化でActionsの時間/quotaやdurabilityが問題になった場合にCloud Run Jobs等を再検討します。
最新の着手順・未完了Issueの計画・個別の受入状態は[次の作業](next-work.md)を正本とします。
DB/Vector DB/複数LLMへの移行は、今回の配布・Webの前提ではありません。

## 保守性の改善

[リファクタリング計画](refactoring-plan.md)のR1〜R5は2026-10-07に完了・取込済みです。
実Batchの成功保存/公開/再実行は本番受入済み。確定請求照合は明細待ちで、費用推定は完了しています。

## 既存計画完了後のNextStep

- [x] NS1: 検索キーワード・Note本文の固有語彙のWikiLinkについて、対応する公開Noteを優先し、未解決の場合はGoogle検索へつなぐ。

2026-10-11の追加要望です。Knowledge Graph Qualityの評価とNS1の実装・本番受入は完了しました。請求明細待ちとsource障害は独立して追跡します。
本文へのWikiLink付与、SSG時の解決、既存Noteの互換性、検証と完了条件は
[NS1の完了状態](next-work.md#ns1-google-search-fallback)と受入記録に集約しています。実装・全Python543件/PR/main CI・架空3件/実125件のChromium・本番Pages配信照合まで完了です。[NS1記録](ns1-search-fallback.md)で追跡します。

日次のGCS読取り短縮も実Actions受入済みです。最大8件並列とrunner内世代cacheで、生成0の同条件runが39分22秒→15分30秒。全件検査・保存/費用/配信不変を確認し、[性能記録](daily-performance.md)へ集約しました。

新規記事だけの収集も659件/PR/main CI・生成0本番受入済みです。既知111件を本文GET前に除外し、生成上限で本文取得も止め、全体15分30秒→5分51秒。配布assetの差分/完全版の復元契約は[設計記録](incremental-collection.md)で未採用案として区別します。
