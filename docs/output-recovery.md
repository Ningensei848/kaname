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

## 受入状態

元のDeepMind打切り1件を限定1論理生成/1HTTPで保存・公開し、追加生成0の再実行まで受入済み。#178はClosed。
通常出力2,048・30件/run・HTTP retry3の既定を維持する。将来の打切りを完全に防ぐ保証はない。
[整理前の全文・受入証拠](https://github.com/Ningensei848/kaname/blob/archive/pre-housekeeping-2026-10-16/docs/output-recovery.md)へ元usage/費用・固定公開版・保存不変の照合を保全した。
