# 新規記事だけの収集と差分配布

2026-10-12 JST、成功済み記事の本文を日次で再GETする処理を止め、未知/未完了記事だけをNote化します。公開済みNoteはGCS/Gitから利用します。収集と配布の差分は別の責務です。

## 収集の変更 — 本番受入完了

従来はRSS全件の本文をGETした後でraw/content hashを比較していました。直近は7 source・259候補で約9分。保存Noteを読み直す時間ではなく、元サイトへのHTTP・robots・redirect・間隔制御が中心です。初回の未Note化保留145件も残っており、すべてが既存記事の再取得という意味ではありません。

- 日次設定を`processing.article_policy: new_only`に変更。`discovery.py`が成功indexのsource別元URL/canonical URLを正規化して事前除外し、既知本文へのHTTPを行いません。
- 成功indexのない失敗/未完了を既知扱いにしません。receiptの復旧とBatchの回収・保存を先に行い、その成功結果もURL判定に反映します。
- 日次の生成上限に達したらfetch/convertの補充・消費を止め、未消費候補はpendingへ残します。最大`workers - 1`件の先行HTTPは残る場合があります。上限0では本文HTTP0です。
- dry-runは未知の本文を検査する読取り専用操作で、生成枠0でも本文を検査します。
- 同じURLの後日修正は日次では自動検知しません。`--recheck-known`で元の全件hash再検査を明示的に使えます。旧設定に新項目がない場合は`recheck`で互換動作を維持します。
- 本文hashによる重複判定・厳格なNote検証・単一writer・公開ポリシーを維持します。

再検査は`python -m techkb dry-run --recheck-known`（生成/保存0）、保存も必要な場合は`python -m techkb run --recheck-known`です。後者は新しい本文の生成に通常の費用/件数上限を適用します。

## 現在の保存・配布の責務

| 領域 | 保存するもの | 主な利用 |
|---|---|---|
| GCS（非公開） | 全生成Noteの履歴、成功index、receipt、pending、元usage | 正本・再開・監査・全体復旧 |
| `main` | コード・設定・文書 | 収集/公開処理の実装 |
| `content` | 最新の公開Note群と全体manifest | 日次Quartz・固定版の再build・submodule |
| Pages | 検証済みのHTML/検索index/assets | 閲覧 |

GCSの「正本」は生成Noteと運用記録です。原記事HTML/原文を常に保存する構成ではなく、既存のraw保存無効を維持します。Quartzの固定公開版からの再buildはすでにGCS/Gemini/元サイトへの本文取得を必要としません。

`content`は各commitで完全な公開版を表しますが、Gitは内容hashで同じblobを共有します。毎回全Noteの独立コピーをGit履歴へ増やす意味ではありません。日次exportのGCS読取りと、Git/Quartzの入力取得は別工程です。前段のGCS監査は並列取得・runner内cacheで短縮済みで、別run間の永続差分exportは未実装です。

## Release assetsの差分配布案 — 未採用・設計候補

[GitHub Releases](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases)ではtagに対応した配布ファイルを置けます。[Immutable releaseの手順](https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository)ではdraftにassetsを揃えてからpublishできます。日々の公開NoteをコードのGit treeへ置かず、配布assetとして持つ案は成立します。

ただし「今日の差分だけ」では新しいrunnerが昨日までのNoteを復元できません。次の契約が必要です。

1. 最初と定期checkpointに、完全な公開snapshotを置く。
2. 各差分に`base_dataset_digest`/`target_dataset_digest`、追加・変更Noteの安定IDとhash、削除/取り下げID、target全体manifestを含める。
3. builderは前回の完全版かcheckpointを取得し、差分を順に適用してtarget digestを検証。base不一致・欠けた差分・順序違いでは停止し、GCS正本から全体復元する。
4. 完成版を原子的に切り替え、その全体をQuartzに渡す。raw/state/receipt/usageはassetsへ入れない。
5. 新Noteで既存ページの検索・タグ・backlink・WikiLink解決先が変わるため、Note差分とHTMLの再build範囲を別管理する。コード/config/lock変更・切戻しも無効化条件に含める。

直ちにReleaseへ移行する操作は行っていません。現在のcontentブランチは固定版参照とsubmoduleを支えており、Release化するなら互換性と日次の復元コストを比較します。まず収集済み本文の再GETと、生成枠を使い切った後の無駄な取得を削減します。

## 検証・受入

- [x] 全Python659件・新規記事限定17件が成功（Batch2件を含む）。
- [x] [PR #176](https://github.com/Ningensei848/kaname/pull/176)をmain `77463ccdd7538bc63460a4d22a75cb1c005b5a39`へ取込み。[PR CI](https://github.com/Ningensei848/kaname/actions/runs/38235284776)/[main CI](https://github.com/Ningensei848/kaname/actions/runs/38235716620)のPython/Webが成功。
- [x] [生成0の日次run](https://github.com/Ningensei848/kaname/actions/runs/38236132360)の収集は32秒（前回543秒）。RSS259候補・既知111件skip・本文HTTP/生成/保存0、index408・元pending145件の全項目を保持。本文判定を行わなかった3件を追加してpending148（DeepMind99/Cloudflare20/Meta9/Apple10/Microsoft10）。未分類3件を新たな保存成功や対象確定と扱わない。
- [x] 既存884オブジェクト（pendingを除く）の世代/CRC、Note/receipt/index/usage/Batchの集合・元費用を保持。公開版の最終照合も成功。
- [x] 全工程success。公開126件/959検索リンク・最新Note/receipt/index/snapshot bytes一致、content/dataset/artifactと実配信manifest・HTML hash不変。追加Gemini USD 0。
- [x] 同じ7 source・生成0の日次全体は930秒→351秒（15分30秒→5分51秒、62.26%短縮）。記事収集543秒→32秒、HTTPはRSS/robotsの14応答、本文HTTP0。生成30件の通常run時間の保証には使わない。

未Note化候補の本番生成やRelease assetsへの切替えを完了扱いにしません。

工程と検証計数は[実測JSON](archive/2026-10/new-only-acceptance-2026-10-12.json)へ保存。現行の初回保留は148件で、未分類3件を含みます。Release assetsへの配布切替えと、別run間の差分GCS監査/export・差分HTMLビルドは未実装の設計候補です。
