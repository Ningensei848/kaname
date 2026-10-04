# 検証記録 — 2026-10-04

## 開発停止時の本番確認 — 2026-10-04

ユーザー指示で開発とCodexの自動継続を停止しました。既存の日次workflowは稼働中です。
mainの実装commitは`f7bbc28f240b94ebf5b85cc72981996b17b19e05`（PR #95）。
最終修正後は全103テストに成功し、[PR CI](https://github.com/Ningensei848/kaname/actions/runs/37164238148)と
[main CI](https://github.com/Ningensei848/kaname/actions/runs/37164366370)も成功しました。

| run / 入力 | 結果 | 保存状態・費用 |
|---|---|---|
| [37164369505](https://github.com/Ningensei848/kaname/actions/runs/37164369505) / batch、max_calls=1 | success、Batch提出1、標準呼出0、保存0 | audit: index 96、pending 78、issues 0。未決済Batch 1件 |
| [37164923005](https://github.com/Ningensei848/kaname/actions/runs/37164923005) / max_calls=0 | failed、batch_failed 1、batch_saved 0、標準呼出0 | batch_result/google-research/ValueError。Audit skip。使用量からのBatch費用推計USD 0.0016944、未決済Batch 0件 |
| [37165511894](https://github.com/Ningensei848/kaname/actions/runs/37165511894) / schedule、standard、上限30 | success、呼出30、保存30、失敗0 | audit: index 126、pending 48、truncated_rows 100、issues 0 |

3 runともheadは上記mainです。最後の日次runは2026-10-04 09:37:28–09:46:44 JSTに実行され、
費用推計は10月4日UTCでUSD 0.0995463、10月累計USD 0.4013871。unknown usage/未決済Batchは0、
旧reportのモデル仮定は9件です。通知投稿は各runとも0件。費用は実測tokenと設定単価による推計であり請求額の照合ではありません。

上記はActionsのrun report、audit、cost出力を保存して確認しました。今回の3 runに別の独立GCS照合は追加していません。
Batch失敗の根本原因は未調査です。後続standard成功はBatch成功の証明ではありません。
Phase 1受入は完了、Phase 2受入は未完了として[Issue #94](https://github.com/Ningensei848/kaname/issues/94)を開いたままにします。
再開条件、認証、GCS ledgerと非公開ログの所在は[引継書](handoff-review-2026-10-04.md)を参照してください。

## Phase 2実装とローカル検証 — 2026-10-04

Python 3.12.13、google-genai 1.75.0、Playwright 1.63.0の実Chromiumで全102テストに成功しました。
設定検証とgit diff --checkにも成功。以下は実装とfixture検証で、実Batch API/GCSの受入は別項目として残します。

| 機能 | 確認 |
|---|---|
| HTML一覧/Playwright | RSSなし発見、実ChromiumのJS描画、外部/private fetchとWebSocket遮断、resource失敗検出 |
| 本文抽出 | navigation差分で再LLMしない、selector不一致時はpending維持 |
| 決定的フィルタ | NFKC keyword、domain、source category、除外時LLM/成功登録なし |
| Batch | submit/poll/standard切替、曖昧な作成の再送禁止と照合、結果順序変更、部分失敗、保存障害からreceipt復旧 |
| Batch SDK | 固定版SDKをMockTransportで実行し、Structured JSON/category/minimalのwire形式とinline結果解析を確認 |
| Vault同期 | 再同期、remote更新、ローカル編集/未管理ファイル保護、計画後の編集競合、path traversal/case衝突/symlink拒否 |
| 費用 | usage/thinking、historical rate snapshot、日月境界、重複report抑止、unknown usage/待機Batch、予算到達 |
| 通知 | 連続失敗と復旧、同一incident key、closed Issueも重複投稿しない（GitHub MockTransport） |
| Raw lifecycle | source age/prefix、他のrule保護、metageneration条件、再適用時変更なし |

日次workflowへの永続的`issues: write`追加は自動承認レビューで一度拒否されました。
2026-10-04に対象`Ningensei848/kaname/.github/workflows/daily.yml`・権限・通常runからの
連続失敗/予算到達時の自動投稿を明示した確認に、ユーザーが許可しました。その承認後に追加しています。
Issue #94でPhase 2の受入項目を追跡します。投稿fixtureは実Issueを作りません。

GCS lifecycleは通常writerへbucket更新権限を追加せず、管理者が明示適用する実装です。
既存sourceのraw保存はfalseのため、本番の削除ruleは適用していません。
利用者Vaultのパスは未指定のため、正式同期CLIは一時Vaultで検証しています。
実Chromiumはfixtureのscriptを実行し、未承認の新しい実サイトを巡回していません。

## 翌日の定期実行 — 2026-10-03

[run 37085168871](https://github.com/Ningensei848/kaname/actions/runs/37085168871)はevent `schedule`、
head `2b024a6`、Collect/Audit成功。ログでは30件処理・保存、失敗0件、
入力175,931・出力18,717・thinking 0 token、成功index 96件、pending 59件、truncated_rows 75、issues 0。
report IDは`20261003T011222Z-10250355`。この翌日分はActionsの結果を確認し、独立したGCS再照合は行っていません。
Phase 1受入は前日の定期runと読取りWIF照合で完了済みです。


## Phase 1最終受入完了 — 2026-10-03

[定期run](https://github.com/Ningensei848/kaname/actions/runs/36952132802)はevent `schedule`、
head `f0fe413d699d7a5232f5b13b2621d6f1882d80c4`、Collect/Auditとも成功でした。
2026-10-02 10:41 JSTに開始（07:17のcronから遅延）、10:48 JSTにworkflow完了。
reportは `runs/2026/10/20261002T014150Z-77ab903c.json` です。

| 項目 | 結果 |
|---|---|
| 発見 / 取得 | 110 / 110 |
| Gemini論理呼出 / HTTP通信 | 30 / 30 |
| Gemini成功 / 失敗 / usage不明 | 30 / 0 / 0 |
| 保存 / receipt復旧 | 30 / 0 |
| raw / content duplicate | 2 / 15 |
| 入力 / 出力 / thinking tokens | 174,952 / 18,915 / 0 |
| 成功index | 36 → 66（増分30） |
| pending | 78 → 63 |
| audit | success、truncated_rows 51、issues 0 |

ローカルADCは再認証を要求したため、同じdaily workflowのWIFを使う読取り専用
[照合run](https://github.com/Ningensei848/kaname/actions/runs/37080742206)を実行しました。
head `2b024a6`、全72テスト・WIF・audit-runに成功。Collectはskipされています。
保存済みreportの上記件数・usageと定期runログが一致し、index増分・pending・Note/receipt整合性も成功。
照合に記事取得・Gemini呼出し・GCS書込みはありません。Phase 1受入完了です。

## 上限30件の本番受入継続 — 2026-10-02

Note品質資料・利用条件資料と上限30件への復帰を含むPR #90は、ユーザーにより
2026-10-02 00:00 JSTにmergeされました。merge後に「マージした。続けて。」との指示を受け、
提示した設定での受入継続の承認として記録します。これは記事の個別許諾取得を証明する記録ではありません。
mainのmerge commitは `ac4cc22caf5bc02d7cf408a413039a4d0106f095` です。
入力上限20,000文字、AWS News無効、非公開GCSと原文非保存を維持しています。

本番実行前のauditは成功index 6件、pending 108件、truncated_rows 6件、issues 0件でした。
同じmainの[workflow_dispatch run](https://github.com/Ningensei848/kaname/actions/runs/36881318035)は成功しました。
ユーザーからも定期実行を待たずworkflow_dispatchで今すぐ確認する指示を受けています。
手動runの成功だけではscheduled runの受入項目を完了にしません。

## 上限30件の手動本番run — 2026-10-02

実行時間は00:04:26〜00:09:55 JSTで、CollectとAudit saved stateの両stepが成功しました。
Actionsログのrun reportとGCSの `runs/2026/10/20261001T150426Z-11478e19.json`、
Actionsのaudit結果とrun完了後の独立auditが一致することを確認しています。
run-id、保存先、NoteのcreatedはUTC基準のため、JSTの実行日より前の日付を含みます。

| 項目 | 結果 |
|---|---|
| head / event | `ac4cc22` / `workflow_dispatch` |
| 発見 / 取得 | 110 / 111 |
| Gemini論理呼出 / HTTP通信 | 30 / 30（retryなし） |
| Gemini成功 / 失敗 / usage不明 | 30 / 0 / 0 |
| 保存 / receipt復旧 | 30 / 0 |
| raw / content duplicate | 0 / 3 |
| source内訳 | Google Research 26件、GitHub Blog 4件 |
| 入力 / 出力 / thinking tokens | 176,938 / 18,533 / 0 |
| 成功index | 6 → 36（増分30 = saved） |
| pending | 108 → 78（audit = pending_after） |
| audit | success、truncated_rows 32、issues 0 |

新規30 Noteのfrontmatterはすべて `llm_input_max_chars: 20000` でした。
打切り26件はすべて要約前の注意表示があり、記事原文セクションはありません。
Google Research 26件では著者が未取得、GitHub Blog 4件では取得できています。
Google Researchの代表記事でauthor meta / JSON-LDがなく、役職・所属を含む見出しbylineに
著者名が記載されていることを確認しました。現行のmetadata抽出の制限として残します。

Google Researchの[ERA](https://research.google/blog/empirical-research-assistance-era-from-nature-publication-to-catalyzing-computational-discovery/)と
[Gemini Nano MTP](https://research.google/blog/accelerating-gemini-nano-models-on-pixel-with-frozen-multi-token-prediction/)の2 Noteを原記事と照合し、
中心的な説明・重要ポイント・検索キーワード・資料の位置づけが対応することを確認しました。
これは30件すべての詳細な事実検証ではありません。打切り時の後半欠落の制約を維持します。

## 既存Note metadata更新計画 — 2026-10-01

Geminiを再呼出しせず、成功indexの原記事から著者を再取得し、Noteとreceiptの著者・公開日表記だけを
更新する `refresh-metadata` を追加しました。既定は読取り専用の計画モードで、書込みには
明示的な `--apply` が必要です。全対象の検証完了前には書込みを開始せず、各Noteとreceiptは
世代条件を使い、receipt更新失敗時はNoteのロールバックを試みます。

Python 3.12.13で全65テスト、設定検証、git diff --checkに成功しました。
本番GCSに計画モードを実行し、成功行6件、更新予定5件、変更なし1件、著者取得不能0件、
失敗0件を確認しました。その後、PR #89をmerge済みのmain (`e510b5d`) で、
稼働中のworkflowがないことを確認し、本番Note/stateのsnapshotを保存して `--apply` を実行しました。
更新5件、変更なし1件、著者取得不能0件、失敗0件でした。
適用後のauditは成功行6件、pending 108件、truncated_rows 6件、issues 0件です。
snapshotとの差分を確認し、要約本文・著者/公開日以外のfrontmatter・hash・receipt行・index・pendingが
不変であることを確認しました。Gemini呼出し・workflow実行は行っていません。
適用後に計画モードを再実行し、更新予定0件、変更なし6件、失敗0件も確認しました。

## Phase 1実装の完了 — 2026-10-01

`max_calls_per_run` を通常値30へ復帰し、daily workflowの収集成功後に `audit-state` を追加しました。
全65テストと設定検証に成功しました。30件上限の既存テストは31記事に対して30件を保存し、
1件をpendingへ残すことを確認しています。入力上限20,000文字、原文非保存、AWS News無効を維持します。
実装完了と本番受入完了を区別し、下記のユーザー確認と上限30件での定期実行確認を未完了として残します。

## 入力上限の明示 — 2026-10-01

ユーザー方針により、Phase 1の記事Markdown入力上限20,000文字を維持します。
新規Noteでは生成時の `llm_input_max_chars` をfrontmatterへ保存し、打切り時は
AI要約の前に要約範囲と後半の論点欠落の可能性を表示します。
既存Noteは変更せず、Gemini呼出し・GCS書込みも行っていません。
Python 3.12.13で全58テスト、設定検証、git diff --checkに成功しました。

## 読取り専用の受入検査

`audit-state` を追加。追加時点のPython 3.12.13で全56テストが成功しました。
pipelineが生成したデータの整合性、書込みなし、Note/receipt欠落、receipt破損、
hash不一致、原文セクション残存、未登録Note/receipt、重複行、不正パス、
frontmatter境界、空/存在しないsnapshot、ローカルsnapshotでのCLI終了コードを検証しています。
入力上限で本文が打ち切られた成功行数も `truncated_rows` として報告します。
2026-10-01の本番GCS検査は初回にADCの `RefreshError` が発生しましたが、
認証更新を再確認後の再実行で成功しました（成功index 6件、pending 108件、issues 0件、終了コード0）。
GCS書込み・Gemini呼出しは行っていません。初回の認証エラーの原因は未特定です。
GitHub APIでは同日のmain (`e1d48fd`) のworkflow成功を確認しました。
本番受入の品質確認や利用条件の確認が完了したという意味ではありません。

## 実施結果

| 検証 | 結果 |
|---|---|
| Python 3.12の独立venvに依存を導入 | 成功 |
| `python -m techkb validate-config` | 成功。3 sources、指定Geminiモデル |
| `python -m pytest -q` | **65 passed**（2026-10-01） |
| raw一致時の変換前skip | 成功 |
| 動的script差分/content一致時のGemini抑止 | 成功 |
| 同一URLの本文更新 | 成功、別Note生成 |
| 異なるURLの同一本文 | 成功、1回のLLM呼出 |
| Schema不正 | 成功登録なし・pending維持・自己修正なし |
| Note upload失敗 | 成功登録なし・receiptから再課金なしで復旧 |
| index upload失敗 | run失敗・既存Noteを増殖させず復旧 |
| 31記事/上限30 | 30記事処理、1記事pending |
| 全月TSV/TSV内TAB・改行/不正header | 成功 |
| CLIオフラインdry-run | 成功、GCS書込み・Gemini呼出ゼロ |
| CLIオフラインE2Eと再実行 | 成功、Note/TSV/pending/report生成、2回目のLLM呼出ゼロ |
| 実サイトdry-run | **成功**。3 feeds、130記事を取得・変換、失敗0、Gemini/GCS操作0 |
| 実Gemini・GCS・WIF・GitHub Actions | **成功**。run `36312255153`、110件取得、Gemini 1回、失敗0、GCS保存成功 |
| compact Note本番保存 | **成功**。3件を自動生成、旧形式1件を状態整合性を維持して移行、全4件で原文セクションなし |
| 実環境の重複抑止 | **成功**。raw/content duplicateを確認し、新規記事だけGemini対象 |
| GitHub Actions schedule | **成功**。2026-09-28、2026-09-29のscheduled runが完了 |
| 本番metadata更新と適用後audit | **成功**。5 Note/receipt更新、成功6件、pending 108件、issues 0件、要約・状態不変 |
| 上限30件のworkflow_dispatch | **成功**。保存30、失敗0、成功index 36、pending 78、issues 0、ログ/GCS一致 |

テストのHTTP通信にはhttpx.MockTransportを使用します。実際のRSS/Atom解析、HTML cleaner、
MarkItDown、Pydantic、Composer、状態更新、CLIを通しています。
Gemini応答とGCSはテスト用オブジェクトです。実課金は発生させていません。

2026-09-27の実サイトdry-runでは3 sourceのrobots.txt、feed、記事取得に成功しました。
発見130、取得130、would_enrich 130、失敗0、LLM0、保存0、終了コード0でした。
この確認後、[AWS Site Terms](https://aws.amazon.com/terms/)がrobots/data extraction toolsを明示的に許諾対象外としているため、
`aws-news` は書面許諾または別途適用されるライセンスを確認できるまで無効化しました。

## 本番受入で残る項目

- [x] 初回受入用に `max_calls_per_run: 1` を設定。
- [x] GCP project / 非公開bucket / custom IAM role / WIFを設定。
- [x] GitHub repositoryとVariables/Secretsを設定。
- [x] Google Research / GitHub Blogの利用条件確認資料を提示し、ユーザーがPR #90をmergeして受入継続を指示。
- [x] AWS Newsは書面許諾または別途適用されるライセンスを確認するまで無効を維持。
- [x] 実Gemini `gemini-3.5-flash-lite` + minimal + Structured Outputの成功。
- [x] 実GCSへのNote/TSV/pending/receipt/report保存。
- [x] workflow_dispatchから実行成功。
- [x] PR #83適用後のcompact Noteを実GCSへ保存。
- [x] 初回runで作成した旧形式Note/receipt 1件を、indexとの整合性を保ってcompact形式へ移行。
- [x] 同一記事の実環境再実行でLLMを呼ばないこと。
- [x] 07:17 JSTスケジュールによる日次実行成功（GitHub側の開始遅延あり）。
- [x] Note品質資料と入力上限による制約を提示し、ユーザーがPR #90をmergeして受入継続を指示。
- [x] `max_calls_per_run`を30へ戻し、workflow_dispatchで30件の処理・保存と収集後auditに成功。
- [x] 上限30でscheduled runが成功し、report / usage / pending / auditを照合。

全項目を確認し、2026-10-03にPhase 1の本番受入完了と判定しました。Phase 2へ進みます。

## 上限30件での最終受入手順

1. [Note品質](acceptance-note-quality-2026-10-01.md)と[利用条件](source-usage-review-2026-10-01.md)の
   ユーザー最終確認後、上限30件のPRをmainへmergeする。確認したmerge commitを記録する。
2. 次回07:17 JSTのrunを待ち、Actionsのeventが `schedule`、headが上限30件を含むcommit、
   workflow結論が `success` であることを確認する。手動runだけではこの項目を完了にしない。
3. Collectの `run_report` とGCSの対応する `runs/YYYY/MM/<run-id>.json` を照合する。
   `status: success`、failures空、`llm_calls <= 30`、`llm_failed: 0`、
   `llm_processed == llm_calls`、`saved == llm_processed + recovered` を確認する。
   新規記事が30件未満なら実件数を記録し、30件処理したという表現はしない。
4. `llm_http_attempts`、入力・出力・thinking tokens、`llm_usage_unavailable` を記録する。
   retryがある場合、HTTP通信回数は30を超えることがある。usage不明があれば費用確認を残す。
5. Audit saved stateの `status: success` とissues空を確認する。
   成功index増分が `saved` と一致し、auditのpending件数がreportの `pending_after` と一致することを確認する。
   pendingはfeedで増えるため、単純に108−30件になるとは限らない。
6. run URL、commit、処理/失敗/重複件数、usage、成功indexとpending、audit結果を本書へ追記する。
   全項目を確認してREADMEを受入完了へ更新する。

2026-10-02の手動run後の基準は成功index 36件、pending 78件です。以下のscheduled runと保存済みreportの照合を完了しました。

## 残余制約

- API応答後・receipt永続化前の強制終了、および通信timeoutでは厳密なexactly-once課金は保証不可。
- 30件はrun単位。手動再実行を含む日次hard capではない。
- 全HTML変換のため、本文外の可視広告・navigation更新によるcontent hash変更があり得る。
- bucket設定と通常書込み時のGCS generation preconditionは実GCPで成功。競合発生時の停止動作は実環境未検証。
- Obsidianへの正式同期はPhase 2。現状はGCSにObsidian互換Markdownを保存するところまで。
- Google Researchのbylineのみの記事では著者metadataを抽出できず、著者は取得なしとして保存。
