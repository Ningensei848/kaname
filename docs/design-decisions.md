# 収集・復旧・配布の設計補足

プロダクトの境界と公開方針は[ADR-0001](adr/0001-generated-content-module-and-pages.md)で決定しました。
この文書は現行収集の保証と、新しい配布経路をつなぐ責務を説明します。

## 正本と保存途中の復旧

成功TSVを通常の重複排除の正本とし、GCSはNote/index/pending等の複数object transactionを提供しません。
単一writerとgeneration preconditionで競合を検出し、成功hashはNoteとindexの保存後に登録します。

1. RSSと既存pendingを統合した時点でpendingを先行保存する。
2. LLM結果を検証・組立てし、構成済みNoteとindex行をreceiptへ保存する。
3. Noteを保存し、記事ごとの月次indexをcheckpointする。
4. run終端でpendingとreportを保存する。
5. 次回は成功indexに未登録のreceiptからNote/indexを修復する。

receiptは復旧補助で、記事原文を含みません。成功済みreceiptは保持し自動削除しません。
indexを安易に消すと再処理の判断が変わります。
Batchはcreate前の予約、曖昧createの照合、compact outcome、安定したbilling IDを使います。
結果keyの未知/重複、世代競合、durability障害は停止します。

## fetch/convertの並列処理

`processing.workers`の最大件数だけ取得・本文変換を先行し、結果は入力candidate順で主threadへ戻します。
workersは1〜8、運用設定は2です。発見・重複/関連性判定・報告・課金・状態更新には並列workerを使いません。
保存障害後の新規課金を止め、未開始futureをcancelし、実行中の取得終了後にHTTP clientを閉じます。
HTTPはhost単位の排他でrobotsと間隔/retryを維持し、MarkItDown engineはthreadごとに分離します。
同じhostへのHTTPとLLMは逐次なので、全run時間の短縮率は通信条件に依存します。

## 課金と中断の限界

APIの応答後からreceipt等の永続化前に停止すると、結果消失と再課金の可能性があります。
API生成とGCS保存を一つのtransactionにできず、timeoutもAPI側の完了を断定できません。
通信retryを許しながら厳密なexactly-once課金を保証しません。

