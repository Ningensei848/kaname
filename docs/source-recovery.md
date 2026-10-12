# Google Researchと通常収集の復旧

2026-10-12 JST、[#139](https://github.com/Ningensei848/kaname/issues/139)と[#140](https://github.com/Ningensei848/kaname/issues/140)の復旧を開始しました。P4/NS1までの完了範囲は維持しています。

基準状態は成功index336行（Google Research301/GitHub35）、Google保留71件・連続失敗6です。公開Noteの最新版は125件です。10月11日の日次[38100338209](https://github.com/Ningensei848/kaname/actions/runs/38100338209)はstandard30生成・29保存後のcompose ValueErrorで失敗し、構造診断がありません。限定Batchの1成功や公開専用runではsource全体の復旧を証明できません。

追加Gemini API費用はユーザー承認のUSD 1までです。開始時の追加消費はUSD 0。通常standard単価はinput USD 0.30/百万token、output（thinking含む）USD 2.50/百万tokenで、[公式価格](https://ai.google.dev/gemini-api/docs/pricing)と設定を照合済みです。確定請求やGCS/Actions費用とは区別します。

- [x] 既存履歴・実GCS Source Healthとpending・未決済/不明usageの基準を読取り確認。
- [x] standardの安全な画像型/候補/配置診断と、任意runの費用推計上限を実装。
- [x] Python全561件・actionlint・[PR #164](https://github.com/Ningensei848/kaname/pull/164)のPython/Web CI成功。mainへ取込済み。
- [x] USD 1枠内で通常standardの生成/保存を受入。累計72呼出し・71保存、欠損/再試行0、index407。
- [ ] 全41件を含む監査/費用/Git/Pagesの本番公開を受入。
- [x] 実GCSで保留0、両source_completed・連続失敗0・healthyを確認。
- [ ] 追加生成0の再実行で保存・課金の不変を受入。
- [ ] #139/#140と解消した通知を証拠に基づいてClose。

制御の対象・見積りと停止条件は[運用手順](operations.md#費用を限定したstandard収集)に記録しています。生成拒否・曖昧な提出/usage・保存障害を確認した場合は追加生成を止め、原因を修正します。画像を削除/型変換して適合扱いにはしません。

## 先行する定期収集

遅延して開始された[定期run 38191452972](https://github.com/Ningensei848/kaname/actions/runs/38191452972)が01:19 UTCから旧mainで進行しています。初回discoveryの耐久保存により一時的にpendingが110件（Google100/GitHub10）となりました。復旧手動実行を重ねず、収集・usage・writer終了を待ってから実測分を差し引きます。

定期runは30呼出し・29保存、LLM ValidationError 1件で失敗しました。成功index365・Google保留42・連続失敗7、欠損usage0、費用推計USD 0.0934131です。この定期分も保守的に承認枠へ含め、残額USD 0.9065869とします。収集失敗のためaudit/export/Git/Pagesは進めず、公開済み版を維持しました。

## main取込後の限定standard受入

[main CI 38191631457](https://github.com/Ningensei848/kaname/actions/runs/38191631457)成功後、[限定run 38192090307](https://github.com/Ningensei848/kaname/actions/runs/38192090307)をstandard/max_calls=1/max_cost_usd=0.9065869で実行しました。収集は1呼出し・1保存、HTTP試行1・不明usage0・失敗0です。input3560/output644/thinking0、費用推計USD 0.002678。index366・Google保留41、累計追加費用USD 0.0960911・残額USD 0.9039089です。sourceは保留が残るためfailingを維持し、復旧完了扱いにしません。監査・公開は進行中です。

限定Noteは2画像・本文WikiLink 8件を含み、receipt/indexと同一であることを実GCS読取りで確認しました。次の[run 38192547670](https://github.com/Ningensei848/kaname/actions/runs/38192547670)をstandard/max_calls=30/max_cost_usd=0.9039089で提出し、同じwriter排他キューで待機しています。

複数の成功runごとに全状態監査/公開を繰り返す費用を抑えるため、正の費用上限を指定したstandard実行に限り件数上限の拡大を許可する調整へ進みます。待機run 38192547670はwriter steps未開始を確認して取消し、生成/課金0です。通常設定30件・上限未指定の引上げ拒否・不明usage/結果拒否/耐久保存障害での停止は維持します。

PR #166のPython/Web・[main CI 38193231300](https://github.com/Ningensei848/kaname/actions/runs/38193231300)成功後、[全保留run 38193431223](https://github.com/Ningensei848/kaname/actions/runs/38193431223)をstandard/max_calls=100/max_cost_usd=0.9039089で開始しました。先行の限定run 38192090307はcollection/audit/cost/Git/Pagesすべてsuccessで完了しました。

`audit-run`も費用上限を元単価・確定usageで検証し、通常件数を越える正当なstandard実行を認識する調整を実施します。不明usage・再試行・単価欠損・費用超過・不正な上限は拒否し、上限未指定の既存件数判定を維持します。

## 全保留の保存・Source Health復旧と公開互換の補修

全保留runは41呼出し/41HTTP試行・41保存・不明usage0、input147994/output28400/thinking0で成功しました。両source_completed、Google成功372/GitHub35、index407/pending0・連続失敗0・healthyを実GCSで確認済みです。このrunの費用推計USD 0.1153982、開始後累計は定期分を含めUSD 0.2114893（72呼出し）、残額USD 0.7885107です。

追加のローカル実Note公開検証で、旧`concept()`が記号除去後の連続ASCIIスペースを残すために、保存済み407件中1件/検索語1つを再検証で拒否すると判明しました。全41件の生成/保存/usageは確定済みで、通常の状態監査も通過しています。旧コードによる不要な残工程を止めるためrun 38193431223はCost/notification工程で取消しました。GCSの保存・課金記録は削除せず、Geminiの再生成なしで公開検証の互換を直します。

新規ラベルは記号除去後の空白を整理し、160文字で切った末尾の空白/ピリオドも除き、再適用で変わらない形にします。旧保存ラベルは旧formatterが出力し得た形式だけを受け入れ、キーワード/著者のbytesを保持します。構文区切り、非ASCII空白、長さ超過、本文への未審査WikiLinkは拒否します。

Python全609件・関連143件が成功。実41Noteはすべて公開適合（59画像）、元単価/確定usageによるaudit-runも全407行/pending0/issues0で成功しました。元Note/receiptを保持した固定実125件のローカルGit版はexport/build/Chromiumに適合し、検索リンク936件・画像要求243回・外部resource通信0を確認しました。このlocal commitは検証用で、リモート公開とは区別します。修正のPR/main CI後に、max_calls=0のrunで保存済み結果を本番公開・ゼロ生成再実行します。
