# RSS追加 — DeepMindの限定受入完了

2026-10-12 JST、ユーザーの選択により、既存[PR #134](https://github.com/Ningensei848/kaname/pull/134)の5候補からDeepMindを先行追加し、実1件の保存/公開・追加生成0の本番受入まで完了しました。この受入時は他4社を無効の候補として保持しました。その後の明示指示による[4社有効化](four-source-activation.md)は別の記録で管理します。以下の無効/未確認の記載は初期確認時点の状態です。元PRの古いCI成功だけを本番受入とは扱いません。

## 取得と利用条件の初期確認 — 完了

既存のrobots検査付きFetcherで5フィードと各1記事を取得できました。robotsは各HTTP 200で、現行User-Agentのフィード取得を許可しています。この読取り検査ではGemini/GCS/公開の更新は行っていません。

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

初回100候補の無課金検査では97件の本文を抽出でき、3件はCloud Blog/Antigravityへ移る別レイアウトでした。最終host filter追加後の全100件再検査はsuccess（would_enrich97/filter3・失敗0・LLM0・GCS書込み0）です。今回の先行対象から最終hostで除外します。ブラウザ取得や別サイトの本文抽出を自動で拡大しません。

## 本番受入 — 限定1件の保存/公開・ゼロ生成再実行まで完了

- [x] 更新後[PR CI](https://github.com/Ningensei848/kaname/actions/runs/38210171406)と[main CI](https://github.com/Ningensei848/kaname/actions/runs/38210490547)が成功。全Python620件、source専用67件・本文/並列回帰、Webを確認。PR #134は`cd678b7d5a706e3937a1c54c30aabd2054183404`で取込済み。
- [x] 実GCSのindex407/pending0・未決済Batch/不明usage0と他writer不在を読取り確認。開始時877オブジェクトの世代/CRCを固定し、本番提出直前にも不変を照合。
- [x] [限定run](https://github.com/Ningensei848/kaname/actions/runs/38210790344)を最大1 standard呼出し・推計上限USD 0.10で開始。実Note/receipt 1件・index408/pending96・対象外filter3件・元usage確定（input3002/output623/thinking0・HTTP試行1・不明usage0）を確認。
- [x] 限定runの収集・監査・費用・export/Git/Pagesがすべてsuccess。新しい障害Issueなし。
- [x] 新規Noteが厳格な公開検証に適合。Note/receiptの本文bytesと、数値をTSV表現へ正規化したindex行が一致。入力打切りfalse。
- [x] 公開126件/検索リンク959件。全最新版のGCS Note/receipt/indexとsnapshot bytesが一致し、新規1件の配信HTML hashとartifact、site-manifestの実配信が一致。
- [x] [追加生成0の再実行](https://github.com/Ningensei848/kaname/actions/runs/38213251145)の収集はsuccess、新規呼出し/保存0・index408/pending96。既存880オブジェクト（保存/課金/既存run等）の世代/CRC、pending bytes、日次/月次費用不変、新規の課金/Noteオブジェクトなしを実GCSで照合。pendingの保存世代は更新されますが、内容は同一です。
- [x] ゼロ生成runの監査・費用・export/Git/Pagesすべてsuccess。公開commit/dataset/artifactとsite-manifest・新規Noteの配信HTMLが限定runの公開版と完全一致。限定受入を完了。

限定runとゼロ生成再実行後、既存2 sourceはhealthy/pending0/連続失敗0を維持しています。DeepMindは保存1/pending96/連続失敗0、全候補の完了前なのでSource Healthはunverifiedです。限定受入の成功を全sourceのhealthyや初回backlog解消と同一視しません。

初回RSSには100件の過去記事が含まれます（先行対象97件・対象外3件）。限定1件の成功と全対象記事の受入を区別し、追加生成0のrunに残り96件を生成させません。通常の1日1回schedule・全source合計30件・本文20,000文字・standard・workers 2は維持します。

以前の月500〜550円は2 sourceの実行履歴に基づく推定です。新sourceの初回backlogや実呼出し数の増加後にも同額になる保証とは扱いません。新runの元usage/単価を残し、既存承認の累計へ追加します。今回の限定1件は推計USD 0.0024581、通常復旧からの累計USD 0.2139474、承認USD 1の残額USD 0.7860526です。確定請求とは区別します。請求明細との確定照合[#116](https://github.com/Ningensei848/kaname/issues/116)は引き続き明細待ちです。

## 限定受入の公開版

- content commit: `b871690bda9ebe0d4712b473d75c9423f6550545`
- dataset digest: `bfdd3c297fcf1b2d2838a88ff8a647a0b6cb7db409dee4d5b9a624466940664a`
- artifact digest: `a04472f25c5e137128ecb1e60b7df5593b5a5ae1f51fdb86fcf2cced1683097f`

[本番配信](https://ningensei848.github.io/kaname/)のmanifestと新規NoteのHTMLを上記版と照合しました。
