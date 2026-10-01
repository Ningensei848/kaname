# 検証記録 — 2026-10-01

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
- [ ] Google Research / GitHub Blogの取得条件・利用規約をユーザーが最終確認。
- [x] AWS Newsは書面許諾または別途適用されるライセンスを確認するまで無効を維持。
- [x] 実Gemini `gemini-3.5-flash-lite` + minimal + Structured Outputの成功。
- [x] 実GCSへのNote/TSV/pending/receipt/report保存。
- [x] workflow_dispatchから実行成功。
- [x] PR #83適用後のcompact Noteを実GCSへ保存。
- [x] 初回runで作成した旧形式Note/receipt 1件を、indexとの整合性を保ってcompact形式へ移行。
- [x] 同一記事の実環境再実行でLLMを呼ばないこと。
- [x] 07:17 JSTスケジュールによる日次実行成功（GitHub側の開始遅延あり）。
- [ ] 生成Noteの日本語・要約・重要ポイント・検索キーワード・資料の位置づけ・出典情報・frontmatter品質をユーザーが確認。
- [ ] `max_calls_per_run`を30へ戻し、上限30でscheduled runが成功。

これらが完了するまで「日次運用可能なMVP受入完了」とは判定しません。
受入後はdocs/roadmap.mdのPhase 2へ着手してください。

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

2026-10-01時点の基準は成功index 6件、pending 108件です。上限30件のscheduled runは未実行です。

## 残余制約

- API応答後・receipt永続化前の強制終了、および通信timeoutでは厳密なexactly-once課金は保証不可。
- 30件はrun単位。手動再実行を含む日次hard capではない。
- 全HTML変換のため、本文外の可視広告・navigation更新によるcontent hash変更があり得る。
- bucket設定と通常書込み時のGCS generation preconditionは実GCPで成功。競合発生時の停止動作は実環境未検証。
- Obsidianへの正式同期はPhase 2。現状はGCSにObsidian互換Markdownを保存するところまで。
