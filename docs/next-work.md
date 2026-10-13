# 次の作業と優先順位

2026-10-13 JST、指定されたP4: Parallel Processingまでの作業は完了しました。NS1と通常収集の復旧も本番受入まで完了しました。DeepMind追加も限定1件の保存/公開・ゼロ生成再実行まで完了しました。Microsoft Research/Meta/Apple/Cloudflareも有効化・生成0の本番受付/配信まで完了し、現在は有効7 source・index437/public155/pending127です。通常日次がDeepMind29件を追加保存し、別の1件は出力上限で失敗（#178）したため、保存分の公開と生成失敗を分けて管理します。新規記事限定の日次受入も完了し、収集543→32秒・全体15分30秒→5分51秒（生成0）を確認しました。以下は完了状態と後続作業の着手順です。
通常schedule、Pages切戻し・復帰、T0/O1/O2とR1〜R5は受入・取込済みです。
P1、P3のcorpus、P4のParallelは実装・実CI検証完了、P3のSource Healthは実GCS読取り受入済みです。
2026-10-12 JST、P2の画像型/候補外IDを解消し、実Batchの3画像入りNoteを保存・公開済みです。追加生成0の再実行・監査/費用/Git/Pagesまで受入完了です。
費用推定とBatch切分けの根拠は[今回の作業記録](archive/2026-10/p1-p4-implementation-2026-10-11.md)にあります。
READMEの古い未完了記載を理由に再実装しません。進捗は[検証・受入](verification.md)と各Issueで区別します。

