# 現行コレクタと互換syncの操作手順

新しい標準経路は[生成NoteのGit配布とPages](publication.md)です。以下は現在実行できるCLIの説明です。
公開snapshotの`export-notes`は[配布契約](publication.md)、`publish-notes`は[Git配布手順](git-distribution.md)、
ローカルWebは[preview手順](web-preview.md)を参照してください。
Git配布/Web buildは実装・実Note受入済み、Pages deploy workflowと初回実deployの受入も完了しています。[Pages手順](pages.md)を参照してください。既存syncをsubmodule更新として使いません。
設定・副作用を確認して操作し、既存日次writerとGCS更新を重ねないでください。

## 取得・本文・フィルタ

既存sourceの既定はRSS/HTTP・全HTML変換です。新機能はsourceごとに選択します。
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
追加resource domainは明示指定。redirect先のallowlist判定が取得後になるF3は未修正です。本番browser利用を広げる前に対処します。JSの本文はcontent hashで比較し、元のHTTP HTMLだけをraw hash/opt-in保存に使います。
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
ただしusageの部分欠落を検出できないF4、receipt後の中断でreportが残らないF5は未修正です。
現行cost-reportのsuccessだけで費用の完全性を保証しません。[現在の指摘](verification.md)を参照してください。
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
成功で失敗streakをresetします。collector障害の扱いはありますが、先行sourceの保存障害による打切りで
未検証sourceをresetするF6は未修正です。実際の復旧と未処理を分ける修正が必要です。
Batch usage reportは通知回数に含めず、収集run側の失敗だけを数えます。
同じ失敗streak・同じ日/月予算はbody markerで重複抑止。閉じたIssueも再作成しません。
復旧後の新しい障害は別Issueです。閉じたIssueの再openやコメント追加は行いません。
GITHUB_TOKENには対象repositoryのIssues書込み権限が必要。本文に記事本文・認証情報・生エラーは含めません。
日次workflowは収集失敗時もWIF成功なら費用・通知計画を出力します。
daily.ymlの`issues: write`と通常runからの必要時自動投稿はユーザー承認済みです。
対象は`Ningensei848/kaname`。承認の過去記録は[履歴](archive/README.md)にあります。
`notifications.github_repository`を空にすると自動投稿を無効化できます。
WIFやGCS読取り自体が失敗するとhistoryを取得できないため、Actions標準の失敗通知から認証/権限を復旧してください。

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
