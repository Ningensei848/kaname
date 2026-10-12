# Daily TechKBの所要時間短縮

2026-10-12 JST、日次runの長時間化を調査し、通信待ちと重複読取りを削減します。Python/Nodeの役割とGCSの書込み境界を保って、実測を基準に変更します。

## 調査 — 完了

直近の成功5 runは23〜39分でした。Gemini生成0のrunでも長時間で、全Note/receiptの逐次GCS読取りとexportの再読取りが支配的です。最新runのPages環境準備は61秒、ビルド/検査91秒、deploy/配信照合約35秒。Pythonの全テストは29秒で、削除による効果は小さいため維持します。

| run | 全体 | 収集 | 監査 | 費用/計画 | 通知 | export |
|---|---:|---:|---:|---:|---:|---:|
| [38218566607](https://github.com/Ningensei848/kaname/actions/runs/38218566607) | 39.37分 | 9.15分 | 7.42分 | 2.90分 | 1.40分 | 13.75分 |
| [38213251145](https://github.com/Ningensei848/kaname/actions/runs/38213251145) | 26.98分 | 7.58分 | 4.30分 | 1.47分 | 1.15分 | 8.13分 |
| [38210790344](https://github.com/Ningensei848/kaname/actions/runs/38210790344) | 27.55分 | 7.57分 | 4.30分 | 1.58分 | 1.18分 | 8.83分 |
| [38195858526](https://github.com/Ningensei848/kaname/actions/runs/38195858526) | 31.27分 | 3.95分 | 6.50分 | 2.40分 | 1.40分 | 12.53分 |
| [38192090307](https://github.com/Ningensei848/kaname/actions/runs/38192090307) | 23.32分 | 3.85分 | 4.42分 | 1.65分 | 0.98分 | 8.35分 |

従来の`GCSStore.read`は1オブジェクトごとにmetadata取得と世代指定の本文取得を行います。監査では過去408成功行のNote/receiptを逐次取得し、exportも全世代の整合性検査後に同じbytesを再取得して競合を検知します。費用/通知は別CLIで同じrun/usageを繰り返し取得していました。

記事は最大2件の先行取得でも、sourceごとに並んだcandidateとhost単位の間隔/transport lockにより同一hostの通信を直列化します。並列数を増やすだけでは同じhostの間隔を短縮できません。取得順や再検査頻度を変えることはfreshness/課金対象の変更になるため、今回は通信層の重複を先に削減します。

## 実装 — 完了・実CI/Actions受入待ち

- `storage.py`は世代指定の読み書き、競合拒否、clientの所有を担当。
- `read_snapshot.py`は読取り専用の世代catalog、最大8件の並列ダウンロード、CRC32C検査とcacheを担当。raw HTMLは取得対象に含めません。
- `audit.py`/`costs.py`/`publication`は既存の全件の整合性・課金・公開ポリシー検査を維持。CLIが必要prefixの読取りcontextを選び、成功結果や通知の適用前にlive catalogを再確認します。
- exportは出力をinstallする前にlive catalogを再確認。追加/削除/置換/同じbytesの世代更新を拒否し、indexは最後に再確認します。
- 日次runnerの`TECHKB_READ_CACHE`を共用し、bucket/name/generation/CRCで一致する過去bytesだけを再利用。監査→export、費用→通知で追加本文ダウンロードを避けます。cacheはprivateなrunner一時領域のみ、Actions cache/artifactへ保存しません。**別run間の永続cacheではありません**。cache破損時は再取得し、検査結果自体はcacheしません。
- 課金・GCS更新は既存の単一writerを維持。Node/Quartzはpublic snapshotからのレンダリングとbrowser検査の責務を維持します。

[Cloud Storageの強い整合性](https://docs.cloud.google.com/storage/docs/consistency)と[世代の前提条件](https://docs.cloud.google.com/storage/docs/request-preconditions)を基準に、本文を再取得する代わりにlive catalogの世代/CRCを照合します。一覧全体を原子的transactionとは扱いません。

## 実GCSの読取り専用測定 — 完了

ローカルADC、同じindex408/pending145/公開126件の測定です。Actionsとは通信条件が異なるため、この値をActionsの短縮保証に使いません。

| 工程 | 取得objects | 本文download | cache hit | 全体 |
|---|---:|---:|---:|---:|
| 監査・cold | 819 | 819 | 0 | 5.935秒 |
| export・warm | 818 | 0 | 818 | 2.298秒 |
| 費用・cold | 64 | 64 | 0 | 0.527秒 |
| 費用・warm | 64 | 0 | 64 | 0.218秒 |

監査の成功/件数・日次/月次費用/元usageと価格・公開dataset digestが従来版と完全一致。GCS書込み/Gemini呼出し0。

## 本番受入 — 未完了

- [x] 全Python642件（並列読取り・世代競合/cache破損/公開前停止10件を含む）とactionlintが成功。
- [ ] WebとPR/main CI。
- [ ] mainから生成0の日次runを実行し、全工程の時間・cache hit/downloadを比較。
- [ ] 既存Note/receipt/index/usage/Batchの世代・元費用、公開126件のbytes/配信版を保持して完了。

差分Quartzビルドや前回artifactの再利用には、Note以外のリンク/タグ/検索index、Webコード/config/lock変更、切戻しの無効化条件が必要です。今回の支配的なGCS読取りを先に解消し、残る時間を本番で計測して後続の優先順位を決めます。
