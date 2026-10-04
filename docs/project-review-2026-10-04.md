# 再開後の追記 — 2026-10-04

以下は開発停止中に作成した固定mainのレビュー報告を保存したものです。元の本文は当時の検証範囲を示します。
再開後にローカル実行環境を復旧し、HEADが`c8e98f87019a54bded7241931d2dc3d40661d564`、
working treeがuntracked `HANDOFF.md`のみであることを確認しました。ローカルADCでGCSの読取りも成功しました。
これにより、本文中の「ローカル状態/ADC未確認」「シェル起動不可」という制約は解消しています。
全体レビューの対象commit自体は変えていません。

実Batchの台帳はcomplete、outcome.errorはValidationError、receiptなし、入力6,096・出力624・thinking 0でした。
対応するbilling reportのValueErrorとの相違はF2と一致しました。具体的なvalidation field/codeは旧台帳に残らず、
実jobのGETもまだ行っていないため根本原因の詳細は未確定です。

`codex/batch-safe-diagnostics`ではF2の型保持・安全な診断と既存jobのGET専用検査を実装し、
実Chromiumを含む全125テストに成功しました。本番の新規実行・有料提出・GCS/Vault更新・権限変更・
PR merge・heartbeat再開は行っていません。Phase 2受入は未完了です。
実装の現在の状態と順序は[対処計画](review-remediation-2026-10-04.md)、
実台帳の読取り証拠は[検証記録](verification.md#再開後のbatch診断修正--2026-10-04)を参照してください。

再開後の修正working treeで[オフライン再現ケース](review-reproductions-2026-10-04.py)も実行しました。
F2の型保持はpass、未修正のF1/F3/F4/F5/F6は各期待値に対してfailとなり、次を再現しました。
本番API・実Vault・GCS書込みは使っていません。通知のaudit対象範囲は未確認仕様なので除外しました。

| 指摘 | 再現結果 |
|---|---|
| F1 | 最後のhash確認後の編集がremote updateで上書きされる |
| F3 | browserは拒否しても、未許可のoutside.exampleへHTTP要求が送信される |
| F4 | input countがNoneでもusage available=Trueになる |
| F5 | receiptにinput100が残る中断から再課金なしで回収しても費用が0になる |
| F6 | 未検証sourceの既存失敗streakが先行sourceの保存障害で消える |

この6ケースの実行結果は1 passed / 5 failed / 1 deselectedです。正常系125テスト成功とは別の、
未修正指摘を実証するための期待失敗テストであり、通常suiteに未修正のassertを統合していません。
本文で「実行待ち」としたケースのうち上記6件は、この追記をもって実行済みに更新します。

---

# kaname 全体レビュー — 2026-10-04

レビュー対象: Ningensei848/kaname
レビュー方式: GitHub上の固定commitの全体静的レビュー、既存Actionsログ照合。ファイル保存後に対象commit・指摘件数・参照行と記述を再照合した。
機能修正・本番受入実行は行っていない。

## 結論とレビューの限界

**Phase 1受入済みの記録は維持する。Phase 2は受入未完了。確定した実装・資料上の指摘は7件（P1: 1、P2: 5、P3: 1）。**

実Batch失敗は、Actionsログと分岐の照合により「結果key照合を通過した後、個別応答の検証またはNote組立てで失敗した」範囲まで絞れた。ただしprivate ledgerが読めず、**実際の失敗を引き起こしたJSON/schema/category等の根本原因は未確定**。後続standardの成功はBatch成功の証明に含めない。

各確定指摘はソース上の具体的な条件と制御フローに基づく。今回、新しいPython/Chromium再現テストは実行できていない。「再現済み」「103テストを今回再実行した」とは扱わない。既存CIの103 passedと、レビューで追加した実行待ちの再現ケースを区別する。

## 対象commit・作業ツリー・最新Actions

- 実装基点: `f7bbc28f240b94ebf5b85cc72981996b17b19e05`（PR #95）。
- 固定して読んだ最新main: **`c8e98f87019a54bded7241931d2dc3d40661d564`**（PR #96 merge）。
- GitHub compareでは基点からahead 2 / behind 0。変更はREADME、verification、roadmap、handoff-review、review-promptのみ。src/config/prompts/tests/lock/workflowsの実装は基点と同じ。
- レビュー末尾のbranch読取りでもmainは上記SHA。
- **ローカルHEAD、git status、tracked変更、untracked一覧は未確認。** シェル実行はzsh/bash/shおよび明示workdirでもプロセス生成時の「No such file or directory」で起動不可。Node実行もsandboxCwdのLinux file URIをローカルURIとして扱えず起動不可。
- ローカルADCの有効性も今回未確認。過去のADC再認証要求と、Actions WIF成功を分けて扱う。
- rootのHANDOFF.md、既存ローカル変更には触れていない。報告と再現ケースは/tmpの新規ファイルに保存した。checkoutの修正・削除・commitはしていない。
- GitHub上にはAGENTS.mdがなく、ローカルの未追跡AGENTS等は読めていない。そのためローカル設定・未commit実装をレビューしたという保証はない。

最新6件のActions一覧、関係jobのstep結果、最新Checks・Batch取り込み・後続日次のログを読取りで確認した。時刻はJST。

| run | head / event | 結果・確認内容 |
|---|---|---|
| [37166459485](https://github.com/Ningensei848/kaname/actions/runs/37166459485) | c8e98f8 / push | 最新main Checks success。10-04 09:56:55のログで103 passed、設定検証成功 |
| [37166347161](https://github.com/Ningensei848/kaname/actions/runs/37166347161) | 81f3435 / pull_request | 引継ぎPR Checks success（一覧確認） |
| [37165511894](https://github.com/Ningensei848/kaname/actions/runs/37165511894) | f7bbc28 / schedule | 日次standard success。30呼出/30保存、batch_saved=0。audit index126/pending48/issues0。101 passed, 1 skipped |
| [37164923005](https://github.com/Ningensei848/kaname/actions/runs/37164923005) | f7bbc28 / workflow_dispatch | Collect failure。WIF success、audit skipped、Batch保存0/失敗1。cost/notify step success |
| [37164369505](https://github.com/Ningensei848/kaname/actions/runs/37164369505) | f7bbc28 / workflow_dispatch | Batch提出run success（一覧と引継ぎ記録）。提出成功と結果保存成功を区別 |
| [37164366370](https://github.com/Ningensei848/kaname/actions/runs/37164366370) | f7bbc28 / push | 実装基点Checks success（一覧確認） |

最新main比較の根拠: [固定commit間の比較](https://github.com/Ningensei848/kaname/compare/f7bbc28f240b94ebf5b85cc72981996b17b19e05...c8e98f87019a54bded7241931d2dc3d40661d564)。
dailyの「1 skipped」はブラウザtest moduleのskipであり、full CIの103ケース通過と同等ではない。

## 最初に調べた実Batch失敗

### 既存ログで確認できたこと

取り込みrunのreport IDは `20261004T002631Z-3aff5c70`。
batch_failed=1、batch_saved=0、llm_calls=0、saved=0、pending78→79。
唯一のfailureはbatch_result/google-research/ValueError。state_or_recoveryのfailureはなかった。
同じjobでWIF stepと費用集計は成功しているため、この失敗をGCS認証失敗と説明する根拠はない。

cost出力はUTC 10-04の既知費用USD 0.0016944、uncertain_runs=0、pending_batch_items=0。
収集reportのstandard使用量は0であり、Batch使用量は別reportに計上する実装。
後続日次の費用はUTC 10-04 USD 0.0995463、10月USD 0.4013871、audit issues0。
これは設定価格による推計で、invoice照合ではない。

### コードから絞れる範囲

1. 未知/重複結果keyならbatch.py:108–109から外へ例外が出てstate_or_recoveryとして記録される。今回のreportと一致しない。
2. 今回はbatch.py:162–164の個別outcome error経路に到達している。
3. 元の例外はbatch.py:132–133で型名だけをledgerへ保存する。一方、収集とbilling双方のreportには新しく作ったValueErrorを渡す（F2）。
4. usage_available=falseならbilling reportのllm_usage_unavailableを増やし、costがpartialになる。uncertain_runs=0というログと現行コードを合わせると、この1件にはusage_metadataを持つresponseが存在したと推定できる。
5. したがって、欠落結果/responseなしを主因とする説明より、validate_responseまたはその後のcomposeまでの例外が整合的。ただし4は集計ログからの推論であり、ledger実読取りによる確定ではない。

**現時点でcategory違反・JSON不正・出力打切り・SDK変換不整合のいずれかを根本原因と断定しない。**
候補metadataからのNote組立て例外もledgerを確認するまで除外しない。

### 根本原因確定に追加で必要な証拠

読取り権限を持つ主体で、以下だけをprivateのまま確認する。権限拡張やAPIキー抽出は不要。

- `state/batches/20261004T001622Z-e22604f8.json` のstatus、model、categories、item status、outcome.error、usage_available、usage、receiptの有無、settled_at、billing_run_id。
- そのbilling_run_idに対応するrecord_kind=batch_usage report。件数、型、使用量、価格snapshotの一致。
- outcome.errorがValidationErrorなら、既存ledgerにはvalidationのfield/codeが残らないため、これだけではJSON不正/必須field欠落/長さ制約等をさらに区別できない。
- 既存job結果を読取りできる許可済み手段があれば、原文や値を出力せずfinish reason、text有無、validationのfield位置とcodeのみを確認する。既存job結果の読取り可否も今回は未確認。
- 同じcandidate/content hashが後続standardで保存されたかをindex/receiptのprivate照合で確認する。候補URL・原文を公開報告へ転記しない。

取り込みrunのActions artifacts一覧は空だった。private ledgerはGitHub artifactからも取得できていない。`batch-status`はcompleteを除外するので今回の完了失敗ledgerの確認に使えない。
`run --max-calls 0`は回収・取得・書込みを行うため読取り診断として実行しない。

## 優先度順の確定指摘

P1はデータ損失につながる問題、P2は特定条件での保証違反・運用機能の欠落、P3は資料の不整合。
以下の行番号は上記固定mainのソースに対応する。

### F1 — P1: Vaultの最終確認後の編集を無条件置換で消す

**対象:** [src/techkb/sync.py:91–96](https://github.com/Ningensei848/kaname/blob/c8e98f87019a54bded7241931d2dc3d40661d564/src/techkb/sync.py#L91)、同14–20。

**発生条件:** 管理対象Noteのremote更新、または新規作成を同期中に、最後のlocal hash/exists確認後からos.replaceまでの間にObsidian等が対象pathへ保存する。
.tempの書込みとfsyncもこの間に入る。.techkb-sync.lockは同じ同期CLI間だけの排他で、編集アプリは取得しない。

**影響:** 新しいローカル編集、または直前に作成された未管理ファイルをremote bytesで置換する。conflictsは増えず、manifestもremote hashになり、編集内容を復旧するコピーを残さない。
計画後の再hashは有効だが、置換に対する条件付き更新ではない。

**根拠:** current==baseline判定後、atomicが無条件os.replaceを行う。tests/test_sync.pyの計画中の編集ケースは最後のチェック前に編集し、この区間を検証していない。
添付のtest_edit_after_last_hash_check_is_not_lostはatomic呼出時に編集を注入する実行待ちケース。

**最小修正案:** 編集側と共有する確実な排他がない間は、既存Noteのremote更新を別の競合ファイルへ書き、対象Noteを自動置換しない保守的な動作にする。新規対象も排他的作成を使う。
単に「置換前にもう一度hash」するだけでは窓は残る。自動更新を維持するなら、対応OS/編集方式に応じた置換前提と損失を防ぐ回復設計を明示して実装する。

**必要な検証:** 最終確認後のin-place編集・編集アプリのatomic rename・新規ファイル作成を注入。変更内容が保持されること、競合通知、manifestの不更新、Linux/Windows双方の挙動を確認。
利用者Vault未指定という未受入項目とは別の実装問題。

### F2 — P2: Batch reportが元の例外型をValueErrorへ置き換え、診断を失う

**対象:** [src/techkb/batch.py:132–133](https://github.com/Ningensei848/kaname/blob/c8e98f87019a54bded7241931d2dc3d40661d564/src/techkb/batch.py#L132)、152、162–164。
reporting.py:48–51は渡された例外の型名だけを記録する。

**発生条件:** 個別結果のJSON/schema/category検証、Note組立てなどが失敗する。実例のbatch_result経路もここに該当。

**影響:** ValidationError等もreport上はValueErrorとなり、原因の位置やvalidation codeを失う。private ledgerを読む必要があるうえ、ledgerにも型しかなく、同じ型の原因は分からない。課金済み失敗の診断・再試行判断を妨げる。

**根拠:** outcome.errorには元型を保存するが、billingとcollectionのfail呼出はともにValueError()を新規生成して渡す。
既存SDK testはwireとresponse accessorを検証するだけで、実SDK応答をsettle→validation→compose→保存へ通していない。

**最小修正案:** reportに安全なerror_type/codeを渡せる経路を追加し、outcomeの元型を保持する。失敗位置、finish reason、text有無、Pydanticのfield位置/type等を値・input・例外本文抜きでcompact記録する。
元の応答全文やSDK例外本文をログへ出す修正は避ける。

**必要な検証:** malformed JSON、必須field欠落、category違反、空要点、打切り、responseなしを分ける。固定SDK＋MockTransportからsettle/receipt/audit/costまで通し、原文・秘密・validation inputが報告に混入しないことを確認。
この指摘は診断欠落を確定するもので、今回の生成失敗の根本原因を確定したものではない。

### F3 — P2: ブラウザresourceのredirect先を取得してから許可ドメインを検査する

**対象:** [src/techkb/browser_fetcher.py:43–46](https://github.com/Ningensei848/kaname/blob/c8e98f87019a54bded7241931d2dc3d40661d564/src/techkb/browser_fetcher.py#L43)、fetcher.py:96–112。

**発生条件:** 許可されたhostのscript/xhr/fetch等が、resource_domainsにない公開hostへHTTP redirectする。robots.txtのredirectも同様にHTTP層内で処理する。

**影響:** self.http.getがredirect先のrobotsとbodyまでGETした後に、browser側で拒否する。最終的にpage失敗となっても、未承認hostへの通信は既に発生している。queryを含むredirect先ならそこへ情報を送信してしまう。
private IP検査が通常機能する場合のprivateアクセスを断定する指摘ではない。公開hostのallowlistをすり抜ける問題。

**根拠:** browser側は入口requestと返却後の最終URLを検査。HTTPの各redirect hopにはbrowser allowlistが渡されていない。
既存ブラウザtestは直接private URLを要求するケースだけで、許可hostからのredirectを検証していない。

**最小修正案:** HTTP層に任意のdestination policyを渡し、各article/resource/robots redirectの次hopを通信前に検査する。通常HTTP/RSSの既存挙動とbrowser policyを区別する。

**必要な検証:** MockTransport＋実Chromiumでallowed→disallowed、allowed→disallowed→allowed、robots redirect、allowed CDN redirectを検証。
disallowed hostへのHTTP要求が0であることをassertする。DNS検査と接続のraceという既知制約とは別。

### F4 — P2: usage metadataの部分欠落を完全な実測値とみなす

**対象:** [src/techkb/gemini.py:60–62](https://github.com/Ningensei848/kaname/blob/c8e98f87019a54bded7241931d2dc3d40661d564/src/techkb/gemini.py#L60)、operations.py:50–57。
standardとBatchの両方がこの関数を利用する。

**発生条件:** usage_metadataはあるが、prompt_token_countまたはcandidates_token_countがNone。例えばinput不明、output20、thinking5。

**影響:** 不明なinputを0にしてavailable=Trueを返す。llm_usage_unavailableは増えず、costはsuccess/uncertain_runs=0とし、過小推計の可能性を表示しない。予算通知も既知の下限であることを示せない。

**根拠:** 欠落fieldにor 0を使い、metadata object全体の有無だけでTrueを返す。既存testはmetadata全欠落相当のunknown reportだけを検証。
添付ケースではoutput20を保ったままavailable=Falseを期待する。

**最小修正案:** 課金対象の必須countの存在/型/非負を検証し、欠落があれば既知countを維持してpartial扱いにする。
thoughts_token_count省略を仕様上0とみなせるかは固定SDK/モデルの契約を確認して別に決める。省略fieldをすべて機械的にunknownにする必要はない。

**必要な検証:** 完全、input欠落、output欠落、全欠落、明示0、thoughts省略、異常型/負値をstandard/batchとcostまで通す。
実際の今回のBatchにfield欠落があったことまでは確認していない。

### F5 — P2: standardのreceipt保存後の中断で費用が履歴から消える

**対象:** [src/techkb/pipeline.py:45–51](https://github.com/Ningensei848/kaname/blob/c8e98f87019a54bded7241931d2dc3d40661d564/src/techkb/pipeline.py#L45)、143–164、192–198、operations.py:34–62。

**発生条件:** standardの有料応答を受け、token付きreceipt（必要ならNote/indexも）を保存した後、run reportの保存前にrunnerが強制終了する。report保存だけ失敗しても同じ。次回はreceiptまたは成功hashから再課金せず復旧する。

**影響:** Note/indexの整合性は復旧する一方、旧呼出のusageはruns/に存在しない。復旧runのtotal_*は0で、cost_reportはreceipt/indexを参照しないため、使用量を漏らしてsuccessを返す。
known usageを復元できるチェックポイントがあるのに費用へ反映されない問題。API応答消失・receipt保存前のexactly-once不可という既知制約とは別。

**根拠:** receipt rowは入力/出力/thinking countを保持するが、回収は_saved/recoveredのみ増やし、billingを復旧しない。
Batchでは別billing reportを保存してからNoteを保存するが、standardには同等の復旧経路がない。
添付ケースはRunReport.finishで停止を模擬し、receiptのinput100に対して次runの費用が0になる条件を作る。

**最小修正案:** receiptに元のusage event ID/run ID、時刻、model、価格snapshotを保持し、元report未保存時に使用量を復旧できるようにする。
集計の識別子を共通化し、reportとreceiptを単純加算しない。成功済みreceiptの回収が二重計上を生まない設計にする。

**必要な検証:** receipt直後、Note直後、index直後、report書込み失敗で中断し、再課金0、使用量欠落0、費用重複0を確認。
月跨ぎ、価格変更、複数記事run、schema失敗usage、既存Phase 1 receiptとの互換性も確認。

### F6 — P2: 保存障害による打切りで未検証sourceの失敗streakをresetする

**対象:** [src/techkb/operations.py:85–93](https://github.com/Ningensei848/kaname/blob/c8e98f87019a54bded7241931d2dc3d40661d564/src/techkb/operations.py#L85)、pipeline.py:36、171–177。

**発生条件:** source Bに既存の連続記事失敗があり、次runでは先行するsource Aのraw/receipt/Note/index保存が失敗して処理をbreakする。Bの失敗記事を再検証しないが、report.source_idsにはBが初めから含まれる。
storage障害がAのsource failureだけに記録され、pending/reportの最終書込みは成功する場合。

**影響:** failedにcollectorがないため、Bは「今回failureなし」でstreak=0になる。Bの復旧を確認していないのに、必要なIssue通知を消す/遅らせる。
手順書の「collector全体の障害時に未検証sourceのstreakを勝手にresetしない」と一致しない。

**根拠:** source_idsはenabled一覧、完了一覧ではない。保存障害はsource.idを付けて記録しbreakする。通知側はstageや打切り情報を使わず、source_idsからcoveredを作る。
既存tests/test_operations.pyはcollectorの部分中断を扱わない。

**最小修正案:** collectorを止めるdurability失敗を全体障害として記録し、sourceの検証済み/未処理/失敗を分ける。未処理sourceのstreakは保持し、実際の復旧確認でresetする。
古いreportのsource_idsは完了を保証しないので、履歴互換の扱いも明示する。

**必要な検証:** A障害前にB完了、A障害後のB未処理、上限でB未処理、feedのみ成功、disabled source、全体state障害を区別。
通知incident key・closed Issue重複抑止が変わらないことをMockTransportで確認。

### F7 — P3: README/設計資料が現在の受入状態・実装と矛盾する

**対象:** [README.md:207](https://github.com/Ningensei848/kaname/blob/c8e98f87019a54bded7241931d2dc3d40661d564/README.md#L207)、[docs/design-decisions.md:35–36](https://github.com/Ningensei848/kaname/blob/c8e98f87019a54bded7241931d2dc3d40661d564/docs/design-decisions.md#L35)、同55。

**発生条件/影響:** 運用者が費用節/設計補足を受入判断に使うと、Phase 1 scheduled受入が未完了、failureのIssue送信が未実装と読める。現行冒頭、verification、daily.ymlと矛盾する。
また「最小項目数は強制しない」「technical insights」は、現行models.pyのkey_points/related_concepts min_length=2および現在のschemaにない項目名と一致しない。

**根拠:** 最新mainの上記行、models.py:7/11、既存本番受入記録、daily.yml:92–99の比較。

**最小修正案:** 古い状態記述を現在の受入済み/未受入に更新し、実装済み通知と未実装hard capを分ける。
schemaの説明を実際の最小件数とfieldへ合わせる。生成要件そのものをレビューだけで緩めない。

**必要な検証:** README/roadmap/verification/phase2-operations/design-decisionsの状態表現、CLI名、schema条件を一度に照合。paid test不要。

## 未確定の疑い・追加評価

ここでは修正必須の確定指摘と混ぜない。

1. **実Batch生成失敗の正確な原因:** 上記ledger/既存結果の読取り待ち。F2を直すだけで元生成が成功するとは限らない。出力上限・schema/SDK互換を実際の安全な診断値で判定する。
2. **PlaywrightのHTTP以外の通信:** routes/WebSocket/service worker対策は読んだが、WebRTC、prefetch等を含むOSレベルの全通信遮断は検証していない。具体的なfixtureとネットワーク計測が必要。未確認の迂回を確定脆弱性としない。
3. **audit失敗の通知範囲:** dailyはaudit失敗でActionsをfailedにするが、notifyはcollection reportのみを読む。成功収集＋missing indexed Note等のaudit失敗を3回続けてもcollectionはsuccessのままで、自動Issueの対象にならない。
   この挙動は静的に確認できるが、「失敗通知」の合意範囲にauditを含むかが資料から確定しないため、仕様確認項目とする。添付testはauditも通知対象とした場合の期待値。必要ならaudit resultを独立した運用historyへ記録する。GCSに読取りできないWIF/ADC障害をActions標準通知に委ねる既知制約とは分ける。
4. **HTTP timeoutはrun全体の取得時間上限ではない:** httpx timeoutは接続/読取り単位、response bytes制限はある。遅い分割応答の総時間やブラウザrender完了の意味は追加fixtureで確認する。workflow90分による強制終了とF5の接点を評価する。
5. **同一originの表現:** parse_listingはnetlocだけ比較しschemeを含めない。HTTPS一覧からHTTP同host linkを許す。資料の「同一origin」を厳密なscheme/host/portとするか確認し、必要なら条件を合わせる。
6. **syncのOS固有境界:** remote同士のcasefold衝突・symlink・予約文字は拒否するが、Windowsのpath正規化やファイルロック、外部からのdirectory差替えまで今回は未実行。F1の確定したファイル編集競合を越える部分は追加評価。
7. **依存の供給網/脆弱性:** lockでruntimeを固定し最新CIでinstall成功していることは確認した。全固定版のCVE確認、配布wheel/hashの照合、Actions tagの将来の変更までは調査していない。脆弱性なしとは判定しない。
8. **current GCS:** index126等は既存run時点のログ。稼働中の日次による後続変更、IAM/lifecycleの現在値、全Noteの品質は今回独立照合していない。

## 既知の仕様・意図的な制約・未受入事項

| 区分 | 内容 |
|---|---|
| 受入済み | Phase 1の通常30件手動/定期runと読取りWIF照合。既存記録を今回の静的レビューで覆さない |
| 意図的仕様 | standard既定、30件はrun単位、retryを含む日次hard capなし。予算は通知閾値 |
| 意図的仕様 | 20,000文字の先頭のみ。truncated注意と上限記録、後半欠落、既存Note非再要約 |
| 意図的仕様 | 本文抽出/JSはopt-in。切替はcontent hashを変え再課金し得る。全文変換のnavigation差分も既知 |
| 意図的仕様 | failed Batch候補はpendingで保持しstandard再処理可能。Batch保存成功と同義ではない |
| 意図的仕様 | 曖昧createのblind再提出をしない。complete失敗ledgerはbatch-statusに出ない。batch-collect CLIはない |
| 既知の制約 | API応答後・receipt前の停止/timeoutでexactly-once課金不可。F5はreceipt後の費用復旧の別問題 |
| 既知の制約 | 単一writer前提、複数object transactionなし、独立writerの先行LLMをgeneration条件では防げない |
| 既知の制約 | DNS検査と接続のrace。proxy自動継承なし。robots許可は利用権確認の代替ではない |
| 意図的仕様 | Vaultは片方向、remote削除でlocal削除しない。manifest最後、中断でuntracked conflict、stale lockは手動確認 |
| 意図的仕様 | raw false/retention未設定。旧rawを一括削除しない。retention削除で既存ruleは自動解除しない |
| 未受入 | 実Batchの成功結果保存と独立audit/cost照合 |
| 未設定/未受入 | 利用者Vault、本番lifecycle管理者適用、実invoiceとの費用照合 |
| 利用条件 | AWS無効。Google/GitHubは資料提示と継続承認済み。個別許諾取得の証明ではない。公開は別判断 |
| 後続Phase | Phase 3の4必須項目、Quartz公開、条件付きCloud Run移行。今回未実装を新規不具合としない |
| 停止状態 | 開発停止、heartbeat PAUSEDという引継ぎを尊重。設定を再開/変更していない |

## 横断レビューで確認した実装の接点

src/techkbの全Python file、config2件、prompt、pyproject、runtime/browser lock、全test moduleとfixture、両workflowを固定commitから読み、READMEと指定docs、設計/品質/利用条件/GCP資料を照合した。

- 成功indexを重複排除の正本とし、raw一致→content一致→LLMの順序を維持。失敗hashを成功登録しない。pending先行保存・記事ごとのindex checkpoint・receipt復旧を確認。
- Batchはcreate前予約、曖昧submitのdisplay name照合、model照合bind、content hash key、未知/重複keyで停止。compact outcome永続化と安定billing ID、成功時だけ保存/完了にする流れを確認。
- receipt保存障害で後続の有料処理を打ち切る。Batch保存途中障害も次回receipt回収とhash判定を利用する。
- HTTPは各redirectでURL/public IP/robotsを再確認、trust_env=false、展開後bytes制限、host間隔、有限retry。F3はこの一般HTTP対策へのbrowser allowlistの追加が不足する接点。
- Geminiは固定モデル/minimal/構造化JSON、category enum、ツール無効、本文を命令扱いしないprompt。composeのエスケープと原文非保存を確認。日本語の全件事実検証をしたという意味ではない。
- GCSStoreはUBLA/PAP要求、object generation条件を使用。設計されたwriter権限はbucket getとobject list/get/create/deleteのみ。lifecycleは管理者別操作、metageneration条件と無関係rule保護。
- costはreport IDによる重複排除、model/mode/価格snapshot、output+thinking、UTC境界、待機Batchとunknownを区別。F4/F5が正確さの欠落。
- Issue通知はbody marker、closedを含むページング、同incidentの再投稿抑止。ネットワーク失敗時に生例外を表示しない。F6のstreak判定とは別に確認。
- CLIは既存commandを維持し、--max-callsは減少だけ、state-dirはinspection限定。batch-bind/--applyが書込み操作であること、dry-runにも記事ネットワークがあることを資料と照合。
- full Checksはbrowser/runtime導入後test、dailyはbrowser未導入でvalidate/testを先に実施し、必要source時に後からbrowserを導入。full CIが別に103ケースを実行する点を確認。
- GCS条件付き更新、Issue、lifecycle、Vault等のfixture成功は実GCP/実Vault/実Issueの受入と分けた。

## 再現ケースと未実行の検証

別添: `/tmp/kaname-review-01a1046d-repros.py`。

現行実装に対して望ましい挙動をassertするreview用pytestケース7件を保存した。
F1/F2/F3/F4/F5/F6と、通知のaudit範囲確認に対応する。**今回の環境では実行していない。現行mainで該当assertが失敗する想定であり、既存103テストへ追加統合したわけではない。**

既存testsのMemoryStore/FakeSDK/BatchSDK、httpx.MockTransport、一時Vaultだけを使い、paid API/GCS/利用者Vault/Issue投稿は呼ばない。browserケースだけ実Chromiumが必要。
実行する際は、同じ固定commitと依存lockの隔離環境で以下を使う。未commit変更のあるcheckoutでの結果を固定mainの証拠として混ぜない。

```bash
# repository rootから。既存の検証venvが利用できる場合の例。
PYTHONPATH=src:tests /tmp/kaname-venv/bin/python -m pytest -q /tmp/kaname-review-01a1046d-repros.py
# ブラウザケースを含む場合:
PLAYWRIGHT_BROWSERS_PATH=/tmp/kaname-browsers PYTHONPATH=src:tests /tmp/kaname-venv/bin/python -m pytest -q /tmp/kaname-review-01a1046d-repros.py
```

F5の停止注入はfinallyのreport保存直前にBaseExceptionを送る。真の電源断やGCS障害試験を今回行ったものではない。
最新103 passedのCIはこれらの境界を証明していない。

## Phase 2受入に残る作業と着手順

開発停止を維持する。以下は再開指示後の提案で、実行承認やworkflow起動を含まない。

1. **証拠確保とBatch原因の確定:** 既存private ledger/billing reportを読取りで確認し、安全な分類値だけを記録する。既存job結果を読取り可能なら追加照合。課金済み1件を盲目的に再提出しない。
2. **offline検証環境を復旧:** local HEAD/statusを確認し、HANDOFF/ローカル変更を保全する。固定mainの隔離checkoutで追加ケースを実行し、静的指摘を実行証拠へ更新する。
3. **F1の編集保護を先に修正:** 利用者Vaultへ正式同期する前に、最終check後の編集/新規ファイル競合を保護する。
4. **F2と実Batch原因を修正:** 診断欠落を直し、実際のfailure codeに沿った最小修正に限定。schemaを根拠なく緩めたり、paid再生成を診断手段にしない。
5. **F3、F4/F5、F6を修正:** browserの通信前policy、usage completeness、standard使用量復旧、source streakの実検証状況をそれぞれfixtureで確認。
6. **F7/通知範囲を整理:** 資料の状態/schemaを合わせ、audit failureを自動Issueの対象にするか定義。既存に承認されたissues:writeを改めて承認待ちにしない。
7. **統合検証:** 固定lock/実Chromiumで全既存test＋必要な回帰test、validate-config。Batchの部分失敗・並び替え・保存障害・recovery・standard切替・費用重複なしをSDK MockTransportからend-to-endで検証。
8. **ユーザーの再開/実受入指示後のみ、本番Batch受入:** 新しい有料提出が必要かを既存job証拠から決める。成功結果をNote/receipt/index/pendingに保存し、同じjob/content再実行で再課金・重複保存なし、billing費用1回、成功auditを読取り照合する。失敗再処理と待機を成功と混同しない。
9. **利用者別の受入:** 指定されたVaultのpreview/競合確認、必要なら管理者lifecycle plan/apply、予算値とinvoice照合を別に行う。raw false/retention未設定の現状で削除ruleの本番適用は必須でない。
10. **受入記録更新:** commit/run/report ID、Batch保存件数とusage、audit/cost、残余制約を記録してからPhase 2完了とする。Issue #94はその前に閉じない。Quartz/公開・Phase 3・automation再開は別指示。

## 今回行っていない操作

新しい本番workflow_dispatch/re-run、paid Gemini API、GCS/Vaultデータ変更、認証権限変更、Secret抽出、Issue投稿CLIの起動、公開/デプロイ、PR作成/merge、automationの再開は行っていない。
ActionsとGitHubソースを既存の読取りAPIで取得したのみ。生ログ・記事原文・APIキー・候補URLを成果物へ保存していない。
