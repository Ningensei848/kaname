# 残余制約の解消作業

2026-10-25。[作業一覧](next-work.md#残余制約と条件付きの作業)の残余項目を引き継ぐ。全体は未完了で、ローカル受入・main反映・本番受入を区別する。既定の生成設定や予算は変更せず、検証に新規の有料生成を使わない。

| ID | 完了を立証する条件 | 現在の状態 |
|---|---|---|
| R01 / #116 | 同じ対象期間/project/service/SKU・請求時間帯・適用換算レート・調整/税に対応づけ、既知/unknown usage・元価格・安定課金IDを保持して差額を計算する | 部分完了。CSVのproject/JPY/9/24〜10/23と、別途提供された9/1〜10/24のSKU内訳を区別した。Cloud Billing APIを有効化し、公式Catalogから9月・10月の円建て4 SKU単価と換算レートを取得。保存usageとの比較を実施したが、請求数量/割引/調整/税と未観測期間の帰属は未確定。公開単価は[取得記録](billing-catalog-2026-09-10.json)、個人の金額/明細は非公開で保管。export新設・新規query課金は行っていない |
| R02 / Graph | 概念と記事の関係を明示した設計で、存在する公開Note間に根拠のある導線を作る。自分自身/欠落/曖昧な推定先を排し、保存bytesと従来検索を保持して実HTML/index/移動を検証する | 実装・ローカル受入済み。321 Noteの検索語1,534件ではタイトル完全一致/正規化案とも0辺。定義先を推定せず、2つ以上の具体的な共有検索語を根拠に69 Note・136有向辺を別の関係として導入。[設計](graph-quality.md#共通検索語によるnote間の導線) |
| R03 / cache・差分build・DB | 現公開版と現在のGCSで、全件整合性/前後catalogを保持した工程時間・転送・メモリを測り、導入条件を判定する。制約が確認されれば同じgateで改善する | 評価完了、現規模では追加基盤を見送る。全state/runsを含む監査対象GCS 1,315 object/7,881,765 bytes、603成功行、最大RSS115,368 KiB。16並列load5.690秒、全体7.695秒、index349,566 bytes/0.006秒。全Web build/全受入3回も同じartifact/coverageで成功、全体中央値211.307秒。DB・run間cache・差分HTMLの導入が必要になる制約は現在未確認。下記の測定を基点に再判断する |
| R04 / Windows同期 | 新旧root/state/lock、編集・候補保持、両root拒否、全writer停止を伴う明示移行を現行コード・実Windows/一時NTFSで確認する | ローカル受入済み。Windows Python 3.13.1/NTFSとLinuxで成功。検査は `scripts/verify_sync_filesystem.py`。実Vault・利用者プラグインは従来どおり別の対象指定が必要 |
| R05 / 生成と保存 | 生成前の予約・取得済み応答の復旧・不明応答の後続run停止・明示的再試行の費用/対象制限・元課金履歴の保持を中断箇所ごとに検証する。API側の厳密なexactly-once保証とは区別する | 実装・境界テスト成功。standard予約/応答/元組立て情報を保存し、取得済み結果は追加API0で復旧。不明なtimeout/切断/5xxは自動再送しない。元runのusageと失敗した再試行も保持。現GCSの読取りでは未解決のstandard予約・旧保留usageは0件。[操作](operations.md#standard生成の予約と明示的な再試行) |
| R06 / 要約の事実確認 | 固定321 Noteのタイトル/要約/重要ポイント/資料の位置づけを原典の根拠と対応づけ、訂正・時点差・未確認をNote hash単位で記録する。対象外/未確認を全件確認済みとしない | 未完了。原典照合を45件実施し、12件で用語/数量/精度/提供時期・機能制約の訂正候補。12件のhash固定計画・履歴付き訂正/中断復旧を実装し、321件のローカルsnapshotへ適用/監査した。本番反映と残り276件は未完了。以下の確認記録を参照 |
| R07 / npm監査 | 既知警告の状況と修正版を再確認し、新規警告を例外化せず固定lock/integrityを更新、実監査と全Webを検証する | 依存更新・実監査・fixture/固定321件のGit/実Release全Webのローカル受入済み。旧2 advisoryは公式撤回、TOMLは新規3 advisoryの修正版5.0.1へ更新。警告0、許可例外0。[依存](web-preview.md#固定依存と残る制約) |

## 今回固定する版と境界

公開入力はcontent `406a716ef2462de01cc50faf09542c3e741c9b79`、dataset `595c002b1b9d60e1b9b5752cc62bf9edd98d158ede94176fe437d81f8a788733`、321 Note。元Markdown/manifestのbytesは変更していない。
実Web受入では全64一覧・3,241検索リンク・共有語136辺・画像付き192 Note/465画像の表示確認・検索ショートカット4通り・4幅・外部要求0を確認した。共有語のリンクは実際の移動/戻るまで検証した。

R05はAPIとGCSの分散transactionを導入するものではない。[generateContentの公式契約](https://ai.google.dev/api/generate-content)と[retryの説明](https://ai.google.dev/gemini-api/docs/troubleshooting)を確認したが、この実装でAPI側の処理とローカル/GCSのcommitを一体で確定する保証は立証していない。応答保存前に結果を失った場合、明示的な再試行には二重課金の可能性を残す。新規機構を導入する前の履歴から、失われた結果や未記録の元価格を推測復元しない。

R01では、支払・前払い・税・消費額を混同せず、現在の市場為替で過去のUSD推計を逆算しない。追加CSVの条件は利用者から確認した。後から提供されたSKU内訳は別の対象期間として扱う。利用者の居住時間帯はJSTだが、[Reportsの課金日区分](https://docs.cloud.google.com/billing/docs/how-to/reports)と同一とは仮定しない。

当初のSERVICE_DISABLEDを解消するため既存projectの `cloudbilling.googleapis.com` を有効化し、既存認証で公式Catalogの履歴価格を読み取った。IAM・請求先の変更、export作成、有料queryは行っていない。[Catalog契約](https://docs.cloud.google.com/billing/docs/reference/rest/v1/services.skus/list)の月区分はAmerica/Los_Angeles。9月の公表JPY/USD換算レートは約159.375、10月は約157.195で、[取得記録](billing-catalog-2026-09-10.json)に正確な返却値・SKU ID・有効日時・JPY units/nanosを残した。計算には丸めたレートでなく返却された円単価を使い、期間の絞込みと価格の有効時刻を分離する。run開始時刻と価格有効日時を照合した参考計算であり、個々の請求timestampは未取得である。

旧価格欠損9 runはActionsの元checkout/config/SDKと保存96 Noteを照合し、当時のモデル・standard mode・入出力token総数を確認した。元reportへ価格を追記せず、元価格と後から取得した公開価格を区別する。請求accountの最新4 SKU価格も取得し、公表単価と契約単価の一致・割引0を確認した。ただし最新値の取得は9月の契約価格や請求数量の証明ではない。百万token単位の最新価格は履歴Catalogのtoken単位nanosより精度が高いため、非公開比較に両者の精度差による感度も残した。保存usageは9/27からで、9/1〜9/26のproject全体利用は未観測。公開価格と契約単価、整数表示のSKU費用と未丸め費用、調整/税も同じと仮定しない。非公開の比較記録では期間・JST/Pacificシナリオ別に差を算出したが、完全照合や過剰請求の立証とはしない。既存CSVの残高検算完了を完全照合の完了へ置き換えない。

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

- Note `0d89805d9a93a297775ab35612d5d93ed4da1eeed982f3fcdb103a0273857e00`：重要ポイントの「ミリ秒単位」は[原典](https://blog.google/innovation-and-ai/models-and-research/gemini-models/introducing-agentic-video-in-gemini/)のsub-secondより細かい精度を断定するため、「1秒未満」へ修正する。モデル/ベンチマークの最大改善値/API提供/YouTubeへの今後の展開は一致した。

- Note `0da5ce80a6ea6e673e9c1726a129abeb1f5c317e8adfe2110e63400d74b4c30c`：[原典](https://research.google/blog/research-2026-10-ways-were-amplifying-human-ingenuity/)のTimesFM/TabFMのGemini for business統合は予定であり、その限定を要約へ追加する。MedGemmaの公開とAMIEの臨床研究を分け、AMIEの公開も示唆する重要ポイントを修正する。10/20のSynaptics発売追記は10/16生成の後であり、当時のNoteの誤りとは扱わない。

- Note `1542677d60df19fd297288d04f50e3c2b351ed5a746cb79b0e49fec9906e5e0b`：[原典](https://deepmind.google/blog/teaching-ai-to-see-the-world-more-like-we-do/)は100万枚の画像から数百万の判断データを生成している。要約の「数百万枚の画像」を「100万枚の画像」に直し、データの種類と件数を区別する。

- Note `1b499f786fc3a15442f694a69dc2d9589e630e658e81e5e56dc8159bdd1f6bc8`：資料の位置づけが「短い文脈」の非効率性としているが、[原典](https://machinelearning.apple.com/research/selection-structured-reasoning)の問題設定は小型モデルの容量制約である。「小型モデルでの推論の非効率性」に直す。

- Note `1c7f4fe01d7c843ec24c22a487d2fd3dff71947e57e93294d5cd8b2c359f6441`：[原典](https://engineering.fb.com/2026/10/15/ml-applications/how-meta-built-forum-ai-native-engineering/)はhuman-on-the-loopを目標とし、一部工程では人が各反復に関与すると明記する。要約と重要ポイントを、全面移行の完了ではなく段階的な自律化として記述する。

- Note `1ceda08d39d967b49c82f7937ace210a2daaf3ef65eac0d6a2d7fb280c4fe1be`：[原典](https://blog.cloudflare.com/emudhra-certificate-compromise/)の10/19約17:00 UTCはCloudflareが侵害を把握した時刻である。重要ポイントも把握日として記述し、鍵の侵害そのものの発生日と混同しない。

- Note `1f1c14a1caf775277d37ce96d65f8889d1b5343aaa92aeb7c8b6ae126bcf85fd`：[原典](https://blog.google/innovation-and-ai/technology/developers-tools/gemini-3-pro-image-developers/)のphysicsは照明・カメラ・フォーカス・色調などの画像表現の制御であり、「物理演算」を示すものではない。Google Search groundingも有効化時のWeb参照として説明し、常時の動作や正確性を保証する表現を避ける。

[訂正文案](note-reviews/2026-10-25-corrections.json)の12件を `config/note-corrections/` の実行可能計画へ変換した。元Note hash・置換後テキストhash・出典・置換数を固定し、訂正履歴のfrontmatterと可視footerを付けるため、最終Note hashは文案hashと異なる。訂正者は `automated_assistant` とし、人による専門家確認とは表示しない。

原receiptの全bytesを非公開の訂正履歴へ保持し、durable intentによりreceipt/Noteの片側保存から追加生成なしで復旧する。生成日時/モデル/本文hash・安定ID・index・runs/usageは維持する。12件の適用は実GCSを読んだメモリ上のsnapshotだけで実施し、index/runs/usageと費用集計が不変、監査成功、321件中ちょうど12 Note変更を確認した。訂正後datasetは `d4166060aef453f32ad6e0ec7ce214ab25cf0014a72a0c9b5eb4901343a97dc2`。ローカルGit/組立てたReleaseの復元bytesも一致した。実GCS・公開content/Release/Pagesへの訂正適用は未実施である。

Dailyの既存WIF許可対象内に専用jobを追加し、既定はpreview、他modeとの混在を認証前に拒否する。適用と公開は別操作。[操作と復旧](operations.md#原典照合による既存noteの訂正)を参照する。45件の結果を全321件へ一般化しない。
