# 公開基盤のリファクタリング計画

今回の標準経路（HTTP/standard収集→audit→Git配布→Pages）の実装と公開専用受入は完了しています。
通常scheduleの初回連続実行、履歴版への実切戻し、実Batchの成功保存は運用受入として別に確認します。
F3も通信前のhost検査へ修正済みです。以下を小さいPRで順に進めます。並列収集・source health・graph品質改善は機能追加であり、この計画とは分けます。

## 維持する契約

CLI名・引数、既存GCS object path/receipt/index、Note bytes・安定ID・dataset digest、content履歴とPages URLを維持します。
API前後のusage保存順序、receipt→Note→indexの復旧順序、non-force push、公開前の世代/bytes検査を維持します。
リファクタリングで追加のGemini呼出し、依存更新、IAM/Secret変更、本番stateの移行を行いません。

| 順番 | 対象と変更 | 完了条件 |
|---|---|---|
| 1 | `operations.py`の費用集計と通知を分離。usage journal読取り・reportとの統合・価格計算を独立した関数へ抽出 | 月跨ぎ、元価格、partial、report優先、二重計上防止、閉じたIssueの重複抑止テストが維持される。既存import/CLI出力は互換 |
| 2 | `pipeline.py`のstandard呼出し/usage保存とreceipt作成を抽出。Batchでも共通のNote/row作成処理を利用 | 中断・保存失敗の障害注入テストと既存Note bytesが一致。durabilityが失われた後の有料処理0、回収時の追加API0 |
| 3 | `publication.py`の公開Note検証、整合読取り、snapshotの原子的installを分離 | 旧compact形式を含む同一入力の全Note bytes/manifest/digest一致。不完全読取り・余計なfile・symlinkの拒否を維持 |
| 4 | `site.py`/`web`の版情報とartifact検査の重複を共通化。network検査と純粋な検証を分離 | 架空Noteと固定実contentの検索/リンク/画面幅検査、公開元Markdown hash一致、外部resource要求0が維持される |
| 5 | CLIの依存生成と終了コード処理を整理。workflowの同じ準備処理は権限境界を保てるものだけ共通化 | 全CLI回帰、actionlint、同じ公開版のローカルbuildが成功。WIF・Git書込み・Pages・Issueのjob権限を維持 |

最初はPR 1だけを実施し、差分が小さくレビューできる単位で進めます。全体を書き直すPRや、改名だけの大規模変更は行いません。
テストは実装の形ではなく既存の入出力・副作用・復旧を判定し、抽出先をなぞるだけのテストは追加しません。

## 実施・検証の手順

1. 各PRの対象モジュールと既存の契約テストを列挙し、変更前の結果を記録する。
2. 処理の順序を変えずに抽出し、既存の公開importには互換入口を残す。
3. 対象テストと必要な全体回帰を実行。公開コードを変更するPRでは固定contentのartifact受入も行う。
4. CI成功後に取り込み。追加の実deployは公開挙動に変更がある場合に限る。

## 先に確認する運用事項

- 次の通常scheduleで収集・usage保存・audit・Git・Pagesが連続成功すること。失敗時はstageの原因を修正してから次のPRへ進む。
- 実Batch受入には追加有料提出の計画が必要。今回のリファクタリングで自動実行しない。
- invoice照合、利用者Vault/NTFS、実切戻しはそれぞれ独立した受入として扱う。


## タスク一覧と実施順

| ID | Issue | 開始条件 |
|---|---|---|
| T0 | #108 | なし |
| O1 | #109 | #108 |
| R1 | #110 | #108 |
| R2 | #111 | #110、#109 |
| R3 | #112 | #111 |
| R4 | #113 | #112 |
| R5 | #114 | #113 |
| O2 | #115 | #109、個別実行承認 |
| O3 | #116 | #109、確定請求明細 |
| Batch受入 | #94 | #111、新規提出の個別承認 |

実装順: #110 → #111 → #112 → #113 → #114。最初の実装はR1のみ。T0のローカル検証完了をR1着手の前提とする。O1 #109 成功をR2着手の条件とする。

O1はR1の準備と並行可。O2/#94/O3は別々に受入判定する。

## デスクトップ引継ぎの状態（2026-10-06）

計画の9件の新規Issueを登録し、Batch受入は既存#94を更新しました。Issueは完了条件と依存関係を持ちますが、作成だけで実装・受入済みとは扱いません。

T0はローカル実行経路の問題により未完了です。ローカルのHEAD・作業差分・AGENTS.md・固定依存のテストは未確認です。GitHubの最新mainとChecks成功は確認済みですが、ローカル検証の代用にはしません。現時点でR1〜R5の実装は開始していません。

- 通常scheduleは既存の自然な実行を確認し、新しいautomationや停止済みheartbeatの再開は行いません。
- O2は両版のローカルbuildを済ませ、切戻し先・復帰先・期待digestを固定してから個別承認を得ます。
- #94の追加提出は最大1件の具体的な手順と費用見積を準備してから個別承認を得ます。
- 利用者Vault/Windows・NTFSとbrowser source実受入は対象指定後の後続です。並列収集・source health・回帰corpus・graph品質は既存バックログに残します。

実行経路の確認と登録したIssueは[引継ぎ記録](archive/2026-10/refactoring-handoff-2026-10-06.md)にあります。
