# 公開基盤の実装状態

[ADR-0001](adr/0001-generated-content-module-and-pages.md)に基づく公開基盤は実装済みです。
過去の工程別計画は[履歴](archive/2026-10/publication-implementation-plan.md)へ保存しました。
現在の保守性改善は[責務整理](refactoring-plan.md)、機能追加と未完了受入の優先順位は[次の作業](next-work.md)を正本にします。

| 工程 | 実装状態 | 正本 |
|---|---|---|
| 成功Noteから公開snapshotをexport | 実装・本番受入済み | [公開・配布](publication.md) |
| 固定snapshotをGit content履歴へ配布 | 実装・本番受入済み | [Git配布](git-distribution.md) |
| Quartz入力・静的成果物・公開前検査 | 実装・fixture/固定実content検証済み | [Web preview](web-preview.md) |
| Pages公開と配信版照合 | 初回公開・通常schedule・切戻し/復帰を受入済み | [Pages](pages.md)、[日次公開](daily-publication.md) |

実装・ローカル検証・本番受入を区別します。現在の保証と未受入範囲は[検証・受入](verification.md)で確認してください。
人力Vaultの管理、画像保存、GCS停止中の新規成果の代替保存は、この公開基盤の機能に含めません。
