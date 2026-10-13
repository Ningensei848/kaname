# 日次Web検証の性能調査

2026-10-13 JST、実装・本番受入完了です。公開156件の生成0 runでは収集28秒に対し、Web環境準備62秒・Release復元12秒・build/検証111秒、全体411秒でした。[元run](https://github.com/Ningensei848/kaname/actions/runs/38364553083)を基準に工程別に測ります。

同じHTMLを検索リンク・アンカー・通常リンク・出典で最大4回解析していました。`link_acceptance.parse_html`で検証済みartifactから1回だけ解析し、同じ検証の各工程へ渡します。HTMLのID集合も一度作り、内部アンカーを照合します。別runや別artifactへ解析結果・成功判定を持ち越しません。

画像入り102 Noteのブラウザ検査も直列でした。`image_acceptance.check_image_pages`で最大2つのブラウザへ分割します。Pythonの各threadが自身のPlaywright/runtime/browser/contextを所有し、オブジェクトをthread間で共有しません。検索等のブラウザを閉じてから画像のpoolを起動し、同時browser数も最大2です。全画像の読込み・重複・4幅のoverflow・JSエラーと予期しない外部通信の拒否を維持し、どのworkerの失敗も受入失敗とします。

検索操作・新しいタブ・出典・元Markdown・版表示・全静的リンク/アンカー・4幅・私的pathの404確認も維持します。画像は以前と同じローカル代替応答を使い、元画像hostへ通信しません。`check:pages -- --image-workers 1`で画像検証を直列へ戻せます。上限は2で、0・3以上・bool等の不適合値を拒否します。

Quartz自体は1 threadを維持します。固定engineの並列処理はMarkdownの128件単位のchunkで、現規模では156 Noteと一覧/版表示等の14ページ、計170入力を128/42件に分けます。他のCPU検査終了後に同じ156件を測定すると、1 threadは18.327秒・2 threadは19.020秒、全artifact digestは一致しました。この測定で速度向上は得られないため、通常設定を増やしません。検索・タグ・関連リンク・全文indexの再生成とHTML全体buildは維持します。

## 検証・受入

- [x] 関連72件成功。Unicode/相対/絶対/拡張子付きのアンカー、検索リンクの改変・rel/target/graph違反を拒否。実Chromium2つで各Noteを1回訪問し、画像を代替応答で検査。worker JSエラー/外部通信を拒否、直列切戻しを確認。
- [x] 実156件の同じartifactで1/2画像ブラウザを比較した初期案は113.940→98.937秒。検索1,377リンク・画像入り102ページ・画像259応答・外部通信0・元bytes不変。最終版はpool前に検索のブラウザを閉じて同時数を2に抑え、本番の工程時間はActionsで別途測ります。
- [x] 全Python735件・actionlint成功。
- [x] [PR #184](https://github.com/Ningensei848/kaname/pull/184)取込・[最終PR CI](https://github.com/Ningensei848/kaname/actions/runs/38391958012)・[取込後main CI](https://github.com/Ningensei848/kaname/actions/runs/38392516675)のPython/Web成功。
- [x] [生成0の本番run](https://github.com/Ningensei848/kaname/actions/runs/38395575197)で全工程success。本文HTTP/生成/保存/追加Gemini費用0、既存950オブジェクト世代/CRC・成功index/Note/receipt/元usage・費用不変、保留126件の全項目とbytes保持（同内容のpending書直しだけ世代更新）。3 Release/6 assetsのID/size/digest・公開commit/dataset/artifact・実配信不変。

初回の[本番試行](https://github.com/Ningensei848/kaname/actions/runs/38393154698)は、収集前の通常pytestで新しい実ブラウザテストがPlaywright不在により失敗しました。GCS認証・収集・生成・保存・配信はskipです。[通知#185](https://github.com/Ningensei848/kaname/issues/185)は本番受入完了まで修正後の本番受入を確認してCloseしました。

実ブラウザの4ケースを`web/tests`へ移し、Web CIで必ず実行します。通常の`tests`にはHTML/アンカー/検索と、ブラウザ不要の入力上限/空集合検査を残し、収集jobの依存を増やしません。[PR #186](https://github.com/Ningensei848/kaname/pull/186)取込、修正後の全Python732件と実Web4件・PR/main CIが成功。Playwrightをimportできない通常pytestも727成功/既存任意module1 skipを再現し、収集jobの実行と生成0での受入を完了しました。

別run間のprivate GCS cache、ReleaseのHTTP重複取得、Web環境そのものの再利用、差分HTML buildは別の候補です。今回の効果を未測定の候補の効果と混同しません。

## 通信の追加改善 — 実装・検証中

最初の本番比較ではWeb工程の改善は3秒に留まり、監査/配信の変動で全体は49秒増えました。これを日次全体の短縮達成と扱いません。ローカルpreview serverはHTTP/1.0でresourceごとに接続を閉じていたため、HTTP/1.1・Content-Length・TCP_NODELAYで再利用します。redirect/HEAD/元bytes/私的path拒否を実TCP接続で回帰検証します。

各画像のscroll・実読込み・重複検査も、以前は3回のPython/ブラウザ往復でした。実際にscrollしながら1回の待機条件で`complete`/`naturalWidth`/一意性を同時に検査し、重複は即座に拒否します。遅延読込みの強制eager化や画像/画面幅検査の省略は行いません。実156件の計数/bytes・CI・本番の再比較で採用効果を確認します。

追加案のローカル全156件は93.435→80.346秒、同じ1,377リンク/画像入り102頁/259画像応答・外部通信0。通常Python733件、持続TCP接続と実ブラウザを含む関連23件も成功しました。初段階の本番値を追加案の成功値で上書きせず、次の生成0 runを別記録で比較します。

## 実Actionsの結果

同じ156 Note/1,377検索リンク/画像入り102ページ/画像259応答で、Web build/検証は111→108秒（2.7%短縮）、全体は411→460秒でした。全リンク・全画像・4画面幅を維持し、Quartz全体buildも継続しています。単一run同士の比較で、runner準備・queue・通信時間は変動します。

[ローカル測定](archive/2026-10/web-validation-local-2026-10-13.json)と[本番受入JSON](archive/2026-10/web-validation-acceptance-2026-10-13.json)へ計数・固定版・各工程の時間を保存しました。最終版のローカル検証は93.435秒で、同時browser最大2・検証計数一致。DeepMind69保留/failing/streak2などのsource未完了状態を維持し、性能検証の成功をsourceの全件完了と扱いません。

初回の収集前テスト失敗と全951世代不変・API呼出し0の証拠は[失敗記録](archive/2026-10/web-validation-failed-attempt-2026-10-13.json)に残します。
