# 日次Web検証の短縮

2026-10-13 JST、実装・本番受入中です。公開156件の生成0 runでは収集28秒に対し、Web環境準備62秒・Release復元12秒・build/検証111秒、全体411秒でした。[元run](https://github.com/Ningensei848/kaname/actions/runs/38364553083)を基準に工程別に測ります。

同じHTMLを検索リンク・アンカー・通常リンク・出典で最大4回解析していました。`link_acceptance.parse_html`で検証済みartifactから1回だけ解析し、同じ検証の各工程へ渡します。HTMLのID集合も一度作り、内部アンカーを照合します。別runや別artifactへ解析結果・成功判定を持ち越しません。

画像入り102 Noteのブラウザ検査も直列でした。`image_acceptance.check_image_pages`で最大2つのブラウザへ分割します。Pythonの各threadが自身のPlaywright/runtime/browser/contextを所有し、オブジェクトをthread間で共有しません。検索等のブラウザを閉じてから画像のpoolを起動し、同時browser数も最大2です。全画像の読込み・重複・4幅のoverflow・JSエラーと予期しない外部通信の拒否を維持し、どのworkerの失敗も受入失敗とします。

検索操作・新しいタブ・出典・元Markdown・版表示・全静的リンク/アンカー・4幅・私的pathの404確認も維持します。画像は以前と同じローカル代替応答を使い、元画像hostへ通信しません。`check:pages -- --image-workers 1`で画像検証を直列へ戻せます。上限は2で、0・3以上・bool等の不適合値を拒否します。

Quartz自体は1 threadを維持します。固定engineの並列処理はMarkdownの128件単位のchunkで、現規模では158入力を128/30件に分けます。他のCPU検査終了後に同じ156件を測定すると、1 threadは18.327秒・2 threadは19.020秒、全artifact digestは一致しました。この測定で速度向上は得られないため、通常設定を増やしません。検索・タグ・関連リンク・全文indexの再生成とHTML全体buildは維持します。

## 検証・受入

- [x] 関連72件成功。Unicode/相対/絶対/拡張子付きのアンカー、検索リンクの改変・rel/target/graph違反を拒否。実Chromium2つで各Noteを1回訪問し、画像を代替応答で検査。worker JSエラー/外部通信を拒否、直列切戻しを確認。
- [x] 実156件の同じartifactで1/2画像ブラウザを比較した初期案は113.940→98.937秒。検索1,377リンク・画像入り102ページ・画像259応答・外部通信0・元bytes不変。最終版はpool前に検索のブラウザを閉じて同時数を2に抑え、本番の工程時間はActionsで別途測ります。
- [x] 全Python735件・actionlint成功。
- [ ] PR/mainのPython/Web CI。
- [ ] 追加生成0の日次で全工程・GCS保存/費用・Release/公開版不変と実工程時間を受入。

別run間のprivate GCS cache、ReleaseのHTTP重複取得、Web環境そのものの再利用、差分HTML buildは別の候補です。今回の効果を未測定の候補の効果と混同しません。
