# #94: Batch事前検査のWIF境界修正

基点はPR #124/#125取込後のmain `152ced8a90df428f30904026c10a292cc91f6f35`。
2026-10-07 UTC（2026-10-07 JST）に独立workflowを一度実行した。
[run 37635478553](https://github.com/Ningensei848/kaname/actions/runs/37635478553)は
`google-github-actions/auth@v3`で失敗し、GCS事前検査のstepはskipされた。
Gemini呼出し、GCS読取り/書込み、記事取得、通知、Git更新、Pages deployは行っていない。

## 原因と修正

WIFの応答は`unauthorized_client`で、attribute conditionによる拒否だった。
既存の[設定文書](../../gcp-setup.md)と[配布契約](../../publication.md#workflowと復旧)にも、
WIFが`daily.yml@refs/heads/main`だけを許可すると記載されている。
PR #125ではmain条件だけを確認して独立workflowを追加し、このworkflow path制約を見落とした。
読取り専用かどうかと、認証可能なworkflowかどうかは別である。

IAM・Secret・Service Account・WIF条件を変えず、`daily.yml`に手動入力`batch_preflight`を追加した。
`true`の場合はmain限定の検査専用jobを実行し、通常collect/publish/pages/notify jobはskipする。
専用jobの権限は`contents: read`と`id-token: write`のみ。
通常collectと同じ`techkb-gcs-single-writer`を使い、GCS検査scriptを読取り専用store経由で実行する。
Gemini/GitHub書込み用Secretを渡さず、費用通知、export、artifact uploadを行わない。
対応しない独立`batch-preflight.yml`は削除した。

他モード、verification/diagnostic ID、baseline、collection mode変更、max_callsとの併用は認証前に拒否する。
入力未指定のscheduleと通常手動実行では従来の処理を維持する。
既存CLIの15コマンド、API、schema、GCS path、料金設定、日次scheduleは変更していない。

## 検証と次の操作

- 変更前のBatch関連回帰: **69 passed**（5.02s）、actionlint成功。
- 新規workflow境界15ケースと既存preflight 7ケース: **22 passed**（0.89s）。
  認証前の競合拒否、main制約、成功/失敗時の有料処理・書込み・通知・公開skip、
  最小権限、writerロック、既存4モードの互換を確認した。
- 全Python回帰: **341 passed**（36.15s）。actionlint 1.7.12と`git diff --check`成功。
  CIは修正PRで確認する。修正後の実WIF検査は未実施。

修正PRのCI成功・main取込後に、`daily.yml`を`batch_preflight=true`で一度実行する。
GCSの最新audit・active ledger・未計上Batch・未完了standard usageを確認してから、有料提出の個別承認へ進む。
今回の認証拒否をBatch提出失敗として計上せず、#94は未受入のまま維持する。
新規有料提出はまだ承認されておらず、実行もしていない。
詳細な認証ログ、運用識別子、原文、課金明細は公開Issue/archiveへ転載しない。
