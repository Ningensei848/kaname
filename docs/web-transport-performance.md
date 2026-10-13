# Web検証の通信短縮 — 受入完了

2026-10-13 JST、[PR #187](https://github.com/Ningensei848/kaname/pull/187)と取込後main CI・[生成0の本番run](https://github.com/Ningensei848/kaname/actions/runs/38400686121)が成功しました。Web build/検証は108→99秒（8.33%短縮）、全体は460→445秒でした。最初の156件版のWeb111秒からは約10.81%短縮です。全体445秒は以前の411秒より長く、日次全体の継続的な短縮達成とは扱いません。

## 原因と変更

preview serverがHTTP/1.0でresourceごとに接続を閉じ、ブラウザ検証では数千回のローカル通信が発生していました。HTTP/1.1の持続接続、正確なContent-Length、TCP_NODELAYへ変更しました。redirect/HEAD/元bytes/私的pathの404を同じ実TCP接続で確認します。公開サイトの配信方式やartifactのbytesは変更しません。

各画像のscroll・実読込み・重複確認も3回のPython/ブラウザ往復でした。1回の待機条件で実際にscrollし、complete/naturalWidth/一意性を同時に検査します。重複は即座に拒否します。画像の強制eager化や検査の省略をせず、全画像と4幅（375/768/1024/1440）のoverflow確認を維持します。画像ブラウザは最大2、`--image-workers 1`で直列へ戻せます。

## 検証・受入

- [x] Python733件・実Web5件/関連23件・PR/mainのPython/Web CI成功。持続接続のredirect/HEAD/元bytes/404、worker JSエラー/外部通信/重複拒否を検証。
- [x] 同じ実156件のローカル検証は93.435→80.346秒。検索1,377リンク・画像入り102頁・画像259応答・外部通信0、全件の検証計数が一致。
- [x] 生成0の実日次の全工程success。本文HTTP/API試行/生成/保存/追加Gemini費用0。index438/public156/pending126、既存951オブジェクト世代/CRC・成功index/Note/receipt/元usage・日次/月次費用不変。pendingは同bytes書直しだけ世代更新。
- [x] 3 Release/6 assetsのID/size/digest・content/dataset/artifact・GCS/公開Markdown/配信版不変。全156 Noteの最新receipt/Note/index/snapshotを照合。

[ローカル証拠](archive/2026-10/web-transport-local-2026-10-13.json)と[本番受入/各工程](archive/2026-10/web-transport-acceptance-2026-10-13.json)を保存しました。先の[解析共有/画像並列](web-validation-performance.md)の本番値（111→108秒、全体411→460秒）や依存障害#185の履歴を上書きしません。#185はPR #186と実日次の復旧受入でClose済みです。

単一run間の比較で、監査・queue・準備・配信確認の時間は変動します。全体の安定した短縮、private GCS差分読取り、CIと日次の検査責務、Web環境/artifactの再利用条件は次の候補です。Source HealthのdegradedとDeepMind69保留/failing/streak2を維持し、性能検証の成功をsourceの全件完了と扱いません。
