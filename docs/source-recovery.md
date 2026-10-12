# Google Researchと通常収集・公開の復旧 — 完了

2026-10-12 JST、[#139](https://github.com/Ningensei848/kaname/issues/139)・[#140](https://github.com/Ningensei848/kaname/issues/140)・[#165](https://github.com/Ningensei848/kaname/issues/165)を実受入の証拠でCloseしました。開始時の保留71件を保存し、成功index407（Google Research372/GitHub35）・pending0・連続失敗0・両source healthyです。通常のstandard設定30件、fetch/convertの2 workerを維持しています。

追加Gemini API費用推計は、遅れて開始した定期分も含めUSD 0.2114893（72呼出し・71保存）、復旧完了時点の承認USD 1の残額はUSD 0.7885107です。その後のDeepMind先行追加による消費・現在の残額は[追加受入記録](source-onboarding.md)で管理します。確定請求・GCS/Actions費用とは区別します。確定請求の照合[#116](https://github.com/Ningensei848/kaname/issues/116)は明細待ちでOpenです。

## 完了した受入

- [x] 既存失敗と実GCSの基準（index336/pending71・Google連続失敗6）を確認。
- [x] standardの構造診断と任意の費用停止制御を実装し、費用制限付きstandardの件数拡大・元単価による監査を追加。PR #164/#166/#167を取込済み。
- [x] 全保留の71件を保存。41件まとめたrunは41HTTP試行/41保存・再試行/不明usage/失敗0、59画像を含む全41Noteが公開適合。実audit-runは全407行/pending0/issues0。
- [x] 保存済み1件/検索語1つの旧スペース形式を、再生成・元Note/receipt/IDの変更なしで互換受入。PR #168取込、Python609件・関連143件・PR/main Python/Web CI成功。
- [x] 固定実125件のローカルGit版でexport/build/Chromium成功。検索936リンク・画像243要求・外部resource通信0。
- [x] 追加生成0の本番再実行でcollection/audit/cost/export/Git/Pagesすべてsuccess。新規生成/保存0、両source_completed/pending0/healthy。
- [x] 既存875オブジェクト（Note/receipt/index/usage/Batch台帳/既存run）の世代・内容、pending bytes、日次/月次費用不変を実GCSで照合。新規の課金・Noteオブジェクトなし。
- [x] 公開最新版125件・936検索リンク、全最新版のGCS Note/receipt/indexとsnapshot bytesが一致。保存した71件の配信HTML hashとartifact、配信manifestを照合。
- [x] #139/#140/#165をCloseし、未完了Issueを整理。

## 実行と費用の記録

| 実行 | 新規呼出し / 保存 | 費用推計USD | 結果 |
|---|---:|---:|---|
| [定期 38191452972](https://github.com/Ningensei848/kaname/actions/runs/38191452972) | 30 / 29 | 0.0934131 | 旧mainでLLM ValidationError 1件。usage欠損0。失敗として公開停止 |
| [限定 38192090307](https://github.com/Ningensei848/kaname/actions/runs/38192090307) | 1 / 1 | 0.002678 | 2画像・本文WikiLink 8件、保存/監査/費用/Git/Pagesすべてsuccess |
| [待機 38192547670](https://github.com/Ningensei848/kaname/actions/runs/38192547670) | 0 / 0 | 0 | writer steps未開始を確認して取消し。全保留の1 runへまとめた |
| [全保留 38193431223](https://github.com/Ningensei848/kaname/actions/runs/38193431223) | 41 / 41 | 0.1153982 | collection/audit/cost success。保存/usage確定後、旧公開検証の残工程を取消し。結果を次のゼロ生成runで公開 |
| [再実行 38195858526](https://github.com/Ningensei848/kaname/actions/runs/38195858526) | 0 / 0 | 0 | 全工程success。保存済み全結果の公開・保存/課金不変を受入 |

全保留runはinput147994/output28400/thinking0、限定runはinput3560/output644/thinking0です。全runの元単価とusageを保存し、失敗した1呼出しも費用へ含めています。standard単価input USD 0.30/百万token・output（thinking含む）USD 2.50/百万tokenは[公式価格](https://ai.google.dev/gemini-api/docs/pricing)と照合済みです。

## 旧検索語形式の補修

旧`concept()`は記号除去後に連続ASCIIスペースを残し、160文字で切った末尾も再適用で変わる場合がありました。保存済み407件のうち1件/検索語1つが公開検証で拒否されることを、ローカル実Note検査で発見しました。

新規の検索語/著者ラベルは記号除去後の空白と切断後の末尾を整理します。保存済みラベルは旧formatterが出力し得た形式だけを互換受入し、元bytesを保持します。構文区切り、非ASCII空白、長さ超過、本文への未審査WikiLinkは拒否します。画像の削除や型変換で生成拒否を成功扱いにする変更はありません。

PR #168の[PR CI](https://github.com/Ningensei848/kaname/actions/runs/38195232555)・[main CI](https://github.com/Ningensei848/kaname/actions/runs/38195525317)と、固定実125件のChromium・本番配信照合が成功しました。費用制御の対象と見積り・停止条件は[運用手順](operations.md#費用を限定したstandard収集)にあります。

## 公開版

- content commit: `dfd4aebed88f22bbd7f3538511d4e019ee4ae5ae`
- dataset digest: `d12a18435e240adba90dd0750135e6a8894d325a9572302838043cd44ea781c0`
- artifact digest: `b93e7c65744b74f7ddad79302a06db827871441a5e3c1a0dbc15f57205e4d273`

通常復旧の受入時、[本番配信](https://ningensei848.github.io/kaname/)は上記manifestと一致しました。その後の最新公開版は[DeepMind追加記録](source-onboarding.md)で確認できます。ローカル検証用commitは本番commitと区別し、受入は実配信で確認しています。
