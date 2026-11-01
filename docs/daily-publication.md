# 日次公開と再実行

`daily.yml`は毎日07:17 JST（22:17 UTC）に通常収集を実行し、成功後に同じ生成Note群をGitとPagesへ公開します。
既存の収集上限・Gemini設定・WIFの`daily.yml@refs/heads/main`条件は維持します。

| 工程 | 操作・権限 | 失敗時 |
|---|---|---|
| collect | 既存WIFで収集・audit。成功後にGCS読取りexport。`contents: read`、`id-token: write`、既存通知用`issues: write` | 後続公開を停止 |
| publish | 公開snapshot artifactのみ取得。`contents: write`でcontentへnon-force push、fresh cloneで全bytesを検証後、完全版/差分Releaseをdraftで検査してpublish | Pagesを停止。競合は上書きしない |
| pages | 固定Releaseから全体を復元してbuild/deploy（手動はGit互換も可）。`contents: read`、`pages: write`、`id-token: write` | 失敗状態と配信版照合を記録 |
| notify-publication | GCS/収集Secretを使わず`issues: write`でstageとrun URLを通知 | 通知job自体の失敗はActionsで確認 |

GCSの単一writer concurrencyはcollect・Batch preflight・画像補完jobで共有し、Git配布は`kaname-content`、Pagesは`kaname-pages`で直列化します。
Git/Pages jobへGemini/GCSのSecretを渡しません。artifactは検証済みの公開Note/manifestだけで、保持期間は2日です。
入力snapshot不整合、remote取得失敗、content branch不在、競合は固定errorで停止し、force pushや自動branch作成をしません。
日次Pagesは既に後続版へ進んだcommitのdeployを拒否します。手動の履歴版deployは[Pages手順](pages.md)で行います。
Git更新なしでもPagesを再deployし、前回の公開失敗を再試行できます。

## Batch受入の事前検査

`daily.yml`の手動入力`batch_preflight=true`は、GCSを読む検査専用jobだけを実行します。
通常collectと同じwriterロックを使い、既存WIFのmain/daily条件内でauditと未決済/未計上を確認します。
記事取得、Gemini、GCS書込み、通知、export、Git更新、Pagesは実行しません。
検査jobの権限は`contents: read`と`id-token: write`だけで、Gemini/GitHub書込み用Secretを渡しません。
他モードや収集overrideとの同時指定は認証前に拒否します。
`ready`でも有料提出は個別承認後です。詳細は[操作手順](operations.md#実batch受入の事前検査)を参照してください。

## 既存Noteの限定画像補完

`image_repair_plan`と`image_repair_apply`で、レビュー済み計画のプレビューまたは適用を行います。
通常のcollect/publish/pagesはskipし、Geminiを呼ばず、要約を維持します。
同じGCS writer lockで直列化し、適用とaudit成功後に公開専用実行を行います。
詳細は[画像補完と復旧](operations.md#既存noteへの画像補完)を参照してください。

## 公開だけを再実行

```bash
gh workflow run daily.yml --repo Ningensei848/kaname --ref main -f publish_only=true
```

既存Noteのaudit/export、Git/Release配布、Pages更新だけを実行します。記事取得、Gemini呼出し、費用/通知stateの更新はありません。
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

## 検査・読取り性能の設定

設定検証は毎回実行し、`scripts/daily_validation.py`で同じmain SHAの最新Checks push run/attemptとscope/test/web-preview成功を確認する。
照合不能・失敗・実行中・別SHA・不完全応答では従来の全単体テストへ戻る。`--full-tests`でも全実行できる。
GCS/費用/全Web/配信版の実検査は省略しない。

監査/export/費用/通知はlive世代catalogを使い、本文downloadは最大16並列。日次のrepository variable `GCS_READ_WORKERS`、ローカルの`KANAME_GCS_READ_WORKERS`で1〜16を選べる。
省略は16、8で旧並列数、1で逐次へ戻す。不正値は認証・生成前に拒否する。
SDK認証/retry/custom TLSを維持し、標準Storage接続poolをworker数へ合わせる。書込み/生成は単一writerのままである。
`KANAME_READ_CACHE`は同じprivate runner内の世代/CRC一致bytesだけを再利用し、検査結果やcatalogをcacheしない。
毎回の全件検査とlive catalog再確認を維持し、private bytesをActions cache/artifactへ保存しない。

## Release差分配布

完全版checkpointと最大7段の差分から公開Note全体を復元する。同じcontent commitではReleaseを増やさず、asset欠損/改変/基底不一致で停止する。
契約は[Release配布](release-distribution.md)、現在の受入範囲は[検証基準](verification.md)を参照。
通常schedule・切戻し/復帰・CI再利用・GCS16並列は受入済み。[整理前の全文・受入証拠](https://github.com/Ningensei848/kaname/blob/archive/pre-housekeeping-2026-10-16/docs/daily-publication.md)と[archive索引](archive/README.md)へ当時のrun/件数を保全した。
