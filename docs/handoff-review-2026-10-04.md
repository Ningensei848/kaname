# 開発停止・全体レビューへの引継ぎ — 2026-10-04

## 停止指示と結論

ユーザーは「区切りのいいところで作業を停止し、ファイルにない状態を保存し、別セッションのGPT-6.1 Solへ全体レビューを依頼する指示文をまとめる」と指示しました。
機能実装・修正・新しい本番runの起動を停止しています。この引継ぎは実装再開の指示ではありません。
次のセッションには[全体レビュー依頼文](review-prompt-2026-10-04.md)を渡してください。

- Phase 1: 上限30件の手動/定期runと独立したWIF/GCS照合で本番受入完了。
- Phase 2: 8機能のコードとfixture検証をmainへ統合済み。実Batchの結果取り込みが失敗したため最終受入は未完了。
- 通常収集: 停止前に完了した日次runは30件保存・失敗0件・整合性問題0件。
- Codexの自動継続: heartbeat `kaname-phase-1-phase-2` は **PAUSED**。古い継続指示を再生しないこと。
- 本番の日次GitHub Actions: 既存scheduleは稼働を継続。停止したのは開発作業とCodexの自動継続であり、このsnapshot以降もGCS状態は進み得ます。

## コードと検証の基点

対象は `Ningensei848/kaname`、作業場所は `/home/ningensei848/dev/kaname`。
実装基点はmain `f7bbc28f240b94ebf5b85cc72981996b17b19e05`。
この文書を保存するdocs commit以降に変更があれば、その差分と現在のActions状態を先に確認してください。

