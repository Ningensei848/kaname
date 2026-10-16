# 次の作業と優先順位

2026-10-16 JST。ユーザーの継続指示により、20項目すべての終了または使用可能量の終了まで作業を進める。
元の20項目の根拠/完了条件と、依存関係・検証済み進捗は[監査一覧](repository-audit.md#改善の依存関係と進捗)で管理する。

| 順序 | 作業と依存 |
|---|---|
| 1 | A01: ローカル基点/指示/一時物を調査し、private記録を保全して環境を確立 |
| 2 | A04/A05: Web契約のCI対象抜けを埋め、Docs/Actionsの静的検証を必須gateにする |
| 3 | A06/A07: 現行依存を再監査し、既知例外のversion/配置/経路を固定 |
| 4 | A12/A14 → A11/A13: identity/fixture依存を先に分離し、収集状態遷移とWeb検証を整理 |
| 5 | A08/A09 → A10/A19: 同一版のHTTP/bytes/工程/メモリを計測し、cache再利用と規模判断を行う |
| 6 | A15/A16: 新公開版のGraph評価と画像候補/選択の匿名指標を整える |
| 並行 | A03/A17/A18: source保留/実環境/総予算の条件を確認して受入。A20の旧branchは祖先・独自commitを保全して整理 |
| 外部入力待ち | A02: 確定期間の請求明細を元usage/価格/legacy/unknownと対応付ける。推計で代用しない |

## 継続作業の現在地

A01/A04〜A16/A18〜A20の整理・実装・評価はローカル検証まで完了。A06の既知advisory、A09の性能未立証、A10のcache未採用は、評価の結論として制約を保持する。
全Python835件・Web11件、実246記事の前後各3回の全Web受入、Release同一chain読取り比較、Graph再評価、実GCS規模計測、Windows一時NTFSの受入を実施した。

残る進行中作業は、専用Draft PR #194の新しいheadに対するCI、A03の通常30件/cap付き実行後のusage/source-health/公開照合、A02の確定明細、A17の利用者指定環境である。
整理Draft PR #193と改善Draft PR #194はいずれもmainへ未merge。元の監査基点を残し、進捗は[監査一覧の表](repository-audit.md#改善の依存関係と進捗)だけを更新する。

## 完了済み機能の扱い

標準収集/復旧、公開snapshot、Git/Release/Pages、通常schedule/切戻し、実Batch保存/公開/生成0再実行、画像対応、NS1、Source Health、corpus/並列化、旧R1〜R5、CI再利用、GCS16並列は受入済み。
古い「未完了」記述を理由に再実装しない。保証は[検証基準](verification.md)、当時のrun/commit/件数/費用は[archive索引](archive/README.md)を参照する。

<a id="ns1-google-search-fallback"></a>

NS1の動作は[検索リンク仕様](ns1-search-fallback.md)。Graphの正規化/同義語適用は別の改善候補である。
