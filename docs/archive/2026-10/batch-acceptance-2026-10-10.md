# #94: 実Batch受入の実行記録（2026-10-10）

画像対応PR #128を取り込んだmain `cff14e256dd0225f254ff0bf989c73567f0fefb6`を対象にしています。
ユーザーから、最大1 job・最大1 inline requestを一度だけ提出し、読取り診断、成功結果の
GCS保存・費用計上・Git/Pages公開、追加提出0での再実行まで個別承認を得ました。
必要な通常workflowの通知を含み、失敗・曖昧な結果では停止して再提出やschema緩和を行わない範囲です。

## 提出直前の検査

[読取り専用検査 run 38022068028](https://github.com/Ningensei848/kaname/actions/runs/38022068028)はsuccess。
2026-10-10 **12:56:54 JST**にready、audit success、障害0を確認しました。
成功index行306、pending29、未決済Batch台帳・未計上Batch item・未完了standard usage・
不確実なusageはすべて0です。collect/publish/pages/notify-publicationはskipしました。
提出時に他のdaily runが実行中でないこと、検査後にdaily runやmain変更がないことを再確認しました。

## 提出と費用

[提出 run 38022404206](https://github.com/Ningensei848/kaname/actions/runs/38022404206)を
mainから`collection_mode=batch, max_calls=1`で一度だけ起動しました。
有効sourceのpending/discovery順で最初の適格候補を対象にし、記事URLは固定していません。
モデルは`gemini-3.5-flash-lite`、thinking `minimal`、本文20,000文字、出力上限2,048 tokensです。
画像候補の説明は入力metadataに含み、画像bytesやURLをLLMへ送りません。

[公式価格](https://ai.google.dev/gemini-api/docs/pricing)を2026-10-10に再確認しました。
Batch単価は入力USD 0.15 / 1M、出力（thinkingを含む）USD 1.25 / 1Mで、記録済み設定と一致します。
入力10,000〜20,000 tokens・出力/thinking合計2,048という仮定の推計はUSD 0.00406〜0.00556。
本文文字数はprompt/schema/metadata込みの入力token上限ではなく、この推計は金額hard capではありません。
無料枠を織り込まず、GCS/GitHub基盤の費用と確定請求照合は別に扱います。

## 受入結果

提出runはcollect・audit・Git・Pagesまでsuccess。reportは`batch_submitted=1`、
`llm_calls=0`、`llm_http_attempts=0`、`saved=0`、`recovered=0`でした。
公開contentは提出前の`d39c2cacd087185be85c8c3564e4bd646d324cfc`から変わっていません。
成功index行306、pending73。費用reportは未計上Batch item 1によるpartialで、unknown usageは0でした。
発見によるpendingの増加を、成功保存と取り違えません。

[読取り診断 run 38023404910](https://github.com/Ningensei848/kaname/actions/runs/38023404910)は
GETに成功し、API状態`JOB_STATE_SUCCEEDED`、返却1件、STOP/textありを確認しました。
返却内容は`ValidationError`で拒否され、構造的なcodeは次のとおりです。

| field | code |
|---|---|
| `title_ja` | `missing` |
| `$`（未知field名は非公開） | `extra_forbidden` |
| `images` | `model_type` |

診断workflowのsuccessは読取り操作の成功です。本件の生成結果はschema不適合で、
#94の成功保存・復旧・二重計上防止の本番受入は未完了です。#127の画像入り実Note受入も未完了です。
失敗条件に従い、成功回収・再提出・schema緩和を行わず停止しました。

## 失敗後の回収

ユーザーから改めて、失敗結果・usageの回収と台帳完了化、必要な通常通知を個別承認されました。
[失敗回収 run 38046725127](https://github.com/Ningensei848/kaname/actions/runs/38046725127)を
mainから`collection_mode=batch, max_calls=0`で起動しました。
reportは`batch_submitted=0`、`llm_calls=0`、`llm_http_attempts=0`、`batch_failed=1`、
`batch_saved=0`、`saved=0`、`recovered=0`。不正な応答を保存せず、同じValidationErrorを記録しました。
pendingは重複等の処理で73から62へ変わっています。
費用reportはsuccess、未計上Batch item・unknown usage・未完了standard usageはすべて0です。
提出前後の費用reportにある推計増分は**USD 0.0017257**。確定請求実額ではありません。
Batch課金専用runにusageを記録するため、収集reportのtoken合計0を無料処理と解釈しません。

workflowは既知のschema拒否を失敗として保持してfailureとなり、Git公開とPagesはskipしました。
ユーザー承認の必要な通常通知が[Issue #129](https://github.com/Ningensei848/kaname/issues/129)を作成しました。
通知stageはcollectionで、この失敗回収runに対応します。

回収後の[読取り検査 run 38047134399](https://github.com/Ningensei848/kaname/actions/runs/38047134399)はsuccess。
**20:08:46 JST**にready、audit success・障害0、成功index行306・pending62を確認しました。
未決済Batch台帳・未計上Batch item・未完了standard usage・不確実なusageはいずれも0です。
[対象Batch診断 run 38047146590](https://github.com/Ningensei848/kaname/actions/runs/38047146590)もsuccessで、
当該台帳は`complete`、記録済みエラーは`ValidationError`、APIの返却結果は同じschema拒否です。
これらの検査は読取りだけを行い、新規提出・GCS更新・公開は行っていません。
失敗usageの回収は完了し、成功保存の本番受入は引き続き未完了です。

## ローカルの切分け

固定SDKのHTTP送信を`httpx.MockTransport`で捕捉し、本番promptの`systemInstruction`、
完全な`responseJsonSchema`（必須`title_ja`、画像配列とImageSelection定義）、JSON MIME、
出力上限・thinking設定、画像URLを含まない候補metadataが送信payloadに入ることを確認しました。
外部APIの挙動を再現した検証とは扱わず、API側がschemaを逸脱した理由は未確定です。

今回と同じ構造的なエラーを持つ合成応答を実SDK経由で返す回帰を追加しました。
保存0、診断から入力値を出さないこと、失敗usageの保持・安定IDによる費用重複防止を確認します。
Batch SDK/inspect/diagnostics/保存・復旧・画像の関連回帰は**59 passed**。
このローカル検証は追加課金・GCS更新を伴いません。

運用識別子・原文・認証情報・課金明細は公開記録へ転載しません。

#116は確定明細がないため今回は待機です。
