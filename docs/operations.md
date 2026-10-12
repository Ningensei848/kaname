# 現行コレクタと互換syncの操作手順

新しい標準経路は[生成NoteのGit配布とPages](publication.md)です。以下は現在実行できるCLIの説明です。
公開snapshotの`export-notes`は[配布契約](publication.md)、`publish-notes`は[Git配布手順](git-distribution.md)、
ローカルWebは[preview手順](web-preview.md)を参照してください。
Git配布/Web buildは実装・実Note受入済み、Pages deploy workflowと初回実deployの受入も完了しています。[Pages手順](pages.md)を参照してください。既存syncをsubmodule更新として使いません。
設定・副作用を確認して操作し、既存日次writerとGCS更新を重ねないでください。

## GCS障害と公開の復旧

GCSへの認証・読取り・保存・exportに失敗したrunは失敗として扱い、Git/Pagesの新規更新へ進みません。
保存の耐久性を失った後は追加有料処理を止めます。以前の公開Git版と成功したPagesは維持されます。
保存失敗を警告だけに変えて新規収集を継続する経路や、ローカル代替保存はありません。

1. Actionsのstageと固定error codeを確認し、GCS認証・通信・世代競合の原因を解消します。同じbucketのwriterを重ねません。
2. GCS復旧後は`python -m techkb audit-state`で保存状態を確認します。receipt/usageの回収が必要な場合は、通常writerと重ならない時間に`python -m techkb run --max-calls 0`を使います。この操作にはHTTP通信、GCS更新と既存Batchの照合・回収があり、新規の有料提出はありません。
3. 保存状態が正常になったら[日次公開の公開専用再実行](daily-publication.md#公開だけを再実行)でaudit/export/Git/Pagesへ進めます。これはGCS読取りが必要です。
4. GCS停止中に公開済みGit版を再build/deployする場合は、[Pages手順](pages.md)の固定`content_commit`を使います。この経路はGCS、記事取得、Geminiを使いません。ローカルbuild/検証と本番deployは別の操作です。

不完全な出力を完成版として再利用せず、新しい出力先で再実行します。成功版や曖昧なBatch予約を自動削除しません。
Git履歴からのPages切戻しは非公開GCS/indexを巻き戻しません。

## 費用を限定したstandard収集

`python -m techkb run --llm-mode standard --max-calls 30 --max-cost-usd 1`で、このrunの新規standard生成に費用推計上限を指定できます。Daily Actionsでも`max_cost_usd`を指定します。正の費用上限を指定したstandard runでは`--max-calls`を設定値より増やし、保留をまとめて処理できます。上限未指定では従来どおり件数を減らすだけです。通常scheduleは空欄で従来どおりです。Batch・公開専用・読取り専用モードとは併用できません。

生成前に実際の入力・system/schemaのUTF-8 bytes、1,024 framing token相当、出力上限の2倍と全HTTP再試行回数から保守的に予約額を計算し、計測済みinput/output/thinking費用との合計が上限を越える記事は保留します。単価未定義・非有限/正でない上限はクライアント生成前に拒否します。APIが返したusageが欠ける、再試行が起きる、結果が厳格検証/画像組立てで拒否される場合は、次の有料呼出しへ進みません。既存のusage checkpoint・receipt・保存耐久性の停止条件も維持します。

これは保存された単価とtoken見積りによるrun単位の制御で、確定請求・GCS/Actions費用や複数runの総上限を保証しません。複数runでは各runの実測usageを元単価で集計し、承認枠の残額を次の`max_cost_usd`に渡します。不明usageがあれば追加生成を停止して確認します。予算停止で保留が残るsourceは復旧完了になりません。`max_cost_usd`・`budget_deferred`・固定`budget_stop_reason`をrun reportに残します。`audit-run`もこの上限を元単価・確定usageで照合し、費用制限付きstandardの件数拡大を認識します。不明usage・再試行・元単価の欠損・上限超過や不正な上限は監査を失敗させます。

standardのLLM/compose失敗にはBatchと共通の安全な構造診断を記録します。型・既知field/error code・候補/選択/重複/候補外/配置不適合の件数だけを残し、APIエラー本文・生成文・画像IDを診断へ保存しません。

## 既存Noteへの画像補完

要約を再生成せず、レビュー済みの画像URLと配置だけを追加できます。現在の対象はGlucoFM 1件です。
`config/image-repairs/<Note ID>.json`に対象Note・取得した本文MarkdownのSHA256、画像URLと配置を固定します。
対象は最新の公開revisionで、Noteとreceiptが一致し、既存画像がないことを確認します。
本文はsourceの通常取得・抽出経路を使い、候補に存在するHTTPS画像だけを採用します。
Gemini呼出し、画像バイナリ取得、index・usage・生成日・モデル・元本文hashの変更はありません。
画像追加を取り除くと元Noteの全bytesへ戻ることも検査します。古い要約の入力打切り表示は維持します。

```bash
# GCS読取りと記事本文の取得のみ。出力先は新しいディレクトリを指定
python scripts/repair_note_images.py --plan config/image-repairs/<Note ID>.json --output /tmp/image-preview
# 検証した計画をNoteと対応receiptへ適用
python scripts/repair_note_images.py --plan config/image-repairs/<Note ID>.json --output /tmp/image-apply --apply
```

ActionsではDaily TechKBの`image_repair_plan`に上記パスを指定します。
`image_repair_apply=false`がプレビュー、`true`が適用です。他の実行mode・上限指定とは併用しません。
mainのレビュー済み計画だけを許可し、日次writerと同じconcurrencyで直列化します。
収集・公開jobは実行せず、検証済みNoteと判定JSONを7日間のartifactへ保存し、最後に`audit-state`を実行します。

適用は世代条件を付けてreceipt、Noteの順で保存します。Note保存に失敗した場合は新しいreceiptに復旧用bytesが残ります。
同じ計画を専用スクリプトで再実行すると、記事再取得・Gemini呼出しなしで再開します。
通常の収集は登録済みNoteをskipするため、この片側更新を通常収集で修復しようとしません。
競合・hash不一致・異なる計画は停止し、既存公開版を維持します。
適用とauditが成功した後、別のDaily実行で`publish_only=true`を指定してGit/Pagesを更新します。

## 取得・本文・フィルタ

現行の有効sourceはRSS/HTTPです。Google Researchは`content_selector: .blog-detail-wrapper`で、
分割された本文・画像・キャプションをまとめて抽出し、ナビゲーション・サイドバー・関連記事を入力から除きます。
GitHub Blogは全HTML変換を維持します。取得方式・本文抽出はsourceごとに設定します。
本文抽出を切り替えるとcontent hashが変わるため、再処理・課金の可能性を考慮してください。

```yaml
- id: example
  name: Example
  enabled: false
  type: html
  listing_url: https://example.com/blog/
  link_selector: article a.post
  base_url: https://example.com/
  fetcher: playwright
  render_selector: article
  resource_domains: [cdn.example.com]
  max_browser_requests: 40
  request_interval_seconds: 2
  extract_main: true
  content_selector: article .body
  category: software-development
  relevant_filter:
    include_keywords: [Python, 開発]
    exclude_keywords: [sponsored]
    include_domains: [example.com]
    exclude_domains: []
    include_categories: [software-development]
    exclude_categories: []
```

HTML一覧は同じnetlocのリンクを発見します。現行判定はschemeを比較しないため、厳密な同一origin判定とは区別します。RSSの場合は`type: rss`と`feed_url`を指定。
`fetcher: playwright`は一覧と記事を描画し、RSS自体は通常HTTPで取得します。
selectorがない`extract_main: true`はarticle/mainを優先し、navigation等を除去します。
指定content selectorが一致しない記事は失敗しpendingへ残ります。
includeは各種類内でOR、種類間でAND、excludeは優先です。NFKC/casefoldでkeywordを比較。
domainは完全一致、`*.example.com`はsubdomainのみ。categoryはsourceの固定値で、LLM判定ではありません。
除外記事はLLMを呼ばずpendingから外し、成功hashを登録しません。次回feedから再評価されます。

Playwrightには`pip install -r requirements-browser.lock`と`python -m playwright install --with-deps chromium`が必要です。
daily workflowはenabled sourceで必要な場合だけ導入します。ブラウザ通信は既存HTTP fetcherを通り、
robots、公開IP確認、間隔、応答サイズを適用。GET/document/script/CSS/xhr/fetchのみで、WebSocket・service workerを遮断します。
追加resource domainは明示指定。初回document・resource・robotsの各redirect先は、host allowlistをDNS/HTTP通信前に検査します。JSの本文はcontent hashで比較し、元のHTTP HTMLだけをraw hash/opt-in保存に使います。
HTTPのDNS検査と接続は別処理であり、厳密なネットワーク隔離ではありません。

## 互換機能: Obsidian Vaultへの直接同期

```bash
python -m techkb sync --vault /absolute/path/to/vault --dry-run
python -m techkb sync --vault /absolute/path/to/vault
# GCSの代わりに取得済みsnapshotを利用
python -m techkb sync --state-dir local-snapshot --vault /absolute/path/to/vault
```

Vaultの`TechKB/notes/`へ片方向で保存し、`TechKB/.techkb-sync.json`に前回hashを記録します。
GCSへは書込みません。既存Noteは管理対象でも自動置換しません。
新しいsubmodule配布経路は別の契約です。このCLIをsubmodule checkoutへ向けず、コピー同期とGit更新を重ねません。
ローカル編集・未管理ファイル・リモート更新は、元Noteを保持して競合（終了コード1）として返します。
更新候補は`TechKB/incoming/notes/<object-pathのSHA-256>/<remote-contentのSHA-256>.md`へ別保存します。
結果の`updates`に元Noteと候補の相対path、`created/unchanged/conflict`を表示します。
同じ候補は再作成せず、候補側に編集があればそのファイルも保持して`conflict`を表示します。
候補内容を確認して利用者が手動で統合してください。候補が元Noteと一致すれば次回はunchangedです。
元Noteを削除して再取得する場合は、ローカル変更を先に退避し、編集アプリも停止してから行います。
manifestは候補保存時に元Noteを更新済みとして扱いません。`written/planned`は元Noteの新規作成、
`incoming_written/incoming_planned`は候補の保存/計画です。dry-runは候補pathを`planned`として表示します。
リモート削除でローカルNote・候補は消しません。候補の削除や整理は利用者が明示して行います。
新規ファイルは同じディレクトリに完成bytesを用意し、hard linkで上書きせずatomicに公開します。
途中でローカルファイルが作られた場合も置換せず、更新候補へ回します。manifestは最後に更新します。
hard linkを使えないfilesystemでは安全に失敗し、部分的なNoteや無条件置換へfallbackしません。
Linuxの実行環境で検証済み。Windows/NTFSや利用者Vaultでの実検証は別の受入項目です。
中断時は未追跡ファイルが競合として残る場合があり、自動上書きより保護を優先します。
同一Vaultの同時同期はlockで拒否します。プロセス強制終了後は稼働していないことを確認してlockを手動削除。
symlinkを含むVaultパスは拒否します。dry-runはlock用のTechKBディレクトリだけ作成し、Note/manifestを更新しません。
編集アプリとの共通lockはありません。確認後の編集は上書きしませんが、その回のconflict判定に
間に合わない場合は次の同期で検出します。外部プロセスによる親ディレクトリ差替えまでの隔離は保証しません。

独立Pagesは[公開snapshot](publication.md)から作り、人力Vaultの同期を前提にしません。
人力Vaultのrepo・公開・コミュニティプラグインは利用側の責務です。

## 非同期Gemini Batch

```bash
python -m techkb run --llm-mode batch --max-calls 1
python -m techkb batch-status
# 新規の有料処理を増やさず、既存ジョブを照合・保存
python -m techkb run --max-calls 0
```

恒常的に使う場合は`llm.mode: batch`をapp.yamlへ設定。既定は`standard`です。
手動Actionsでも`collection_mode`と`max_calls`を指定できます。上限は標準呼出とBatchリクエストの合計で、
HTTP retry/poll回数や日次hard capではありません。`--max-calls`は設定上限を減らす場合だけ使用できます。
各inlineリクエストは同じStructured Output/category enum/minimal/20,000文字を使います。
本文はメモリからAPIへ送り、GCSのledgerには保存しません。ledgerはhash・出典metadata・元記事word countのみ。
結果受領後はcompact Note/receiptを保持し、原文は含みません。

`state/batches/<id>.json`の予約を書いてから一度だけsubmitし、APIのjob名を保存します。
次runはstandardモードでも既存Batchをpollし、in-flightのcontent hashを再課金対象から外します。
API作成がtimeoutした場合は同じdisplay nameのjobを探します。0件/複数件なら停止して予約を維持し、
自動でsubmitを繰り返しません。API管理画面等でjobを確認後、完全一致するdisplay name/modelを検証して結びつけます。
400/401/403/404/422の明確な作成拒否は予約を終了し、standard収集を妨げません。

```bash
python -m techkb batch-bind --batch-id YYYYMMDDTHHMMSSZ-xxxxxxxx --job-name batches/JOB_ID
```

曖昧な予約を手で消すと二重課金の可能性があるため、submitの成否を確認してから復旧してください。
結果はmetadata keyで対応づけ、未知/重複keyは停止。個別失敗はpendingに残し、成功した記事だけ保存します。
Note/indexの途中失敗は既存receipt復旧を利用し、再LLMはありません。
compact結果を先に永続化してから保存し、usageは専用`record_kind: batch_usage` reportへ一度だけ計上します。
作成runのreportを上書きせず、安定した別run IDで再開時の費用重複を防ぎます。
収集runの`llm_*`はstandard通信、`batch_submitted/saved/failed/jobs_pending`はBatch処理です。
`audit-run`の保存件数はstandard成功 + receipt復旧 + batch保存で照合します。

[公式Batch API](https://ai.google.dev/gemini-api/docs/batch-api)の完了目標は24時間です。
作成API応答とジョブ完了・Note保存は別で、待機中を完了とみなしません。
実サービスでのBatch確認は検証記録へ別途記載します。

### 実Batch受入の事前検査

`daily.yml`をmainから`batch_preflight=true`で手動実行すると、
判定は`techkb.batch.preflight(store, app)`へ集約し、既存スクリプトは薄い入口として使用します。
既存WIFと通常収集のwriterロック内で、GCSのaudit・未決済/未計上Batch・未完了standard usageを読み取ります。
検査専用jobは`contents: read`と`id-token: write`だけを持ち、通常のcollect/publish/pages/notify jobはskipします。
他の実行モード、verification/diagnostic ID、baseline、collection mode変更、max_callsとの同時指定は認証前に拒否します。
既存WIFは`daily.yml@refs/heads/main`だけを許可するため、独立workflowからは実行しません。

```bash
gh workflow run daily.yml --repo Ningensei848/kaname --ref main -f batch_preflight=true
```

新規提出、Gemini GET、記事取得、GCS書込み、通知、Git更新、Pages deployは行いません。
出力は件数と判定だけで、本文・台帳ID・object path・費用明細を含みません。
`ready`でも有料提出の個別承認が必要です。`blocked`/`failed`なら提出せず調査します。
unknown usageの件数は残り、請求照合完了を意味しません。
具体的な提出・回収・再実行・費用推計は[#94の準備記録](archive/2026-10/batch-acceptance-preparation-2026-10-07.md)、
独立workflowの実WIF拒否と修正は[修正記録](archive/2026-10/batch-preflight-workflow-fix-2026-10-08.md)を参照してください。

### Source Healthの読取り

```bash
python -m techkb source-health
python -m techkb source-health --state-dir /path/to/private-snapshot
```

source設定、保存済みrun、index、pendingからJSONを返します。GCSまたはローカルsnapshotの読取りだけを行い、
記事取得・Gemini呼出し・状態更新・通知・公開は行いません。Gemini API keyは不要です。
出力はsource ID、状態、UTC時刻、件数だけで、記事URL・本文・run/台帳ID・認証情報を含みません。
`status=success`と終了コード0は読取りの成功で、収集元の状態は`health`で判定します。

- 全体の`health`は`healthy`、`degraded`、`unverified`、全source無効時の`disabled`。
- 各sourceは`healthy`、`failing`、`incomplete`、`unverified`、`disabled`。
  連続失敗はsourceの明示的な完了でresetし、全体のsuccessや上限到達による未完了では維持します。
- `last_success_at`は当該sourceが明示的に全処理を完了したrunの開始時刻です。
  `last_note_saved_at`は成功index行の最新保存時刻で、部分的な成功も確認できます。
- `success_rows`は当該sourceの全成功index行数（過去版を含む）、`pending_candidates`は現在の保留候補数です。
- `latest_run_counts`は当該sourceの最新収集runにある`discovered`、`saved`、`recovered`、
  `batch_submitted`、`batch_saved`。発見はfeed/listing解析後、pendingとの重複整理前の件数です。
  `recovered`と`batch_saved`は`saved`の内数です。発見0と発見記録不明を区別し、
  source別の件数がない過去runは`null`を返します。全体件数を各sourceへ割り当てません。

無効化したsourceの過去記録も表示します。dry-runとBatch課金専用runはhealth履歴から除外します。
このCLIはNote/receiptの整合性auditと確定請求照合とは別の、source運用状態の表示です。

### 既存Batchの読取り診断

`BATCH_ID`へ確認対象の台帳ID（`YYYYMMDDTHHMMSSZ-xxxxxxxx`形式）を設定してから使います。
個別の過去run/台帳IDは[履歴](archive/README.md)へ保存しています。

```bash
# completeを含む指定台帳を読むだけ。Gemini認証は不要
python -m techkb batch-inspect --batch-id "$BATCH_ID"
# 取得済みsnapshotでも実行可能
python -m techkb batch-inspect --batch-id "$BATCH_ID" --state-dir local-snapshot
# 環境変数に正規のGEMINI_API_KEYが設定された環境で、既存job結果をGET
python -m techkb batch-inspect --batch-id "$BATCH_ID" --remote
```

`batch-status`と異なり、completeになった失敗も確認できます。`--remote`は台帳に紐付いたjobの
結果取得と現在のvalidatorによる検査だけを行います。新規提出・記事取得・Note保存・費用計上・
GCS更新・Issue投稿は行いません。待機中jobは応答欠落の失敗に数えません。
終了コード0と`status: success`は検査操作の成功であり、Batch保存成功や受入完了を意味しません。
生成結果の検証状況は`remote_state`と`remote_outcomes[].error_type`を別に確認します。
組立て・保存経路はこの診断では検証しません。

出力は件数・例外型・処理段階・既知schema field名/Pydantic code・text有無・finish reasonに限定し、
記事本文、生成文、未知field名、validation input、例外本文、API resource名を表示しません。
これから決済する失敗はcollection/billing reportにも元の例外型と安全な診断情報を残します。
旧台帳には型名しかないため、過去の詳細を復元したり既存reportを書き換えたりはしません。
既存jobの取得が失敗する場合は、その型だけを表示して終了コード1とします。

Actionsでは`diagnostic_batch_id`だけを指定し、`verification_run_id`を空にします。
このモードは既存のWIFと`GEMINI_API_KEY` Secretをjob内で使用し、通常のCollect/Audit、費用・通知・
Issue投稿をskipします。両診断入力の同時指定はWIF認証前に拒否します。
日次scheduleと入力未指定時の通常動作は維持します。Secretの抽出、権限拡張、匿名公開は不要です。
診断モードの成功は検査操作の成功です。新規有料提出や結果の保存とは別の操作として扱います。

## 実測usageと予算

```bash
python -m techkb cost-report
python -m techkb cost-report --as-of YYYY-MM-DD --state-dir local-snapshot
```

run reportをIDで重複排除し、入力 + 出力/thinkingの実測トークンから日次/月次USDを計算します。
時間境界はUTC。Batchは結果を観測した日へ計上。invoiceやGCS/Actions料金、取得不能usageの費用は含みません。
不明usage・未決済Batchは`partial`と件数を表示し、既知の費用だけを下限として集計します。
standardは`state/standard-usage/<元run ID>.json`へ呼出し前の予約と取得後のusageを保存します。
最終reportを優先し、reportがなければjournalを元のUTC日付・model・価格で集計します。
receipt後の中断・再回収でも費用を重複計上しません。`incomplete_standard_runs`はreport未保存で応答も不明な予約の件数です。
部分欠落metadata、応答未保存の予約、複数HTTP試行の不明課金はpartialとなり、既知countを保持します。
thinking欠落を0とするのは合計countから0を証明できる場合だけです。
旧receiptで課金記録への参照がなければ、復旧runにusage不明を記録し、過去の単価・日付は推測しません。
API応答と永続化の間の停止には再課金の可能性が残ります。invoiceとの照合は別途必要です。
旧Phase 1 reportはmodel記録がないため現在設定model/standard価格を仮定し、仮定件数を表示します。
新reportはmodel/modeと単価をsnapshotし、後の単価更新で履歴を再評価しません。

推計に使う単価はconfigと既定設定を確認し、[公式価格](https://ai.google.dev/gemini-api/docs/pricing)の変更とは別に管理します。
以下は設定例です。保存済みrunの価格snapshotを後の単価で上書きしません。
別modelは`costs.prices`へ設定し、単価未設定の場合は確定費用とみなしません。

```yaml
costs:
  daily_budget_usd: 1
  monthly_budget_usd: 10
  prices:
    gemini-3.5-flash-lite:
      standard: {input_usd_per_million: 0.30, output_usd_per_million: 2.50}
      batch: {input_usd_per_million: 0.15, output_usd_per_million: 1.25}
```

予算は通知の閾値です。到達時はIssue/planを確認し、価格・unknown usage・invoiceを照合し、
必要ならsource無効化や上限削減で次runから調整します。即時停止のhard capではありません。

## 連続失敗とIssue通知

```bash
python -m techkb notify          # planだけ。投稿なし
python -m techkb notify --apply  # GITHUB_TOKENで設定repositoryへ必要時だけ投稿
```

`notifications.consecutive_failures`（既定3）以上のsource/collector失敗と予算到達を対象にします。
sourceの失敗streakは明示的な`source_completed_ids`だけでresetします。
feed取得だけの成功、予算上限で未処理、先行sourceの保存障害による打切りは復旧とみなしません。
旧reportの`source_ids`も完了の証拠として使いません。無効化sourceの履歴は保持し、通知は有効sourceだけです。
collectorはrun成功でresetします。
Batch usage reportは通知回数に含めず、収集run側の失敗だけを数えます。
同じ失敗streak・同じ日/月予算はbody markerで重複抑止。閉じたIssueも再作成しません。
復旧後の新しい障害は別Issueです。閉じたIssueの再openやコメント追加は行いません。
GITHUB_TOKENには対象repositoryのIssues書込み権限が必要。本文に記事本文・認証情報・生エラーは含めません。
日次workflowは収集失敗時もWIF成功なら費用・通知計画を出力します。
daily.ymlの`issues: write`と通常runからの必要時自動投稿はユーザー承認済みです。
対象は`Ningensei848/kaname`。承認の過去記録は[履歴](archive/README.md)にあります。
`notifications.github_repository`を空にすると自動投稿を無効化できます。
収集/audit/export/Git配布/Pages失敗は、GCSに依存しない別jobから即時Issue通知します。
GitHub run IDのmarkerで閉じたIssueも重複抑止し、安全なstage名とrun URLだけを掲載します。
このworkflow通知はsource/予算通知とは別です。[日次公開手順](daily-publication.md)を参照してください。

## Source単位のRaw HTML削除

```yaml
store_raw_html: true
raw_retention_days: 14
```

sourceのopt-in rawを`raw/<source-id>/YYYY/MM/<hash>.html`へ保存します。
保存期間未設定は保持。既存`raw/YYYY/MM/`はsourceを識別できないため削除ruleに含めません。

```bash
python -m techkb raw-lifecycle          # 現在rulesとsource設定から計画
python -m techkb raw-lifecycle --apply  # bucket更新権限を持つ管理者が適用
```

GCSのDelete/age/matchesPrefix ruleによって期限後に自動削除されます。
実行SAの通常writer roleへbucket更新権限を追加しません。ADCが失効していれば管理者が再認証して実行してください。
bucket metagenerationで競合を検出。source prefixに対する単純な既存age/Delete ruleだけ置換し、
他のruleや旧rawは維持します。retentionを設定から消しても既存ruleは自動で解除しません。
停止したい場合は管理者が該当ruleを明示解除。削除はGCS側で非同期であり、適用直後の消去を保証しません。


## 通常収集・検査・metadata更新

```bash
python -m techkb run                 # 有料生成、GCS更新
python -m techkb dry-run             # GCS読取り、記事通信あり、Gemini/GCS更新なし
python -m techkb audit-state         # GCS読取りだけ、記事通信なし
python -m techkb audit-state --state-dir local-snapshot
python -m techkb audit-run --run-id "$RUN_ID" --expected-success-before N
python -m techkb refresh-metadata    # 原記事通信あり。既定は計画だけ
python -m techkb refresh-metadata --apply
```

`RUN_ID`と`N`は対象runの値に置き換えます。auditはNote/receipt/index/hash/pendingの整合性を検査し、
自動修復や日本語品質の全件確認は行いません。対象runの次runが状態を変える前に照合します。
`--state-dir`は同じ構造の読取りsnapshot用です。不完全なsnapshotを本番状態として扱いません。
dry-runでもRSS/記事を取得し、空のlocal stateは既知hashゼロとして扱います。

metadataのapplyはNote/対応receiptだけを世代条件付きで更新し、要約/hash/index/pendingを維持します。
複数object全体のatomic更新ではなく、失敗時の補完/rollbackと適用後auditが必要です。
collectorと同時に更新操作を行いません。相対prompt_fileはapp.yamlの親の親を基準に解決します。
CLIは.envを自動読込みしません。APIキーをコマンド履歴へ書かず、環境変数/Secretで渡します。

```text
notes/YYYY/MM/YYYY-MM-DD_title_hash12.md
state/index/YYYY-MM.tsv
state/pending.tsv
state/receipts/<content-sha256>.json
state/batches/<batch-id>.json
runs/YYYY/MM/<run-id>.json
raw/<source-id>/YYYY/MM/<raw-sha256>.html  # opt-in
```

これらは非公開GCSの収集・復旧形式です。新しい公開Git snapshotへ丸ごとコピーしません。
公開には[配布契約](publication.md)に従う専用exportを使います。


## 取得・変換の並列数と抽出回帰

`config/app.yaml`の`processing.workers: 2`で、最大2件のfetch/convertを先行処理します。
1〜8の整数が有効です。`workers: 1`で逐次処理へ戻せます。
課金・usage・Note/index保存・重複判定は入力順の単一writerで、30件上限を並列数で増やしません。
host間隔・robots・retryも維持するため、並列数を増やしても同じhostへの要求頻度は増えません。

本文抽出/画像候補/変換依存を変えた場合は`python scripts/regression_corpus.py`で
有効3 source（Google Research/GitHub Blog/DeepMind）の4レイアウトの合成fixtureを比較します。差分があると失敗するので、本文/末尾/画像/captionをレビューしてからgoldenを更新します。
fixtureは原文のコピーや実サイトへの定期アクセスではありません。
GitHub Blogの全ページ変換など現行baselineの限界も[検証記録](archive/2026-10/p1-p4-implementation-2026-10-11.md)で区別します。


## Knowledge Graphの品質評価

固定公開contentを読取り専用で評価します。

```bash
python -m techkb graph-quality --public-snapshot /path/to/public-content
python -m techkb graph-quality --public-snapshot /path/to/public-content --details
```

認証・API呼出し・GCS/Note書込みは不要です。既定出力は件数のみ、`--details`は公開語句とNote IDも含みます。評価成功とリンク解決を区別し、曖昧候補や未解決語を任意のNoteへ結び付けません。正規化規則・指標・固定実contentの結果は[品質評価](graph-quality.md)を参照してください。


## 本文・検索キーワードの検索導線

SSG時に一意な公開Noteタイトルへ解決し、未解決のWikiLinkはGoogle検索を別タブで開くリンクへ投影します。APIキー・追加Gemini呼出し・CSPの外部resource許可は不要です。公開元Noteのbytes・ID・dataset digestは変えず、Web成果物は新しい投影で再ビルドします。本文への自動WikiLinkは新規Noteだけに適用し、旧Noteの一括再生成を行いません。
別名表示・見出し・コード等の扱いと受入状態は[NS1記録](ns1-search-fallback.md)を参照してください。見出し欠落はリンク監査で検出します。`check:preview`/`check:pages`は検索リンクのhref・別タブ・opener不在・graph除外を検査し、Googleの遷移レスポンスをテスト内で代替して実検索を送りません。


## 保存済み検索語ラベルの互換

新規Noteの検索語/著者ラベルは、記号を空白へ置換した後に空白を整理し、160文字制限の切断後にも末尾を整理します。公開検証では、旧formatterが残した連続ASCIIスペースや160文字の切断位置の空白/ピリオドを含む保存済みラベルも限定して認めます。元Note/receipt/IDを変更せず、本文への任意WikiLink、構文区切り、非ASCII空白、長さ超過は拒否します。既存Noteを新しいラベルへ一括書換えたり、検証拒否だけを理由に要約を再生成したりしません。
