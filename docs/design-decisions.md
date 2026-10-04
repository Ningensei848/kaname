# Phase 1設計補足

要件の処理順序・責務分離・ファイルベース構成を維持しつつ、障害時の整合性を以下で補います。

## 保存の途中失敗

GCSはNote・index・pendingの複数objectにまたがるtransactionを提供しません。
LLM成功後にNote保存だけが成功しindexが失敗すると、単にrun終端でTSVをuploadする実装では再課金が起こります。

本実装では次のチェックポイントを追加します。

1. RSSと既存pendingを統合した時点でpendingを先行保存。
2. LLM結果のvalidation・Note組立て後、`state/receipts/<content_hash>.json` にNoteとindex行を保存。
3. Noteを保存してから、その記事の月次indexを保存。
4. 成功後だけ既知hashをメモリに追加。
5. run終端でpendingを更新してreportを保存。
6. 次回は全indexとpending読込みの後、RSS取得前に未登録receiptを修復。

記事内のraw→content→LLM→Note→indexの順序は変えません。
月次TSVは記事ごとに原子的なobject置換を行います。単一writerとgeneration preconditionで競合時はfail closed。
index upload失敗後には追加のLLM呼出を行いません。
receiptは復旧用であり、通常の重複排除は成功TSVのhashで判断します。
成功済みreceiptは追加保管コストが生じます。MVPでは保持し、削除運用は明示的に実施してください。

## 厳密な「必ず一度だけ」の限界

**APIが応答を生成した直後からreceiptがGCSに永続化される前の停止・通信断**では、結果を失う可能性があります。
Gemini生成とGCS書込みを1つの原子transactionにできないため、自動再試行と厳密なexactly-once課金の両立はできません。
通信timeout時にはAPI側の処理完了有無も断定できません。ユーザー要件の通信retry例外もこの限界を伴います。
本実装は通常再実行・Note失敗・index失敗の再課金を防ぎますが、この極小区間まで完全保証とは表記しません。
このため受入は「正常終了後とreceipt保存済み障害後の再実行」を自動確認し、API応答消失は残余制約とします。

## 設定とSchema

目安の最小項目数は内容捏造を避けるため強制しません。最大数と文字列型、category enumを強制します。
空のtechnical insightsも有効とし、Schema errorで再生成させません。
APIのretryはSDK内部を1 attemptに固定し、アプリ側で通信障害だけを最大3retryします。
出力candidate tokensとthinking tokensを分離して記録します。

## HTTPと入力境界

robots.txtの404/410は指定なし、それ以外の拒否・障害は取得中止とします。
robots自体のredirectは最大5回、記事も最大5回。sourceの利用条件を自動解釈はしません。
Pythonによる事前DNS検査はprivateアドレスへの意図しないアクセスを減らす措置です。
DNS rebindingに対する完全なネットワーク隔離は提供しません。source設定は信頼する管理者のみ編集してください。
HTTPは環境proxyを自動継承しません（`trust_env=False`）。proxyが必須の環境は明示設定の拡張が必要です。

## 追加実装の境界

`pipeline.py` は手順の調停のみ、fetch/convert/dedupe/enrich/compose/storeは別moduleです。
`Store` protocolによりテストではMemoryStoreを注入し、GeminiはSDK clientを注入できます。
Phase 2のPlaywright・本文/フィルタ・Batch・同期・費用/通知・raw lifecycleを追加しました。
操作と実環境確認の区別は[Phase 2手順](phase2-operations.md)と[検証記録](verification.md)を参照。
Phase 3の並列化は未実装です。
日次/月次の厳格なUSD cap、failureのIssue送信も未実装です。

30記事/runの処理上限は通信retry回数や日次の手動run数を含むhard spend capではありません。
Cloud Billing Budgetも通常は通知であり自動停止を保証する仕組みではありません。
