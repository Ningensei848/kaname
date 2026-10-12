# 現在の検証範囲と受入基準

要件は[仕様書](specification.md)、操作は[運用手順](operations.md)、公開契約は[公開・配布](publication.md)を正本とします。
本書は実装・ローカル検証・本番受入を区別して現在の状態を示します。
過去のrun、commit、件数、初回受入値は[責務整理前の検証記録](archive/2026-10/verification-before-domain-refactoring-2026-10-10.md)へ保存しました。

## 現在の状態

| 領域 | 実装・検証 | 未受入・限界 |
|---|---|---|
| standard収集 | 本番稼働。部分usage、receipt復旧、保存失敗後の停止を障害注入で検証 | 確定請求明細との照合 |
| Batch | PR #153/#156で画像型/候補外IDを解消。個別承認1job/1記事の実返却が厳格検証に成功し、3画像入りNote 1件を保存・公開。receipt/Note/index・artifact/Git/GCSのbytes一致、index336/pending71、課金record1・usage欠損0 | 追加生成0の再実行も全工程success、保存/課金bytes・世代・日次/月次費用・公開manifest/content commit不変を受入。外部画像の内容・存続はGit版で固定できない |
| Google Research本文抽出 | 本文専用selectorを実記事4件で検証。GlucoFMの8図候補、standard/Batchの末尾図配置とnavigation変更の重複判定をoffline回帰 | GlucoFM補完は本番受入済み。新規Batch Noteでも3画像の実選択・保存/公開を受入 |
| 記事画像 | 候補ID/URL/配置、standard/Batchをoffline検証。GlucoFMの2図補完、実GCS/Git/Pages、375/1440pxの実画像読込みを受入済み | 新規Batch Noteの3画像実選択・保存/公開を受入。外部画像の内容・存続はGit版で固定できない |
| 公開snapshot/Git | 初回公開と通常schedule受入済み。完了manifest・世代/bytes・競合拒否を検証 | 利用者Vault/プラグイン/NTFSは別の受入 |
| Web/Pages | fixture/固定Git版、元Markdown、検索・内部リンク・画面幅・配信版照合を検証。初回公開・通常schedule・切戻し/復帰、責務整理後の124件版の本番更新・配信照合を受入済み | — |
| Source Health | 読取り専用CLI、時刻順、旧計数null、source完了とstreakをoffline検証 | 2026-10-11に実ADC/GCS読取りを受入。全体degradedはGoogle Researchの既知失敗・pendingを反映 |
| CI対象選択 | 固定base/head分類、設定のみPRの必要検査成功・Web省略、本体PRのPython全460件/Web成功 | 未知path・比較失敗では全検査 |
| Regression Corpus | 有効2 sourceの合成HTML・本文/画像golden・差分検出3件を検証 | 実サイトの将来のDOM変更を自動取得する機能ではない |
| Parallel Processing | fetch/convert最大2件、入力順・単一writer・host間隔・robots・課金停止の回帰12件を検証 | 本番の時間短縮は未計測。workers: 1で逐次へ戻せる |
| Knowledge Graph Quality | 検証済み公開snapshotの無通信/無書込み評価、同義語/異なる語16例を含む27件、固定実content125 Noteの元hash不変 | 検索語612件は全件未解決。正規化案の保存/公開への適用、本文WikiLink・Google検索はNS1で実装済み・本番受入待ち。詳細は[品質評価](graph-quality.md) |
| NS1の検索導線 | 共通本文WikiLink/公開検証/投影・クエリ/保護構文40件、全Python542件、架空3 NoteのChromium受入 | 固定実content125 Note/612検索リンク・元hash不変を受入。本番Pagesは進行中。[NS1記録](ns1-search-fallback.md) |
| browser/互換sync | 実Chromium・一時Vaultで回帰検証 | 指定browser source、利用者環境の本番受入 |

Batchの個別承認後の提出・拒否・追加提出0での失敗usage回収は[実行記録](archive/2026-10/batch-acceptance-2026-10-10.md)を参照してください。
PR #148のGET診断でimages文字列3件を確認し、#149/#151/#153で直接object定義とAPI対応responseSchemaに修正しました。
その後の候補4件/選択5件は候補外ID 1件と確定し、#156で記事別候補ID.enum/件数上限を追加しました。
関連86件・全Python476件/Web・PR/main CI成功後、別枠1job/1記事の実Batchが厳格検証に適合し、画像3件のNoteを保存・公開しました。
追加生成0の回収workflowはcollection/audit/cost/Git/Pages・配信元Markdown照合すべてsuccess。
台帳complete・課金record1・usage欠損0、input3553/output729/thinking0、費用推計USD 0.0014442（約0.23円）。
追加生成0の再実行もcollection/audit/cost/Git/Pages・配信照合すべてsuccess、データ/費用/公開版不変、課金record1を受入済みです。根拠は[受入記録](archive/2026-10/batch-images-type-diagnosis-2026-10-11.md)で追跡します。

Google Researchの本文抽出・実HTTP検証と画像候補の残課題は[検証記録](archive/2026-10/google-research-body-extraction-2026-10-10.md)にあります。

altエスケープとmedia captionの修正・実HTML再生は[検証記録](archive/2026-10/image-candidate-text-matching-2026-10-11.md)を参照してください。

既存Noteの限定補完の実装・障害復旧・本番受入は[記録](archive/2026-10/glucofm-image-repair-2026-10-11.md)で追跡します。

## P1〜P4の今回の検証

CI対象分類・実Git比較15件、設定混在233件、Regression Corpus3件、Parallel12件、
standard/Batchの実HTTP payload比較（画像あり/なし）を追加しました。
Source Healthの実GCS読取りと最新preflight readyを確認しています。
P1は設定のみPR #142のPython成功/Web省略・既存check成功、本体PR #141の全検査成功を受入済みです。
Python全460件、fixtureのQuartz/Chromiumも成功。
費用はスクショと全Daily履歴から推定済みです。実Batch成功保存/公開・追加生成0の再実行まで受入完了、指定されたP4: Parallel Processingまで完了しました。確定請求照合は明細待ちの別項目です。
実装・計数・限界は[作業記録](archive/2026-10/p1-p4-implementation-2026-10-11.md)で追跡します。

## 責務整理のローカル検証

変更前はPython 378件、Web依存監査4件、設定検証が成功しました。
変更後は**Python 382件・Web監査4件・設定・npm依存監査・actionlint**が成功しました。
画像付きfixtureと固定公開Git版のQuartz/Chromium受入、変更前後のNote/manifest/Quartz入力bytes一致、
wheel収録と配信後検証の`python -I -S`実行も確認しました。
具体的な固定版・件数・digestは[ローカル検証記録](archive/2026-10/domain-refactoring-2026-10-10.md)にあります。

## 責務整理のPR・本番受入

追加承認後、PR #131をCI成功時のheadでmainへ取り込み、マージ後CIも成功しました。
固定公開content 124件のPages更新・全元Markdown配信照合と、移設後の読取り専用Batch preflight readyを確認しました。
更新前後のdataset/artifact digestは同一で、新規の有料収集・Batch提出・GCS書込みは行っていません。
run、commit、digest、GCS判定と独立検証の証拠は[PR・本番受入記録](archive/2026-10/domain-refactoring-production-2026-10-10.md)にあります。

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
