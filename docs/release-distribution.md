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

- [x] 完全版/差分/追加/更新/削除、深度上限、破損ZIP・descriptor・基底拒否、draft途中失敗の再開、公開済み版の変更拒否、redirectの認証剥離を実装。
- [x] 全Python693件、Release34件、Git/Pages互換とactionlintが成功。既存125→126件を追加1件の差分（28,345 bytes）で復元し、UTC固定のQuartz成果物は現行配信版hashと一致。
- [x] [PR #179](https://github.com/Ningensei848/kaname/pull/179)をmain `f62b2ce9381d81989f2b37f9894f630235612fa4`へ取込み。[PR CI](https://github.com/Ningensei848/kaname/actions/runs/38355145861)/[main CI](https://github.com/Ningensei848/kaname/actions/runs/38355706688)で全Python693件と実126件のGit/Release両入力・Chromium検査が成功。
- [x] 既存125件の[完全版](https://github.com/Ningensei848/kaname/releases/tag/notes-dfd4aebed88f22bbd7f3538511d4e019ee4ae5ae)はZIP330,620 bytes。公開APIの匿名復元も成功。
- [x] [公開専用run](https://github.com/Ningensei848/kaname/actions/runs/38356072092)でGITHUB_TOKENのcontents権限のみで固定tag/draft/upload/検証/publishが成功。[155件版](https://github.com/Ningensei848/kaname/releases/tag/notes-92dcd8ecdf4045470e0536cc68998a2dfc997a62)は基底125件から変更30件/削除0、ZIP96,849 bytes/descriptor2,832 bytes。audit437成功行/pending127、export・復元・Chromium・Pages配信までsuccess。旧公開126件の元Markdown不変、復元した155件の全bytes・検索1,359リンク・実配信manifest/HTML/版一致。
- [x] [公開専用の再実行](https://github.com/Ningensei848/kaname/actions/runs/38357056972)も全工程success。Release2件/asset4件のまま、ID/size/SHA-256不変、追加Release/asset/content commit 0。全155 Note・dataset/artifact・実配信版が初回と一致。

公開専用モードではCollect・費用/通知state更新をskipし、GCSはaudit/exportの読取りのみです。今回の配布受入の追加Gemini呼出し/費用は0です。ローカルADCは期限切れのため、独立したGCS全オブジェクト世代の前後照合は未実施です。Actionsの既存WIF認証・整合性監査は成功しており、CLI認証更新後の補足照合と区別します。

直前の[通常日次](https://github.com/Ningensei848/kaname/actions/runs/38339836814)でDeepMind29件を保存し、1件は`MAX_TOKENS`/`json_invalid`で拒否しました。公開155件にはその29件を含み、旧126件を変更していません。この収集失敗は[Issue #178](https://github.com/Ningensei848/kaname/issues/178)をOpenで管理し、差分配布成功を生成成功扱いにしません。通常日次の30呼出しは元usageが全件判明、推計USD 0.076561。承認USD 1の台帳へ保守的に合算し、累計USD 0.2905084/残額USD 0.7094916です。

別run間の差分GCS監査/exportと差分HTML buildはこの変更の範囲に含めません。Release配布を時間短縮と同義にはせず、Actionsの工程時間で結果を測ります。

実測は公開専用で420秒/412秒（7分/6分52秒）、155 Note/1,359リンクです。以前の126 Note・生成0の通常run351秒とは入力件数とモードが異なり、今回のRelease切替えだけで時間が短縮したと扱いません。工程時間・固定版・検証計数は[受入JSON](archive/2026-10/release-distribution-acceptance-2026-10-13.json)に保存しました。
