# kaname 現行仕様

[ADR-0001](adr/0001-generated-content-module-and-pages.md)に基づき、LLM生成Noteを独立した公開リソースにします。
以下は採用した要求です。実装・検証済みの範囲は[検証・受入](verification.md)で区別します。

## 要求と責務

| 要求 | 仕様 |
|---|---|
| 日々変わるLLMリソース | kanameが収集・要約・履歴・配布版を管理する |
| 人力Vaultに組み込む | 公開NoteのGit repoをsubmoduleとして参照可能にする |
| Webで独立して参照する | 同じ公開Note snapshotからGitHub Pagesを作る |
| 本体Vaultの人力編集と公開判断 | 別repo側の責務。kanameは読取り・同期・公開を行わない |
| コミュニティプラグイン利用 | 利用側の選択。kanameは通常のGitとObsidianで読めるMarkdownを提供する |

## データの境界

| 領域 | 正本・更新主体 | 公開範囲 |
|---|---|---|
| 収集/復旧 | 非公開GCSの成功index、Note、receipt、pending、run/Batch記録。コレクタが更新 | 外部配布しない |
| 生成Note配布 | 本repoの`content`branchに確定したsnapshot。export処理が更新 | 有効な生成Note群を公開 |
| Web | 配布snapshotを指定してbuildした静的成果物 | GitHub Pagesで公開 |
| 人力Vault | 利用者が別repoで管理する内容とsubmoduleの参照commit | 利用者が別途判断。本セッションの対象外 |

コード・設定・文書は`main`、公開Noteとmanifestは`content`へ分けます。
repoの可視性とGCSの可視性は別です。本repoはPUBLICでもGCSはUBLA/PAPを維持します。
Pages buildは人力Vault、収集state、rootの文書archiveを入力にしません。

## 生成Note

compact NoteにはAI要約、重要ポイント、資料の位置づけ、検索語、出典と生成情報を含めます。
記事原文・raw HTML・認証情報は含めません。AI生成であることと、出典へのリンクを表示します。
入力を20,000文字で打ち切ったNoteは、提示された部分の要約であることを保持します。
旧形式で上限値を保存していない打切りNoteは、元bytesとflagを保持し、Webでは上限未記録と表示します。
schemaを満たさない生成結果は成功Noteにせず、公開snapshotにも入れません。
公開許容は全生成Noteに適用し、本文の不正・秘密の混入・取り下げ対象は検査失敗/明示除外として扱います。
品質とsourceの取扱いは[source方針](source-policy.md)に従います。

現行のGCS object名は変更しません。exportで安定したNote識別子を付け、
同じsourceとcanonical URLの更新は同じNote識別子の新しい版として配布します。
入力Markdownの`content_sha256`と、公開Note bytesのhashは別の意味を持ちます。
最新の生成版はGit上で追跡し、公開snapshot全体のdigestをmanifestに残します。

## 更新・参照・編集

既存日次収集の成功後に、GCSの成功状態を読み、完全な配布snapshotを作る工程を追加します。
変化がないsnapshotの再実行で新しい配布commitや再生成を増やしません。
配布候補は全件検証してから確定し、途中の書込みや失敗したbuildを最新版として扱いません。

Pagesは最新の成功公開版を参照します。利用側のsubmoduleは親repoが記録するcommitに固定され、
更新は利用側のGit操作または対応プラグインで行います。kanameは親repoの参照commitを自動変更しません。
同じsnapshotを指定した場合は、VaultとWebで同じNote bytes/hashを確認できることを保証対象にします。
Pagesの表示中のcommit/digestを確認でき、利用側も同じ版を取得できるようにします。

人力の注釈・構成・公開範囲は生成領域の外に保持します。
利用側の更新方法には、submodule内部の人手の変更があれば停止し、強制reset/cleanで消さないものを選びます。
第三者プラグインの動作確認は利用側の責務で、kanameの保証には含めません。
生成側の新しい公開版による置換と、互換syncが人のファイルを保護する動作は責務を分けます。

## 収集基盤との互換性

既存のstandard収集、CLI/パッケージ名`techkb`、設定、GCS保存形式、重複判定を維持します。
既定はGoogle Research/GitHub Blog、HTTP/RSS、standard、30件/run、minimalです。
本文抽出・ブラウザ・raw保存・Batch切替は明示設定とします。
成功TSVを通常の重複排除の正本にし、失敗hashを成功登録しません。
receiptで保存途中から復旧し、記事ごとにindexをcheckpointします。

export・Git配布・Pages buildは既存成功Noteを使い、記事再取得・追加LLM呼出し・GCS更新を行いません。
配布やWebの失敗は収集の成功状態を巻き戻しません。再試行は同じsnapshotを再利用します。
直接syncは互換機能として既存Note/候補を保持します。submodule更新の実装として流用しません。
詳細な現行操作は[操作手順](operations.md)、保証の限界は[設計補足](design-decisions.md)を参照してください。

## 対象外と未確定の実装詳細

人力Vaultのrepo作成・内容の取込み・公開・プラグイン設定、原文の再配布、モデル学習は対象外です。
DB/Vector DB/複数LLMへの移行を、この構成の前提にはしません。
PagesのSSGはQuartz 5.0.0と固定pluginでpreviewを実装し、fixtureで検証しています。
元Markdownは同じbytesで静的artifactに含めます。実Note117件のGit公開と同じ配布commitのWeb buildを受入済みです。
Pages deploy workflowは実装済みで、初回実deployの受入と日次公開の自動化は未完了です。[Pages手順](pages.md)を参照してください。
build・artifact・依存上の制約は[Web preview](web-preview.md)を参照してください。
公開運用の権限・初回配布・自動更新の具体的なworkflowは実装PRで示します。
初回Git配布は既存Noteの読取りだけで行います。GCS/Vault変更、権限変更、有料呼出し、
本番workflow_dispatch、Issue手動起動、automation再開は行いません。
