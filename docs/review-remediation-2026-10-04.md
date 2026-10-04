# レビュー後の対処計画 — 2026-10-04

レビュー基点はmain `c8e98f87019a54bded7241931d2dc3d40661d564`。
実装基点`f7bbc28f240b94ebf5b85cc72981996b17b19e05`からは資料のみの差分です。
再開時のworking treeはuntracked `HANDOFF.md`のみで、既存ファイルを保全しています。
ユーザー指示により対処を再開しましたが、heartbeatのPAUSEDと既存日次workflowは変更していません。
全体レビューの確定指摘・未確認範囲は[レビュー報告](project-review-2026-10-04.md)を参照してください。

## 順序と完了条件

一つずつPRで対処します。実Vault未使用のため、まず失敗した実Batchの診断を進めます。
データ損失につながるVaultのP1はその次に直し、修正前の正式同期を行いません。
優先順位の判断が分かれる項目は利用状況を確認して決めます。

| 順序 | 対処 | 完了条件 | 現状 |
|---|---|---|---|
| 1 | F2: Batchの安全な診断と実失敗原因の特定 | 元例外を保持し、既存結果のfield/codeを確認して必要な最小修正を決める | 診断修正とGET専用検査を実装。125テスト成功。実GETは未実施 |
| 2 | F1/P1: Vault編集保護 | 最終確認後の編集・atomic rename・新規ファイル作成を失わない | 未修正。実Vault同期は待つ |
| 3 | F3: ブラウザredirectの通信制約 | 各resource/robots redirectを通信前に判定し、未許可hostへの要求0 | 未修正 |
| 4 | F4/F5: usage不明と中断時の費用復旧 | 既知値を保ったpartial表示。receipt後の中断でも欠落/二重計上0 | 未修正 |
| 5 | F6/F7: 失敗通知と資料 | 未検証sourceのstreakを維持。実装・保証・受入状態の説明を一致させる | 未修正。auditをIssue対象に含めるかは要確認 |
| 6 | Phase 2受入と成果の閲覧 | 成功BatchのNote/receipt/index/pending/audit/cost照合。認証済みの閲覧経路を確認 | 未受入。匿名GCSアクセスは許可しない |
| 7 | Phase 3 / Quartz等 | roadmapの項目に従い別途着手 | 未着手 |

## 今回の最初の対処

実台帳のoutcome.errorは`ValidationError`でした。billing/collection reportの`ValueError`は
Batch決済時に例外を作り直す実装による診断欠落です。課金記録は入力6,096・出力624・thinking 0で、
この変更はその履歴を修正せず保持します。
JSON/schema検証で失敗したことは確認できましたが、旧台帳は型名のみなので具体的なfield/codeは不明です。
後続standardの30件保存はBatch受入成功に含めません。

`RunReport.fail_recorded`を追加し、collection/billing双方で元の例外型を保持しました。
今後の失敗には処理段階、既知schema field名とPydantic code、text有無、finish reasonを追加します。
原文・生成文・値・未知field名・validation input・例外本文・秘密は記録しません。
diagnosticsのない旧outcomeからの復旧も維持します。

`batch-inspect`はcompleteを含む指定台帳の読取りに対応し、`--remote`ではそこに紐付いた既存jobをGETします。
記事取得・Batch create/list/bind・費用計上・Note保存・GCS書込みは行いません。
Actionsの`diagnostic_batch_id`分岐は既存Secretをjob内だけで使用し、通常収集・費用・Issue投稿をskipします。
詳細は[操作手順](phase2-operations.md#既存batchの読取り診断)を参照してください。

全125テストに成功。固定SDKのMockTransportでは、正常結果の保存/audit、ValidationErrorの診断、
繰返し決済の費用重複なし、新規提出1回を確認しました。
読取り専用CLIではcomplete台帳、待機job、未知/重複key、snapshot、引数拒否、closeも検証しています。
実GCSの台帳読取りは成功しましたが、実Gemini jobのGETはまだ実施していません。
別途レビュー用の[再現ケース](review-reproductions-2026-10-04.py)でF1/F3/F4/F5/F6の期待失敗を確認し、
F2の型保持ケースは成功しました。これらの未修正事項は正常系125テストではカバーされていません。

次の本番診断は取り込み済みcodeから既存jobをGETする方法です。新しいworkflow_dispatchの起動は
別途ユーザー指示を確認してから行います。結果を取得できなければその制約を記録し、再提出を診断手段にしません。
具体的なfield/codeに沿って修正した後、有料提出・結果保存を伴う本番受入の条件を決めます。
今回の修正だけで元の生成失敗を解消した、あるいはPhase 2を受入したとは判断しません。
