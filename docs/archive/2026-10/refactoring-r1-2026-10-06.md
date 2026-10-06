# R1: 費用集計・通知の分離とローカル回帰（2026-10-06）

対象Issueは#110。実装基点はmain `4af02d221e117f1c383ee5313bc3a17dbdd8b6f3`。
T0のローカル基点受入はPR #117の引継ぎ記録に保存した。

## 変更

- run_historyへ履歴読取りと重複/識別子検査を移した。
- costsでcheckpoint読取り、最終reportとの照合、元単価によるUTC費用計算、未決済Batchの読取りを分離した。
- notificationsで取得済みreportからの失敗判定とIssue送信を分離した。
- operationsは既存のhistory/cost_report/notification_plan/publish_issuesのimport入口を維持する。

storeの読取り順序、最終report優先、元run ID/日付/価格、partial判定、通知key、閉じたIssueの重複抑止を維持する。
Note生成・receipt/index保存・usage checkpoint書込み・CLI・workflow・依存lockには変更がない。

## ローカル検証

Python 3.12.13、Node 24.15.0と既存lockを使用した。
通常sandbox経路の起動制約があるため、承認されたexec_command経路でWSL内の検証を実施した。

| 検証 | 結果 |
|---|---|
| 変更前のvalidate-config | success |
| 変更前の全Python回帰（実Chromiumを含む） | 270 passed、31.91秒 |
| 変更後の費用/通知/usage復旧/Batch/公開通知の対象回帰 | 53 passed、5.97秒 |
| 変更後の全Python回帰（実Chromiumを含む） | 270 passed、31.05秒 |
| 変更前実装との合成データ比較 | 費用19ケース・通知4ケースのJSON結果/例外/読取り順序が一致 |
| cost-report/notifyのoffline CLI比較 | JSON出力bytesと終了コード0が変更前と一致 |
| git diff --check | success |

合成データ比較には空履歴、usageだけの復旧、pending、最終report優先、usage値/識別子の衝突、負のcount、重複report、単価不明/旧形式、partial、dry-run、月跨ぎ、未決済/拒否済みBatch、未処理sourceのstreak維持と実復旧を含めた。
追加の実API呼出し・記事取得・GCS操作・Issue障害通知の実投稿は行っていない。

## 後続

R1のCI/レビュー/取込とO1 #109の通常schedule受入後に、R2 #111へ進む。
本番Batchの追加提出、Pages切戻し、請求照合は独立した受入として継続する。
