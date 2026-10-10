# 現在の検証範囲と受入基準

要件は[仕様書](specification.md)、操作は[運用手順](operations.md)、公開契約は[公開・配布](publication.md)を正本とします。
本書は実装・ローカル検証・本番受入を区別して現在の状態を示します。
過去のrun、commit、件数、初回受入値は[責務整理前の検証記録](archive/2026-10/verification-before-domain-refactoring-2026-10-10.md)へ保存しました。

## 現在の状態

| 領域 | 実装・検証 | 未受入・限界 |
|---|---|---|
| standard収集 | 本番稼働。部分usage、receipt復旧、保存失敗後の停止を障害注入で検証 | 確定請求明細との照合 |
| Batch | 提出・回収・診断・費用照合をoffline検証。読取り専用preflightの本番受入済み | 実提出はschema不適合で成功保存0。成功Note保存の本番受入は未完了 |
| 記事画像 | 候補ID/URL/配置、standard/Batch、公開bytes、Chromium表示をoffline検証 | 画像入り実Noteの本番受入。外部画像の内容・存続はGit版で固定できない |
| 公開snapshot/Git | 初回公開と通常schedule受入済み。完了manifest・世代/bytes・競合拒否を検証 | 利用者Vault/プラグイン/NTFSは別の受入 |
| Web/Pages | fixture/固定Git版、元Markdown、検索・内部リンク・画面幅・配信版照合を検証。初回公開・通常schedule・切戻し/復帰は受入済み | 責務整理のローカル検証は完了。追加承認に基づき本番反映を確認する |
| Source Health | 読取り専用CLI、時刻順、旧計数null、source完了とstreakをoffline検証 | 新CLIの本番GCS読取りを実施したとは扱わない |
| browser/互換sync | 実Chromium・一時Vaultで回帰検証 | 指定browser source、利用者環境の本番受入 |

Batchの個別承認後の提出・拒否・追加提出0での失敗usage回収は[実行記録](archive/2026-10/batch-acceptance-2026-10-10.md)を参照してください。
本番prompt/schemaのSDK送信と不適合応答の拒否は確認済みですが、生成側の逸脱原因は未確定です。
schemaの緩和や有料再提出を今回の責務整理に含めません。

## 責務整理のローカル検証

変更前はPython 378件、Web依存監査4件、設定検証が成功しました。
変更後は**Python 382件・Web監査4件・設定・npm依存監査・actionlint**が成功しました。
画像付きfixtureと固定公開Git版のQuartz/Chromium受入、変更前後のNote/manifest/Quartz入力bytes一致、
wheel収録と配信後検証の`python -I -S`実行も確認しました。
具体的な固定版・件数・digestは[ローカル検証記録](archive/2026-10/domain-refactoring-2026-10-10.md)にあります。

## 継続する受入基準

- 保存障害で後続の有料処理を止める。API前後のusageとreceipt復旧で、元の日付・単価・既知countを保持し二重計上しない。
- Batchの曖昧な提出を自動再提出しない。preflightは書込み・記事取得・Gemini操作を行わず、未決済と不明usageを隠さない。
- 不完全manifest、改変bytes、私的ファイル、symlink、別commit、fixtureの本番混入を拒否する。
- GCS/export失敗後にGit/Pages更新へ進まない。固定公開Git版のWeb buildにGCS/Gemini認証を要求しない。
- 同じNoteの元Markdown bytes・安定ID・dataset digestをGit/Webで照合する。静的artifactのhashとNote集合のhashを混同しない。
- 検索・全内部リンク・出典・版表示・375/768/1024/1440pxと画像をChromiumで確認する。許可画像のレスポンスだけを検証内で代用し、想定外の外部resourceを拒否する。
- 互換syncは人の編集を保持する。browserはdocument/resource/robotsのredirect先を通信前に検査する。

## 既存の修正と証拠

F1〜F6（Vault編集保護、Batch元例外型、browser redirect、部分usage、中断時費用、未処理source）は対応済みです。
当時の再現・修正・受入証拠は[旧検証記録](archive/2026-10/verification-before-domain-refactoring-2026-10-10.md)と[履歴入口](archive/README.md)にあります。
独立した未完了受入は[次の作業](next-work.md)で追跡します。
