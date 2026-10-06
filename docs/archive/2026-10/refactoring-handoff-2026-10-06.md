# デスクトップ引継ぎ・タスク登録（2026-10-06）

## 確認した基点

GitHub上のmainは `4af02d221e117f1c383ee5313bc3a17dbdd8b6f3`。
[Checks run 37438974393](https://github.com/Ningensei848/kaname/actions/runs/37438974393)はcompleted/success。
これは既存CIの結果を読取りで確認した証拠であり、このデスクトップ環境でのテスト結果ではない。

## 完了した作業

- 同名タスクの重複がないことを確認し、T0/O1/R1〜R5/O2/O3の9件のIssueを作成。
- 各Issueへ目的・開始条件・完了条件・検証対象を設定。
- #94は新規作成せず、現在のBatch受入条件と安全な診断結果の要約へ更新。詳細な運用・課金情報は掲載しない。
- #108へタスク一覧と実装順を設定。

| ID | Issue | 開始条件 |
|---|---|---|
| T0 | #108 | なし |
| O1 | #109 | #108 |
| R1 | #110 | #108 |
| R2 | #111 | #110、#109 |
| R3 | #112 | #111 |
| R4 | #113 | #112 |
| R5 | #114 | #113 |
| O2 | #115 | #109、個別実行承認 |
| O3 | #116 | #109、確定請求明細 |
| Batch受入 | #94 | #111、個別提出承認 |

## T0の未完了事項

exec_commandはLinux shell、Windows PowerShell、別作業ディレクトリでも起動前に
`Failed to create unified exec process: No such file or directory (os error 2)`で失敗。
Node REPLも作業ディレクトリのlocal file URIを認識できず失敗した。

GitHubの読取り・Issue操作は利用できる。実行環境が復旧するまで、ローカルHEAD/差分、AGENTS.md、依存導入、Python/Web検証は未確認として残す。

リファクタリングの開始条件を満たしていないため、R1〜R5のコード変更は行っていない。
自然なscheduleの受入、切戻し、有料Batch提出、請求照合も未実施。

## 再開順

T0の実行経路とローカル検証を復旧 → R1だけを実装/検証してPR → R1取込とO1受入後にR2。
以降はR3 → R4 → R5を1 Issue/1実装PRで進める。
