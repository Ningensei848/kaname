# Google Researchと通常収集の復旧

2026-10-12 JST、[#139](https://github.com/Ningensei848/kaname/issues/139)と[#140](https://github.com/Ningensei848/kaname/issues/140)の復旧を開始しました。P4/NS1までの完了範囲は維持しています。

基準状態は成功index336行（Google Research301/GitHub35）、Google保留71件・連続失敗6です。公開Noteの最新版は125件です。10月11日の日次[38100338209](https://github.com/Ningensei848/kaname/actions/runs/38100338209)はstandard30生成・29保存後のcompose ValueErrorで失敗し、構造診断がありません。限定Batchの1成功や公開専用runではsource全体の復旧を証明できません。

追加Gemini API費用はユーザー承認のUSD 1までです。開始時の追加消費はUSD 0。通常standard単価はinput USD 0.30/百万token、output（thinking含む）USD 2.50/百万tokenで、[公式価格](https://ai.google.dev/gemini-api/docs/pricing)と設定を照合済みです。確定請求やGCS/Actions費用とは区別します。

- [x] 既存履歴・実GCS Source Healthとpending・未決済/不明usageの基準を読取り確認。
- [x] standardの安全な画像型/候補/配置診断と、任意runの費用推計上限を実装。
- [ ] 回帰・PR CI/main取込を完了。
- [ ] USD 1枠の残額を各runへ渡して通常standardの実生成・保存・監査/費用/Git/Pagesを受入。
- [ ] 保留解消、source_completed・連続失敗0・healthyを確認し、追加生成0の再実行を受入。
- [ ] #139/#140と解消した通知を証拠に基づいてClose。

制御の対象・見積りと停止条件は[運用手順](operations.md#費用を限定したstandard収集)に記録しています。生成拒否・曖昧な提出/usage・保存障害を確認した場合は追加生成を止め、原因を修正します。画像を削除/型変換して適合扱いにはしません。
