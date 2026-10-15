# GCS読取りの並列数・接続再利用 — 本番受入中

2026-10-15 JST、日次のGCS全件監査を維持したまま、読取りを既定8→16並列とする変更に着手しました。変更前の186記事版では監査70秒のうち939オブジェクトの取得が64.565秒でした。最新通常日次は30件を保存し、index498/public216/pending80です。今回の比較はこの216記事版で生成0として実施します。

## 変更と責務

`read_snapshot`が最大16件で取得し、世代条件付きdownload・CRC32C・取得前後のlive catalog確認・全件監査を継続します。世代別cacheは同じprivate runner内だけで使い、catalogや検証結果をrun間で再利用しません。未変更bytesのcache利用と、Note/receipt/index/usageの検査は従来どおりです。

GCS backendはSDKが作った認証済みSessionを保持し、Storage endpointに限って標準HTTP接続の再利用枠をworker数へ揃えます。SDKのretry設定・Sessionの認証設定・その他endpointは変更せず、独自/TLS用adapter subclassは置き換えません。書込みの並列化やretry追加は行いません。requestsは既存lockの2.34.2のまま、直接利用をpyprojectにも明示します。

日次はrepository variable `GCS_READ_WORKERS`（省略時16）、ローカルCLIは`TECHKB_GCS_READ_WORKERS`で1〜16を選べます。8で従来の並列数、1で逐次へ戻せます。不正な値は日次の設定検証でGCP認証・有料生成前に拒否します。

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
- [ ] PR/mainの必須CI・実Actionsで同じ216記事の生成0比較。
- [ ] 変更後の保存・元usage/費用・旧保留候補・Release/公開全bytes・配信の不変確認。

## 費用と作業状態

[2026-10-15通常日次](https://github.com/Ningensei848/kaname/actions/runs/38660489853)は30 API試行/30保存、input92,321/output17,378/thinking0、不明usage0です。元の単価による推計USD 0.0711413を以前の累積USD 0.3749107へ一度だけ加算し、追加承認USD 1の累積USD 0.4460520・残額USD 0.5539480とします。今回の性能試験は新規生成0です。

作業一覧のGCS取得短縮を受入中とし、完了後に完了表へ移します。長期的な全体時間の安定、run間のprivate cache、Releaseの重複HTTP、Pages配信待ちは別の後続です。確定請求照合#116は明細待ちを維持します。
