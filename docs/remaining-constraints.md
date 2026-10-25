# 残余制約の解消作業

2026-10-25。[作業一覧](next-work.md#残余制約と条件付きの作業)の残余項目を引き継ぐ。全体は未完了で、ローカル受入・main反映・本番受入を区別する。既定の生成設定や予算は変更せず、検証に新規の有料生成を使わない。

| ID | 完了を立証する条件 | 現在の状態 |
|---|---|---|
| R01 / #116 | 同じ対象期間/project/service/SKU・請求時間帯・適用換算レート・調整/税に対応づけ、既知/unknown usage・元価格・安定課金IDを保持して差額を計算する | 未完了。既存2 CSVは同じhashで、帰属/時間帯/換算レート等の列がない。追加の `agent_billing_data.csv` はGemini APIの小計1行。利用者から対象project・JPY・9/24〜10/23の出力条件を得た。SKU/請求時間帯/適用換算レート等は未記録。Drive・請求書メールでは不足項目を補う資料なし。現在の認証ではBilling APIが403、対象projectのBigQuery datasetも0件。権限変更・export新設・新規query課金は行わない |
| R02 / Graph | 概念と記事の関係を明示した設計で、存在する公開Note間に根拠のある導線を作る。自分自身/欠落/曖昧な推定先を排し、保存bytesと従来検索を保持して実HTML/index/移動を検証する | 実装・ローカル受入済み。321 Noteの検索語1,534件ではタイトル完全一致/正規化案とも0辺。定義先を推定せず、2つ以上の具体的な共有検索語を根拠に69 Note・136有向辺を別の関係として導入。[設計](graph-quality.md#共通検索語によるnote間の導線) |
| R03 / cache・差分build・DB | 現公開版と現在のGCSで、全件整合性/前後catalogを保持した工程時間・転送・メモリを測り、導入条件を判定する。制約が確認されれば同じgateで改善する | 評価完了、現規模では追加基盤を見送る。全state/runsを含む監査対象GCS 1,315 object/7,881,765 bytes、603成功行、最大RSS115,368 KiB。16並列load5.690秒、全体7.695秒、index349,566 bytes/0.006秒。全Web build/全受入3回も同じartifact/coverageで成功、全体中央値211.307秒。DB・run間cache・差分HTMLの導入が必要になる制約は現在未確認。下記の測定を基点に再判断する |
| R04 / Windows同期 | 新旧root/state/lock、編集・候補保持、両root拒否、全writer停止を伴う明示移行を現行コード・実Windows/一時NTFSで確認する | ローカル受入済み。Windows Python 3.13.1/NTFSとLinuxで成功。検査は `scripts/verify_sync_filesystem.py`。実Vault・利用者プラグインは従来どおり別の対象指定が必要 |
| R05 / 生成と保存 | 生成前の予約・取得済み応答の復旧・不明応答の後続run停止・明示的再試行の費用/対象制限・元課金履歴の保持を中断箇所ごとに検証する。API側の厳密なexactly-once保証とは区別する | 実装・境界テスト成功、全Python/Web924件と追加境界テスト成功。standard予約/応答/元組立て情報を保存し、取得済み結果は追加API0で復旧。不明なtimeout/切断/5xxは自動再送しない。元runのusageと失敗した再試行も保持。現GCSの読取りでは未解決のstandard予約・旧保留usageは0件。[操作](operations.md#standard生成の予約と明示的な再試行) |
| R06 / 要約の事実確認 | 固定321 Noteのタイトル/要約/重要ポイント/資料の位置づけを原典の根拠と対応づけ、訂正・時点差・未確認をNote hash単位で記録する。対象外/未確認を全件確認済みとしない | 未完了。原典照合を18件実施し、5件で用語/数量/機能制約の訂正候補。残り303件と訂正反映が未完了。以下の確認記録を参照 |
| R07 / npm監査 | 既知警告の状況と修正版を再確認し、新規警告を例外化せず固定lock/integrityを更新、実監査と全Webを検証する | 依存更新・実監査・fixture/固定321件のGit/実Release全Webのローカル受入済み。旧2 advisoryは公式撤回、TOMLは新規3 advisoryの修正版5.0.1へ更新。警告0、許可例外0。[依存](web-preview.md#固定依存と残る制約) |

## 今回固定する版と境界

公開入力はcontent `406a716ef2462de01cc50faf09542c3e741c9b79`、dataset `595c002b1b9d60e1b9b5752cc62bf9edd98d158ede94176fe437d81f8a788733`、321 Note。元Markdown/manifestのbytesは変更していない。
実Web受入では全64一覧・3,241検索リンク・共有語136辺・画像付き192 Note/465画像の表示確認・検索ショートカット4通り・4幅・外部要求0を確認した。共有語のリンクは実際の移動/戻るまで検証した。

R05はAPIとGCSの分散transactionを導入するものではない。[generateContentの公式契約](https://ai.google.dev/api/generate-content)と[retryの説明](https://ai.google.dev/gemini-api/docs/troubleshooting)を確認したが、この実装でAPI側の処理とローカル/GCSのcommitを一体で確定する保証は立証していない。応答保存前に結果を失った場合、明示的な再試行には二重課金の可能性を残す。新規機構を導入する前の履歴から、失われた結果や未記録の元価格を推測復元しない。

R01では、支払・前払い・税・消費額を混同せず、現在の為替で過去のUSD推計をJPYへ逆算しない。追加CSVの通貨/期間/projectは利用者の出力条件で確認した。固定期間の保存usageを元run IDで統合し、元価格のある推計と旧価格不明9件を分けた。UTC/JSTと米国太平洋時間では境界のrunが1件異なり、請求側の時間帯を未確定のまま同期間と扱わない。製品別小計をこのアプリだけの消費額とも仮定しない。不足資料を取得できるまで完全照合/差額は未確定である。既存データによる残高検算の完了を、完全照合の完了へ置き換えない。

## 全WebとGCSの規模評価

同じ固定321 Noteを `scripts/benchmark_web.py --repeats 3` で全体build・全ブラウザ受入した。毎回入力Gitの前後、dataset、artifactと全検査件数を確認し、部分build・検査省略・入力cacheの持越しは行わない。依存engineとOS cacheは通常の同一環境であり、cold machineの測定ではない。

| 測定 | 1回目（秒） | 2回目（秒） | 3回目（秒） | 中央値（秒） |
|---|---:|---:|---:|---:|
| 全build | 53.299 | 70.207 | 67.630 | 67.630 |
| 全受入 | 133.388 | 141.968 | 143.677 | 141.968 |
| 合計 | 186.687 | 212.175 | 211.307 | 211.307 |

全回artifact `22681f844c17e6b2f09ef80db1f0ef80ad7fd81592060448b76d998a0f3783ee`。321 Note・64一覧・3,241検索リンク・136共有語辺・192画像付きNote/465画像の表示確認、検索ショートカット4通り、4幅、外部要求0で一致した。通常ナビゲーションの付随画像通信は2/1/3件で変動したが、465画像の検査は全回実行した。通信数を検査件数の代わりに使わない。実Release復元bytesもGitと一致し、同じ成果物への全受入が成功した。27件fixtureは9一覧・6共有語辺の移動/戻るも成功。

GCSは全state/runs込みで約7.9MB、全読取り監査7.695秒、最大RSS約113MiB、index読取り0.006秒だった。現在の規模でDBやrun間cacheを導入せず、全件整合性と全体buildを維持する。今後データ量・工程時間・転送・メモリが実行枠や利用要件を制約した時は、同じ検査範囲で再測定する。この数字を恒久性能や本番CDNの評価としない。

## 原典との比較で確認した要修正点

次は2026-10-25時点の原典との比較であり、人間の専門家による認証ではない。原典の更新と生成当時の情報を区別する。[確認記録](note-reviews/2026-10-25.json)は固定Note ID/元Markdown hashで管理し、単にリンクが開くことやJSON schemaに通ることを事実確認としない。

- Note `052905967cd9c26a9a3dfb1ea2e8e4673142f52d0088f4160b947be02c3b2a68`：MedGemmaを「オープンソース」とした記述を要訂正とした。[原典](https://research.google/blog/bringing-foundational-models-to-the-front-lines-of-tb-screening/)はMedGemmaをopen-weightと明記し、MedSigLIP等の説明と区別している。モデルの公開とオープンソースを一括しない表現にする。
- Note `be3f1c0bcc40779de6e564476b7298ca69a2e3a08d76314fa33b74b2d9042469`：「フルビジネストラランザクション検出」は[原典のfull transaction detection](https://blog.cloudflare.com/full-transaction-waf/)の訳語として要訂正。HTTPのリクエストと応答の組を指し、「ビジネス」の追加と誤記を修正する。
- Note `81773d6be66ee1db0972d4fc28b5bc7c34c0ae72cd8a13934f87eb95473ec27e`：記載された2 CVE・無料/有料WAFの既定防御・request/responseの検出を[原典](https://blog.cloudflare.com/php-vulnerabilities-waf-protection/)と対応づけ、今回の比較では重大な不一致を見つけなかった。原典の10/23追記はNote生成後であり、新しいCVEまで当時のNoteに含まれていたとはしない。

- Note `0584b40568213c3756c7d8b8947bfd35321f9f72af6c81031d0b0b4a045544d2`：学習データ数の重要ポイントが「170万件以上」だが、[原典](https://deepmind.google/blog/beyond-tree-cover-mapping-the-worlds-forest-types/)は約170万件としている。下限の断定を避け、要約と同じ「約170万件」にする。

- Note `0763ba87a2c5f42f9562df1e47ddebb23b6aedb45bcfff75c0edb604dd35ba9d`：Gemini Omni Flashの動画入力対応が無条件に記述されている。[原典のLimitations](https://blog.google/innovation-and-ai/models-and-research/gemini-models/gemini-omni-flash-nano-banana-2-lite/)は、動画参照がAPIで受理されても発表時点では正しく処理されないと明記する。利用可能な機能と既知の制約を区別して追記する。

- Note `08eb26e4bb422574080621243ab16e70a56948062165b7f87c3cb2651399f903`：[原典](https://research.google/blog/next-generation-medical-image-interpretation-with-medgemma-15-and-medical-speech-to-text-with-medasr/)のmedical dictationを要約で「医療辞書」としている。「医療音声の書き起こし」に直し、既に書き起こしと記述している重要ポイントと整合させる。

[訂正文案](note-reviews/2026-10-25-corrections.json)に元/訂正案のhashと置換箇所数を固定した。元のNote bytesへ適用でき、5件とも既存の厳格なNote検証に通ることを一時メモリ上で確認済みだが、保存bytes・receipt・公開版はまだ訂正していない。訂正時は元の生成結果と人による訂正の出典/責任範囲を混同せず、変更と配布版を追跡する。18件の結果を全321件へ一般化しない。
