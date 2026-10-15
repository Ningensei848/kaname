# GCS読取りの並列数・接続再利用 — 本番受入完了

2026-10-15 JST、[PR #191](https://github.com/Ningensei848/kaname/pull/191)・main CI・[生成0の本番run](https://github.com/Ningensei848/kaname/actions/runs/38734712249)まで受入完了しました。同じ216記事でGCS取得56.405→22.501秒（60.11%短縮）、全件監査62→27秒、日次全体469→422秒（10.02%短縮）です。全件検査を維持し、追加Gemini費用は0です。単一のrun間比較で、継続的な時間はrunner・queue・配信待ちでも変わります。

## 変更と責務

`read_snapshot`が最大16件で取得し、世代条件付きdownload・CRC32C・取得前後のlive catalog確認・全件監査を継続します。世代別cacheは同じprivate runner内だけで使い、catalogや検証結果をrun間で再利用しません。未変更bytesのcache利用と、Note/receipt/index/usageの検査は従来どおりです。

GCS backendはSDKが作った認証済みSessionを保持し、Storage endpointに限って標準HTTP接続の再利用枠をworker数へ揃えます。SDKのretry設定・Sessionの認証設定・その他endpointは変更せず、独自/TLS用adapter subclassは置き換えません。書込みの並列化やretry追加は行いません。requestsは既存lockの2.34.2のまま、直接利用をpyprojectにも明示します。

日次はrepository variable `GCS_READ_WORKERS`（省略時16）、ローカルCLIは`TECHKB_GCS_READ_WORKERS`で1〜16を選べます。8で従来の並列数、1で逐次へ戻せます。不正な値は日次の設定検証でGCP認証・有料生成前に拒否します。

## 実Actions比較

| 工程 | 8並列 | 16並列 |
|---|---:|---:|
| GCS取得（999個・download数同じ） | 56.405秒 | 22.501秒 |
| GCS全件監査 | 62秒 | 27秒 |
| 日次全体（queue込み） | 469秒 | 422秒 |
| collect job | 156秒 | 104秒 |
| publish job | 47秒 | 48秒 |
| pages / build job | 209秒 | 189秒 |
| pages / deploy job | 43秒 | 64秒 |

[変更前run](https://github.com/Ningensei848/kaname/actions/runs/38730037020)と変更後runで、同じ216 Note・content/dataset/artifactを維持しました。本文HTTP・API試行・生成・保存は0、exportは998件すべてcache hitで追加download0です。pool調整・並列数を合わせた変更の効果であり、pool単独の寄与を分離した測定ではありません。

## ローカル比較

実GCSの999オブジェクトを、byte cacheなし・各構成で新しいSDK clientを作って比較しました。全構成で世代・CRC・SHA-256・498成功行/保留80件の監査結果が一致し、GCS書込み・Gemini呼出しは0です。

| 構成 | 取得秒 | catalog再検証・監査込み秒 |
|---|---:|---:|
| 8並列・標準pool（初回） | 10.942 | 12.786 |
| 16並列・標準pool | 3.844 | 4.900 |
| 16並列・pool調整 | 3.386 | 4.523 |
| 8並列・標準pool（再比較） | 7.106 | 8.414 |
| 16並列・pool調整（再比較） | 3.128 | 4.120 |

[数値証拠](archive/2026-10/gcs-read-local-2026-10-15.json)を保存しました。初回の接続/DNS準備やサーバ側の状態も影響するため再比較を含めています。ローカルとGitHub runnerの絶対時間を混同せず、pool単独の効果もこの少数試行から断定しません。Googleの[transfer manager資料](https://docs.cloud.google.com/python/docs/reference/storage/latest/google.cloud.storage.transfer_manager)にも、多数の小さいファイルではTHREADが効率的な場合があると記載されています。

## 検証・受入

- [x] 8/16並列上限・世代変更拒否・CRC/cache/公開拒否・環境値の1/8/16切戻し・認証/retry/独自TLS保持を検証。関連94件と変更箇所78件が成功。
- [x] ローカルのGCS全件監査・費用・公開216件の全bytesを独立照合。全体degraded、DeepMindは91成功行/13保留/failing/streak2を保持。
- [x] Python全786件/Web5件・PR/main CI・actionlintが成功。実Actionsで同じ216記事・生成0を比較し、全読取り16 workers、main CI成功の再利用も確認。
- [x] 独立GCS読取りで既存1079世代/CRC・全498成功行・元usage/費用・公開216件の全bytes一致。旧80候補を全項目保持、新候補0件追加、現在保留80件。5 Release/10 assetsのID/size/digest、content/dataset/artifact・Git全219ファイル・公開snapshot全218ファイル・実配信版/全元Markdownを照合。

GCSの1,080オブジェクトの比較基準は変更前の収集checkpoint後・変更後runの前に取得しました。pendingの同bytes書直し以外の1,079世代/CRCは保持し、追加は生成0 report 1件だけです。読取り中と監査後のcatalogも不変でした。現在の保留80件はDeepMind13/GitHub4/Google Research3/Microsoft11/Meta13/Apple16/Cloudflare20で、全体degraded・各sourceの健全性を保持しています。

## 費用と作業状態

[2026-10-15通常日次](https://github.com/Ningensei848/kaname/actions/runs/38660489853)は30 API試行/30保存、input92,321/output17,378/thinking0、不明usage0です。元の単価による推計USD 0.0711413を以前の累積USD 0.3749107へ一度だけ加算し、追加承認USD 1の累積USD 0.4460520・残額USD 0.5539480とします。今回の性能試験は新規生成0です。

作業一覧のGCS取得短縮を完了表へ移しました。[各工程と保存/費用の受入証拠](archive/2026-10/gcs-read-acceptance-2026-10-15.json)を保存しています。長期的な全体時間の安定、run間のprivate cache、Releaseの重複HTTP、Pages配信待ちは別の後続です。確定請求照合#116は明細待ちを維持します。
