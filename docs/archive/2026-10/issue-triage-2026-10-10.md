# Issue照合・Close・残件計画（2026-10-10）

ユーザーの「Issueを照会し、実装済みはClose、未実装は実装計画を立てる」という指示に従って整理しました。
基点mainは`e0dae2b0c0f26a7a88b68130bcf3b92c7390796a`です。

## 照合と操作結果

GitHubの全12 Issueを取得し、Open 4件の本文/議論、現在のコード、実装PR、受入記録と照合しました。
2026-10-10 21:51 JSTに、既存Issue本文の競合更新がないことを確認して更新しました。
コメントは追加せず、本文に根拠/計画を記録しました。

| Issue | 操作 | 根拠と限界 |
|---|---|---|
| [#127](https://github.com/Ningensei848/kaname/issues/127) | completedとしてClose | 画像候補・選択・配置・字数との分離・公開/Web検査はPR #128/#131で実装済み。画像入り実Noteの本番受入は別 |
| [#129](https://github.com/Ningensei848/kaname/issues/129) | 回収済みの障害通知としてClose | 失敗usage回収・台帳complete・audit/費用確認完了。原因とBatch成功保存は#94をOpenで追跡。重複通知markerを保持 |
| [#94](https://github.com/Ningensei848/kaname/issues/94) | Openを維持、本文/計画更新 | 旧最大1件提出・失敗回収・preflight readyは完了だが、成功保存/再実行の実受入は未完了。古い未承認/未実施記載を現在の証拠へ更新 |
| [#116](https://github.com/Ningensei848/kaname/issues/116) | Openを維持、待機条件/照合計画更新 | 推計・usage復旧は実装済み。確定請求明細がなく実照合は未完了 |
| #108〜#115 | 既存Closed 8件を維持 | 完了済みT0/O1/R1〜R5/O2を再実装・再オープンしない |

整理後はOpen 2件、Closed 10件です。#129のCloseをschema逸脱の修正やBatch成功保存の受入とは扱いません。
#127のCloseを画像入り実Noteの本番受入と混同しません。

## コードと検証の証拠

- [画像実装](article-images-2026-10-10.md)、[実Batchと失敗回収](batch-acceptance-2026-10-10.md)、[責務整理の本番受入](domain-refactoring-production-2026-10-10.md)を照合。
- 最新main CIは全Python382件と画像付きfixture/固定公開124件のQuartz・Chromium受入が成功済み。
- 今回の対象回帰は`test_images`、`test_batch_sdk`、`test_batch_diagnostics`、`test_source_health`、`test_operations`、`test_remote_publication`の**59件成功**。
- `source_health.py`、CLI入口、source別計数、時刻順・旧runのnull・読取り専用回帰を確認。実装済み機能を次の実装としていた文書を修正。
- 未実装の代表corpus、HTTP取得/変換の並列化、alias/graph評価・解決はコードとバックログを照合し、[次の作業](../../next-work.md)へ具体的な順序・対象・完了条件を記録。
- Batchの切分けは[公式Batch API](https://ai.google.dev/gemini-api/docs/batch-api)と[構造化出力](https://ai.google.dev/gemini-api/docs/structured-output)を照合資料にした。既存の送信回帰が正しいことから、schema不送信や特定schema機能の非対応を未確認の原因として断定しない。

本整理では新規の有料処理、Gemini操作、GCS読取り/書込み、workflow起動、Pages更新、新機能実装を行っていません。
本番受入に関する以前の一度限りの提出承認を、新規提出へ流用しません。
未追跡のHANDOFF.mdは保持しました。
