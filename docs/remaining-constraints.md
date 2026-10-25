# 残余制約の解消作業

2026-10-25。[作業一覧](next-work.md#残余制約と条件付きの作業)の残余項目を引き継ぐ。全体は未完了で、ローカル受入・main反映・本番受入を区別する。既定の生成設定や予算は変更せず、検証に新規の有料生成を使わない。

| ID | 完了を立証する条件 | 現在の状態 |
|---|---|---|
| R01 / #116 | 同じ対象期間/project/service/SKU・請求時間帯・適用換算レート・調整/税に対応づけ、既知/unknown usage・元価格・安定課金IDを保持して差額を計算する | 部分完了。CSVのproject/JPY/9/24〜10/23と、別途提供された9/1〜10/24のSKU内訳を区別した。Cloud Billing APIを有効化し、公式Catalogから9月・10月の円建て4 SKU単価と換算レートを取得。保存usageとの比較を実施したが、請求数量/割引/調整/税と未観測期間の帰属は未確定。公開単価は[取得記録](billing-catalog-2026-09-10.json)、個人の金額/明細は非公開で保管。export新設・新規query課金は行っていない |
| R02 / Graph | 概念と記事の関係を明示した設計で、存在する公開Note間に根拠のある導線を作る。自分自身/欠落/曖昧な推定先を排し、保存bytesと従来検索を保持して実HTML/index/移動を検証する | 実装・ローカル受入済み。321 Noteの検索語1,534件ではタイトル完全一致/正規化案とも0辺。定義先を推定せず、2つ以上の具体的な共有検索語を根拠に69 Note・136有向辺を別の関係として導入。[設計](graph-quality.md#共通検索語によるnote間の導線) |
| R03 / cache・差分build・DB | 現公開版と現在のGCSで、全件整合性/前後catalogを保持した工程時間・転送・メモリを測り、導入条件を判定する。制約が確認されれば同じgateで改善する | 評価完了、現規模では追加基盤を見送る。全state/runsを含む監査対象GCS 1,315 object/7,881,765 bytes、603成功行、最大RSS115,368 KiB。16並列load5.690秒、全体7.695秒、index349,566 bytes/0.006秒。全Web build/全受入3回も同じartifact/coverageで成功、全体中央値211.307秒。DB・run間cache・差分HTMLの導入が必要になる制約は現在未確認。下記の測定を基点に再判断する |
| R04 / Windows同期 | 新旧root/state/lock、編集・候補保持、両root拒否、全writer停止を伴う明示移行を現行コード・実Windows/一時NTFSで確認する | ローカル受入済み。Windows Python 3.13.1/NTFSとLinuxで成功。検査は `scripts/verify_sync_filesystem.py`。実Vault・利用者プラグインは従来どおり別の対象指定が必要 |
| R05 / 生成と保存 | 生成前の予約・取得済み応答の復旧・不明応答の後続run停止・明示的再試行の費用/対象制限・元課金履歴の保持を中断箇所ごとに検証する。API側の厳密なexactly-once保証とは区別する | 実装・境界テスト成功。standard予約/応答/元組立て情報を保存し、取得済み結果は追加API0で復旧。不明なtimeout/切断/5xxは自動再送しない。元runのusageと失敗した再試行も保持。現GCSの読取りでは未解決のstandard予約・旧保留usageは0件。[操作](operations.md#standard生成の予約と明示的な再試行) |
| R06 / 要約の事実確認 | 固定321 Noteのタイトル/要約/重要ポイント/資料の位置づけを原典の根拠と対応づけ、訂正・時点差・未確認をNote hash単位で記録する。対象外/未確認を全件確認済みとしない | 未完了。原典照合を77件実施し、36件に訂正候補。36件のhash固定計画を321件の公開snapshotで検証した。先の20件は実GCS読取り後のメモリ上の適用/監査も成功。追加16件の実GCS監査はADC再認証待ち。本番反映と残り244件は未完了。以下の確認記録を参照 |
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


- Note `207636f937b6c5e819a3e65705c6054fccf8873b7ee58db2666692b3f28bdafe`：[Omni 1.1 Flashの原典](https://blog.google/innovation-and-ai/technology/developers-tools/build-with-gemini-omni-1-1-flash/)の40秒は動画の累積長の上限。追加で40秒延長できる意味と区別し、10秒単位の延長と累積上限を明記する。

- Note `2106c2e5fddd4ff7a46c3e33f2e9d8be286a785dcf86f4786609695ba203ee8a`：[スマートフォンでの心拍測定の原典](https://research.google/blog/towards-passive-heart-health-monitoring-via-smartphone-camera/)のHR評価は信頼度による測定選別後の結果である。研究データ/モデルも、IRB承認等を満たす研究者の申請による非商用研究向けと明記する。

- Note `226d46957d80d407b3c27d9326c6335a50b7d50545bf914a015bc2985f79191c`：[OAuth移行の原典](https://blog.cloudflare.com/oauth-for-all/)のblue-green deploymentを「ブルーグリーンデプロイ」へ修正する。

- Note `2305d08929302b19d3cff782f2f79be4d91eb421d7801cc9f40ec66c434c4ef1`：[PaperVizAgent/ScholarPeerの原典](https://research.google/blog/improving-the-academic-workflow-introducing-two-ai-agents-for-better-figures-and-peer-review/)の60.2対50.0はLLM判定による比較評価。その評価主体を明記し、literature-groundedも「学術文献に裏付けられた」へ修正する。

- Note `2313553cd7a41529be7108ba86c1a8c8dc4652d1f350a2df030ac80bbe8da481`：[I/O Researchの原典](https://research.google/blog/a-new-era-of-innovation-google-research-at-io-2026/)の短期気象/災害予測を気候変動予測と区別する。Gemini for Scienceの発表と段階的アクセスも、無条件の公開完了としない。

- Note `23f6a4650f5cd70ccd39137f696b47a25055c59caaf7bb3e78ec44caa1186ca8`：[Marketing ops as codeの原典](https://github.blog/ai-and-ml/github-copilot/marketing-ops-as-code-automating-events-from-planning-to-follow-up-on-github/)は人の事前承認と終了後のコマンド起動を含む。全工程の無条件な自律実行と読める要約を修正する。

- Note `24285ad0c88f2d982a928f465f40825ac4029e011c9de03c80e0245368c2a440`：[WeatherNext 3の原典](https://blog.google/innovation-and-ai/models-and-research/google-deepmind/introducing-weathernext-3/)の約5倍は主要表面変数の空間解像度であり、精度の倍率ではない。medium-rangeは「中期」、100メートルは風速を測る高度として記述する。

- Note `255477ff21ef8c368d608123c42b0ba24cfdb2c043b42c921f299d133f6839f2`：[Cyberの原典](https://deepmind.google/blog/introducing-gemini-3-5-flash-cyber/)の表示日/構造化データと[同時発表](https://blog.google/innovation-and-ai/models-and-research/gemini-models/gemini-3-6-flash-3-5-flash-lite-3-5-flash-cyber/)は7月21日。Noteの7月17日を訂正する。CyberGymの大型モデルに対する競争力と、Big Sleepでのmainline Flashへの優位も区別する。

- Note `262b3d946d3a466922d3fb85aa602b22751b3b65fbf1ef7e625cd1ad8b47873b`：[原典](https://blog.google/innovation-and-ai/models-and-research/gemini-models/gemini-omni/)。音声参照は発表時点では声のみであり、その他の音声入力は今後の対応である。あらゆる入力という要約・ポイントにこの制約を明記する。 物理法則の直観を利用した動画表現を、検証済みの物理シミュレーションと混同しない。
- Note `26d7e55c48b9580825af7085289454557fc1fdb4b3699ade5efb57439d7ee498`：[原典](https://github.blog/security/how-one-bug-bounty-researcher-chooses-the-features-they-investigate/)。重大な脆弱性なら必ず3万ドル以上を得られるという最低額の保証に読める表現を、達する場合もある報酬として明確にする。
- Note `28d1e98bb25b487f0b8b2be2538cc863fce18b879816bfea748565b905659b2a`：[原典](https://blog.google/innovation-and-ai/models-and-research/gemini-models/gemini-3-1-flash-lite/)。2.5倍の速度向上は回答全体ではなく最初の応答トークンまでの時間である。重要ポイントも要約と同じ指標に揃える。
- Note `2a729e1bf8b6101c618e2955226c786627406284dffa86213219b7e93e895a18`：[原典](https://blog.google/innovation-and-ai/products/identifying-ai-generated-media-online/)。100 billion images and videosは1,000億以上の画像・動画であり、100億以上の画像という記載を数値と対象の両方で訂正する。 AI Content Detection APIの初期提供対象は信頼されたパートナーであり、その条件を要約へ加える。
- Note `2b60af235639ce04c74309137694ed0c208fc82d06a6cd6f61fd5283eddc01a2`：[原典](https://deepmind.google/blog/opening-new-paths-in-aging-research/)。重要ポイント末尾の「イ号」は原典にない無関係な断片であり削除する。
- Note `2bab48de568bc41c8e148b80d48d50d63ae6bd0b1ac8cbc4eef092cfea30501c`：[原典](https://blog.google/innovation-and-ai/products/nano-banana-pro/)。リアルタイム情報はGoogle Search接続を利用する場合であり、モデルが常時最新情報を持つと読める表現を限定する。 この発表のGemini画像検証はGoogle AI生成物が対象であり、任意の他社AI画像まで判別できる表現を避ける。
- Note `2c9ae35cb12b9c73a7012b0a49f7a1f59acb51431030baf2befb41eb3c4594ae`：[原典](https://blog.google/innovation-and-ai/technology/ai/veo-3-1-ingredients-to-video/)。参照画像をインディレッドとする無意味な語を、素材となる参照画像に修正する。 1080p/4Kアップスケーリングの提供先はFlow・Gemini API・Vertex AIのみであり、全製品の共通機能にしない。 SynthIDで検証する対象はGoogle AI動画であり、任意の他社AI動画の判別と混同しない。
- Note `2d411b6cf0a87af1ed5edb38f92c6d7865804ea2ca9694dfec8732776e4a7a41`：[原典](https://deepmind.google/blog/gemini-robotics-2-brings-whole-body-intelligence-to-robots/)。ASIMOV-Agenticは安全判断や不確実性対応の評価であり、ベンチマーク自体が安全性を担保するという表現を修正する。 原典の表示日と構造化データは7月30日であり、元Noteの公開日7月28日を訂正する。生成日時や元index/usageは保持する。
- Note `2e65d7de98b253645cbce9d356a7b1fe2e0309189ed80818bdde559a9e7993d1`：[原典](https://machinelearning.apple.com/research/code-switching-detection)。monolingual recordingsは単音節ではなく単一言語の録音であり、言語選択的次元を特定するデータ条件を訂正する。
- Note `2f4cf4df821bb266280ee282b1b81eb78846041010bfc0d3ccaffbbab3f284f7`：[原典](https://github.blog/security/application-security/ai-powered-fuzzing-with-the-github-security-lab-taskflow-agent/)。自動生成される判定・修正案はモデルの誤りを含み得るため人のレビューを要するという原典の条件を要約へ追記する。
- Note `2f708dbc986963571a994ea397143ad533b3ba68240a192f16a5946f97aa05e7`：[原典](https://blog.cloudflare.com/accountable-mixed-use-ai-crawlers/)。Accountable事業者の名称をアカウント対象企業と誤訳している。提供機能と期限付き対応約束による指定と説明する。 Bingのrobots.txt連携は2027年初頭予定であり、設定だけで全3社へ現在通知されるとはしない。NOARCHIVE等の別途指定を明記する。
- Note `30aaa77a962aeda46534d4aa7283ee78c117d794f9c089243a5c67ca3c6c1135`：[原典](https://blog.google/innovation-and-ai/models-and-research/gemini-models/gemini-3-6-flash-3-5-flash-lite-3-5-flash-cyber/)。17%のtoken削減と350 token/秒はArtificial Analysisの評価・測定であり、全タスクの保証として記述しない。 本日利用可能なのは3.6 Flashと3.5 Flash-Lite。Cyberは政府・信頼されたパートナー向けの今後の限定pilotであり3モデル共通の一般公開としない。
- Note `33573d87ace2ac630b100068682320ead77cf27064b612c3c99b3e6137cefb7e`：[原典](https://research.google/blog/thinking-to-recall-how-reasoning-unlocks-parametric-knowledge-in-llms/)。有限回のpass@k実験を、推論OFFでは知識へ到達できないという絶対的不能の証明にしない。今回の評価で到達しにくかったとする。
- Note `33e7191d6a66c8028781f9a738d0f85a7f3c9fa4692fa1c0097eaa57ac9d2b3a`：[原典](https://research.google/blog/advancing-amie-towards-expert-level-audio-visual-clinical-consultations/)。30名は比較対象PCP10名と独立評価医20名の合計であり、30名のPCPを比較対象とする要約を訂正する。
- Note `3452bb14aa1949796352c3eea64bc678d4b0572583d9565ec0efd47b8cac7548`：[原典](https://deepmind.google/blog/gemma-scope-2-helping-the-ai-safety-community-deepen-understanding-of-complex-language-model-behavior/)。原典の表示日・構造化データは2025年12月19日であり、元Noteの12月16日を訂正する。
- Note `34a7e3ef42756700cd0c50ead44c3cf3b33cc1249f7ffbecf04367c5959c9981`：[原典](https://deepmind.google/blog/uniting-biological-toolkits-for-a-new-approach-to-als/)。原典の表示日・構造化データは2026年5月19日であり、元Noteの5月16日を訂正する。

[訂正文案](note-reviews/2026-10-25-corrections.json)の36件を `config/note-corrections/` の実行可能計画へ変換した。元Note hash・置換後テキストhash・出典・置換数を固定し、訂正履歴のfrontmatterと可視footerを付けるため、最終Note hashは文案hashと異なる。訂正者は `automated_assistant` とし、人による専門家確認とは表示しない。

原receiptの全bytesを非公開の訂正履歴へ保持し、durable intentによりreceipt/Noteの片側保存から追加生成なしで復旧する。生成日時/モデル/本文hash・安定ID・index・runs/usageは維持する。20件の適用は実GCSを読んだメモリ上のsnapshotだけで実施し、index/runs/usageと費用集計が不変、監査成功、321件中ちょうど20 Note変更を確認した。訂正後datasetは `18935841deb0aca80a8b46c2d0d126ef26145feb4e3249e1d609ebfe14fe6fb1`。ローカルGit/組立てたReleaseの復元bytesも一致した。実GCS・公開content/Release/Pagesへの訂正適用は未実施である。


追加16件は、先の20件の公開snapshotを入力に純粋なNote検証を通し、計36件を訂正した321件のローカルGit/組立てたReleaseのbytes一致を確認した。datasetは `3824e536c9db46b26722f9c855cae2059b22104fecb57e07bff4a9a87881cfa1`。元の生成情報と既存20件の結果bytesは維持した。ADCと既存gcloudの認証は再認証を要し、新しいGCS読取りは失敗したため、追加16件の現在のreceipt/index/usage監査まで済んだとはしない。認証設定の変更や実GCS書込みは行っていない。

Dailyの既存WIF許可対象内に専用jobを追加し、既定はpreview、他modeとの混在を認証前に拒否する。適用と公開は別操作。[操作と復旧](operations.md#原典照合による既存noteの訂正)を参照する。77件の結果を全321件へ一般化しない。
