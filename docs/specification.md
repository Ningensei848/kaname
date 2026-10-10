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

## PythonとWebの境界

Pythonの`techkb`は収集・要約・非公開stateと、公開snapshot検証・Quartz入力Markdownの生成を担います。
受渡しは[公開・配布契約](publication.md)の`manifest.json`と`notes/<id>.md`です。
Quartz入力は実行ごとの専用stagingへ生成し、共有の`web/content/`を状態管理に使いません。
`web/kaname_web`はHTML後処理、成果物のseal/検証/配置、Pages準備、配信後検証を担います。
Web側の入口はnpmタスクで統一し、Python補助処理とChromiumを併用します。
依存脆弱性監査とリンク・画面・配信版検査を区別します。実行方法は[Web preview](web-preview.md)と[Pages](pages.md)を参照してください。

GCS障害時に新規保存や公開更新を成功扱いせず、既存の公開済みGit/Pagesを維持します。
固定公開Git版からの再buildにはGCS/Geminiを使いません。
元記事を再取得できても、生成Note・usage・Batch提出状態の復旧保証は必要です。
API前後のusage、receipt、世代/bytes検査、完了manifestを維持します。
復旧操作の正本は[運用手順](operations.md#gcs障害と公開の復旧)です。

## 生成Note

compact NoteにはAI要約、重要ポイント、資料の位置づけ、検索語、出典と生成情報を含めます。
記事原文・raw HTML・認証情報は含めません。AI生成であることと、出典へのリンクを表示します。
入力を20,000文字で打ち切ったNoteは、提示された部分の要約であることを保持します。
旧形式で上限値を保存していない打切りNoteは、元bytesとflagを保持し、Webでは上限未記録と表示します。
schemaを満たさない生成結果は成功Noteにせず、公開snapshotにも入れません。
新規Noteには記事本文の画像候補から選んだ図・写真を出典のHTTPS URLで直接表示できます。
候補ID・配置は要約本文と別に扱い、要約の300〜500字や元記事の語数へ画像URLを加えません。
画像自体の解析・ダウンロード・同梱・既存Noteの再生成は行いません。閲覧時に画像hostへ外部通信します。
公開検査はNoteに記録した画像と位置が一致するものだけを許可し、画像以外の外部resourceは許可しません。
公開許容は全生成Noteに適用し、本文の不正・秘密の混入・取り下げ対象は検査失敗/明示除外として扱います。
品質とsourceの取扱いは[source方針](source-policy.md)に従います。

現行のGCS object名は変更しません。exportで安定したNote識別子を付け、
同じsourceとcanonical URLの更新は同じNote識別子の新しい版として配布します。
入力Markdownの`content_sha256`と、公開Note bytesのhashは別の意味を持ちます。
最新の生成版はGit上で追跡し、公開snapshot全体のdigestをmanifestに残します。

## 更新・参照・編集

既存日次収集の成功後に、GCSの成功状態を読み、完全な配布snapshotを作ります。
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
Google Researchの本文入力と画像候補は`.blog-detail-wrapper`内の本文・図・キャプションを使い、
ページのナビゲーションや関連記事で20,000文字の入力枠を消費しません。selector不一致は失敗としてpendingへ残します。
成功TSVを通常の重複排除の正本にし、失敗hashを成功登録しません。
receiptで保存途中から復旧し、記事ごとにindexをcheckpointします。

Source Healthは非公開state/runを読むCLIのJSONとして提供します。
sourceの明示的完了を最終成功とstreak resetの根拠とし、未完了・dry-run・Batch課金runを区別します。
新しい収集runはsource別の発見・保存・復旧・Batch提出/保存件数も記録します。
旧runのsource別件数不明はnullで表示し、記事取得・LLM呼出し・状態更新・通知・公開は行いません。

export・Git配布・Pages buildは既存成功Noteを使い、記事再取得・追加LLM呼出し・GCS更新を行いません。
配布やWebの失敗は収集の成功状態を巻き戻しません。再試行は同じsnapshotを再利用します。
直接syncは互換機能として既存Note/候補を保持します。submodule更新の実装として流用しません。
詳細な現行操作は[操作手順](operations.md)、保証の限界は[設計補足](design-decisions.md)を参照してください。

## 対象外と実装状態

人力Vaultの管理・公開・プラグイン設定、原文の再配布、モデル学習は対象外です。
DB/Vector DB/複数LLMへの移行、画像ファイル保存、GCS停止中の代替保存を前提にしません。
Quartz 5.0.0と固定pluginを使い、元Markdownを同じbytesで成果物に含めます。
公開・通常schedule・切戻し/復帰は受入済みです。現在の状態と未受入範囲は[検証・受入](verification.md)を参照してください。
