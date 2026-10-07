# R5: CLIの依存生成とworkflow準備の整理

Issue #114。基点mainは`81e7e3dbea050ef968063eacd78edc8e946e7a63`（R4 / PR #122取込後）。

## 変更と維持する契約

- 内部モジュール`_cli_arguments.py`へparserとコマンド横断の引数検証を抽出した。
  parser定義と横断検証の構文木は基点mainと同一。CLI名、引数、default、help、
  override上限、snapshot/applyの制約を保持する。
- CLI内の`_Dependencies`でstore・HTTP・記事取得adapter・Geminiの生成と所有を共通化した。
  各コマンドは必要な依存だけを要求する。通常snapshotと公開export専用snapshotの検証を
  混ぜず、dry-runの従来のsnapshot挙動も保持する。既存`techkb.cli`のclient importと
  テストの差替え入口を維持する。
- `batch-bind`は必要引数をclient生成前に検査し、GCSと既存BatchをGETするGeminiだけを使う。
  記事取得/変換clientやenrichment promptを要求しない。既存の予約照合とledger保存は
  `BatchManager.bind`のままで、新規Batch提出や記事生成を追加しない。
- JSON出力と終了判定を共通化し、コマンドごとのUnicode escapingとstatus判定を保持する。
  parserの終了2、実行失敗の終了1、例外本文を出さない診断、ExportErrorのcode出力を維持する。
- 記事取得adapterの生成失敗でも取得済みHTTP clientをcloseする。
  HTTP close失敗時もfinallyでGeminiをcloseし、元のclose例外は伝播する。
- 権限を指定しない二つのcomposite actionへ、固定Python環境の準備とWeb build環境の準備を移した。
  Checks、collect、publish、通知、Pages buildが必要な準備だけを呼ぶ。
  collectの条件付きbrowser installとPages deployの標準ライブラリ検証は従来のjob内に残る。

## ローカル検証

Python 3.12.13 / Node 24.15.0、既存固定依存、実Chromium。
通常sandbox起動制約のため、承認されたexec_command経路で実行した。

| 時点 | 検証 | 結果 |
|---|---|---|
| 変更前 | CLIを含む対象9 suite | 121 passed（13.90s） |
| 共通化直後 | 同じ既存suite | 121 passed（11.92s） |
| 最終差分 | 対象9 suite、追加した振舞いを含む | 167 passed |
| 最終差分 | 全Python回帰、実Chromiumと課金/保存/中断の障害注入を含む | 319 passed（35.25s） |
| 変更前/最終差分 | actionlint 1.7.12 | 成功 |
| 最終差分 | 全workflow/compositeのrun scriptのbash構文検査 | 成功 |
| 最終差分 | validate-config / git diff --check | 成功 |

actionlintは[公式release v1.7.12](https://github.com/rhysd/actionlint/releases/tag/v1.7.12)の
Linux amd64 archiveを`/tmp`へ取得し、公開SHA-256
`8aca8db96f1b94770f1b0d72b6dddcb1ebb8123cb3712530b08cc387b349a3d8`を照合した。
repoの依存やlockは変更していない。

全15コマンドの正常系は以下の既存/追加テストで確認した。

| コマンド | 正常系の確認 |
|---|---|
| run / dry-run | 既存のCLI E2E。real Fetcher/変換/検証とmock HTTP/SDKで実行 |
| validate-config / audit-run / cost-report / notify / batch-status / sync | 実収集fixtureのローカルsnapshot。不要clientの生成を禁止し、認証なしで成功 |
| audit-state | 既存のローカルsnapshot整合検査 |
| refresh-metadata | 既存のGeminiを生成しないmetadata refresh |
| raw-lifecycle | bucketだけを使うpreviewと明示apply。世代7の条件付き更新 |
| batch-bind | timeout後の予約を既存remote jobに照合。GET一回、close一回、新規提出0 |
| batch-inspect | 既存のoffline/remote GET限定、本文非公開、close検証 |
| export-notes / publish-notes | 既存のclient不要export / ローカルbare repositoryへの公開 |

追加46ケースで、全15コマンドの主要な不正引数がclient生成前に失敗することと、
各コマンドの実行失敗時に必要なclientだけが生成・解放されることを確認した。
さらに、収集失敗reportでrun/dry-runが終了1を返すこと、dry-runの保存0、
Batch予約不一致時の保存0、SDK例外の機密本文非表示、adapter生成失敗とclose失敗の解放、
parserの終了2を確認した。通信・課金・bucket変更はfixtureだけで代替した。

## Workflow境界の照合

基点mainと最終YAMLを比較し、準備stepを除くstep定義とworkflow/job定義が同一であることを確認した。
全run scriptをbash -nでも検査した。

- schedule、dispatch/call inputs、main限定、job permissions、needs/if、outputs、timeout、
  concurrencyとcancel設定、checkoutのcredential保持設定が同一。
- WIFのcollect境界、既存GCS権限、Git書込みのpublish境界、Pages build/deploy、
  Issue通知job、各stepのSecret/token envが同一。
- compositeにSecret/token参照はなく、browser/editableの固定入力だけで準備内容を選ぶ。
- non-force pushとremote bytes照合を行うwrapper/本体、deploy後の配信版検証stepは変更なし。
  既存のremote競合/roundtrip検証も全回帰で成功した。

## 固定公開版のartifact受入

- content commit: `e3ef457f3edab5b4ca90601c922cc3b415d288ab`、118 Notes。
- dataset digest: `22fe4c95ad6e3b25bcc24047ef6c9c4fb75eb30a1d730b1de2a3e0b2fa595898`。
- ローカルartifact digest: `35f3c0002ef891fb778a29b0ac8dd5d9d4ff65a9f41ea1009348df99354849f5`。
  R3/R4の同じ固定版と一致する。
- build_pages.py / check_pages.pyが成功。全元Markdown hash、検索、ローカルリンク、
  出典、版表示、375/768/1024/1440px、非公開pathの404、外部resource要求0を確認した。
- artifactはignoredの`web/.cache/r5-pages-artifact`へ保存した。

未管理`HANDOFF.md`のbytesを保持した。CI成功とレビュー/取込でR5を完了する。
O2 #115（実切戻し/復帰）、#94（実Batch）、O3 #116（invoice照合）は独立した運用受入として残る。
