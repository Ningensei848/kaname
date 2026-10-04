> 履歴資料：当時の判断・検証・作業記録です。現在の仕様は[仕様書](../../specification.md)、現状は[検証・受入](../../verification.md)を参照してください。本文の過去の状態を現在の実装状況として扱わないでください。

# source利用条件の確認資料 — 2026-10-01

対象は、Google Research / GitHub Blogの公開RSSと公開記事を取得し、変換後Markdownの先頭
20,000文字までをGeminiへ送信して日本語要約を非公開GCSへ保存するPhase 1の運用です。
記事原文とraw HTMLは保存せず、公開ホスティングやモデル学習はこの実装の対象に含めません。

## 取得と保存の現状

両sourceは現在有効です。HTTP実装はrobots.txt確認、host単位2秒以上の間隔、timeout、
response上限、redirect先の再検査を行います。robotsの拒否・取得障害時は記事取得を止めます。
robotsによるアクセス可否だけでGemini送信・保存の利用条件が確認済みとは扱いません。
2026-10-01の再取得では両robots.txtがHTTP 200で、Google Researchは `Allow: /`、
GitHub Blogは空の `Disallow:` でした。両サイトfooterのTermsリンクも上記規約へ到達することを確認しました。

## 確認先と残る判断

| source | 公式確認先 | 確認内容と残る判断 |
|---|---|---|
| Google Research | [Google利用規約（日本）](https://policies.google.com/terms?hl=ja&gl=jp)、[robots.txt](https://research.google/robots.txt) | 利用規約は機械可読指示に反する自動取得を禁じ、第三者の知的財産権の尊重と送信するcontentの権利確認を求める。robotsを遵守した取得と、個々の記事のGemini送信・非公開要約保存を区別してユーザーが最終判断する。 |
| GitHub Blog | [GitHub Terms of Service](https://docs.github.com/en/site-policy/github-terms/github-terms-of-service)、[robots.txt](https://github.blog/robots.txt)、各記事の表記 | TermsのG節ではGitHub等がcontentの知的財産権を保持し、明示許諾または法による権利以外を留保する。公開repositoryのfork権やpolicy文書のCC0をBlog記事の許諾とみなさない。個別記事の条件とGemini送信・非公開要約保存をユーザーが最終判断する。 |
| AWS News | [AWS Site Terms](https://aws.amazon.com/terms/) | 自動取得に関する制限のため無効を継続。書面許諾等を確認するまで有効化しない。 |

2026-10-01に上記Google/GitHubの規約を参照しました。GitHub Blog記事に適用される
個別の追加条件と、要約処理を許す具体的な権利根拠の確認は未完了です。
初回確認ではGoogle Researchの成功Noteはありませんでしたが、2026-10-02の手動runで26 Noteを保存し、
2 Noteを原記事と照合しました。詳細は[検証記録](verification.md)へ記録しています。

## 最終受入で記録すること

- ユーザーがGoogle Research / GitHub Blogの取得・Gemini送信・非公開要約保存について判断した日付と対象範囲。
- 制限するsourceがある場合の `config/sources.yaml` の変更と既存pendingの保留。
- 上限30件のPRのmerge commitとscheduled runの結果。

2026-10-02に、ユーザーが本資料を含むPR #90をmergeし、「マージした。続けて。」と指示しました。
提示したGoogle Research / GitHub Blogの取得・Gemini送信・非公開要約保存の運用について、
受入継続の承認として記録します。個別の利用許諾取得を証明する記録ではありません。
Quartz等で公開する場合は、公開対象と再配布条件を別途確認します。
