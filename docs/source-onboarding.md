# RSS追加 — DeepMindの限定受入

2026-10-12 JST、ユーザーの選択により、既存[PR #134](https://github.com/Ningensei848/kaname/pull/134)の5候補からDeepMindを先に進めます。他4社は無効の候補として保持します。元PRの古いCI成功だけを本番受入とは扱いません。

## 取得と条件の確認 — 完了

既存のrobots検査付きFetcherで5フィードと各1記事を取得できました。robotsは各HTTP 200で、現行User-Agentのフィード取得を許可しています。Gemini/GCS/公開の更新は行っていません。

| 候補 | RSS件数 | 状態と根拠 |
|---|---:|---|
| Google DeepMind | 100 | 先行対象。新旧3記事と初回100候補を確認。Google Blogへのredirectにも各hopのrobots検査を適用。[Google利用規約](https://policies.google.com/terms?hl=en-US)の機械可読指示・第三者権利の条件と既存の公開方針に従う。ユーザーの選択は第三者からの個別許諾取得を証明しない |
| Microsoft Research | 10 | 無効の候補。[公式条件](https://www.microsoft.com/en-us/legal/terms-of-use)のDocumentsの限定用途・ネットワーク掲載・改変・画像の条件を、外部AI送信と公開要約へどう適用するか未確認 |
| Engineering at Meta | 9 | 無効の候補。footerの[Terms](https://www.facebook.com/policies)はloginへ移動。[自動取得条件](https://www.facebook.com/legal/automated_data_collection_terms)もloginとなり、Blog/RSSへの適用範囲を確認できていない。認証回避しない |
| Apple ML Research | 10 | 無効の候補。footerの[公式条件](https://www.apple.com/legal/internet-services/terms/site.html)は自動取得と掲載/配布を制限。RSSの提供を本文のAI利用・公開許諾とみなさない |
| Cloudflare Security | 20 | 無効の候補。[robots](https://blog.cloudflare.com/robots.txt)は`ai-input=yes`を示す一方、[公式条件](https://www.cloudflare.com/website-terms/)§8はAI用途botの明示許可・専用User-Agentを要求。現行取得器との適合を確定していない |

上記は運用の確認状態です。取得できること、AI利用できること、生成要約を公開できることを同一視しません。他4社の有効化は今回の受入へ含めません。

## 本文抽出 — 実装・ローカル検証完了

ページ全体の変換では新記事のナビゲーションが入力枠を消費します。旧DeepMind記事では汎用のarticle優先抽出が関連記事カードを選び、実本文を落とす例もありました。

source固有のセレクタで、旧`template-blog-page`の本文rich-textを含むsectionと、移動先Google Blogの`article.uni-article-wrapper`を取得します。`article_domains`で最終取得先をDeepMind/Google Blogに限定し、範囲外は本文変換・生成前にfilterして処理済みとします。この設定は最終URLを判定するもので、HTTP redirect通信自体の許可リストではありません。各hopのrobots/公開host検査は既存Fetcherが行います。空の設定は既存sourceの動作を維持します。

対象内で本文セレクタが一致しなければ生成前に停止し、pendingを維持します。本文の取得失敗を汎用抽出で隠しません。

実取得済み3記事の本文は9,246 / 1,745 / 7,376文字、画像候補4 / 0 / 3件です。すべて入力上限20,000文字以内で、関連記事カードを除外できました。新旧の合成corpusと、本文末尾/図の保持・ナビゲーション変更で再生成0・本文不一致で生成0の回帰を追加しました。原記事本文や画像bytesはrepositoryへ追加しません。

初回100候補の無課金検査では97件の本文を抽出でき、3件はCloud Blog/Antigravityへ移る別レイアウトでした。今回の先行対象から最終hostで除外します。ブラウザ取得や別サイトの本文抽出を自動で拡大しません。

## 本番受入 — 未完了

- [ ] 更新後PR CIとmain CIを確認。
- [ ] 実GCSのindex/pending/usageと他writer不在を読取り確認。
- [ ] 最大1 standard呼出しの限定runで実Noteの保存・監査・費用・Git/Pagesを確認。USD 1の既存承認残額USD 0.7885107を超える追加生成をしない。
- [ ] 生成されたNote/receipt/indexと公開snapshot/配信を照合。拒否・不明usage・曖昧な提出では追加生成を停止して診断。
- [ ] 追加生成0の再実行で保存/課金の不変を確認し、本番受入を完了として記録。

初回RSSには100件の過去記事が含まれます（先行対象97件・対象外3件）。限定1件の成功と全対象記事の受入を区別し、追加生成0のrunに残り記事を生成させません。通常の1日1回schedule・全source合計30件・本文20,000文字・standard・workers 2は維持します。

以前の月500〜550円は2 sourceの実行履歴に基づく推定です。新sourceの初回backlogや実呼出し数の増加後にも同額になる保証とは扱いません。新runの元usage/単価を残し、既存承認の累計へ追加します。請求明細との確定照合[#116](https://github.com/Ningensei848/kaname/issues/116)は引き続き明細待ちです。
