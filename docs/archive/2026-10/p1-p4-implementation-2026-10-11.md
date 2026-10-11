# P1〜P4（Parallel Processingまで）の実装・受入記録

2026-10-11。P4のKnowledge Graph QualityとNS1は今回の範囲外です。
元から存在したNS1の未コミット計画は保持しています。

## P1: PR検証の対象選択

固定base/headの`git diff --no-renames --name-only -z`で削除・renameの両側を分類します。
比較不能・未知pathではPython/Webの全検査へ戻します。
文書のみは重い検証を省略、sources設定は本文/画像/HTTP/corpus、app設定は生成/保存/公開契約、
画像補完計画は実JSONのschemaと補完回帰を検査します。Python/依存/共通契約は全Python回帰を残します。
Webと公開契約の変更はWeb受入を実行し、混在変更では必要な検査群を合併します。

実検証は`python-checks`/`web-checks`で実行し、既存の`test`/`web-preview`は
`always()`でscopeと実jobの結果を集約します。必要な検査の失敗・中断をskip成功へ変換しません。
分類/実Git比較15件、設定混在の対象回帰233件、actionlint成功。
実PRのjob選択は別途CIで確認します。

## P2: 費用推定とBatch切分け

ユーザー提供のAI Studioスクショは、月額上限800円・現在175円、
2026-09-14〜2026-10-11の28日表示173.04円です。
上限表示と期間合計は範囲/更新時刻が異なるので、確定明細や同一期間の請求とは扱いません。

[抽出した計数](actions-cost-evidence-2026-10-11.json)はDaily TechKB全33回
（schedule14回、手動19回）のログから収集report21回を抽出したものです。
standard336呼出しと別のBatch提出2 requestを区別します。
公開/診断/事前検査/補完だけの手動実行を、有料の新規生成回数へ加えません。
10月2〜10日は通常30呼出し/日、standard HTTP attemptも30/日で、thinking tokenは0でした。
Batch回収費用は専用reportへ記録するため、収集reportのtoken0を無料と誤認しません。

[最新の日次run](https://github.com/Ningensei848/kaname/actions/runs/38100338209)のcost-reportは
10月推計USD 1.0921521、9月推計USD 0.0152929、unknown/未計上Batch/未完了standard usageはいずれも0。
通常9日平均は約USD 0.09897/日、31日なら約USD 3.08です。
[公式価格](https://ai.google.dev/gemini-api/docs/pricing)の
Gemini 3.5 Flash-Lite standard（入力0.30/出力2.50 USD per 1M、thinkingを出力へ加算）、
Batch（入力0.15/出力1.25）は設定と一致します。

円の目安は、スクショ175円と10月台帳1.092 USDの対応を仮に使った外挿が約492円/月、
表示済み10日で175円として31日へ伸ばす保守的な外挿が543円/月です。
この対応は為替レートの測定ではなく、時差・反映遅延・他利用の有無も確定していません。
そのため通常運用の目安を500〜550円/月とします。

| 同程度の記事長・出力・再試行率を仮定 | 円/月の目安 |
|---|---:|
| 現状と同程度 | 500〜550 |
| 有料処理量25%増 | 625〜690 |
| 有料処理量50%増 | 750〜825 |
| Batchを同じtoken量で安定運用できた場合 | 通常推計の約半分（成功受入前の仮定） |

800円以内という見立ては現状〜25%増なら妥当です。50%増まで保証はできません。
無料枠を見込まず、GCS/Actions費用と確定請求照合をこのAPI推計へ混ぜません。

安くするため、今回の調査は新規Gemini呼出し0、CIの不要なPython/Web/Chromiumを省略し、
fetch/convertを並列化します。本文20,000文字・出力2,048 token・通常30件上限は維持します。
公開repoのActions実行時間をGemini料金へ換算しません。
Batchは単価が半分でも拒否後の再生成が節約を相殺するため、通常設定はstandardのままです。

同じarticle/metadata/画像/prompt/schemaをstandardとBatchへ渡し、固定SDKの実HTTP serializerで
payloadの完全一致を確認しました。送信差分に基づく修正理由は得られていません。
既存のschema拒否・失敗usage回収は維持し、schema緩和や盲目的な有料再提出を行いません。
**#94の成功保存は未受入、#116の確定請求照合は明細待ち**です。
今回の費用推定と無課金切分けの完了を、それらのCloseと取り違えません。

## P3: Source Healthの実GCS読取り

2026-10-11 10:57 JST、再認証後の実ADCでCLIの読取りが成功しました。
GCS一覧/ダウンロードのみで、記事取得・Gemini・write・通知・export・公開は行いません。
335 success行、pending72件。GitHub Blogはhealthy（35行、pending0、最新保存1件）、
Google Researchはfailing（300行、pending72、最新保存28件、streak3）、AWSはdisabled。
CLI自体のsuccessとsource全体のdegradedを分け、部分保存をsource完了扱いしません。

同日のpreflightは01:57:20 UTCにready、audit success/障害0。
active ledger・未計上Batch・未完了standard usage・不明usageはいずれも0でした。
この読取りでSource Healthの本番GCS受入は完了し、sourceの既知失敗は残ります。

## P3: Regression Corpus

Google Researchの複数本文section/別mediaと、GitHub Blogのarticle/figureを模した
合成HTML・本文golden・画像候補manifestを固定しました。原文/画像bytesはコピーしません。
`python scripts/regression_corpus.py`は変換差分をunified diff、候補変化をJSONで示し、差異で失敗します。
source設定と20,000文字上限を実設定から読み、変更を自動承認するgolden再生成は実行しません。
本文の末尾・画像8/1件・caption/alt・差分検出の回帰3件が成功しています。

GitHubは現在の全ページ変換をbaselineとして固定しています。navigationが残る既存挙動を、
本文selectorで除去済みと偽りません。実サイトのDOM変化は新fixtureをレビューして取り込みます。
このoffline corpusだけでは、実サイトの将来の変更を自動取得・検知しません。

## P4: Parallel Processing

`processing.workers`は1〜8、既定モデルは1、運用設定は2です。
最大workers件のfetch/convertを先行処理し、完了順に関係なく入力candidate順で結果を処理します。
報告、重複判定、LLM/Batch準備・提出、usage、receipt/Note/index/pendingは主threadだけで行います。
保存障害で後続課金を止め、未開始futureをcancel、実行中の無課金取得が完了してからclientを閉じます。

HTTPはhostごとの排他で開始間隔・retryを維持し、robots cacheは別lockで重複取得を防ぎます。
robotsが別hostへredirectしても複数transport lockを逆順で取得しません。
MarkItDownはthreadごとに独立したengineを使います。
同じhostのnetworkとLLMは逐次なので、全runの時間が半減するとは主張しません。

並列完了の逆転、単一writer、重複/上限、保存障害時の先行取得最大2件、dry-runの無更新、
host間隔/robots一回、異なるhostの実同時要求、設定上限を10件で検証しました。
12件・各取得0.1秒の模擬benchmarkは、workers1で1.374秒、workers2で0.768秒（約44%短縮）。
実HTTP/LLMの本番時間計測とは別です。`workers: 1`で逐次へ戻せます。
