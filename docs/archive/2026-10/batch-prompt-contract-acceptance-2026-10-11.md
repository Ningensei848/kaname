# #94: 出力形式の明示後の限定Batch受入（2026-10-11）

ユーザーから「追加の操作を許可する」と個別承認を受領しました。
承認対象はPR #145のmain反映、最大1 job/1 requestを一度だけ提出、回収・成功保存/公開・
audit/cost・追加提出0での再実行です。以前の許可枠とは別の追加枠で、再拒否後の有料再提出は行いません。

## 対策候補と無課金検証

[PR #145](https://github.com/Ningensei848/kaname/pull/145)で`prompts/enrich.txt`に出力キーを列挙し、
日本語タイトルは`title_ja`、`images`は`image_id`と`after`を持つオブジェクト配列と明示しました。
schema/model/通常standard設定・入出力上限は維持します。
APIがschemaを逸脱した原因を確定した修正ではなく、自然言語でも形式を明示する改善候補です。

既存回帰59件、[PR CI](https://github.com/Ningensei848/kaname/actions/runs/38129468339)のPython全460件・
Web fixture/実公開content・既存checkすべてが成功しました。
main `613f1df04102902faa70bc19bfe50080705011f9`に取り込み、
[取込後CI](https://github.com/Ningensei848/kaname/actions/runs/38130196755)もPython/Web成功です。

## 提出前検査

[読取り専用preflight 38130202269](https://github.com/Ningensei848/kaname/actions/runs/38130202269)はsuccess。
2026-10-11 10:01:34 UTC（19:01:34 JST）にready、audit success・問題0、成功index行335、pending72。
active Batch・未計上Batch item・未完了standard usage・不明usageはいずれも0でした。
提出直前にmainの版と他のdaily実行がないことを再確認しました。

## 限定提出

[提出workflow 38130541246](https://github.com/Ningensei848/kaname/actions/runs/38130541246)を
上記mainから`collection_mode=batch, max_calls=1`で一度だけ起動しました。
有効sourceのpending/discovery順で最初の適格候補を使い、記事URLは固定していません。
モデルは`gemini-3.5-flash-lite`、thinking minimal、本文20,000文字、出力上限2,048 tokensです。
SDKはPOST自動再送を無効にし、曖昧な提出失敗でも同じ有料提出を繰り返しません。

読取り確認で新規台帳1件・inline request 1件・台帳submittedを確認しました。
[既存jobのGET診断 38130891879](https://github.com/Ningensei848/kaname/actions/runs/38130891879)を起動し、単一writer制御で提出runの監査/出力完了後に実行します。
提出runはcollection・audit・費用出力・Git/Pagesまでsuccessでした。
reportはbatch_submitted 1、standard呼出し/HTTP attempt 0、保存/復旧0、pending72です。
auditは成功index335・問題0。費用はこの時点で未計上Batch item 1によるpartialでした。

## GET診断と成功保存の判定

診断runはsuccessで、API状態JOB_STATE_SUCCEEDED・返却1件・STOP/textありでした。
厳格検証は`ValidationError`、`images: model_type`で拒否しました。
今回の診断にtitle_ja missing・未知fieldのextra_forbiddenはありませんが、
imagesの型不一致が残り、成功Noteの本番受入には至っていません。
有料再提出を停止し、schema緩和・返却内容の型変換で受理しません。
API側の逸脱理由は未確定で、#94はOpenを維持します。

## 追加提出0の失敗usage回収

[回収run 38131944963](https://github.com/Ningensei848/kaname/actions/runs/38131944963)を
collection_mode=batch・max_calls=0で起動しました。
reportはbatch_submitted/standard呼出し/HTTP attempt/保存/復旧0、batch_failed 1。
pending72を維持し、同じimages型不一致を記録しました。
workflowは拒否を正しくfailureとして保持し、audit/export/Git/Pagesはskip、費用処理と通常通知はsuccessです。

台帳complete・item done・適合receipt0、失敗したcontentのreceipt/成功indexがないことを読取り確認しました。
成功index行は335のままです。安定IDのBatch課金recordは1件で、usage欠損0。
入力3,514/output717/thinking0 tokens、保存済みBatch単価で**USD 0.00142335**の推計です。
約0.2円という対応は従来の円換算目安による推計で、確定請求・GCS/Actionsの費用とは区別します。
回収後costはsuccess、2026-10月USD 1.09491250、未計上Batch/未完了standard/不明usageは0です。
今回の通常通知は[Issue #146](https://github.com/Ningensei848/kaname/issues/146)に対応します。

## 追加提出0の再実行

[再実行38132255609](https://github.com/Ningensei848/kaname/actions/runs/38132255609)も
collection_mode=batch・max_calls=0で起動しました。回収後のNote/receipt世代・index bytes・台帳/課金bytesをbaselineにしています。
再実行の収集後に、Note/receipt世代・index bytes・台帳/課金bytesがbaselineから不変で、課金record1を照合しました。
再実行はcollection・audit・cost・export・Git・Pages build/deployまでsuccessでした。
reportはstandard call/HTTP attempt、Batch提出/保存/失敗/pending、保存/復旧、token合計がすべて0。
auditは問題0・成功index335・pending72です。
日次/月次costは回収時と完全一致し、10月USD 1.09491250、欠損/不明/未計上usage0を維持しました。
提出時からの10月推計増分が今回1件のUSD 0.00142335と一致することも照合しています。

Git/Pagesは試行前と同じ公開125件版`238ecc96e8b9cd7f39dbdaf9f9d9f3cb16fbfb40`を維持し、
dataset digestは`eb64e954c0781711ede03688622434505caccf7ab688619bbaefbfc593d745f4`です。
同じ公開版の再deploy成功を、今回のBatch成功保存と混同しません。

許可された追加1件の試行と後処理は完了です。P1/P3/P4と費用推定は完了していますが、
#94の適合応答の成功保存受入は未完了で、Openを維持します。
#146は拒否後のusage回収・追加提出0の再実行で後処理済みとし、原因は#94へ引き継ぎます。
#116の確定請求照合は明細待ち、#139/#140の既知運用失敗は別途対応です。
運用識別子・API resource名・応答原文・認証情報は公開記録へ転載しません。

## P4の本番時間観測

提出runは`processing.workers: 2`の本番実行です。Collectは10:03:29〜10:07:20 UTCの3分51秒、
auditは10:07:20〜10:12:28 UTCの5分8秒で成功しました。
Collectには記事取得以外のdiscovery・状態読取り・Batch提出も含みます。
workers: 1で同じ候補を処理した比較がないため、本番短縮率とは扱いません。
公開snapshotの再照合は並列fetch/convertの対象外です。

## 無課金の送信形式比較

固定SDKのMockTransportで、同じ厳格ArticleEnrichmentをresponse_json_schemaとresponse_schemaで送信しました。
外部API接続・新規生成・GCS更新は0です。
前者はresponseJsonSchemaに画像itemsの$refとadditionalProperties falseを維持して送信します。
後者はresponseSchemaで画像参照を展開しますが、送信上のadditionalProperties falseは維持されませんでした。
この差だけではAPI不適合の原因・解消を証明できないため、今回の本番送信形式は変更していません。
本番の受理条件であるPydantic厳格検証も維持しています。
