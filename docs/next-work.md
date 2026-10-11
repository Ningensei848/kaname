# 次の作業と優先順位

2026-10-11に未解決Issueを再照会した着手順です。
通常schedule、Pages切戻し・復帰、T0/O1/O2とR1〜R5は受入・取込済みです。
P1、P3のcorpus、P4のParallelは実装・実CI検証完了、P3のSource Healthは実GCS読取り受入済みです。
費用推定とBatch切分けの根拠は[今回の作業記録](archive/2026-10/p1-p4-implementation-2026-10-11.md)にあります。
READMEの古い未完了記載を理由に再実装しません。進捗は[検証・受入](verification.md)と各Issueで区別します。

| 優先 | 作業 | 理由・開始条件 | 次に必要な判断 |
|---|---|---|---|
| 実装/限定受入済み | [#127 記事画像](https://github.com/Ningensei848/kaname/issues/127) | 実装済みでClosed。GlucoFM 1件の2図補完・GCS/Git/Pages・実画像表示を受入済み | 新規LLMの実選択は別受入。旧Noteへの一括適用はしない |
| 完了（実CI受入） | [#135 PR検証の対象整理](https://github.com/Ningensei848/kaname/issues/135) | 固定base/headの対象分類・設定別検査・既存check名の結果集約を実装。分類/実Git比較15件・設定混在233件・actionlint成功。設定のみPR #142で必要検査成功/Web省略を受入 | #142は検証後Close、本体PR #141のPython全460件・Web検査も成功 |
| P2 | [#94 実Batch受入](https://github.com/Ningensei848/kaname/issues/94) | 最大1件を個別承認後に提出したが、返却JSONがtitle_ja欠落・未知field・images型不一致で拒否された。追加提出0の失敗usage回収・台帳完了化・auditは完了。本番成功保存は未受入 | standard/Batchの実SDK payloadは完全一致。原因は未確定、schema厳格検証を維持。最新preflight ready後の許可済み最大1件でも同じschema拒否を再現。追加有料提出を停止。台帳complete・欠損usage0・追加提出0の再実行でデータ/課金不変とaudit成功を確認 |
| 費用推定完了・確定照合待ち | [#116 確定請求照合](https://github.com/Ningensei848/kaname/issues/116) | スクショとDaily履歴33回から月500〜550円程度、25%増なら625〜690円を推定。確定明細は未提供 | 実請求との差額は明細提供後に照合。推定を確定請求扱いしない |
| 完了（本番読取り受入） | Source Health Checkの実環境受入 | 実ADC/GCSで335成功行・pending72を読取り。github-blog healthy、google-research failing、AWS disabledを確認 | sourceの既知失敗を監視。CLI成功とsource健全性を分ける |
| 完了（実装・実CI検証） | Regression Corpus | 有効2 sourceの合成HTML・本文golden・画像候補manifest、差分CLIと回帰3件を追加 | 変更時は差分をレビューしてgoldenを更新する |
| 完了（実装・実CI検証） | Parallel Processing | fetch/convertをbounded・入力順で並列処理。既定設定2、LLM/usage/保存は単一writer。host間隔・robotsを排他制御 | 本番の時間短縮は今後の日次runで観測。workers: 1で逐次処理へ戻せる |
| 観測済み・別途対応 | [#139 Google Research連続失敗](https://github.com/Ningensei848/kaname/issues/139) / [#140 日次収集失敗](https://github.com/Ningensei848/kaname/issues/140) | 10月11日の日次runは30生成・29保存後のcompose失敗。Source Healthは失敗/pendingを正しく表示 | 原因の修正・受入は別途対応。今回の無課金runを有料生成の復旧と混同しない |
| P4 | Knowledge Graph Quality | 表記揺れ・同義語・tags/WikiLinkの品質を評価する | 良否の評価例を確認 |
| 対象指定後 | browser source・利用者Vault/NTFSの受入 | 実装済み機能の環境別受入。人力Vaultの管理は利用側の責務 | 検証するsourceまたはVaultと操作範囲を確認 |
| NextStep（既存計画完了後） | [NS1: 検索キーワード・本文のGoogle検索フォールバック](#ns1-google-search-fallback) | 2026-10-11の追加要望。上記の既存作業の完了・受入後に着手する未実装項目 | 既存Noteへのリンクを優先し、未解決WikiLinkをGoogle検索へつなぐ |

読取り専用事前検査の承認範囲と実結果は[Batch事前検査の受入記録](archive/2026-10/batch-preflight-acceptance-2026-10-10.md)にあります。
個別承認後の提出・schema拒否・失敗usage回収とローカル切分けは[実Batchの実行記録](archive/2026-10/batch-acceptance-2026-10-10.md)にあります。

責務整理はPR #131の取込み、main CI、固定124件版のPages更新・配信照合、読取り専用Batch preflightまで完了しました。
証拠は[PR・本番受入記録](archive/2026-10/domain-refactoring-production-2026-10-10.md)に保存しています。
GlucoFMの限定補完は[受入記録](archive/2026-10/glucofm-image-repair-2026-10-11.md)で完了を確認できます。
新規LLMの画像選択・実Batch成功保存などの未完了受入は上表で個別に扱います。

## 未完了Issueの実装・受入計画

#127と#129は実装・失敗回収の証拠に基づきClose済みです。#94と#116はOpenを維持します。#135は実CI受入完了で、本体PR #141はmain取込済みで、#135はCloseしました。

### #135: PR検証の対象選択 — 実CI受入完了

`checks.yml`と`scripts/check_scope.py`で比較base/headを固定し、削除・renameの両側を分類します。
文書のみ、source設定、app設定、画像補完計画、Python、Web、混在を選択し、未知path・比較失敗は全検査へ戻します。
設定検証と対象別回帰、実計画のschema検査を維持し、既存`test`/`web-preview`で成功・省略を集約します。
分類/実Git比較15件、設定混在233件、actionlintが成功。設定のみのPR #142ではPython必要検査と既存checkが成功、Web検査はskip。検証後にマージせずCloseしました。
本体PR #141はmain取込済みで、Python全460件/Web双方・取込後CIも成功しています。
文書のみPR #144でも必要なscope/既存checkは成功、Python/Webの重い検査はskipを実CIで受入済みです。

### #94: API返却不適合で成功保存が未受入

- [x] 同じ入力のstandard/Batchを固定SDKの実HTTP serializerで比較。画像あり/なしともpayloadは完全一致し、送信側の修正理由は得られませんでした。
- [x] 公式Batchの構造化出力契約を照合し、厳格schema・候補ID検証を維持しました。API側の逸脱理由は未確定です。
- [x] 最新preflight ready・費用/操作範囲の個別承認後、最大1 job/1 requestを一度だけ提出。返却1件は同じschema拒否を再現し、承認時の停止条件に従い有料再提出を止めました。
- [x] 追加提出0で失敗usage回収・台帳complete・費用記録success。再実行も提出/保存/復旧0で、台帳・課金record・index・Note/receipt不変、二重計上0を照合しました。
- [ ] 適合応答のNote/receipt/index・公開bytes、audit/costの成功保存受入。#94はOpenを維持します。schema緩和や盲目的な再提出で完了扱いしません。

再拒否・回収・再実行の証拠は[今回の作業記録](archive/2026-10/p1-p4-implementation-2026-10-11.md#許可後の最大1件batch再受入)にあります。
追加の有料試行やmodel/schemaの切替は、原因と操作範囲を再評価する別判断です。

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

## NS1: 検索キーワード・本文のGoogle検索フォールバック

2026-10-11のユーザー要望を記録した、未着手のNextStepです。
上表の既存作業の完了・受入後に着手します。請求明細待ちなどの未完了項目を、この追加計画によって完了扱いにはしません。
この節を後続実装の要求・着手条件・完了条件の正本とし、ロードマップから参照します。

### 要求と現行との差

検索キーワードとNote本文の固有語彙を、クリックだけで調べられるようにします。
対応する公開Noteがあれば内部リンクを優先し、なければその語句のGoogle検索を開きます。

現在、`composer.py`は`related_concepts`を「検索キーワード」の`[[語句]]`として出力します。
`site.py`の`project_content`は、公開manifest内で同じタイトルが一意に見つかった語句だけを内部リンクにし、
一致なし・同名複数の場合はプレーンテキストにしています。本文の固有語彙を自動でWikiLinkにする処理はありません。
このため、未解決リンクの変換と本文へのWikiLink付与の両方が実装対象です。

Google検索のリンクは`https://www.google.com/search?q=<URLエンコードした語句>`とします。
`q`が検索語句のパラメータであることは[Googleの説明](https://support.google.com/analytics/answer/1012264?hl=en)で確認できます。
API呼出しやAPIキーは不要で、利用者がリンクをクリックした際に検索ページへ遷移します。

| 入力と公開先の状態 | 生成するリンク |
|---|---|
| 検索キーワード`[[GlucoFM]]`、対応するNoteなし | `GlucoFM`をクエリにしたGoogle検索 |
| 本文中の`[[GlucoFM]]`、対応するNoteなし | 同じGoogle検索 |
| 対応する公開Noteが一意に存在 | 既存の安定Note IDへの内部リンク |
| 同名Noteが複数、または公開対象から除外されている | Google検索。任意のNoteを選ばない |
| 別名表示`[[語句\|表示名]]` | 内部リンクの解決対象・検索語句は「語句」、表示は「表示名」 |
| コード内・エスケープ済みの`[[語句]]` | 記述を保持し、検索リンクへ変換しない |

### 実装順序と責務

1. **公開Noteの解決と未解決時のリンク生成を共通化する。**
   `src/techkb/site.py`のQuartz入力への投影を主な変更箇所とし、検索キーワードと本文に同じ規則を適用します。
   判定には固定された公開snapshotのmanifestを使います。先行するGraph Qualityで別名・正規化規則を整備した場合は、その一意解決規則に合わせます。
   ブラウザで404を検出してから遷移させる方式ではなく、SSG入力を生成する時点でリンク先を確定します。
   任意の壊れたHTTPリンクや画像URLまで検索へ変換せず、対象はWikiLinkとします。
   アンカー付きWikiLinkはNote部分と見出し部分を分離し、解決できる内部リンクと見出し指定を保ちます。
   Noteが未解決ならNote部分の語句を検索し、見出しだけが不正な場合はGoogle検索へ変換せず、Web側のリンク監査で検出できることを確認します。

2. **本文の固有語彙にWikiLinkを付与する。**
   初期実装では既存の構造化された`related_concepts`を候補として使い、新規NoteのAI要約・重要ポイント・資料の位置づけに現れる語句を共通composerで`[[語句]]`にします。
   候補は製品名・技術名などユニーク性の高い語句に限定し、一般語を無差別にリンク化しません。
   重なる候補は長い語句を優先し、英単語の一部への一致、URL・コード・既存リンク・画像alt/captionへの重複挿入を避けます。
   安全なテキストのエスケープとリンク記法の組立を分け、`inline()`全体の保護を弱めません。
   LLMには現在どおり記法なしの概念名を返させ、追加LLM呼出し・Batch schema変更を伴わせません。
   要約の字数判定は記法を付ける前の要約文で行い、WikiLinkの括弧やGoogle検索URLを字数に加えません。

3. **公開Note検証とWeb表示を合わせる。**
   standard/Batchが同じ本文を生成し、公開Noteの組立検証も同じ規則で受け入れるようにします。
   旧生成形式の検証経路を保持し、本文にWikiLinkを追加していない既存Noteも引き続き公開できるようにします。
   Markdownのコードブロック・コードspan・エスケープ・別名表示を区別し、単純な全置換で記述を壊さないようにします。
   Google検索URLは固定のHTTPS originと`urlencode({"q": 語句})`等で組み立て、日本語・空白・`C++`・`&`を別パラメータに解釈させません。
   外部検索と分かる表示・アクセシブルな説明を付け、Google検索は別タブで開き、`rel="noopener noreferrer"`を適用します。
   内部リンクは既存の遷移・検索・graphの挙動を維持し、外部検索リンクをNote間のgraph edgeに数えません。
   外部検索はクリック時のナビゲーションとし、ページ表示時やビルド時のGoogleへのresource取得・script追加・CSP通信許可の拡張を伴わせません。

4. **既存Noteへの適用と受入を確認する。**
   既存の保存Note・公開元Markdown bytes・Note ID・manifest schemaを維持します。
   既存Noteの明示的なWikiLinkは次のWebビルドからフォールバックの対象になります。
   本文への自動WikiLink付与は新規生成Noteから適用し、旧Noteの一括書換え・要約の再生成はこのNextStepへ含めません。
   投影だけの変更では元snapshotのdataset digestを変えず、Web成果物の検証情報は再ビルドに合わせて更新します。

### 完了条件

- 検索キーワードと本文のWikiLinkを、それぞれクリック一回で内部Noteまたは対応語句のGoogle検索へ移動できる。
- 一意の内部Noteがある場合は内部リンクを優先し、未解決・同名複数・公開除外ではGoogle検索になる。
- 日本語、空白、`C++`、`&`、引用符、別名表示を含むクエリが正しく復号でき、クエリへの別パラメータ混入やHTML/Markdownの破損がない。
- コード・エスケープ・URL・画像記述を保持し、部分一致や候補の重複で本文を壊さない。
- standard/Batchの共通生成、公開Noteの組立検証、Quartz投影、内部リンク監査を対象回帰で確認する。
- fixtureと固定実contentでビルドし、Chromiumでクリック先・別タブ・表示幅・外部リンクの識別・想定外resource通信なしを確認する。
  CIではGoogleへ実検索せず、生成href・復号したクエリ・クリック時のナビゲーション先で判定する。
- 既存Noteの元Markdown hashとIDが維持され、新規Noteの要約本文の字数・画像配置・公開検証が従来の制約を満たす。
- 仕様・運用・検証の正本に実装後の挙動と受入結果を記録してから、NS1を完了とする。
