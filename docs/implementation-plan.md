# 次工程の実装計画

[ADR-0001](adr/0001-generated-content-module-and-pages.md)に基づき、共通の公開生成NoteをGitとPagesで提供します。
人力Vaultのrepo・公開・プラグインは別工程です。ここで実装するのはkanameの配布側だけです。
機能ごとにPRで確認し、実装・offline検証・初回公開・継続運用を区別します。

## 1. 共通exportと配布manifest

**次に着手する工程です。** GCSまたは同じ構造の読取りsnapshotから、成功Noteの公開snapshotを作ります。

- Note ID、最新版の選択、Note hash/dataset digest、manifest schemaを実装する。
- Note/index/receiptと読取り世代を照合し、Note群だけを独立stagingへ出力する。
- 秘密・原文セクション・path traversal・symlink・余計な運用ファイルの混入を拒否する。
- 順序変更、同URLの更新、title/metadata更新、取り下げ、読取り途中の変化、途中失敗をfixtureで検証する。
- 同じ入力で同じbytes/digestになり、LLM呼出し・記事取得・GCS書込みが0であることを確認する。

成果物は再現可能なMarkdown snapshot、manifest、export検証結果です。
全成功Noteを基本とし、Web向けだけの選別や人力Vaultの取込みは追加しません。

## 2. 共通snapshotからWeb preview

Quartzを第一候補に、採用versionとplugin lockを固定し、synthetic Note群からpreviewを作ります。
一覧・source/category・検索・本文・出典・AI生成/打切り表示を実装します。
`/kaname/`配下の安定URL、内部リンク、未存在の概念、危険なHTML/埋込みを確認します。
manifest外・archive・state・receiptがbuild出力へ入らないことを検証します。
配布commit/digestを表示し、同じsnapshotを入力に再buildできます。

成果物は確認可能なWeb previewと静的build artifactです。この段階で本体Vaultは不要です。

## 3. Git配布とsubmodule互換性

`content`branchへ完全snapshotを追加する出版処理を実装します。
新しいsnapshotだけをcommitし、変更なし再実行ではcommitを増やしません。
履歴をforce pushで捨てず、同時publishや途中失敗を検出し、既存公開版を保持します。
一時親repoでsubmoduleの特定commit参照と明示更新を確認し、dirty/未管理ファイルを強制変更しません。
実際の人力Vaultの設定やコミュニティプラグインの導入は行いません。

成果物はGit配布方式・利用側へ渡す契約・再実行/競合検証です。

## 4. 初回公開とPages受入

工程1〜3の成果物を確認したうえで、既存成功Noteを追加生成なしでexportし、Git/Pagesへ配布します。
公開方針は「生成Note群は公開」で確定済みです。配布内容・workflow権限・出力境界を実装PRで示します。
GCSの読取りは現行ADC/WIFの範囲で行い、bucket匿名公開やGemini Secret抽出を前提にしません。
Pages設定、Git書込み、deploy権限は該当工程だけに限定します。
Web URL、配布commit/digest、Note件数、artifact検査、元Noteとのhash一致を記録します。
失敗したdeployの再実行や切戻しで再課金・GCS更新がないことを確認します。

成果物は実際に読めるGitのNoteとPages、および同じ配布版を示す受入証拠です。
人力Vaultへ組み込んだことを、このセッションの完了条件にしません。

## 5. 日次公開の自動化と残る品質・復旧課題

初回公開が受け入れられたら、収集の成功/audit後にexport・Git配布・Pages更新を接続します。
収集と公開のconcurrency・認証・失敗通知を分け、更新なし/収集失敗/公開失敗を識別します。
広い自動化の前に、現行standard経路のF4（usage部分欠落）、F5（中断後の費用復旧）、
F6（未検証sourceの失敗streak）を優先して修正・検証します。
F3（ブラウザredirectの通信前policy）はブラウザsourceの本番有効化前に対処します。
audit/export/deploy障害を通知対象に含める仕様も、この工程で定義します。

実Batchの成功保存/audit/cost受入は独立して継続します。必要な有料提出はその受入計画で扱います。
後続の並列化・source health・回帰corpus・graph品質は[バックログ](roadmap.md)として維持します。

## 工程をまたぐ完了条件

各PRは対象契約の検証結果と残余制約を示します。既存CLI・GCS形式・日次収集に回帰を作りません。
公開版が再現でき、WebとGitで同じNoteを参照できることを優先します。
コードがあるだけで実公開やBatch受入を完了扱いにせず、[検証・受入](verification.md)の状態を更新します。
日次の生ログ・件数推移は[履歴](archive/README.md)へ保存し、計画には完了済み作業の長い列挙を残しません。
