# 現在の検証範囲と受入基準

仕様は[仕様書](specification.md)、操作は[運用手順](operations.md)、公開境界は[公開・配布](publication.md)を正本とする。
runごとの計数・commit・費用・測定結果は[archive索引](archive/README.md)へ分離し、残件は[監査一覧](repository-audit.md)で追跡する。

## 受入済みの範囲

| 領域 | 現在の保証と受入 |
|---|---|
| standard収集・保存 | 本番稼働。usageの部分欠落/中断後復旧、元価格/日付、receipt→Note→indexの保存、障害時の後続課金停止を回帰検証 |
| Batch | 画像型/候補外IDを修正。実Note1件/画像3件の保存/公開、課金1回、追加生成0の回収・再実行まで受入済み |
| 本文・画像 | 有効7 source/8レイアウトの合成corpus。Google Research/DeepMind/追加4社の実本文検査、GlucoFM2図の限定補完と実配信、新規Batchの画像選択を受入 |
| 新規記事限定・並列処理 | 成功URLの本文HTTP省略、明示recheck、receipt/Batch回収、生成枠でfetch停止を受入。fetch/convertはbounded・入力順、課金/保存は単一writer |
| Source Health | 読取りCLI・本番GCS受入済み。未処理sourceや全体successでstreakをresetしない |
| 公開snapshot/Git | Note/receipt/index・元Markdown bytes・安定ID・manifest/dataset・世代/catalogを検査。競合・不完全出力・余分なファイルを拒否。実content/submodule互換を受入 |
| Release配布 | 完全版/最大7差分/削除、固定tagとdigest、draft検査/再開、改変拒否、同版再実行を実Actionsで受入。全体復元/全HTML buildを維持 |
| Web/Pages | fixtureと固定実Git/Release入力、全元Markdown、検索/全ローカルリンク/アンカー/画像/4幅/想定外通信を検証。初回/通常schedule/切戻し/復帰を実deploy・配信照合で受入 |
| 検索・graph | NS1本文WikiLink/内部Note優先/Google検索fallbackを本番受入。Graph評価CLIは読取り専用、正規化は評価案のみ |
| GCS読取り | 16並列/接続pool再利用、世代条件/CRC、同一runner内private byte cache、live catalog再検証を受入。1/8へ切戻し可能 |
| 日次CI再利用 | 同じmain SHAの最新成功Checks/attempt・scope/aggregate jobsをAPI照合。不一致/不完全/照合不能時は全単体テストへfallback。設定/本番状態/公開検査は毎回実行 |
| CI対象選択 | Docs/設定/コード/Webを分類し、Release/配布入力契約とその回帰もWeb対象。未知path/比較失敗は全検査。Docs/actionlintは常時必須gate |
| 互換sync/browser | 人の編集保持・候補別保存、実Chromiumのredirect/robots/host制限を回帰検証。実Windows一時NTFSで編集/候補保持・排他作成・junction拒否を確認。GitHub Blogの一時browser取得も確認。利用者Vaultへの受入は未実施 |
| 任意の推計生成上限 | standardのrun capと任意のUTC日/月残額を回帰検証。unknown/元価格欠損/未計上Batchでは停止。既定null、本番設定への適用は未実施 |

F1〜F7、T0/R1〜R5/O1/O2、旧Batch/画像/NS1の未受入指示は完了証拠に置き換わっている。
当時のテスト件数や単一runの短縮率を、現在の全suite件数・恒久性能保証として転記しない。

## 現在も残る受入・限界

- #116の確定請求照合、legacy/unknownの説明。usage推計と実請求を区別する。
- source別の保留/最終成功/失敗streakの観測。日次の成功だけで全source healthyとしない。
- 利用者が指定するbrowser source運用・実Vaultの受入。既存GitHub記事の一時取得と一時NTFSの成功で、未指定の利用者環境を代用しない。
- npm既知advisoryの例外。詳細は[Web依存](web-preview.md#固定依存と残る制約)。
- APIとGCSは単一transactionでなく、timeout/retryを含む厳密なexactly-once課金は保証しない。
- 出典画像の内容/存続と全Noteの日本語事実確認は固定hashや自動検査だけでは保証しない。
- run間cache/差分HTML buildは未採用。本文上限20,000文字、new_onlyの既知URL再取得省略、予算通知の境界を維持する。

## 継続する受入基準

- 保存障害で後続の有料処理を止める。API前後のusageとreceipt復旧で元の日付・単価・既知countを保持し二重計上しない。
- Batchの曖昧な提出を自動再提出しない。preflightで書込み・記事取得・Gemini操作をせず、未決済/不明usageを隠さない。
- 不完全manifest、改変bytes、privateファイル、symlink、別commit、fixtureの本番混入を拒否する。
- GCS/export失敗後にGit/Pages更新へ進まない。固定公開版のWeb buildにGCS/Gemini認証を要求しない。
- 同じNoteの元Markdown bytes・安定ID・dataset digestをGit/Release/Webで照合し、静的artifact digestと区別する。
- 検索・全内部リンク/アンカー・出典・版表示・375/768/1024/1440pxと画像をChromiumで確認する。検査中は許可画像だけ代用し、想定外resourceを拒否する。
- 互換syncで人の編集を保持し、browserの各redirect先を通信前に検査する。

## 今回の整理で実施した確認

最初の整理ではremote追跡ファイルの静的確認、削除対象の保全先commit/blob照合、現行Markdownの相対path/見出しとarchive参照、コード/設定/workflow/test/lockの不変を確認した。
継続作業でローカルruntimeが復旧し、基点Python786件、CI/文書関連69件、画像補完関連36件、Node監査5件、実npm auditとactionlintを実行した。
全20項目の進捗と実行範囲は[監査一覧](repository-audit.md#改善の依存関係と進捗)で追跡し、既存main Checksの成功とは区別する。
