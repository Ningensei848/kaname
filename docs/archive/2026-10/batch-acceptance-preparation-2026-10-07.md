# #94: 実Batch受入の準備

> 追記: この準備時点の独立workflowは、実WIFでdaily/main限定条件に拒否された。
> [修正記録](batch-preflight-workflow-fix-2026-10-08.md)と[現行操作手順](../../operations.md#実batch受入の事前検査)を参照。
> 下記の独立workflow起動案は現在の操作手順として使わない。新規有料提出は引き続き未承認・未実施。

基点はR5取込後のmain `73281c78bfe314e64165eb7df632f29a05e87da6`。
R2 #111とR1〜R5は取込済み。実Batch受入は未完了で、新規有料提出の個別承認はまだ得ていない。
本記録の作成ではGemini呼出し、GCS書込み、新規提出、deployを行っていない。

## 既存結果と事前状態

既存jobの読取り診断で、必須`title_ja`の欠落と未知fieldによるschema拒否を確認済み。
これが保存失敗の直接原因で、生成側が逸脱した理由は未確認。
後続standard成功はBatch成功として扱わず、schema要件・履歴・元単価を維持する。

[2026-10-07の自然なschedule](https://github.com/Ningensei848/kaname/actions/runs/37557574613)
の収集reportでは未決済job 0・Batch提出/保存/失敗 0、費用reportでは未計上Batch item 0・
unknown usage 0・未完了standard usage 0だった。これはその実行時点の証拠で、提出直前の状態を保証しない。
ローカルADCは更新時に`RefreshError`となり、現在のGCS snapshotを取得できなかった。
認証情報やSecretの抽出、IAM変更は行わない。

このため既存WIFで実行する手動専用`batch-preflight.yml`を用意した。
mainだけで起動し、通常収集と同じ`techkb-gcs-single-writer`ロック内で検査する。
GCSのlist/readだけを渡し、audit・active ledger・未計上Batch・未完了standard usageを確認する。
active/未計上Batch、未完了standard usage、audit障害のいずれかがあれば`blocked`で終了コード1。
認証・解析失敗は例外型だけを出して終了コード1。unknown usageは件数を残し、照合済みと主張しない。
台帳ID・API resource名・原文・Note本文・object path・費用明細は出力しない。
Gemini client、記事fetcher、費用通知、export、Git更新、Pages、artifact uploadは生成・実行しない。
検査の`ready`は有料提出への承認でもBatch受入成功でもない。

## 提出案と費用

新規提出は**1 Batch job、最大1 inline request、一度だけ**。
既存の有効source（Google Research / GitHub Blog）について、現行Pipelineのpending/discovery順で
最初に重複・filter・active判定を通過した1候補を対象にする。個別の記事URLは固定しない。
対象がなければ提出0で停止し、再dispatchやsource変更で候補を作らない。
提出した候補のhash・台帳・課金IDは非公開で対応付ける。

設定は`gemini-3.5-flash-lite`、thinking `minimal`、Structured Output、本文20,000文字、
出力上限2,048 tokens。本文の文字数と、prompt/schema/metadataを含む入力token数は別である。
固定単価は入力USD 0.15 / 1M、出力（thinkingを含む）USD 1.25 / 1M。
[公式価格](https://ai.google.dev/gemini-api/docs/pricing)を2026-10-07に確認した。
[公式thinking説明](https://ai.google.dev/gemini-api/docs/thinking)では
`max_output_tokens`はthinkingと出力の合計に適用される。

推計式は `(input × 0.15 + (output + thinking) × 1.25) / 1,000,000`。
入力10,000 tokens・出力/thinking合計2,048なら **USD 0.00406**、
入力20,000 tokens・同じ出力なら **USD 0.00556**。
これは入力token数を仮定したシナリオ推計で、実候補の計測値や金額hard capではない。
無料枠は織り込まず、回収したusageと元単価から実際の推計を記録する。請求明細照合はO3 #116。
GCS/GitHub基盤の費用はこのGemini推計に含めない。

## 承認後の具体的な操作

1. 準備PRのCI成功・main取込後に、`batch-preflight.yml`をmainから手動実行する。
   最新の件数とaudit結果を確認する。blocked/failedなら提出せず原因を調べる。
   有料提出の個別承認を得てから次へ進む。間に通常runが入った場合は事前検査をやり直す。
2. 通常scheduleと重ならない時間帯に、既存`daily.yml`をmainから
   `collection_mode=batch, max_calls=1`で**一度だけ**dispatchする。
   `llm_calls=0, batch_submitted=1`と予約→API→job名保存を照合する。
   API作成timeoutなどで結果が曖昧なら予約を維持し、追加提出せず既存jobの照合へ移る。
3. 保存済み台帳のjobを既存の`diagnostic_batch_id`経路でGETする。
   非終端状態は待機とする。[公式Batch API](https://ai.google.dev/gemini-api/docs/batch-api)の
   完了目標は24時間で、完了保証ではない。新しい定期実行やheartbeatは追加しない。
4. 終端成功・schema検証成功を確認後、既存`daily.yml`を
   `collection_mode=batch, max_calls=0`で回収する。標準呼出し/新規提出とも0を確認する。
   この操作はGETだけではなく、receipt復旧、Batch結果・usage report・Note/index/pending保存、
   feed/記事取得、費用/通知、audit/export/Git/Pagesの通常処理を伴う。
   承認範囲にはこの保存・公開と次項の再実行を明示的に含める。
5. 同じ上限0で再実行し、`batch_submitted=0, batch_saved=0, saved=0, recovered=0`を確認する。
   元Note bytes・index行・receipt・課金run ID/usage/推計額が変わらず、追加計上もないことを照合する。
   feed発見/pendingやゼロ課金の収集reportの更新はあり得る。全GCS bytes不変とは判定しない。

既存scheduleもBatchを回収し得る。手動回収前に自然なrunで保存された場合は、
そのrunと台帳の対応を確認し、二度目の保存を要求しない。
他の記事のstandard保存をこのBatchの保存と取り違えない。

## 保存と費用の照合条件

- ledgerのoutcome receipt、`state/receipts`、実NoteのUTF-8 bytesが一致する。
- indexのcontent/raw hash、model、tokens、打切り情報がreceipt行と一致し、成功行は1行だけ。
- compact NoteにBatchの元記事word countが保持され、原文を含まない。
- receiptの`usage_run_id`がledgerの安定した`billing_run_id`と一致する。
- 対応reportは`record_kind=batch_usage`で、model/mode、元単価、入力/出力/thinkingがoutcomeと一致する。
  提出runと回収runを同じusageの追加計上に使わない。partial/unknownは正直に残す。
- audit成功、対象pending除去、再実行で対象保存0・提出0・課金増分0を確認する。
- 保存障害は追加有料処理0でreceiptから復旧する。障害を意図的に本番へ注入しない。
  API/schema失敗は安全な診断を記録して停止し、schema緩和・自動再生成・再提出を行わない。

公開Issue/archiveには件数と判定のみを残し、運用識別子・原文・認証情報・課金明細は転載しない。
成功保存と再実行まで確認してから#94を閉じる。

## 検証

- 変更前のBatch/SDK/diagnostics/inspect/usage recovery/operations: **62 passed**。
- read-only検査の追加後: 同じ回帰 + 新規7ケース、**69 passed**。
  未決済/未計上、失敗済みBatch、孤立receipt、書込み禁止、情報非公開、例外とclient解放を確認した。
- 全Python回帰: **326 passed**（35.84s）。actionlint 1.7.12と`git diff --check`成功。
  CI結果は準備PRで確認する。実WIF事前検査はmain取込後で、まだ未実施。
