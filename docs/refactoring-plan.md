# 公開基盤の責務整理

今回のゴールは、Batch事前検証・画像組立・公開snapshot・Web成果物の責務を分離し、
既存の保存・復旧・公開契約を維持してローカル実装・検証とレビュー可能な差分の提示まで完了することです。
実装とローカル回帰検証は完了しました。PR作成・マージ・本番公開は今回の対象外です。
本番反映と実環境のBatch preflightは、追加の承認を得た後続作業として扱います。
検証済み範囲の正本は[検証・受入](verification.md)です。

## 採用する変更

| 順序 | 領域 | 変更 |
|---|---|---|
| 1 | Batch | `techkb.batch.preflight(store, app)`へ読取り専用検査を集約。既存スクリプトは設定・クライアント・出力・後始末だけを担当 |
| 2 | 画像 | URL検査・候補抽出・選択照合は`images`、Markdown画像組立・配置は`composer`へ分離 |
| 3 | 公開 | `techkb.publication`を共通契約・Note検証・snapshot読取り/配置・Git snapshot照合に分割。従来の公開importを維持 |
| 4 | Web | HTML後処理・成果物検査/配置・Pages準備・配信後検証を`web/kaname_web`へ集約。npmタスクを共通入口にする |
| 5 | 文書 | 現行仕様と操作・検証の正本を整理。完了済み計画と受入証拠はarchiveへ保存 |

Python/Webの境界と受渡しは[仕様書](specification.md#pythonとwebの境界)、
公開snapshotの正確な契約は[公開・配布](publication.md)を参照してください。
CLI専用・standard専用の内部モジュールは、その名前だけを理由に移動しません。

## 維持する契約と判断

CLI名・既存引数・JSON、GCS object path、index/receipt、Note bytes・安定ID・manifest schema・
dataset digest、content履歴、Pages URLを維持します。Python/Webの内部関数のimport先は責務に合わせて更新します。
公開パッケージは重い依存を遅延読込みし、配信後検証の`python -I -S`実行を保ちます。

画像は出典HTTPS URLの直接表示を続けます。画像取得・キャッシュ・GCS保存・相対パスfallbackは追加しません。
GCS障害時は公開済みGit/Pagesを維持し、新規公開更新は失敗として扱います。
usageのAPI前後保存、receiptからの復旧、世代/bytes照合、最後に書く完了manifestを保ちます。
元記事の再取得を理由に、生成Noteや課金・Batch提出状態の保全を撤去しません。

## 完了条件

全Python回帰、設定、Web依存監査、workflow静的検証、画像付きfixtureと固定実contentの
Quartz/Chromium受入が成功すること。元Markdown・版/hash照合、検索・内部リンク・画面幅・画像・
想定外通信の検査、保存失敗後の停止/復旧、GCS/export失敗時の公開停止を維持すること。
各段階の検証後に次へ進み、現行文書が実装した挙動を説明し、
レビュー可能な差分とローカル検証結果を提示して完了とします。
依存更新、有料提出、既存Note再生成、本番state/IAM移行は行いません。

## 完了済みの旧計画

T0、R1〜R5、通常scheduleとPages切戻し/復帰は以前に完了しています。
当時の着手指示と進捗は[旧R1〜R5計画](archive/2026-10/refactoring-plan-r1-r5.md)に保存しました。
実Batchの成功保存と請求照合などの後続は[次の作業](next-work.md)へ分けます。

今回の具体的な件数・固定入力・比較結果は[ローカル検証記録](archive/2026-10/domain-refactoring-2026-10-10.md)に保存しています。
