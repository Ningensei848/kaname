# R2: standard処理と共通receipt生成の抽出

Issue #111。基点mainは`a783aa2efd7adfe28b765051360a8eb132857b91`。
R1（#110 / PR #118）は取込済み。O1（#109）は自然なscheduleと全118件のGit/HTTPS照合で受入済み。
O1の証拠と現行受入文書は別の[PR #119](https://github.com/Ningensei848/kaname/pull/119)へ保存した。

## 変更と維持する契約

- 内部モジュール`_standard.py`へ、1回のstandard API呼出しとusage予約/保存を抽出した。
  呼出し予約失敗時のcount巻戻し、API失敗時にもusageを保存するfinally、元の例外型を維持する。
  requestの現在stageをpipelineへ戻し、usage保存失敗を`usage_save`として報告して追加有料処理を停止する。
- 内部モジュール`_receipts.py`へNote・index row・receiptの純粋な生成を抽出した。
  既存composeを使い、standard/Batchで同じschema・key順序・Note bytesを生成する。
  Batchの全文word count、提出時のmodel/打切り上限、後から付与するstable billing run IDを保持する。
- receipt/Note/indexの保存処理と中断時の復旧は移動しない。
  standardはusage予約→API→usage保存→receipt→Note→indexを維持する。
  Batchはoutcomes保存→元課金report→receipt→Note/index→item完了の順序を維持する。
- 既存import、CLI、GCS object path、Note ID、公開内容、依存lock、workflow、認証・権限に変更はない。
  実Batchの追加提出は行っていない。#94の実受入とは独立したoffline検証である。

## ローカル検証

Python 3.12.13、既存固定依存、実Chromium。通常sandbox起動制約が続くため、
承認されたexec_command経路でローカル実行した。

| 時点 | 検証 | 結果 |
|---|---|---|
| ソース変更前 | pipeline / usage_recovery / batch / batch_sdk / batch_diagnostics | 60 passed（6.41s） |
| 不足する契約検査の追加後、ソース変更前 | 同じ対象suite | 63 passed（6.70s） |
| 抽出後 | 同じ対象suite | 63 passed（6.64s） |
| 抽出後 | 全Python回帰、実Chromiumを含む | 273 passed（37.94s） |
| 抽出後 | 基点mainと20個のofflineケースの比較 | 全store bytes、全report bytes、書込み順序、API/submit回数が一致 |

追加した検査は、打切り有無のstandard/BatchのNote bytes・row/schema一致、
Batch提出後に設定が変わっても元model/入力上限を維持すること、全文word countとbilling参照、
有料呼出しをusage保存が挟む順序を対象とする。
既存usage保存障害テストも2候補へ拡張し、追加API 0、receipt 0、元例外型とstageを確認した。

20ケースの比較は標準成功、dry-run、打切り、schema/API失敗、raw/usage予約/usage保存/receipt/Note/index/report障害と復旧、
Batch成功・打切り・pending・schema拒否・曖昧submit・重複/未知response key・Note保存復旧を含む。
日時とrun IDだけを同じ値へ固定し、テスト用MemoryStoreとFake SDKで元実装と抽出後を比較した。

`git diff --check`は成功。未管理`HANDOFF.md`のbytesは変更せず保持した。

CI成功とレビュー/取込の後にR3（#112）へ進む。
