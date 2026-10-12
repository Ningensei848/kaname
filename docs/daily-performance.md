# Daily TechKBの所要時間短縮 — 完了

2026-10-12 JST、GCS読取りを並列化し、同じrunnerで変更のないbytesを再利用しました。同じ7 source・生成0の実Actionsで **39分22秒→15分30秒（60.63%短縮）**。全工程と公開版の一致まで受入完了です。通常の生成30件のrun時間を保証する測定ではありません。

## 原因と実測

成功5 runは23〜39分（平均29分42秒）。Gemini生成0でも長時間で、過去408行のNote/receiptの逐次読取りとexportによる全件再取得が支配的でした。`GCSStore.read`は各objectでmetadata取得と世代指定の本文取得を行い、費用/通知の別CLIも同じreport/usageを繰り返し取得していました。

[改善前run](https://github.com/Ningensei848/kaname/actions/runs/38218566607)と[改善後run](https://github.com/Ningensei848/kaname/actions/runs/38228574550)の比較です。全件の検査、記事取得順/間隔、生成上限0を維持しました。

| 工程 | 改善前 | 改善後 |
|---|---:|---:|
| 記事収集 | 9分09秒 | 9分03秒 |
| 全件監査 | 7分25秒 | 1分02秒 |
| 費用/通知計画 | 2分54秒 | 0分16秒 |
| 通知適用 | 1分24秒 | 0分06秒 |
| export | 13分45秒 | 0分13秒 |
| 全体（準備・Git・Pagesを含む） | 39分22秒 | 15分30秒 |

Actionsのqueueと通信条件も全体時間に含まれます。改善前5 runと改善後の工程/計数は[改善前JSON](archive/2026-10/daily-performance-before-2026-10-12.json)・[改善後JSON](archive/2026-10/daily-performance-after-2026-10-12.json)で追跡できます。

## 責務の分離と並列処理

- `storage.py`は世代指定の読み書き、競合拒否、clientの所有を担当。
- `read_snapshot.py`は読取り専用のlive catalog、最大8件の並列download、CRC32C検査とcacheを担当。必要prefixだけを取得し、raw HTMLは含めません。
- `audit.py`/`costs.py`/`publication`の全件の整合性・課金・公開内容検査は維持。CLIは検証済みの読取りcontextから結果を受け取り、成功出力/通知適用前にlive catalogを再確認します。
- exportは出力install前にlive catalogを再確認。追加/削除/置換/同じbytesの世代更新を拒否し、indexを最後に再確認します。
- `TECHKB_READ_CACHE`はprivateなrunner一時領域。bucket/name/generation/CRCが一致するbytesだけを再利用し、cache破損時は再取得します。検査結果はcacheせず、Actions cache/artifactにも保存しません。**別run間の永続cacheではありません**。
- Gemini生成とGCS更新は既存の単一writerです。Node/Quartzはpublic snapshotのレンダリングとbrowser検査を担当します。

[Cloud Storageの強い整合性](https://docs.cloud.google.com/storage/docs/consistency)と[世代の前提条件](https://docs.cloud.google.com/storage/docs/request-preconditions)を基準に、本文を再取得する代わりにlive catalogの世代/CRCを照合します。一覧全体を原子的transactionとは扱いません。

実Actionsの計数です。監査で取得したうち818 objectを、exportで追加downloadせず再検査しています。

| 工程 | objects | 本文download | cache hit | workers |
|---|---:|---:|---:|---:|
| Audit saved state | 819 | 819 | 0 | 8 |
| Cost and notification plan | 66 | 66 | 0 | 8 |
| Cost and notification plan | 66 | 0 | 66 | 8 |
| Publish necessary notifications | 66 | 0 | 66 | 8 |
| Export only validated public Notes | 818 | 0 | 818 | 8 |

## 検証と本番受入 — 完了

- [x] 全Python642件（並列数・世代競合・cache破損・公開前停止10件を含む）、actionlint成功。
- [x] [PR #173](https://github.com/Ningensei848/kaname/pull/173)をmain `64f5121f4d22741d1316d211ab2c5c57563f9428`へ取込み。[PR CI](https://github.com/Ningensei848/kaname/actions/runs/38225651234) / [main CI](https://github.com/Ningensei848/kaname/actions/runs/38226125735)のPython/Web成功。
- [x] ローカル実GCSで監査5.935秒、export2.298秒（追加download0）、費用cold0.527秒/warm0.218秒、監査/費用/公開digest一致。Actionsと異なる通信条件なので、この値をActionsの保証には使わない。
- [x] 生成0の本番で収集・監査・費用・export・Git・Pages・配信版確認がすべてsuccess。追加生成/保存/課金record0、index408/pending145を保持。
- [x] 再測定前の既存883オブジェクト（pendingを除く）の世代/CRC、Note/receipt/index/usage/Batchの集合、元usage/価格・日次/月次費用、元pendingの全項目を保持。
- [x] 公開126件の最新Note/receipt/indexとsnapshot bytes一致、959検索リンクを検証。公開commit/dataset/artifactと実配信manifest・HTML hashは従来版と一致。
- [x] 一時的な収集失敗の復旧を確認し、通知[#174](https://github.com/Ningensei848/kaname/issues/174)をClose。Open Issueは明細待ち#116のみ。

追加Gemini費用USD 0。元の承認USD 1枠は累計USD 0.2139474、残額USD 0.7860526です。確定請求・GCS/Actions費用とは区別します。

## 一時的なHTTP 500の記録

最初の[実測run](https://github.com/Ningensei848/kaname/actions/runs/38226576230)はDeepMindの3記事でfetch失敗。HTTP 500を14応答観測し、既存retry後も3件が失敗したため監査/公開は正しくskipしました。生成/保存0・元費用/保存を保持。同じ設定の再取得で3件すべて200・最終host適合を確認して再測定し、全工程が成功しました。

失敗reportは削除しません。DeepMindはpending96件があるため、生成0の成功で未完了sourceのstreakをresetしない既存規則によりSource Healthはfailing/streak1を保持しています。現在の取得成功と、全候補のNote処理完了を区別します。他2既存sourceはhealthy、追加4社はunverified/streak0です。

## 残る時間と後続候補

収集9分03秒が残り時間の中心です。記事取得は最大2件の先行処理でも、candidateのsource別の並びとhost間隔/transport lockにより同じhostを直列化します。以前のrunではredirectも含むHTTP応答351回を観測しました。並列数を増やすだけで同じhostの間隔は短縮しません。

Web環境準備55秒、Quartzビルド/検査89秒、deploy/配信確認を含むjob約32秒。Python全テスト35秒も維持します。次の候補はsource別の先行取得、HTTP条件付き再取得、Webコード/config/lock・Note以外のリンク/タグ/検索index・切戻しも含む無効化条件を定めたartifact再利用です。取得順/freshness/課金対象/公開provenanceを変える案は、今回の受入と分けて評価します。
