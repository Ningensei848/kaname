# 日次公開と再実行

`daily.yml`は毎日07:17 JST（22:17 UTC）に通常収集を実行し、成功後に同じ生成Note群をGitとPagesへ公開します。
既存の収集上限・Gemini設定・WIFの`daily.yml@refs/heads/main`条件は維持します。

| 工程 | 操作・権限 | 失敗時 |
|---|---|---|
| collect | 既存WIFで収集・audit。成功後にGCS読取りexport。`contents: read`、`id-token: write`、既存通知用`issues: write` | 後続公開を停止 |
| publish | 公開snapshot artifactのみ取得。`contents: write`でcontentへnon-force push、fresh cloneで全bytesを検証 | Pagesを停止。競合は上書きしない |
| pages | 検証済みcontent commitからbuild/deploy。`contents: read`、`pages: write`、`id-token: write` | 失敗状態と配信版照合を記録 |
| notify-publication | GCS/収集Secretを使わず`issues: write`でstageとrun URLを通知 | 通知job自体の失敗はActionsで確認 |

GCSの単一writer concurrencyはcollect jobだけ、Git配布は`kaname-content`、Pagesは`kaname-pages`で直列化します。
Git/Pages jobへGemini/GCSのSecretを渡しません。artifactは検証済みの公開Note/manifestだけで、保持期間は2日です。
入力snapshot不整合、remote取得失敗、content branch不在、競合は固定errorで停止し、force pushや自動branch作成をしません。
日次Pagesは既に後続版へ進んだcommitのdeployを拒否します。手動の履歴版deployは[Pages手順](pages.md)で行います。
Git更新なしでもPagesを再deployし、前回の公開失敗を再試行できます。

## 公開だけを再実行

```bash
gh workflow run daily.yml --repo Ningensei848/kaname --ref main -f publish_only=true
```

既存Noteのaudit/export、Git配布、Pages更新だけを実行します。記事取得、Gemini呼出し、費用/通知stateの更新はありません。
通常収集の入力変更や診断モードとの同時指定は拒否します。通常の入力未指定実行とscheduleは収集します。
追加のGCS IAM権限や新しいSecretは不要です。

## 通知と復旧

source/collectorの連続失敗と予算通知は従来の閾値を使います。
sourceの失敗回数は実際に処理を完了したsourceだけでresetし、未処理sourceと旧reportの不確かな成功は維持します。
収集/audit/export/Git/Pagesの失敗は、閾値を待たずGitHub run IDごとのIssueで通知します。
同一runの再実行は閉じたIssueも含めて重複抑止します。本文はstage名とrun URLで、本文や認証情報は含めません。
通知はmock APIで検証し、実障害を故意に発生させる試験はしていません。

standardのusage journalで中断後の元の日付/価格と既知countを保持し、最終reportと二重計上しません。
呼出し予約のまま応答を失った場合や旧receiptの課金参照欠落はpartialです。APIとGCS間のtransactionやinvoice完全性は保証しません。
詳細は[運用手順](operations.md)を参照してください。

## 受入状態

- クラウドの全264テストが成功。receipt/Note/index/report保存時の中断、usage保存失敗、月跨ぎ/価格変更、部分欠落usage、未処理source、remote競合、Issue重複抑止を検証。
- workflowのactionlintとshell構文を検査。依存manifest/lockは変更なし。
- PR #105取込後のmain `2d33e0cf018c4c9986a19252725d4bc7875cfa99`で、2026-10-06の[公開専用run 37434000683](https://github.com/Ningensei848/kaname/actions/runs/37434000683)が成功。
- 既存WIFの認証、保存状態audit、読取りexport、artifact受渡し、Git配布とremote照合、Pages build/deploy、runnerの配信版照合がすべて成功。Collect・費用/通知state更新はskip、障害通知jobもskip。
- content commitは`4205590eb588f0e0ddc991ef478c1bb2033746da`、Note数117。初回版から最新成功版へ通常pushで進め、同じcommitからPagesを更新。
- dataset digestは`7c5b877882e32855634a1706ef3b7f924a915e31750355d545d970bf0001e08f`、公開artifact digestは`0f9e212bbf8861d1667d8e62746a589b854a8d7efd698fd971651a9008e909f2`。
- クラウドからもHTTPSで公開manifestのbytesと検証済みGit manifestを一致照合し、全117件の元Markdown・トップ・版表示・代表Note HTMLのhashを検証。追加Gemini呼出し/記事取得/GCS書込みなし。
- 通常scheduleの初回連続実行は2026-10-07に受入済み。収集・usage保存・audit・export・Git配布・Pages・全元Markdown配信照合の証拠は[月別受入記録](archive/2026-10/schedule-acceptance-2026-10-07.md)に保存。実切戻し、実Batch/F3 browserの受入と実障害Issue投稿の故意の試験は未実施。
- 初回Pagesの117件公開は[従来の受入](verification.md)で確認済み。今回の実行結果とは区別します。
- O2の切戻し117件/復帰118件は両版のローカルbuild・artifact/browser受入と期待配信digestの照合まで準備済み。実公開操作は個別承認待ち。固定版と復帰手順は[月別準備記録](archive/2026-10/pages-rollback-preparation-2026-10-07.md)に保存。
