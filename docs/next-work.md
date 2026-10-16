# 次の作業と優先順位

2026-10-16 JST。開発をいったん止め、追跡ファイル・Issue・Actionsを棚卸しした。
全20項目の根拠、開始条件、完了条件は[監査一覧](repository-audit.md#残課題改善候補)を正本とする。

| 順序 | 次に扱うもの | 開始条件 |
|---|---|---|
| 1 | A01 ローカルの未追跡/ignoredメモ・一時物の確認 | ローカル実行環境復旧。remote整理だけでは完了にできない |
| 継続運用 | A03 保留60件とsource別完了確認 | 通常日次の既定30件を維持し、source-healthを読む。追加生成や件数拡大は今回の整理に含めない |
| 明細待ち | A02 [#116 確定請求照合](https://github.com/Ningensei848/kaname/issues/116) | 確定期間の明細提供。元usage/価格・legacy/unknown・請求対象外を区別 |
| 開発再開時の先頭 | A04 CIのWeb対象選択、A05 文書/Actions静的検証、A06/A07 依存監査 | CI境界と既知例外の現状を確認してから最小変更 |
| 計測して判断 | A08/A09 Release重複通信と全体時間 | 同じ入力・生成数でのHTTP/bytes/工程計測。全件検証を維持 |
| 保守候補 | A11〜A14 責務/identity/検証の重複と完了planのfixture依存 | 個別差分でCLI/GCS/Note/課金/公開bytesと旧版互換を維持 |
| 対象や要件が決まった時 | A10/A15〜A20 cache/graph/画像指標/環境受入/総予算/規模/旧branch | 各項目の開始条件に従う。大規模移行や自動再生成を先行させない |

最新の[日次run](https://github.com/Ningensei848/kaname/actions/runs/38829280508)は全工程success、成功行528・公開246・保留60。
これはActionsログの観測値であり、今回GCSを直接再監査した結果ではない。日次successと各sourceの処理完了を区別する。
Open Issueは#116のみ、整理前のOpen PRは0件。日々変わる件数やrun履歴をこのページへ蓄積しない。

## 完了済み機能の扱い

標準収集/復旧、公開snapshot、Git/Release/Pages、通常schedule/切戻し、実Batch保存/公開/生成0再実行、画像対応、NS1、Source Health、corpus/並列化、旧R1〜R5、CI再利用、GCS16並列は受入済み。
古い「未完了」記述を理由に再実装しない。保証は[検証基準](verification.md)、当時のrun/commit/件数/費用は[archive索引](archive/README.md)を参照する。

<a id="ns1-google-search-fallback"></a>

NS1の動作は[検索リンク仕様](ns1-search-fallback.md)。Graphの正規化/同義語適用は別の改善候補である。
