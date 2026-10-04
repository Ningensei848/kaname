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

## 課金と中断の限界

APIの応答後からreceipt等の永続化前に停止すると、結果消失と再課金の可能性があります。
API生成とGCS保存を一つのtransactionにできず、timeoutもAPI側の完了を断定できません。
通信retryを許しながら厳密なexactly-once課金を保証しません。

現行standardではreceipt後にreportが残らない中断でも費用履歴が欠落します（F5）。
usage metadataの一部欠落を0/完全扱いする問題もあります（F4）。
これらは「API応答そのものを失う限界」と別の修正対象です。
費用はrunのmodel/mode/価格snapshotと取得できたusageから推計し、invoice・GCS・Actions費用を含みません。
予算は通知閾値で、日次の厳格なUSD capは未実装です。

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
browserのresource allowlistはredirect先の取得前に届いていないためF3として対処します。
この問題を解消する前にbrowser sourceの本番利用を広げません。

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
未検証sourceのstreak判定（F6）とaudit/export/deploy通知は別の修正・仕様化対象です。

未実装項目・残余制約を[検証・受入](verification.md)へ集約し、過去のrunの結果を現在の保証に置き換えません。
