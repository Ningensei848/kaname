# 新規記事だけの収集と差分配布

2026-10-12 JST、成功済み記事の本文を日次で再GETする処理を止め、未知/未完了記事だけをNote化します。公開済みNoteはGCS/Gitから利用します。収集と配布の差分は別の責務です。

## 収集の変更 — 本番受入完了

成功済みURLを本文HTTPの前に除外する。初回バックログと既存記事の再取得を区別する。

- 日次設定を`processing.article_policy: new_only`に変更。`discovery.py`が成功indexのsource別元URL/canonical URLを正規化して事前除外し、既知本文へのHTTPを行いません。
- 成功indexのない失敗/未完了を既知扱いにしません。receiptの復旧とBatchの回収・保存を先に行い、その成功結果もURL判定に反映します。
- 日次の生成上限に達したらfetch/convertの補充・消費を止め、未消費候補はpendingへ残します。最大`workers - 1`件の先行HTTPは残る場合があります。上限0では本文HTTP0です。
- dry-runは未知の本文を検査する読取り専用操作で、生成枠0でも本文を検査します。
- 同じURLの後日修正は日次では自動検知しません。`--recheck-known`で元の全件hash再検査を明示的に使えます。旧設定に新項目がない場合は`recheck`で互換動作を維持します。
- 本文hashによる重複判定・厳格なNote検証・単一writer・公開ポリシーを維持します。

再検査は`python -m kaname dry-run --recheck-known`（生成/保存0）、保存も必要な場合は`python -m kaname run --recheck-known`です。後者は新しい本文の生成に通常の費用/件数上限を適用します。

## 現在の保存・配布の責務

| 領域 | 保存するもの | 主な利用 |
|---|---|---|
| GCS（非公開） | 全生成Noteの履歴、成功index、receipt、pending、元usage | 正本・再開・監査・全体復旧 |
| `main` | コード・設定・文書 | 収集/公開処理の実装 |
| Release assets（受入済み） | 完全版・差分・削除情報・全体manifest | 日次Quartzの固定版復元 |
| `content` | 最新の公開Note群と全体manifest | submodule・Git互換切戻し・版の照合 |
| Pages | 検証済みのHTML/検索index/assets | 閲覧 |

GCSの「正本」は生成Noteと運用記録です。原記事HTML/原文を常に保存する構成ではなく、既存のraw保存無効を維持します。Quartzの固定公開版からの再buildはすでにGCS/Gemini/元サイトへの本文取得を必要としません。

`content`は各commitで完全な公開版を表しますが、Gitは内容hashで同じblobを共有します。毎回全Noteの独立コピーをGit履歴へ増やす意味ではありません。日次exportのGCS読取りと、Git/Quartzの入力取得は別工程です。前段のGCS監査は並列取得・runner内cacheで短縮済みで、別run間の永続差分exportは未実装です。

## Release assetsの差分配布 — 本番公開・再実行受入完了

ユーザー承認を受け、完全版checkpoint＋最大7段の差分、変更/削除ID、基底/target digest、固定tag復元を実装し、実155件の公開まで受入済みです。同版の再実行でも追加Release/asset/content commit 0を受入済みです。日次QuartzはReleaseから全体を復元してbuildし、content/submoduleとGit履歴の切戻しは互換経路として保持します。契約は[Release配布](release-distribution.md)で管理します。

## 受入状態

新規限定収集とRelease配布は実Actionsで受入済み。[整理前の全文・受入証拠](https://github.com/Ningensei848/kaname/blob/archive/pre-housekeeping-2026-10-16/docs/incremental-collection.md)へ初回の計数/短縮/保存照合を保全した。
現在の保留件数は[Source Health](operations.md#source-healthの読取り)で読み取る。[旧監査基点](archive/2026-10/completed-audit-2026-10-21.md#確認できた現在値)の件数は履歴である。別run間の差分GCS監査/exportと差分HTML buildは未採用で、今後の判断は[次の作業](next-work.md)で追跡する。