- [PR #92](https://github.com/Ningensei848/kaname/pull/92): 日次reportとGCS状態の読取り照合。
- [PR #93](https://github.com/Ningensei848/kaname/pull/93): Phase 1受入完了とPhase 2計画。
- [PR #95](https://github.com/Ningensei848/kaname/pull/95): Phase 2実装。コードhead `96929a373704d9ecb68330d1561c1e190df9162b`。
- [Issue #94](https://github.com/Ningensei848/kaname/issues/94): Phase 2追跡。実Batch失敗を残し、閉じないこと。
- 最終ローカル検証: Python 3.12、google-genai 1.75.0、Playwright 1.63.0、実Chromiumで103 tests passed、設定検証成功。
- [PR CI 37164238148](https://github.com/Ningensei848/kaname/actions/runs/37164238148)と[main CI 37164366370](https://github.com/Ningensei848/kaname/actions/runs/37164366370)はsuccess。
- 実Chromiumを入れないdaily側ではブラウザtestのskipがあるため、full CIと件数を混同しないこと。

## 最後の本番状態

以下の3 runはすべて実装基点のmainで動作しました。時刻はJSTです。

| run | 起動・結果 | report ID |
|---|---|---|
| [37164369505](https://github.com/Ningensei848/kaname/actions/runs/37164369505) | 手動 batch/max_calls=1。09:15頃起動、09:22:38完了。success、提出1、保存0、標準呼出0 | `20261004T001622Z-e22604f8` |
| [37164923005](https://github.com/Ningensei848/kaname/actions/runs/37164923005) | 手動 max_calls=0。09:25:54起動。failed、batch_failed 1、batch_saved 0、標準呼出0 | `20261004T002631Z-3aff5c70` |
| [37165511894](https://github.com/Ningensei848/kaname/actions/runs/37165511894) | 既存schedule。09:37:28–09:46:44。success、呼出30、保存30、失敗0 | `20261004T003758Z-c36892d7` |

Batch提出直後のauditはindex 96、pending 78、truncated_rows 75、issues 0。
取り込みrunのfailureは `stage=batch_result / source_id=google-research / error_type=ValueError`。
そのrunのpendingはreport上78→79ですがAuditはskipされ、独立照合はしていません。
最後の日次auditはindex 126、pending 48、truncated_rows 100、issues 0です。
pendingには新規発見・重複等も影響するため、保存数の単純な減算とは一致しません。

Batchの使用量は記録され、費用推計の増分はUSD 0.0016944、未決済Batchは0件になりました。
最後の日次run後のUTC日次費用は10月4日USD 0.0995463、10月累計USD 0.4013871。
unknown usageは0件、旧reportのモデル仮定は9件、予算alertなし。3 runともIssue投稿0件。
これは実測tokenと設定単価による推計で、請求明細との照合はしていません。
今回の3 runの根拠はActions内のreport/audit/cost出力であり、別runによる独立GCS照合は追加していません。

### Batch失敗について分かっていないこと

根本原因は未調査です。`ValueError`だけでは欠落応答、結果key、JSON/schema/category等を識別できません。
`src/techkb/batch.py` の結果処理と `pipeline.py` のfailure記録を追い、非公開ledgerに残ったcompact outcome/error_type/usageを確認する必要があります。
課金された1件を盲目的に再提出しないでください。取り込みが失敗したBatchを成功と扱わないでください。

- ledger: `state/batches/20261004T001622Z-e22604f8.json`。GCS上に保存されます。
- ledgerは記事原文を保持せず、候補metadata/hash、job名、compact outcomes、usage、billing_run_id等を保持する実装です。
- costの未決済0は処理済み状態と整合しますが、停止時にledgerそのものを独立ダウンロードして確認していません。
- `batch-status`はactive jobのみを列挙します。完了した失敗ledgerを表示しない点に注意してください。`batch-collect`というCLIはありません。
- 完了した失敗候補はpendingへ残り、通常standard収集で再処理可能です。後続日次が成功したことだけでは、同じ候補の保存やBatch互換性は証明できません。
- `run --max-calls 0`も記事取得、既存Batchの回収、GCS状態書込みを行うため、レビューの読取り専用コマンドではありません。

## 認証・本番設定・許可済み範囲

GCP projectは `q4rs-project`、private bucketは `kaname-q4rs-project-ningensei848`。
UBLA有効、Public Access Prevention enforced。実行service accountは `kaname-runner`。
ローカルADCは以前の確認で再認証を要求しました。一方、上記ActionsのWIF認証とGCSアクセスは成功しています。
現時点のBatch失敗をgcloud認証失敗と説明する根拠はありません。

WIF trustはこのrepoのmainと `.github/workflows/daily.yml@refs/heads/main` に限定しています。
診断のためにtrustやwriter権限を拡張しないでください。GitHub Secret値を抽出しないでください。
Repository Variablesは `GCS_BUCKET`、`GCP_SERVICE_ACCOUNT`、`GCP_WORKLOAD_IDENTITY_PROVIDER`、Secret名は `GEMINI_API_KEY`。

- Gemini: `gemini-3.5-flash-lite`、thinking minimal、入力上限20,000文字、出力上限2,048 tokens、通常上限30件/run、standardが既定。
- 有効source: Google Research/GitHub Blog。AWS News Blogは利用条件確認待ちで無効。
- sourceは従来HTTP/RSS設定。実JS取得と本文抽出はopt-inで、本文抽出切替はcontent hashを変え得ます。
- 日次cronは `17 22 * * *` UTC（名目07:17 JST、実際はGitHub側で遅延）。GCS writerはActions concurrency `techkb-gcs-single-writer`、cancel-in-progress false。
- ユーザーはdaily workflowへの恒久的 `issues: write` と連続失敗3回以上/設定予算到達時の自動Issue投稿を明示許可済み。再承認は不要。予算額は未設定です。
- 利用者のVaultパスは未指定。一時Vaultでのみ同期検証済み。本番Vaultを書き換えていません。
- raw保存はfalse、retention未設定。本番lifecycleは未適用。通常writerにbucket-update権限を追加していません。
- QuartzによるVaultのSSG公開はVault同期後の別課題で、未実装・未デプロイ。private GCSを公開する指示はありません。
- Phase 3の必須バックログは `docs/roadmap.md` に残しています。

## ファイルになっている診断状態

以下のprivateログはgitignore対象です。GitHubへ原文ログやGCSデータをcommitしないでください。
同じworkspaceのセッションでは参照できます。別環境ではGitHubのrunとこの文書を使って状態を確認してください。

- `local-state/phase2-acceptance-2026-10-04/`: `submission.log`、`collection.log`、`scheduled.log`と各report/cost/notify JSON。submission/scheduledのaudit JSONも保存。collectionはAudit skipのためauditファイルなし。
- `local-state/phase1-scheduled-2026-10-02/`: 元の日次ログ、照合ログ、report、acceptance JSON。Phase 1受入の根拠。
- rootの既存 `HANDOFF.md` は作業前からuntrackedの別引継書です。今回は上書き・削除・commitしていません。現在の状態は本書を優先してください。
- `/tmp/kaname-venv`、`/tmp/kaname-browsers`、`/tmp/kaname-uv-cache` は検証用の一時環境です。永続性は保証されません。
- heartbeat設定は `/mnt/c/Users/ningensei848/.codex/automations/kaname-phase-1-phase-2/automation.toml`。status PAUSED、interval 30分、thread `01a0f282-a025-7093-b2e5-27a66b4b9e69`。

設定検証・offline testを再現する場合は、現在の環境が残っていれば以下を使えます。本番runを起動するコマンドではありません。

```bash
PYTHONPATH=src /tmp/kaname-venv/bin/python -m techkb validate-config
PLAYWRIGHT_BROWSERS_PATH=/tmp/kaname-browsers PYTHONPATH=src /tmp/kaname-venv/bin/python -m pytest -q
```

## 全体レビューで重視する接点

最初に実Batch失敗の原因を根拠付きで調べ、その後に全体の相互作用を評価してください。
特にBatch予約/結果key/usage/永続化/receipt復旧/standard再試行、費用reportの重複計上とunknown判定、
Playwright経由の通信制限とrobots/本文変換、Vault同期の編集保護とpath/競合、通知の失敗履歴とclosed Issue重複抑止、
GCS条件付き更新と権限、CLI/config互換性、CIで証明した範囲とREADMEの記述を確認します。

ブラウザのDNS検査と接続の間のrace等の限界は手順書に記載済みです。
usage metadataの一部欠落を0として扱う可能性はレビュー候補で、未確認の不具合です。
疑いと確定事項を分け、停止時点で調査していない事項を既知の不具合として扱わないでください。
レビューで修正案を出す場合も、実装再開・paid run・本番データ変更・公開・automation再開は改めてユーザーの指示を受けてください。
