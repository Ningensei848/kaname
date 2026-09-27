# TechKB — 技術情報の自動収集・Obsidian蓄積

Python 3.12 / GitHub Actions / Gemini / 非公開GCSによるPhase 1実装です。
RSS → HTTP → raw SHA-256 → HTML整理 → MarkItDown → Markdown正規化 → content SHA-256
→ GeminiのStructured JSON → Pydantic → Markdown → GCS/月次TSVの順で処理します。
SQLite、LLMによるフィルタ、自己修正、画像認識、外部ツールは使用しません。

**実装とローカルテストは完了しています。GCP・Gemini・GitHub Actionsを接続した本番受入は未実施です。**
受入完了まではPhase 1運用開始前として扱ってください。Phase 2/3は[確定バックログ](docs/roadmap.md)です。

## 開始方法

checkoutした `kaname/` ディレクトリで実行してください。

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock
python -m pip install --no-deps -e .
python -m techkb validate-config
python -m pytest -q
```

Windows PowerShellでは ` .venv\Scripts\Activate.ps1 ` で仮想環境を有効化します。
`requirements.lock` は検証時に解決した依存バージョンを固定します。
更新時は新しい仮想環境で `pip install -e '.[test]'` → `pip freeze --exclude-editable > requirements.lock`
→ 全テストを実行してください。Python配布パッケージに実データ・認証情報を含めません。

## 設定

- `config/app.yaml`: HTTP制限、LLMモデル・上限、カテゴリ、保存設定。
- `config/sources.yaml`: RSS/Atom情報源。Google Research、GitHub Blogを有効化し、AWS News Blogは利用条件の確認待ちで無効化。
- `prompts/enrich.txt`: 要約・分類指示。本文は命令として扱わないと明記。
- `GCS_BUCKET`: 非公開バケット名。設定ファイルの値を上書き。
- `GEMINI_API_KEY`: Gemini Developer APIのキー。GitHub Secretsか環境変数で指定。

モデルは指定どおり `gemini-3.5-flash-lite`、thinkingは `minimal` です。
カテゴリはYAMLからSchemaのenumへ反映し、応答後にも検証します。
sourceの `store_full_text: false` はNoteと復旧receiptへの原文保存を無効化します。
LLMにはその場合も本文を送信します。`store_raw_html` は別設定で、source指定が全体設定より優先です。
sourceの削除/無効化後も、既存pendingは消去せず保留します。

## 実行

[GCP初期設定](docs/gcp-setup.md)でWIF・バケット・GitHub Variables/Secretsを設定します。
APIキーをコマンド履歴に直接書かず、シェルの安全な入力またはGitHub Secretsを利用してください。
`.env.example` は項目例であり、CLIは `.env` を自動読込みしません。

```bash
# GCSはADC認証、GeminiはGEMINI_API_KEYを使用
python -m techkb run

# GCS状態を読み、HTTP取得・変換・重複判定だけ行う。Gemini・GCS書込みなし。
python -m techkb dry-run

