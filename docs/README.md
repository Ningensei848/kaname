# 文書の入口

LLM生成Noteを独立した公開リソースとして管理し、同じNote群をGitHub Pagesとgit submoduleで参照する。
人力Vaultの管理・公開は利用側の別リポジトリの責務である。

| 文書 | 読む目的 |
|---|---|
| [監査一覧](repository-audit.md)・[次の作業](next-work.md) | 残課題20項目の根拠/完了条件と優先順位 |
| [ADR-0001](adr/0001-generated-content-module-and-pages.md)・[仕様](specification.md) | 採用構成、責務と境界 |
| [公開・配布契約](publication.md) | Note ID/manifest/snapshotと公開前検査 |
| [操作手順](operations.md) | CLIの副作用、課金、復旧、画像補完 |
| [Git配布](git-distribution.md)・[Release配布](release-distribution.md) | content/submoduleと固定版の完全/差分復元 |
| [日次公開](daily-publication.md)・[Pages](pages.md) | workflow、検査再利用、deploy/切戻し |
| [Web preview](web-preview.md) | build/ブラウザ検査/固定依存と既知警告 |
| [新規記事限定](incremental-collection.md)・[出力打切り復旧](output-recovery.md) | 既知URL再検査と上限付きの1件復旧 |
| [検索リンク](ns1-search-fallback.md)・[Graph品質](graph-quality.md) | WikiLink/Google検索と読取り専用評価 |
| [設計補足](design-decisions.md)・[検証基準](verification.md) | 保存/復旧/課金/通信の保証と未受入範囲 |
| [GCP設定](gcp-setup.md)・[source方針](source-policy.md) | private GCS/ADC/WIFと収集/公開の方針 |
| [archive索引](archive/README.md) | 完了済み計画、過去の検証証拠、引継ぎの保全先 |

仕様の衝突時は最新のユーザー指示を優先してADRへ反映する。
仕様・操作・現在の保証・残課題の正本を分け、同じ進捗や日次件数を複数文書へ転記しない。

## 履歴の扱い

完了済み資料61件は専用archive branchへ退避した。元path/blobと復元方法はarchive索引に残す。
過去の「未完了」「次に実行」「承認枠」は当時の記録であり、現在の作業指示や追加操作の承認ではない。
新たな日次報告をmainに積み上げず、状態が変わった要約だけ現行文書へ反映する。
