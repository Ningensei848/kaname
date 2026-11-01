# 公開NoteのRelease差分配布

2026-10-13 JST、実装・本番公開・同じ版の再実行まで受入完了です。GCSは全生成Note履歴・index・receipt・usageの非公開正本です。日次Pagesの入力を公開Releaseから復元し、`content`はsubmodule・履歴版の切戻し・commitの照合用として維持します。mainへNoteを置かず、既存content履歴も削除しません。

## 配布する版

`notes-<40桁content commit>`の固定tagに、`release.json`と`notes.zip`を配布します。元Git manifestとexport manifestのbytes一致を確認してからtagを作ります。tagは対象content commitを直接指すlightweight tagです。Releaseはソフトウェアのlatest指定を変えません。

- 初回と7段の差分の後に完全版checkpointを作ります。日数やrun数でなく、公開版の差分深度で決めます。復元は最大8 Releaseです。
- 差分ZIPは追加/変更Note、target全体manifest、固定READMEだけを含みます。descriptorに基底tag/dataset、target dataset、全体snapshot digest、変更/削除ID、ZIPのsize/SHA-256を記録します。
- dataset digestは従来どおりNote ID/hash集合、snapshot digestはREADME/manifestを含む全配布path/hash集合のdigestです。原文/raw/state/receipt/usage/Git metadataは含めません。
- draftに2 assetを揃え、遠隔のbytesから全体を復元・検証してpublish。公開済みassetを削除/上書きしません。途中失敗のdraftは同じtag・基底・bytesの場合のみ再開します。不明なPOST結果をその場で自動再送しません。
- 変更のないcontent commitは既存Releaseを読み直して検証し、追加Release・asset・tagを作りません。mainのWeb変更でも同じ公開Note版から再buildできます。

公開assetのバイナリ取得は[GitHub公式API](https://docs.github.com/en/rest/releases/assets)の200/302に対応します。redirect先はGitHubのRelease asset hostに限り、認証ヘッダを転送しません。署名URLやHTTP payloadはログへ出しません。ZIPはファイル名をallowlistで照合し、重複・symlink・path traversal・privateファイル・展開量超過を拒否します。

## 復元とPages

指定tagの基底を完全版まで辿り、古い順に差分を適用します。各段の基底digest・深度・削除対象・target digestを検証し、最終的に従来の公開Noteポリシーで全体を検証します。新しい出力dirへ完成manifestを最後に設置し、既存の異なる出力を上書きしません。receiptはsnapshot外に置き、build/ブラウザ検査でcommitと全体bytesを再照合します。

```bash
python scripts/release_notes.py --repository Ningensei848/kaname restore \
  --tag "notes-$CONTENT_COMMIT" --commit "$CONTENT_COMMIT" \
  --output /path/to/public-content --receipt /path/to/release-receipt.json
```

日次はRelease版を固定して復元し、contentのNote履歴をcloneしません。Quartzには復元した全Noteを渡します。検索・タグ・関連リンクへの影響があるため、HTML全体buildとブラウザ検査は維持します。原記事/GCS/Geminiへの通信と鍵はPagesのbuilderに渡しません。日次ではcontent tipが進んでいれば古い版のdeployを拒否します。

Quartzの実行時タイムゾーンはUTCへ固定します。日本時間のローカル環境でも、Actionsと日付表示・タグ順序・成果物hashを揃えます。

手動切戻しは`pages.yml`へ`content_commit`と`release_tag`を指定します。`release_tag`を省略すれば従来のGit履歴版からの切戻しが使えます。

```bash
gh workflow run pages.yml --repo Ningensei848/kaname --ref main \
  -f content_commit="$CONTENT_COMMIT" -f release_tag="notes-$CONTENT_COMMIT"
```

欠損・改変・tag移動・基底不一致では公開を止め、既存のPagesを維持します。GCSへ黙ってfallbackしたり、指定版を別の最新版へ置き換えません。まず欠けたasset/基底を調べ、正本から監査/exportしたsnapshotを新しい固定版として再配布します。過去のRelease/Git公開履歴からの完全消去は、現在版の取り下げとは別操作です。

## 検証状態

完全版/差分/追加/更新/削除、深度上限、破損拒否、draft再開、公開済み版の変更拒否、redirect認証剥離を検証した。
実ActionsでGit/Release両入力の公開、全元Markdown/検索/リンク/画像/4幅/配信版、同版再実行でRelease/asset/content不変を受入済み。
[整理前の全文・受入証拠](https://github.com/Ningensei848/kaname/blob/archive/pre-housekeeping-2026-10-16/docs/release-distribution.md)へ初回のrun/件数/費用・独立GCS照合を保全した。
Releaseの重複転送削減は受入済みで、日次全体の安定短縮は未立証である。[旧監査A08/A09](archive/2026-10/completed-audit-2026-10-21.md#改善の依存関係と進捗)へ当時の判定を保全し、次の開発は[作業一覧](next-work.md)で追跡する。配布成功をsource健全性や時間短縮の達成と混同しない。

## 同一処理内のasset bytes再利用

Release/tag/asset metadataは復元のたびに取得する。assetのID/size/SHA-256/updated_at/nameが一致し、実bytesのsize/digest検査が成功した場合だけ、同じpublish/restore処理内で再利用する。digest欠損・ID/世代相当metadata変更・別処理には再利用しない。
cacheは最大32MiBのLRUで、処理終了時に破棄する。`ReleaseClient(..., cache_bytes=0)` で従来の全downloadへ戻せる。GCS/private原文やmetadata/検査結果を永続cacheへ置かない。
CLI出力のtransportにAPI要求数・asset取得数/bytes・cache hit・最大cache bytes・経過秒を追加する。公開descriptor/ZIP/Note/receiptの形式とbytesは変更しない。

固定246 Note（content `510dc54a82ebeed360a6f91e07261d45b01f6a75`）の同一chainを一処理内で3回復元した読取り専用比較では、metadata API30回を維持し、asset30→10回・転送2,354,862→784,954 bytes・66.567→52.848秒だった。全復元bytes/dataset/snapshot digestは一致した。
これは公開前/後に重なるchainの再利用を模した一組のローカル比較で、実日次全体の短縮率を保証しない。実publishのfixtureでもmetadata/書込み/asset bytesを変えず、改変・tag変更・欠損digest・上限・処理跨ぎを拒否する回帰を検証する。
