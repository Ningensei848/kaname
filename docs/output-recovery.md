# 出力打切り1件の限定復旧

2026-10-13 JST、Issue #178の失敗対象1件を復旧・保存・公開し、追加生成0の再実行まで受入完了、IssueをCloseしました。通常日次でDeepMind29件は保存され、1件は`MAX_TOKENS`/`json_invalid`で拒否されました。失敗した返却本文は保存していないため、長文化・反復などの具体的な生成内容までは断定しません。

通常の出力上限2,048 tokens・全source合計30件・入力20,000文字・minimal・厳格schemaは維持します。プロンプトへ不要な改行/反復を避ける指示と、要約以外の項目の簡潔さの目安を追加します。過去のNoteや受入モデルの制約は変更しません。

復旧時だけ`--max-output-tokens`で追加の出力余地を指定できます。`run`/standard・明示`--max-calls 1`・正の`--max-cost-usd`を必須とし、Batch/dry-run/診断/公開専用との混在を拒否します。CLIはclient生成前、WorkflowはGCP認証前に不適合入力を拒否します。未完JSONを閉じたり、文字列を変換して受入する処理や自動再生成は追加しません。

```bash
python -m techkb run --llm-mode standard --max-calls 1 \
  --max-cost-usd 0.05 --max-output-tokens 4096
```

Daily Actionsの手動入力も`collection_mode=standard`、`max_calls=1`、`max_cost_usd=0.05`、`max_output_tokens=4096`を使います。通常scheduleでは未指定で2,048のままです。この明示復旧ではHTTP retryも0とし、論理生成/HTTP試行とも最大1です。通常設定のHTTP retryは3のままです。費用予約は指定した出力上限・thinkingの余裕・1回のHTTP試行を含み、不明usageや生成拒否で後続を止めます。金額は実usageと元価格から計上し、上限値を消費額と扱いません。

Googleの[公開モデル定義](https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash-lite)では出力上限65,536 tokensに対応します。[Structured outputs](https://ai.google.dev/gemini-api/docs/generate-content/structured-output?hl=en)のschema対応subsetは制限があるため、この修正では新しいschemaフィールドや受入型を追加しません。

## 検証・受入

- [x] 実GCSで失敗対象が先頭の未知pendingであることを確認。index437/public155/pending127、既存USD 1承認の残額USD 0.7094916。
- [x] 関連107件・actionlint成功。通常上限不変、1件/cap条件、拒否時の無再生成とusage保持、2,048超の実測usage計上、残pending保持、既存Batch schemaとモードの境界を確認。
- [x] 全Python720件が成功。
- [x] [PR #182](https://github.com/Ningensei848/kaname/pull/182)と[main CI](https://github.com/Ningensei848/kaname/actions/runs/38362879732)成功・取込済み。
- [x] [限定復旧run](https://github.com/Ningensei848/kaname/actions/runs/38363473427)で同じ失敗対象を1論理生成/1HTTP試行で保存。input1,456/output514/thinking0、推計USD 0.0017218、不明usage0。index438/public156/pending126、元437行と他候補を保持し、receipt/Note/index・監査/日次/月次費用が一致。
- [x] 既存944オブジェクトの世代/CRCを保持（月次indexとpendingだけ更新）。GCSの最新156 Noteと公開bytes一致、旧155件不変、差分Release変更1件/削除0/depth2、1,377検索リンク・復旧Noteの実ページと配信版が一致。
- [x] [追加生成0の再実行](https://github.com/Ningensei848/kaname/actions/runs/38364553083)も全工程success。本文HTTP/生成/保存/課金0、既存949オブジェクト世代/CRC・成功index/Note/receipt/元usage/日次月次費用不変。pendingは126件の同じbytesを書き直し、世代だけ更新。
- [x] 3 Release/6 assetsのID/size/digest・公開commit/dataset/artifact・実配信版不変。#178をClose。Open Issueは確定明細待ち#116だけ。

[実受入の計数・版・費用・所要時間](archive/2026-10/output-recovery-acceptance-2026-10-13.json)を保存しました。限定復旧は全体7分5秒（収集34秒/監査37秒/export9秒）、生成0の再実行は6分51秒（収集28秒/監査39秒/export9秒）です。後者は公開156件・Release入力で、以前の126件/Git入力の5分51秒と同条件の比較ではありません。

日次の保留は126件です。DeepMindは69件保留・failing/streak2を維持します。1件の復旧成功だけでsource全体をhealthyにしたり、他の保留を消しません。今回の有料復旧は最大USD 0.05の推計capで一度だけ提出し、既存USD 1承認の残額はUSD 0.7077698です。実返却は514 tokensであり、4,096へのoverrideが成功の必要条件だったとは断定しません。今後の出力打切りを完全に防ぐ保証もありません。
