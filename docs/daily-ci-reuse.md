# 日次のCI検査再利用 — 本番受入完了

2026-10-14に着手し、2026-10-15 JSTに[PR #189](https://github.com/Ningensei848/kaname/pull/189)・main CI・[生成0の本番run](https://github.com/Ningensei848/kaname/actions/runs/38636811545)まで受入完了しました。同じ186記事の比較で日次全体は434→450秒（16秒増）、設定検証/重複単体テストの工程は38→3秒でした。全体時間はrunner・queue・通信の影響を含む1組の比較で、毎日の安定値を保証しません。

## CIと日次の責務

`scripts/daily_validation.py`は設定を毎回検証した後、実行中のmainコミットと完全に一致するChecksのpush実行をGitHub APIで確認します。最新run/attemptが完了・成功し、`scope`・`test`・`web-preview`が同じSHAで成功した場合だけ、日次の重複単体テストを省きます。Checksでは従来どおり変更対象に応じたPython/Web検査を実施します。

別SHA・PRの結果、別workflow、別repository、古い成功より新しい失敗/実行中run、不完全な一覧、権限不足・API障害・応答途中切断では、日次runnerで従来の全単体テストを実行します。main以外も同様です。API問い合わせは最大2回・各10秒のtimeoutを持ち、例外に含まれる認証情報をログへ出しません。`--full-tests`で明示的に従来動作へ戻せます。

日次の設定検証、実行モード/費用上限検証、GCS全件監査、usage集計、通知、公開snapshot/Releaseの復元、Quartz全体build、全リンク・全画像・4幅の検証、配信照合は継続します。コードの単体テスト結果を再利用し、GCSの検証結果は毎回取得・検証します。追加する権限はcollect jobの`actions: read`のみです。

## 実Actions比較

| 工程 | 変更前 | 変更後 |
|---|---:|---:|
| 日次全体（queueを含む） | 434秒 | 450秒 |
| 設定検証・単体テスト/CI照合 | 38秒 | 3秒 |
| collect job | 207秒 | 171秒 |
| publish job | 50秒 | 41秒 |
| pages / build job | 136秒 | 145秒 |
| pages / deploy job | 24秒 | 79秒 |

[変更前run](https://github.com/Ningensei848/kaname/actions/runs/38576793852)と変更後runは同じ186 Note・content/dataset/artifactです。生成あり30件の2026-10-14通常日次（651秒）や以前の156記事版とは直接比較しません。変更前はRSSの新候補1件で保留102→103、変更後は新候補7件で103→110となりました。本文HTTP・API試行・生成・保存はいずれも0です。

collect jobは207→171秒、publishは50→41秒でした。一方、Web buildは136→145秒、deployは24→79秒となりました。deploy内のPages処理が6→44秒、配信照合が9→21秒に延び、全体は16秒増です。今回の全体短縮達成とは扱わず、重複検査の35秒削減と区別します。

## 検証・受入

- [x] 関連49件・全Python767件・実Web5件・actionlint・[PR CI](https://github.com/Ningensei848/kaname/actions/runs/38577397359)・[main CI](https://github.com/Ningensei848/kaname/actions/runs/38578311917)が成功。異なるSHA/PR・失敗/実行中CI・必要job欠落・API障害のフォールバック、設定不正時の停止、GCP認証前の検証配置を確認。
- [x] 本番でmain `0509017897d225ba03a1f565e1376e4160ec6262`のChecks `38578311917`/attempt1を再利用。設定検証を毎回実施し、実行工程38→3秒。
- [x] 再認証後の独立GCS読取りで、全468成功行/Note/receipt/indexと公開186件の全bytesが一致。変更後実行前の1,016オブジェクトのうち、pending以外の1,015世代/CRC・元usage・費用を保持。旧103候補は全項目保持、新候補7件だけ追加し、生成0 reportを1件追加。読取り中のcatalog変化なし。
- [x] 4 Release/8 assetsのID・size・digest、content/dataset/artifact、公開snapshot全188ファイルのbytes、GitのNote/manifest・配布メタデータ189ファイル、実配信版と全元Markdownを照合。公開186件・検索1,771リンク・画像入り123頁/306応答・全4幅・外部通信0を維持。
- [x] 日次/月次費用・未決済/不明usage0・追加Gemini USD 0。Open Issueは請求明細待ち#116のみ。解消済み通知#185などはClosedを維持。

GCSの世代基準は変更前runの後・変更後runの前に取得しました。変更前run以前との世代不変を今回のcatalog比較で主張しません。変更前run自体のActions監査・費用・公開版照合は成功しています。

[機械可読の受入証拠](archive/2026-10/daily-ci-reuse-acceptance-2026-10-15.json)に各工程と比較条件を保存しました。次の優先はGCSの取得です。今回の監査70秒のうち、939オブジェクトを8並列で取得する処理が64.565秒でした。同じ世代を固定して8/16並列と接続poolを比較し、全件監査を保ったまま短縮を判断します。全体の継続的な安定短縮、run間のprivate cache、Release作成時の同じ基底assetの再取得、Web環境/artifactの再利用条件も後続です。

## 費用・Source Health

[2026-10-14の通常日次](https://github.com/Ningensei848/kaname/actions/runs/38494491675)は30 API試行/30保存・不明usage0、input124,235/output18,164/thinking0、推計USD 0.0826805でした。以前の追加承認累積USD 0.2922302へ一度だけ加算し、追加承認USD 1の累積USD 0.3749107・残額USD 0.6250893です。今回の性能比較でAPI費用は増えていません。確定請求照合#116は明細待ちのままです。

現在はindex468/public186/pending110。DeepMind43・GitHub4・Google Research3・Microsoft11・Meta13・Apple16・Cloudflare20が保留です。DeepMindは61成功行・failing/連続失敗2を保持。Google Researchは新候補3件を未処理としてhealthy→incompleteとなりました。全体degraded、追加4社unverifiedを維持し、配信成功をsource全件完了とは扱いません。
