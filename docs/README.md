# 文書の入口

現在の要求は「LLM生成Noteを独立した公開リソースとして管理し、同じNote群をGitHub Pagesと
git submoduleで参照する」です。人力Vault側の管理・公開は別リポジトリの責務です。

| 文書 | 読む目的 |
|---|---|
| [ADR-0001](adr/0001-generated-content-module-and-pages.md) | 要求変更の背景、採用する構成、旧仕様を置き換える範囲 |
| [仕様書](specification.md) | 生成Note・人力Vaultの境界、公開範囲、更新・編集の規則 |
| [公開・配布](publication.md) | Git snapshot、Note識別子、Pages/submoduleが共有する契約 |
| [実装計画](implementation-plan.md) | 次の工程、成果物、着手順、完了条件 |
| [操作手順](operations.md) | 現在動くCLIの設定・副作用・復旧操作 |
| [設計補足](design-decisions.md) | 現行収集の状態・receipt・課金・通信の保証と限界 |
| [検証・受入](verification.md) | 現在の実装状態、既知の指摘、受入の判定基準 |
| [バックログ](roadmap.md) | 新要求と継続する必須項目 |
| [GCP初期設定](gcp-setup.md) | 収集基盤の非公開GCS/ADC/WIF設定 |
| [source方針](source-policy.md) | 収集・要約・公開の取り扱い |

仕様の衝突時は最新のユーザー指示を優先し、その決定をADRへ反映します。
実装済みかどうかは検証・受入で確認してください。設計上採用した機能を稼働済みと扱いません。

## 履歴の扱い

[archive](archive/README.md)は当時の検証証拠や判断を保存する場所です。
旧Phaseの計画、日次の件数・run ID、停止時の引継ぎ、レビュー原報告を移しました。
履歴の本文は当時の状態を示し、現在の作業指示には使いません。

今後の日次記録は`archive/YYYY-MM/`へ置き、現行文書には状態が変わった場合の要約だけを更新します。
同じ保証・実装順・受入状態を複数の場所へ複製せず、上表の文書を正本にします。