standardはAPI呼出し前・usage取得後にprivate usage journalを保存し、receiptに元run IDを記録します（F5）。
run reportが失われても元の日付・単価で集計し、reportとの二重計上を防ぎます。
部分欠落usageは既知countを保持してpartialにします（F4）。応答を失った呼出しの費用は不明として残します。
費用はrunのmodel/mode/価格snapshotと取得できたusageから推計し、invoice・GCS・Actions費用を含みません。
`daily_budget_usd`/`monthly_budget_usd`は通知閾値です。standardには明示的なrun単位capと任意のUTC日/月generation limitがあります。通常scheduleではいずれも未指定です。期間limitも元usage/単価による推計で、確定請求の上限を保証しません。設定・unknown usage・Batchとの関係は[運用手順](operations.md#任意のutc日月生成上限)を参照してください。

## 設定・schema・生成内容

`ArticleEnrichment`はstrict/extra禁止です。`key_points`は2〜5件、`related_concepts`は2〜6件、
`tags`は最大8件です。title/summary/positioning等の必須文字列、category候補、空の要点・検索語も検証します。
最小件数を強制しないという旧説明や、現行schemaにないtechnical insightsの説明は採用しません。
promptは根拠のない捏造を求めず、本文を指示扱いしません。schema不正の自動補正/再生成はありません。
通信retryはSDK内部を1 attemptにし、アプリ側で対象の通信障害だけをretryします。
生成診断は例外型・既知field/code・段階・finish reason等に限定し、値・原文・例外本文を出しません。

入力上限は正規化Markdownの先頭20,000文字です。後半の論点を含む完全な記事要約とは扱いません。
新しい公開経路でも打切り表示と生成時の上限値を保持します。

## HTTPとbrowser

robotsの404/410は指定なし、それ以外の拒否・障害は取得を止めます。
記事とrobotsのredirectにURL/public IP/robots確認を行い、環境proxyを自動継承しません。
DNS検査と接続は別で、厳密なネットワーク隔離ではありません。
browserは初回document・resource・robotsの各redirect先を、呼出しごとのhost制限でDNS/HTTP通信前に検査します（F3対応済み）。
許可した転送先でもrobotsを検査します。browser sourceの本番受入は別途行います。

## 人の編集と生成側の更新

互換syncは既存Noteを置換せず、候補を別保存します。新規ファイルは完成bytesを上書きなしで公開します。
これは人が編集するコピーを保護する契約です。
新しい生成モジュールはGit上で版を更新し、利用側がsubmoduleでどの版を参照するか決めます。
人力Vaultの内容や親repoのcommitをkanameのcollector/publisherは更新しません。
収集の重複排除hash、公開Note hash、配布snapshot digest、Git commitは別々に追跡します。

## 公開・通知の責務

export/buildはNoteの再要約を行わず、収集writerと公開writerを分けます。
SSG入力は公開manifestで限定し、repo rootや人力Vaultを包括して公開しません。
収集/監査、export、Git配布、deployの成功を別に扱い、公開失敗を収集成功に隠しません。
現行の日次Issue通知は連続失敗/予算到達について実装・承認済みです。
sourceは実際に処理を完了したrunだけでstreakをresetします（F6）。
audit/export/Git/Pagesの障害はrunごとにIssue通知します。[日次公開](daily-publication.md)を参照してください。

未実装項目・残余制約を[検証・受入](verification.md)へ集約し、過去のrunの結果を現在の保証に置き換えません。

## cacheの採否と無効化条件

| 対象 | 再利用時に必要な条件 | 現在の判断 |
|---|---|---|
| 同一runのGCS bytes | live bucket/name/generation/CRCと前後catalog、全件検査 | 既存private runner cacheを継続 |
| 同一Release処理のasset bytes | fresh tag/metadata・ID/size/SHA-256/updated_at/name、処理内32MiB上限 | 計測で重複転送を確認して採用 |
| 別runのprivate GCS bytes | 権限境界・暗号化/失効・世代/CRC/live catalog・削除検出 | 現規模では永続化を採用しない。全件検査を維持 |
| Web環境 | engine/plugin/font/native依存とlock/integrity、Node/Python版、config/theme、cache所有/破損/並行setup | npm/pipの既存download cacheだけを利用。検証済み環境全体の再利用は未採用 |
| 静的artifact | 全Note/manifest/commit/dataset、全renderer/helper/config/theme/lock、UTC・footer年・runtime、tag/search/link全体、取下げ/rollback | 全体buildと全Web/配信照合を維持。単純なNote差分だけの再利用は不可 |

A10の設計評価として、metadataや検査結果のrun跨ぎreuse、部分HTMLだけの再buildは採用しない。最適化は同一処理内の検証済みbytesに限定し、固定入力の複数回計測を先に行う。

### 固定Web入力の反復計測

`python scripts/benchmark_web.py --content <clean-content-checkout> --content-commit <full-SHA>` は全build/全受入を3回実行し、各回の入力Git状態・dataset/artifact digest・検査件数を照合する。工程のsample/中央値/最小/最大をJSONで出す。検査を間引かず、出力は同じfilesystemの一時領域で作成・削除する。

2026-10-16のcontent `510dc54a82ebeed360a6f91e07261d45b01f6a75`、246記事を共通基点としてWeb共通化前後で各3回計測した。全回dataset `e6562e1b47b4a3baea3e7de573c2d7810d896cda4099050cb17dcf9596863cff`、artifact `0d0b345554b91dfcb89d1351a33e9dac94921657ae883e220e029bd3806840df` が一致した。

| 秒 | 共通化前（中央値 / 範囲） | 共通化後（中央値 / 範囲） |
|---|---|---|
| build | 44.479 / 42.105–46.326 | 44.917 / 40.303–45.371 |
| 全受入 | 146.865 / 142.075–148.236 | 143.667 / 143.273–147.354 |
| 合計 | 191.344 / 184.180–194.562 | 188.190 / 183.971–192.725 |

各回246記事・2,461検索リンク・画像あり156記事・承認画像要求380件・4幅・offline検索クリック1件、外部要求0、画像browser最大2を維持した。範囲は重なり、速度改善は立証していない。runner準備・収集・Release・deployを含む日次全体の計測とは区別する。

## 現規模と移行判断

2026-10-16の実GCS読取りは1,059 object/6,718,993 bytes（最大302,320 bytes）、成功528行・保留60。月次indexは2ファイル/305,512 bytesで、memory上からの読込み0.005秒だった。
全件auditは整合、読取り16並列5.875秒、全体8.851秒、当該SDK/監査専用プロセスの最大RSSは85,628KiB。CLI全体やGitHub runnerの恒久上限ではなく、一度のローカル観測である。
現在はDB/stream化を先行させず、snapshot logにbytes/largest_object_bytes、State logにindex_files/index_rows/index_bytes/load_secondsを追加して規模を継続観測する。
メモリ/時間の実制約が現れた時点で、全件整合性・世代/catalog再照合と公開前gateを維持できる分割/stream化を再評価する。
