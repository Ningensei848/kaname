# kaname — 公開するLLM生成の技術Note

kanameは技術情報を収集・要約し、日々更新される生成Noteを独立したリソースとして提供するプロジェクトです。
**同じ公開Note群を、GitHub Pagesと、人力Vaultからのgit submodule参照で利用します。**
人力で構成するVaultは別リポジトリで管理し、その公開範囲・編集・コミュニティプラグイン設定は本プロジェクトの対象外です。

標準経路の実装は完了しています。HTTPで収集・Geminiで要約し、非公開GCSの成功NoteをGitとPagesへ公開します。
生成Noteを[公開Note一覧](https://github.com/Ningensei848/kaname/tree/content/notes)と
[GitHub Pages](https://ningensei848.github.io/kaname/)で参照できます。
公開専用runで最新成功版への更新と全元Markdownのhash一致を確認しました。
毎日07:17 JSTの通常収集後に公開します。通常scheduleの連続実行と履歴版への切戻し・復帰は2026-10-07に受入済みです。
[日次公開手順](docs/daily-publication.md)に受入結果と再実行方法、[Pages手順](docs/pages.md)に切戻し方法を記載しています。
決定の背景と旧仕様との差は[ADR-0001](docs/adr/0001-generated-content-module-and-pages.md)に記録しています。

```mermaid
flowchart LR
    A[収集・LLM要約] --> B[GCS: 非公開の収集・復旧状態]
    B --> C[成功Noteの版付きexport]
    C --> D[kaname content branch: 公開Markdownとmanifest]
    D --> E[GitHub Pages: 独立したWebリソース]
    D --> F[利用側: git submoduleで特定commitを参照]
```

生成Noteの配布元を独立させることで、Webは新しい公開版へ更新し、人力Vaultは必要な版を参照できます。
Pagesの構築に人力Vaultを読み込まず、本体の編集や公開を待たずに提供します。

## 仕様と実装状態

| 項目 | 状態 |
|---|---|
| RSS/HTTP → Markdown → Gemini → Note/GCS | standard収集の本番受入済み。Google Research/GitHub Blogが有効 |
| 費用記録・復旧・失敗判定 | F4/F5/F6修正済み。部分usage、元の日付/単価、中断復旧、未処理sourceを検証 |
| ブラウザ取得 | F3修正済み。document/resource/robotsのredirect先を通信前に検査。本番sourceの利用は未受入 |
| 非同期Batch | 実装・offline検証済み。成功結果の実Note保存・audit/cost照合は未受入 |
| 既存Vaultへの直接同期 | 互換機能。既存編集を保持し、更新候補を別保存 |
| 公開export・Git配布・Pages | 117件の初回公開と最新成功版への実更新を受入。GitとWebの元Markdown hash一致 |
| 日次公開・障害通知 | 通常scheduleの収集→audit→export→Git→Pagesを受入。stage別Issue通知はmock検証済み |
| 記事画像 | 新規Noteで本文画像の候補ID・配置を選択し、出典のHTTPS画像を直接表示。既存Noteの再生成は行わない |
| 検証 | 実Chromiumを含む全回帰と公開前検査を継続。実施ごとの結果は検証記録を参照 |
| 人力Vaultのリポジトリ・プラグイン・公開設定 | 利用側で決定。本プロジェクトの対象外 |

**既存の成功Noteを追加LLM呼出しなしでexportし、GitとWebで同じbytesを参照できます。**
Git取得・出版・利用側の編集保護は[Git配布手順](docs/git-distribution.md)を参照してください。
現在の検証範囲は[検証・受入](docs/verification.md)を参照してください。

## 残っている確認と次の作業

標準経路のレビュー指摘F1〜F6、通常schedule、実切戻し・復帰、[リファクタリング計画](docs/refactoring-plan.md)のR1〜R5は完了しています。
未完了の作業は次の順で進めます。詳細な開始条件と判断事項は[次の作業](docs/next-work.md)にあります。

1. [#127 記事画像](https://github.com/Ningensei848/kaname/issues/127)：新規Noteへの画像配置とGit/Pagesの検証。画像は出典URLから直接表示する。
2. 現行文書の整合性：完了済みのschedule・切戻し・リファクタリングを未完了扱いしない。
3. [#94 実Batch受入](https://github.com/Ningensei848/kaname/issues/94)：2026-10-10の読取り専用事前検査はready。次は有料提出の個別承認と、最大1件の成功保存・復旧・費用照合。
4. [#116 請求照合](https://github.com/Ningensei848/kaname/issues/116)：確定明細がないため今回は待機。利用可能な確定請求期間と明細を指定して推計と照合する。
5. [バックログ](docs/roadmap.md)：source health、代表サイトの回帰corpus、並列収集、graph品質。browser sourceや利用者Vault/NTFSの受入は対象を指定してから進める。

## 公開するもの

LLMが生成した有効なcompact Note群を公開します。AI要約、重要ポイント、検索語、資料の位置づけ、
出典、モデル・入力打切り情報を含みます。記事原文・raw HTML、認証情報、運用のstate/receipt/run reportは配布しません。
画像は記事のalt・キャプション・周辺テキストを根拠に選び、AI要約または関連する重要ポイント等の直後へ配置します。
要約の300〜500字に画像指定を含めず、元記事の語数にも画像URLを加えません。閲覧時に出典サイトへの外部通信が発生します。
GCS bucketの匿名公開は行わず、公開用NoteをGitへexportする境界を設けます。

公開NoteとPagesは同じsnapshotを使い、Noteの識別子・版・出典を追跡できるようにします。
生成領域への人手の注釈は人力Vault側に保持する運用を基本にします。
仕様は[仕様書](docs/specification.md)、配布契約は[公開・配布設計](docs/publication.md)にまとめています。

## Web previewを確認する

Quartz 5.0.0とpluginを固定し、共通公開snapshotで一覧・検索・出典別/カテゴリ別/日付順・Note本文を確認できます。
元Markdownのbytesとhashを保持します。[起動・検証手順](docs/web-preview.md)を参照してください。
Checksの`web-preview` jobが静的previewとdesktop/mobile画面をartifactへ保存します。Checks jobは検証用です。実deployは日次/Pages workflowが行います。

## 現行コレクタを使う

Python 3.12で、リポジトリrootから実行してください。CLI/パッケージ名は互換性のため`techkb`です。

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock
python -m pip install --no-deps -e .
python -m techkb validate-config
python -m pytest -q
```

ブラウザ機能の検証は[操作手順](docs/operations.md)に従って追加runtimeを導入します。
Windowsでは対応するvenvのPowerShell activateを使用してください。
依存更新は隔離環境で解決し、lock更新と必要な検証を行います。

| 設定 | 役割 |
|---|---|
| `config/app.yaml` | モデル、呼出し/入力/出力上限、カテゴリ、保存・費用・通知 |
| `config/sources.yaml` | 情報源と取得方式。Google Research/GitHub Blog有効、AWS News無効 |
| `prompts/enrich.txt` | 本文を命令として扱わない要約・分類指示 |
| `GCS_BUCKET` | GCS保存先。認証はローカルADCまたはActions WIF |
| `GEMINI_API_KEY` | Gemini認証。GCS認証とは別。環境変数またはGitHub Secretで渡す |

通常はstandard、30件/run、入力20,000文字、出力2,048 tokens、minimalを維持します。
入力上限は記事Markdown部分の文字数でありtoken数や記事全体の保証ではありません。
打切りNoteは制限を表示します。設定変更で既存Noteを自動再要約しません。
予算は通知閾値で、日次の厳格な課金上限ではありません。

```bash
python -m techkb run          # 有料生成・GCS更新を伴う通常収集
python -m techkb audit-state  # GCS読取りだけで整合性を検査
python -m techkb cost-report  # 保存済みreport/usage journalから費用推計
```

`dry-run`にも記事への通信があり、`run --max-calls 0`にも回収・保存があります。
読取り診断、Batch、互換sync、通知、metadata更新、lifecycleの正確な操作と副作用は
[操作手順](docs/operations.md)を参照してください。
現在の定期実行は毎日07:17 JST予定です。GitHub側の遅延があり、同じbucketのwriterは一つに限定します。

## 資料

- [文書の入口](docs/README.md)：現在読む資料と履歴の区別
- [ADR](docs/adr/0001-generated-content-module-and-pages.md)：生成リソースの独立と二つの参照経路
- [仕様書](docs/specification.md)、[公開・配布](docs/publication.md)、[Git配布手順](docs/git-distribution.md)、[実装計画](docs/implementation-plan.md)
- [操作](docs/operations.md)、[設計](docs/design-decisions.md)、[GCP設定](docs/gcp-setup.md)、[source方針](docs/source-policy.md)
- [検証・受入](docs/verification.md)、[バックログ](docs/roadmap.md)

日次の実施報告・旧計画・引継ぎ・レビューは[履歴資料](docs/archive/README.md)へ整理しました。
現行文書には現在の要件・保証・未実装範囲を記載し、過去の件数や作業指示を混在させません。
