# Google Researchと通常収集の復旧

2026-10-12 JST、[#139](https://github.com/Ningensei848/kaname/issues/139)と[#140](https://github.com/Ningensei848/kaname/issues/140)の復旧を開始しました。P4/NS1までの完了範囲は維持しています。

基準状態は成功index336行（Google Research301/GitHub35）、Google保留71件・連続失敗6です。公開Noteの最新版は125件です。10月11日の日次[38100338209](https://github.com/Ningensei848/kaname/actions/runs/38100338209)はstandard30生成・29保存後のcompose ValueErrorで失敗し、構造診断がありません。限定Batchの1成功や公開専用runではsource全体の復旧を証明できません。

追加Gemini API費用はユーザー承認のUSD 1までです。開始時の追加消費はUSD 0。通常standard単価はinput USD 0.30/百万token、output（thinking含む）USD 2.50/百万tokenで、[公式価格](https://ai.google.dev/gemini-api/docs/pricing)と設定を照合済みです。確定請求やGCS/Actions費用とは区別します。

- [x] 既存履歴・実GCS Source Healthとpending・未決済/不明usageの基準を読取り確認。
- [x] standardの安全な画像型/候補/配置診断と、任意runの費用推計上限を実装。
- [x] Python全561件・actionlint・[PR #164](https://github.com/Ningensei848/kaname/pull/164)のPython/Web CI成功。mainへ取込済み。
- [ ] USD 1枠の残額を各runへ渡して通常standardの実生成・保存・監査/費用/Git/Pagesを受入。
- [ ] 保留解消、source_completed・連続失敗0・healthyを確認し、追加生成0の再実行を受入。
- [ ] #139/#140と解消した通知を証拠に基づいてClose。

制御の対象・見積りと停止条件は[運用手順](operations.md#費用を限定したstandard収集)に記録しています。生成拒否・曖昧な提出/usage・保存障害を確認した場合は追加生成を止め、原因を修正します。画像を削除/型変換して適合扱いにはしません。

## 先行する定期収集

遅延して開始された[定期run 38191452972](https://github.com/Ningensei848/kaname/actions/runs/38191452972)が01:19 UTCから旧mainで進行しています。初回discoveryの耐久保存により一時的にpendingが110件（Google100/GitHub10）となりました。復旧手動実行を重ねず、収集・usage・writer終了を待ってから実測分を差し引きます。

定期runは30呼出し・29保存、LLM ValidationError 1件で失敗しました。成功index365・Google保留42・連続失敗7、欠損usage0、費用推計USD 0.0934131です。この定期分も保守的に承認枠へ含め、残額USD 0.9065869とします。収集失敗のためaudit/export/Git/Pagesは進めず、公開済み版を維持しました。

## main取込後の限定standard受入

[main CI 38191631457](https://github.com/Ningensei848/kaname/actions/runs/38191631457)成功後、[限定run 38192090307](https://github.com/Ningensei848/kaname/actions/runs/38192090307)をstandard/max_calls=1/max_cost_usd=0.9065869で実行しました。収集は1呼出し・1保存、HTTP試行1・不明usage0・失敗0です。input3560/output644/thinking0、費用推計USD 0.002678。index366・Google保留41、累計追加費用USD 0.0960911・残額USD 0.9039089です。sourceは保留が残るためfailingを維持し、復旧完了扱いにしません。監査・公開は進行中です。

限定Noteは2画像・本文WikiLink 8件を含み、receipt/indexと同一であることを実GCS読取りで確認しました。次の[run 38192547670](https://github.com/Ningensei848/kaname/actions/runs/38192547670)をstandard/max_calls=30/max_cost_usd=0.9039089で提出し、同じwriter排他キューで待機しています。

複数の成功runごとに全状態監査/公開を繰り返す費用を抑えるため、正の費用上限を指定したstandard実行に限り件数上限の拡大を許可する調整へ進みます。待機run 38192547670はwriter steps未開始を確認して取消し、生成/課金0です。通常設定30件・上限未指定の引上げ拒否・不明usage/結果拒否/耐久保存障害での停止は維持します。