| 優先 | 作業 | 理由・開始条件 | 次に必要な判断 |
|---|---|---|---|
| 通常運用で継続 | 収集保留127件 | 2026-10-13通常日次は29保存/1生成失敗、成功index437。元未処理とRSSの追加候補を含む。日次・全source合計30件で順次処理 | 独立照合でDeepMind70/GitHub1/Microsoft11/Meta12/Apple13/Cloudflare20を確認。通常日次30呼出しUSD 0.076561も承認台帳へ合算し、残額USD 0.7094916。[現状](release-distribution.md) |
| 要対応・Open維持 | [#178 DeepMindのJSON打切り](https://github.com/Ningensei848/kaname/issues/178) | 通常日次の1件がMAX_TOKENS/json_invalid。29件は保存/公開済みだが、失敗した1件の成功受入は未完了 | 出力上限・費用/件数capを保った再検証を別途進める。配布成功を収集成功扱いにしない |
| 後続候補 | GCS監査/export・HTMLの追加短縮 | 新規記事限定とRelease差分配布は受入完了。GCS全件監査・Quartz全体buildを維持 | 別run間の差分GCS監査、ReleaseのHTTP重複取得、検索/リンクの無効化を測定して判断。[現状](release-distribution.md) |
| 費用推定完了・確定照合待ち | [#116 確定請求照合](https://github.com/Ningensei848/kaname/issues/116) | スクショとDaily履歴33回から月500〜550円程度、25%増なら625〜690円を推定。確定明細は未提供。推定は当時の2 source基準で、7 sourceの月額確定値ではない | 実請求との差額は明細提供後に照合。推定を確定請求扱いしない |
| 対象指定後 | browser source・利用者Vault/NTFSの受入 | 実装済み機能の環境別受入。人力Vaultの管理は利用側の責務 | 検証するsourceまたはVaultと操作範囲を確認 |

## 完了済みの作業

完了項目を着手順から分離しました。2026-10-12にGitHubのClosed状態と受入記録を照合し、#139/#140/#165をClose。#94/#108〜#115/#127/#129/#135/#159/#161と解消済みの通知#143/#146/#152/#155はClosedを維持します。後続のPR #134/#171/#173/#176は取込済みでClosed、一時的なHTTP500の通知#174も再実行/配信照合後にClose。Open Issueは明細待ち#116と、2026-10-13の新しい収集失敗#178です。

| 状態 | 作業 | 受入証拠 | 継続時の注意 |
|---|---|---|---|
| 完了（再認証後の独立読取り） | GCS保存/費用/公開版の補足照合 | 全437 Note/receipt/index整合・公開155件の全bytes/配信版一致・元費用不変。読取り前後で946オブジェクト世代/CRC不変、旧883オブジェクト/408成功行保持、未決済/不明usage0 | Source Healthのdegradedを維持し、#178は未解消。元の2公開run前の完全catalog不足を今回の前後比較と区別。[証拠](archive/2026-10/release-gcs-independent-acceptance-2026-10-13.json) |
| 完了（実Release/Actions受入） | [PR #179 Release差分配布](https://github.com/Ningensei848/kaname/pull/179) | Python693件/専用34件・PR/main CI成功。完全版125件から変更30件の差分で155件を復元し、旧126件不変・1,359検索リンク・実配信一致。2回の公開専用run全工程success、追加Release/asset/content commit 0 | GCS正本・content/submodule互換性を維持。再認証後の独立照合も完了（946世代/CRC・元費用・公開bytes一致）。新規API費用0、通常日次の既知USD 0.076561は台帳へ合算。[受入](release-distribution.md) |
| 完了（新規限定・実Actions受入） | [PR #176 新規記事だけの収集](https://github.com/Ningensei848/kaname/pull/176) | 659件・PR/main CI成功。RSS259/既知111 skip/本文HTTP0、収集543→32秒/日次930→351秒（生成0）。元保存884オブジェクト/費用/公開126件・配信不変、index408/pending148 | 未分類3件を含む保留を日次30件で処理。同じURLの編集は明示再検査。Release配布は後続PR #179で実装・本番受入。[受入/設計](incremental-collection.md) |
| 完了（実Actions受入） | [PR #173 日次処理の短縮](https://github.com/Ningensei848/kaname/pull/173) | 同じ7社/生成0で全体39分22秒→15分30秒（60.63%短縮）、監査445→62秒/export825→13秒。Python642件・PR/main CI・本番全工程成功。index408/pending145・保存/元費用/公開126件・配信版を保持 | 追加Gemini USD 0。別run間の永続cacheは含めない。HTTP500履歴によるDeepMindのstreak1は未完了sourceの規則で保持。[受入記録](daily-performance.md) |
| 完了（有効化・生成0本番受入） | [PR #171 追加4社の有効化](https://github.com/Ningensei848/kaname/pull/171) | 実49記事の取得/変換・Python632件/専用79件・PR/main CI成功。本番7 source成功、生成0/index408/pending145、既存881オブジェクト/元費用不変。全工程・公開126件/959検索リンク・保存bytes/配信版照合success | 追加API USD 0、承認残額USD 0.7860526。新4社の実Note生成は日次運用で順次処理。[受入記録](four-source-activation.md) |
| 完了（限定本番受入） | [PR #134 DeepMind追加](https://github.com/Ningensei848/kaname/pull/134) | 本文の新旧2レイアウト、対象外3件filter、実100候補の無課金検査、Python620件/専用67件・PR/main CI成功。実1件保存/公開126件/959検索リンク・ゼロ生成の保存/課金880オブジェクト/費用/公開版不変を照合 | 追加API推計USD 0.0024581。初回保留96件は通常運用で別管理。他4候補の後続有効化は別管理。[受入記録](source-onboarding.md) |
| 実装/限定受入済み | [#127 記事画像](https://github.com/Ningensei848/kaname/issues/127) | 実装済みでClosed。GlucoFM 1件の2図補完・GCS/Git/Pages・実画像表示を受入済み | Google Researchの新規Batch Noteでも3画像の実選択・保存/公開を受入。旧Noteへの一括適用はしない |
| 完了（実CI受入） | [#135 PR検証の対象整理](https://github.com/Ningensei848/kaname/issues/135) | 固定base/headの対象分類・設定別検査・既存check名の結果集約を実装。分類/実Git比較15件・設定混在233件・actionlint成功。設定のみPR #142で必要検査成功/Web省略を受入 | #142は検証後Close、本体PR #141のPython全460件・Web検査も成功 |
| 完了（実Batch本番受入） | [#94 実Batch受入](https://github.com/Ningensei848/kaname/issues/94) | PR #153/#156後の限定1job/1記事で厳格検証に適合し、3画像入りNoteを保存・公開。index336/pending71、receipt/Note/indexと公開bytes一致、課金record1・欠損0。費用推計約0.23円 | 追加生成0の再実行も全工程success。保存/課金bytes・世代・費用不変、課金1回を受入。#94はClose、当該1件の承認枠は使用済み。通常復旧は後続の別枠 |
| 完了（本番読取り受入） | Source Health Checkの実環境受入 | 2026-10-11に実ADC/GCSで335成功行・pending72を読取り。github-blog healthy、google-research failing、AWS disabledを確認 | 後続の通常復旧でindex407/pending0・healthyを確認。CLI成功とsource健全性を分ける |
| 完了（実装・実CI検証） | Regression Corpus | 有効7 source・8レイアウトの合成HTML・本文golden・画像候補manifest、差分CLIと回帰9件。DeepMind新旧と追加4社の本文を保持 | 変更時は差分をレビューしてgoldenを更新する |
| 完了（実装・実CI検証） | Parallel Processing | fetch/convertをbounded・入力順で並列処理。既定設定2、LLM/usage/保存は単一writer。host間隔・robotsを排他制御 | 本番の時間短縮は今後の日次runで観測。workers: 1で逐次処理へ戻せる |
| 完了（品質評価） | [#159 Knowledge Graph Quality](https://github.com/Ningensei848/kaname/issues/159) | 無通信・無書込みCLI、良い/悪い16例・関連回帰27件、固定実content125件を評価し元hash不変。[指標と結果](graph-quality.md) | 正規化案だけでは検索語612件は解決しない。保存/投影への適用は後続で判断 |
| 完了（通常収集・本番公開） | [#139](https://github.com/Ningensei848/kaname/issues/139) / [#140](https://github.com/Ningensei848/kaname/issues/140) / [#165](https://github.com/Ningensei848/kaname/issues/165) | 71保存・index407/pending0・連続失敗0・healthy。ゼロ生成で保存/課金不変、全工程success、公開125件/936検索リンク・配信照合 | API費用推計USD 0.2114893（承認USD 1内）。すべてClose。[復旧記録](source-recovery.md) |
| 完了（本番受入） | [#161 NS1](https://github.com/Ningensei848/kaname/issues/161) | 本文/キーワードの検索導線、Python543件・実125件612リンク・本番配信/GCS/費用不変 | 追加Gemini費用USD 0。[受入記録](ns1-search-fallback.md) |

読取り専用事前検査の承認範囲と実結果は[Batch事前検査の受入記録](archive/2026-10/batch-preflight-acceptance-2026-10-10.md)にあります。
個別承認後の提出・schema拒否・失敗usage回収とローカル切分けは[実Batchの実行記録](archive/2026-10/batch-acceptance-2026-10-10.md)にあります。

責務整理はPR #131の取込み、main CI、固定124件版のPages更新・配信照合、読取り専用Batch preflightまで完了しました。
証拠は[PR・本番受入記録](archive/2026-10/domain-refactoring-production-2026-10-10.md)に保存しています。
GlucoFMの限定補完は[受入記録](archive/2026-10/glucofm-image-repair-2026-10-11.md)で完了を確認できます。
新規LLMの実画像選択3件と実Batch成功保存/公開・追加生成0の再実行は受入完了です。

## 完了記録と待機中の受入

#127と#129は実装・失敗回収の証拠に基づきClose済みです。#94は成功保存・公開・再実行の受入完了でClose。#116は確定請求明細待ちでOpenを維持します。#135は実CI受入完了で、本体PR #141はmain取込済みで、#135はCloseしました。

### #135: PR検証の対象選択 — 実CI受入完了

`checks.yml`と`scripts/check_scope.py`で比較base/headを固定し、削除・renameの両側を分類します。
文書のみ、source設定、app設定、画像補完計画、Python、Web、混在を選択し、未知path・比較失敗は全検査へ戻します。
設定検証と対象別回帰、実計画のschema検査を維持し、既存`test`/`web-preview`で成功・省略を集約します。
分類/実Git比較15件、設定混在233件、actionlintが成功。設定のみのPR #142ではPython必要検査と既存checkが成功、Web検査はskip。検証後にマージせずCloseしました。
本体PR #141はmain取込済みで、Python全460件/Web双方・取込後CIも成功しています。
文書のみPR #144でも必要なscope/既存checkは成功、Python/Webの重い検査はskipを実CIで受入済みです。

### #94: 画像型/候補外IDを解消・実保存/公開/再実行まで完了

PR #153でAPI対応のresponseSchemaに画像object定義を直接送り、画像文字列配列による型不適合を解消しました。
その後の候補4件に対する5件選択は、GET診断で候補外ID 1件と確定しました。
PR #156で記事ごとの候補ID.enumと候補数以内のmaxItemsを追加し、関連86件・全Python476件/Web・PR/main CI成功後にmainへ取込みました。
画像文字列の変換や候補外画像の削除で成功扱いにせず、型・候補・重複・配置の厳格検証を維持しています。

- [x] 事前条件ready・他writer不在・未決済/不明usage0を確認し、個別承認した新しい最大1job/1記事を一度だけ提出。受付・workflow全体success。
- [x] 追加生成0の回収で適合Note 1件/画像3件を保存。成功index335→336・pending72→71、Note/receipt/index一致・公開ポリシー適合を確認。
- [x] 台帳complete・課金record1・usage欠損0。input3553/output729/thinking0、費用推計USD 0.0014442（約0.23円）。
- [x] collection/audit/cost/Git/Pages・配信版/元Markdown照合すべてsuccess。公開125件の最新版に今回のNoteを含み、artifact/Git/GCSのNote bytes一致を確認。
- [x] 追加生成0の再実行で台帳/課金bytes・index・Note/receipt世代不変、課金record1、日次/月次費用同一、公開manifest/content commit不変を照合。collection/audit/cost/Git/Pages・配信照合すべてsuccess。#94をClose。

実行URL・commit・費用・以前の拒否と回収は[画像型と候補制約の受入記録](archive/2026-10/batch-images-type-diagnosis-2026-10-11.md)へ集約しました。
今回の有料2試行合計はUSD 0.00306255（約0.49円）。当時の限定提出枠は使用済みです。その後の通常復旧には追加USD 1の承認があり、[復旧記録](source-recovery.md)で消費・残額を管理します。通常scheduleのstandard設定を維持します。

### #116: 費用推定完了・確定請求照合は明細待ち

今回のユーザー指定に従い、AI Studioの175円/800円表示とActionsのDaily全33回、収集report21回、
standard336呼出し・別Batch2 requestを照合し、月500〜550円、25%増で625〜690円を推定しました。
計算、反映遅延・期間/時間帯の不一致、推計対象外のGCS/Actions、50%増なら800円を越える可能性は
[作業記録](archive/2026-10/p1-p4-implementation-2026-10-11.md#p2-費用推定とbatch切分け)に記録しています。

確定明細がないため実請求との差額はまだ算定できず、#116のinvoice照合はOpenを維持します。
明細提供時に対象期間/通貨/時間帯/調整項目を決め、保存済みusageと元価格を読取り専用で対応付けます。
推定完了を確定照合の完了と扱いません。

## #127の実装範囲

記事本文からHTTPS画像候補を最大12件抽出し、alt・キャプション・周辺テキストを候補IDとともにLLMへ渡します。
画像自体は解析せず、候補にあるIDだけを最大6件選び、AI要約・対応する重要ポイント・資料の位置づけの直後へ配置します。
画像指定は要約文の字数とは別項目です。本文入力は20,000文字のまま、画像URLはLLM入力や元記事の語数へ加えません。
通常の収集で画像なしの旧Note・既存Batch台帳・成功Noteを変更しません。
ユーザー承認済みのGlucoFM 1件は、[専用の画像補完](operations.md#既存noteへの画像補完)で本文だけを再取得し、要約の再生成なしで2図を追加・本番配信済みです。ほかの旧Noteへの一括適用は行いません。

公開Noteに選んだ画像URLと配置を記録し、画像Markdownとの完全一致・位置・秘密の混入を検査します。
画像ファイルは取得・保存・Git同梱しません。Pagesは当該Noteにある画像のみ表示し、画像hostだけをCSPの画像通信へ追加します。
script・connect等の外部通信は引き続き許可しません。HTMLの画像には`referrerpolicy="no-referrer"`を設定します。
HTTP、data URL、認証付きURL、IP/ローカルhost、署名・token付きURL、入力打切り後の説明しかない画像は候補にしません。
元画像の変更・削除による表示の変化はNoteのhashやGit版では固定できません。

standard/Batchのmock実行、復旧と二重計上防止、公開snapshotのbytes一致、実Chromiumの画像表示を検証します。
Web検証では許可された画像レスポンスをローカルで代用し、出典サイトへ実通信せず、ほかの外部resourceは拒否します。
本番のGemini/GCS更新・workflow手動実行・Pages deployと画像入りの実Note受入は別に判定します。

<a id="ns1-google-search-fallback"></a>

## NS1: 検索キーワード・本文のGoogle検索フォールバック — 完了

新規本文の共通WikiLink付与、未解決時のGoogle検索、一意な内部Note優先を実装しました。Python全543件・PR/mainのPython/Web CI、架空3件と固定実125件のChromium、本番Pages更新・配信照合まで成功しています。公開612検索リンク、元Markdown/ID/dataset/GCS/費用不変、新規生成0・追加API費用USD 0を受入済みです。

[#161](https://github.com/Ningensei848/kaname/issues/161)をCloseし、[実装・受入記録](ns1-search-fallback.md)へ証拠を集約しました。要求・以前の実装計画は[履歴](archive/2026-10/ns1-plan-2026-10-12.md)に保存しています。
