# GPT-6.1 Solへの全体レビュー依頼文

以下を別セッションの最初のメッセージとして渡してください。

---

GPT-6.1 Solで `Ningensei848/kaname` の現行プロジェクト全体をレビューしてください。
同じ環境を使う場合のworkspaceは `/home/ningensei848/dev/kaname` です。

最初に `docs/handoff-review-2026-10-04.md` を読み、README、docs/verification.md、docs/roadmap.md、
docs/phase2-implementation-plan.md、docs/phase2-operations.md、設計・品質・利用条件の関連資料を確認してください。
実装基点はmain `f7bbc28f240b94ebf5b85cc72981996b17b19e05`（PR #95）です。
最新mainとの差分、working treeの状態、最新Actionsの結果を先に確認し、どのcommitをレビューしたか明示してください。
既存untrackedの `HANDOFF.md` やローカル変更は上書き・削除しないでください。

Phase 1は本番受入済み、Phase 2は8機能の実装と103テストを統合済みですが、実Batch受入は未完了です。
Batch提出run 37164369505は成功、max_calls=0の結果取り込みrun 37164923005は
`batch_result / google-research / ValueError`で失敗し、保存0件でした。使用量は記録されています。
後続の既存日次run 37165511894は通常30件保存・失敗0・audit issues 0でした。
後続standard成功とBatch受入成功を混同せず、まずBatch失敗の根本原因を調べてください。
認証はローカルADCとActions WIFを区別し、権限拡張やAPIキー抽出を診断の前提にしないでください。

その後、src/techkb、config、prompts、tests、依存lock、GitHub Actionsを横断してレビューしてください。
正しさ、障害復旧と再実行、二重課金/重複保存、状態・index・receipt・pendingの整合性、
ブラウザ取得と通信制約、Vaultの編集保護、費用集計と失敗通知、GCS権限/lifecycle、
設定・CLI互換性、テストの不足、資料が説明する保証と実装の差を確認してください。
必要なoffline検証・再現testは行って構いません。機能修正はまだ始めないでください。

成果物はレビュー報告としてファイルに保存し、優先度順の確定した指摘ごとに
対象file/line、具体的な発生条件、影響、根拠または再現結果、最小修正案、必要な検証を示してください。
未確認の疑いと環境制約は別に記し、既知の仕様・意図的な制約・未受入項目を区別してください。
最後にPhase 2受入に残る作業と、修正に着手する順序を提案してください。指摘がなければその旨と未検証範囲を明示してください。

開発はユーザー指示で停止中です。Codex heartbeatはPAUSEDで、既存の日次workflowだけが稼働を続けています。
レビューでは新しい本番workflow_dispatch、paid API呼出し、GCS/Vaultデータ変更、権限変更、
Issue自動投稿の手動起動、公開・デプロイ、PRマージ、automation再開を行わないでください。
本番の確認が必要で読取りの手段がなければ、分かる範囲と追加で必要な証拠を報告してください。
既存Batchを盲目的に再提出せず、ログ/報告に秘密情報や記事原文を出さないでください。

---