# GCS認証なし。ローカルのstate/index/*.tsvとstate/pending.tsvを読取り専用で使う。
mkdir -p local-state
python -m techkb dry-run --state-dir local-state
```

`--state-dir` が空なら既知hashゼロとして扱います。本番履歴の重複確認にはGCS読取りを使ってください。
dry-runでもRSS/記事へのネットワークアクセスが発生します。返却コードは成功0、障害1です。
設定ファイルを変える場合は `--config PATH --sources PATH` を使用します。
相対 `prompt_file` はapp.yamlの親の親（通常リポジトリroot）を基準に解決します。

GitHub Actionsは毎日07:17 JST、または `workflow_dispatch` で実行します。
スケジュールの実際の開始時刻はGitHub側の遅延を受けます。
1 job / 1 writerとworkflowのconcurrency groupで直列化し、GCS世代条件も併用します。
**同じバケットを別repository/ローカルから同時運転しないでください。**
世代条件は競合時に停止しますが、複数writerでのLLM先行呼出までは防止しません。

## 保存形式と復旧

```text
notes/YYYY/MM/YYYY-MM-DD_title_hash12.md
state/index/YYYY-MM.tsv
state/pending.tsv
state/receipts/<content-sha256>.json
runs/YYYY/MM/<run-id>.json
raw/YYYY/MM/<raw-sha256>.html  # opt-in
```

全月の成功TSVを読み、raw/content hashをメモリ上のsetに展開します。
同じURLも毎回取得し、本文更新を見逃さないようにします。異なるURLでも完全一致本文は重複です。
成功TSVだけが通常の重複排除の正本です。LLM失敗、変換失敗、取得失敗はpendingに残ります。
保存失敗時は後続の有料処理を停止し、workflowを失敗にします。

`state/receipts/` はLLM結果を再利用してNote/TSVの途中失敗から復旧する補助ファイルです。
次のrunで未登録receiptのNoteとindexを修復します。原文保存無効の場合はreceiptにも原文を含めません。
成功済みreceiptは保持し、indexにあるhashは読取りを省略します。MVPでは自動削除しません。
成功indexを安易に削除しないでください。receipt再処理・状態の扱いは[設計上の補足](docs/design-decisions.md)を参照。

## 費用と使用量

本番受入前の一時上限は **1 runあたり1記事** です。初回Note確認後に30へ戻します。
通常運用の上限は **1 runあたり30記事**、本文20,000文字、出力2,048 tokensです。
30/日という運用想定であり、手動で複数回実行すれば日次30を超えます。
通信retryは最大3回で、`llm_calls` は論理記事呼出、`llm_http_attempts` はretryを含む通信回数です。
Schemaエラーは自動修正せず、次のrunに残します。恒常的エラーはログ確認後にsourceを一時無効化してください。

2026-09-25確認の標準API料金は入力$0.30/100万token、出力$2.50/100万token（thinkingを含む）です。
計画値5,000入力+600出力なら1記事$0.003、30記事×30日で$2.70です。
これは上限保証ではなく、GCS・Actions費用は別です。
usageの `output_tokens` は候補出力、`thinking_tokens` は別列に保持します。
費用を計算する際は両方を考慮してください。月次費用集計の正式実装はPhase 2です。

run reportには `total_input_tokens` / `total_output_tokens` / `total_thinking_tokens`、処理・重複・失敗件数を記録します。
Schema不正でも取得できたusageを加算します。timeoutなどusageを取得できない場合は
`llm_usage_unavailable` を増やします。通信失敗時の課金をusageだけから完全には復元できません。

## 運用上の注意

- source登録時に利用条件を確認。HTTPはrobots.txtを確認し、拒否・取得不能時はfail closedで停止。
- CAPTCHA、認証、paywall回避は実装しません。ブロックされたsourceは人が状況確認。
- HTTPはresponseの展開後bytes上限10MB、ホスト単位の待機、timeout、指数backoffを適用。
- private/loopback/link-local IPは拒否。HTTP redirect先でもrobotsとURLを再確認。
- raw bytesはHTTPクライアントが取得したresponse bodyであり、HTML整理前にhash化。
- 全文をsemanticに抽出する処理はPhase 2。本文以外の広告テキスト変化までは現状のhash方式で吸収できません。
- 改行・空白の正規化はコードフェンス内の連続空行を維持します。行末空白除去は要件どおりです。
- 画像はaltテキストだけを残し、外部画像を埋め込みません。Vision/OCRは実行しません。
- 本文・APIキー・SDK例外本文はログに出しません。監査URLはquery/fragmentを落としてログ記録します。
- 本番runの中断は極力避けてください。復旧保証の限界は設計補足に明示しています。

## 検証と受入

[検証記録と残る受入項目](docs/verification.md)を参照してください。
`tests/test_e2e.py` はHTTP transportと外部APIをfixtureへ置換し、実際のCLI・RSS解析・HTML整理・
MarkItDown・Schema validation・Note/TSV/pending/reportの連携と再実行を確認します。
本番Gemini/GCSへの到達性とIAMは、このオフラインテストでは保証されません。

## 公式資料

- [Gemini 3.5 Flash-Lite](https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash-lite)
- [Gemini thinking](https://ai.google.dev/gemini-api/docs/thinking)
- [Gemini料金](https://ai.google.dev/gemini-api/docs/pricing)
- [Google GenAI Python SDK](https://googleapis.github.io/python-genai/)
- [Microsoft MarkItDown](https://github.com/microsoft/markitdown)
- [GCS世代条件](https://docs.cloud.google.com/storage/docs/request-preconditions)
- [GitHub Actions WIF](https://github.com/google-github-actions/auth)
