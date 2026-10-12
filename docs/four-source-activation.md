# Microsoft Research / Meta / Apple / Cloudflareの有効化

2026-10-12 JST、ユーザーの「4候補も有効化してみて」という明示指示により、4社を有効化しました。取得・外部AI送信・生成Note公開の運用判断として記録し、第三者からの個別許諾取得や規約上の問題がすべて解消した証明とは扱いません。以前の保留理由は[初期確認記録](source-onboarding.md)に残しています。

## 設定・無課金検査 — 完了

| source | 本文セレクタ | 初回RSS / 本文取得 |
|---|---|---:|
| Microsoft Research | `.single-post__content` | 10 / 10 |
| Engineering at Meta | `main.site-main > article.post .entry-content` | 9 / 9 |
| Apple ML Research | `.postBody` | 10 / 10 |
| Cloudflare Security | `.article-content` | 20 / 20 |

49記事の実HTTP/robots・本文変換を既存Pipelineのdry-runで確認し、全4 sourceがsuccess、失敗/LLM呼出し/GCS書込み0でした。記事の最終hostも各sourceの公式hostに限定します。本文不一致では生成前に停止し、pendingを維持します。

Cloudflareのページ全体はサンプルで約46,800文字あり、ナビゲーションで入力20,000文字を消費していました。本文だけを選び、Microsoft/MetaのナビゲーションとAppleの関連記事も除外します。本文内の図・caption・末尾は保持します。4社の合成fixtureを追加し、corpusは7 source・8レイアウトです。本文/画像がモデルへ届くこと、厳格な公開適合、ナビゲーション変更で再生成0、本文不一致で生成0を検証しました。全Python632件・関連17件が成功。

## 利用条件と機械可読指示

2026-10-12に公式条件を再確認しました。[Microsoftの条件](https://www.microsoft.com/en-us/legal/terms-of-use)にはcontent/派生物とDocumentsの利用制限、[Appleの条件](https://www.apple.com/legal/internet-services/terms/site.html)には自動取得・送信/掲載の制限があります。Meta Blogのfooterの[Terms](https://www.facebook.com/policies)・[自動取得条件](https://www.facebook.com/legal/automated_data_collection_terms)はloginへ移り、公開Blog/RSSとの適用範囲は確定できていません。今回のユーザー指示をこれらの権利問題の解消と混同しません。

[Cloudflare robots](https://blog.cloudflare.com/robots.txt)は`User-agent: *`に`Allow: /`と`ai-input=yes`を示しています。[公式条件](https://www.cloudflare.com/website-terms/)§8のAI用途botの識別要件を踏まえ、実際の用途を表す専用User-Agent `KanameAISummarizer/0.1 (+https://github.com/Ningensei848/kaname)`へ変更しました。既知の別botを名乗らず、このUser-Agentで4社の全49記事の取得を確認しました。個別User-Agent名の特別許可を取得した記録ではありません。

robots拒否・取得不能・CAPTCHA/認証/paywallでは停止し、回避しません。raw HTML/原記事本文/画像bytesを公開せず、出典付きの生成要約を対象とする既存方針を維持します。AWS Newsは今回の指示の対象外で、無効を継続します。

## 本番反映 — 完了

- [x] [PR #171](https://github.com/Ningensei848/kaname/pull/171)を`bd507b95c693fd349cea8cd5d0569106f60b1646`で取込み。[PR CI](https://github.com/Ningensei848/kaname/actions/runs/38217788866)/[main CI](https://github.com/Ningensei848/kaname/actions/runs/38218186639)のPython/Webが成功。source専用79件も成功。
- [x] 実GCSの開始基準408成功/pending96・不明usage/未決済Batch0、882オブジェクトの世代/CRCと元費用を固定。他writer不在・提出直前の不変を確認。
- [x] 7 sourceの収集処理は成功。保存/生成/HTTP生成試行0、index408を保持し、元のpending96件の全項目を維持して新規49件を追加（pending145）。既存881オブジェクトの世代/CRC、Note/receipt/index/usage/Batchの集合、元価格による日次/月次費用は不変。全有効sourceの連続失敗0を確認。
- [x] [生成0の本番run](https://github.com/Ningensei848/kaname/actions/runs/38218566607)の7 source受付・監査・費用・export/Git/Pages・配信版確認がすべてsuccess。既存DeepMind96件と新規4社49件を保留として管理。
- [x] 既存Note/receipt/index/usage/Batch/既存runの世代・内容、日次/月次費用の不変を照合。公開126件の最新Note/receipt/indexとsnapshot bytesが一致、959検索リンクを検証。公開commit/dataset/artifactと実配信manifest・HTML hashも前回版と一致。新sourceからの実Note生成は今回の生成0検証に含めない。

通常scheduleは1日1回・全source合計30件、本文入力20,000文字・standard・workers 2を維持します。初回保留145件（DeepMind96 / Microsoft10 / Meta9 / Apple10 / Cloudflare20）は通常運用で順次処理します。Google Research/GitHubはhealthy、DeepMindと追加4社は保留があるためunverifiedです。取得成功と実Note生成の受入を区別します。追加APIの既存USD 1枠は累計USD 0.2139474、残額USD 0.7860526で、今回の無課金検査による追加はUSD 0です。確定請求[#116](https://github.com/Ningensei848/kaname/issues/116)は明細待ちを維持します。

過去の月500〜550円の推定は当時の2 sourceと実行履歴を基準としたものです。7 sourceでも1日全体30件の上限は維持しますが、記事の長さや処理件数が変わるため、同じ月額になるとは確定していません。通常runの元usageで追跡し、確定明細が届いたら#116で照合します。

本番配信の固定値：content `b871690bda9ebe0d4712b473d75c9423f6550545`、dataset `bfdd3c297fcf1b2d2838a88ff8a647a0b6cb7db409dee4d5b9a624466940664a`、artifact `a04472f25c5e137128ecb1e60b7df5593b5a5ae1f51fdb86fcf2cced1683097f`。無課金検査から本番の受付・配信まで受入完了。
