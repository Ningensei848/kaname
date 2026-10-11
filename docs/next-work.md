# 次の作業と優先順位

2026-10-11に未解決Issueを再照会した着手順です。
通常schedule、Pages切戻し・復帰、T0/O1/O2とR1〜R5は受入・取込済みです。
READMEの古い未完了記載を理由に再実装しません。進捗は[検証・受入](verification.md)と各Issueで区別します。

| 優先 | 作業 | 理由・開始条件 | 次に必要な判断 |
|---|---|---|---|
| 実装/限定受入済み | [#127 記事画像](https://github.com/Ningensei848/kaname/issues/127) | 実装済みでClosed。GlucoFM 1件の2図補完・GCS/Git/Pages・実画像表示を受入済み | 新規LLMの実選択は別受入。旧Noteへの一括適用はしない |
| P1 | [#135 PR検証の対象整理](https://github.com/Ningensei848/kaname/issues/135) | Checksは設定だけの変更でも全Python/Web検証を実行する。対象別の選択は未実装 | 必要な設定検査を維持してjobを選択する |
| P2 | [#94 実Batch受入](https://github.com/Ningensei848/kaname/issues/94) | 最大1件を個別承認後に提出したが、返却JSONがtitle_ja欠落・未知field・images型不一致で拒否された。追加提出0の失敗usage回収・台帳完了化・auditは完了。本番成功保存は未受入 | 逸脱原因は未確定。自動通知#129はこの既知の拒否に対応し、schema緩和・再提出は行わない |
| P2 | [#116 確定請求照合](https://github.com/Ningensei848/kaname/issues/116) | 費用推計と請求実額の差を説明する。2026-10-10にユーザーから確定明細がないことを確認したため、今回は待機 | 確定明細が利用できる時点で対象期間と非公開明細を指定 |
| P3 | Source Health Checkの実環境受入 | 読取り専用CLI・source別計数・時刻順・旧runのnullは実装/回帰済み | 新CLIの実GCS読取りを別途受入する |
| P3 | Regression Corpus | 代表サイトの本文・画像抽出の変化を継続検出する | 代表sourceとfixtureの扱いを設計時に確認 |
| P4 | Parallel Processing | fetch/convertだけを並列化し、状態更新と課金処理の順序を維持する | 必要な処理時間・並列数を設計時に確認 |
| P4 | Knowledge Graph Quality | 表記揺れ・同義語・tags/WikiLinkの品質を評価する | 良否の評価例を確認 |
| 対象指定後 | browser source・利用者Vault/NTFSの受入 | 実装済み機能の環境別受入。人力Vaultの管理は利用側の責務 | 検証するsourceまたはVaultと操作範囲を確認 |

読取り専用事前検査の承認範囲と実結果は[Batch事前検査の受入記録](archive/2026-10/batch-preflight-acceptance-2026-10-10.md)にあります。
個別承認後の提出・schema拒否・失敗usage回収とローカル切分けは[実Batchの実行記録](archive/2026-10/batch-acceptance-2026-10-10.md)にあります。

責務整理はPR #131の取込み、main CI、固定124件版のPages更新・配信照合、読取り専用Batch preflightまで完了しました。
証拠は[PR・本番受入記録](archive/2026-10/domain-refactoring-production-2026-10-10.md)に保存しています。
GlucoFMの限定補完は[受入記録](archive/2026-10/glucofm-image-repair-2026-10-11.md)で完了を確認できます。
新規LLMの画像選択・実Batch成功保存などの未完了受入は上表で個別に扱います。

## 未完了Issueの実装・受入計画

#127と#129は実装・失敗回収の証拠に基づきClose済みです。#94、#116、追加された#135はOpenを維持します。

### #135: PR検証の対象を選ぶ

設定はPythonの入力なので、設定変更時のPython検証をすべてなくす案は採りません。
不要な全件回帰とWeb buildを減らし、変更による影響に対応した検査を残します。

1. `checks.yml`に変更ファイルの分類を追加する。比較base/headを固定し、分類不能な変更は全検査へ戻す。
2. `config/sources.yaml`だけなら設定と本文/画像抽出、`config/app.yaml`なら設定・生成・公開契約、画像補完計画なら計画schemaの検査を選ぶ。
   Python/依存/共通契約/検証workflowの変更は全Python回帰を維持する。Webと公開契約に影響する変更はWeb受入を残す。
3. 文書のみ、設定のみ、Pythonのみ、Webのみ、混在、削除/rename、分類不能のケースでjob選択を検証する。
   required checkがskipで待ち続けないよう、従来のcheck名と結果集約を保つ。
4. 完了条件は、設定だけのPRで必要な検査が成功し、不要なjobが省略され、混在PRで必要な検査が欠落しないこと。
   この文書更新でworkflowの選択機能を実装済みとは扱わない。

### #94: 実Batchの成功保存

最初に追加課金なしで、同じ入力のstandard/Batch SDK送信payloadとschemaを比較する。
原因を確認できた箇所だけ修正し、schema・候補ID検証、usage/receipt復旧、保存失敗後の有料処理停止を維持する。
送信が正しくAPI応答だけが逸脱する場合は限界を記録し、schema緩和や盲目的な再提出で成功扱いしない。
新しい実提出は最新preflight・対象・費用・操作範囲の個別承認後に最大1 job/1 requestとし、回収・再実行の追加提出は0にする。
適合Note/receipt/index、audit/cost、再実行時の重複保存・二重計上0を確認してCloseする。
詳細は[Issue #94](https://github.com/Ningensei848/kaname/issues/94)の更新済み計画を参照する。

### #116: 確定請求の照合

確定明細が利用可能になった時点で対象期間・時間帯・通貨・集約粒度を決める。
保存済みrun/usageと元価格を読取り専用で対応付け、partial/unknown、調整、推計対象外のGCS/Actions費用を分ける。
必要な場合だけ実明細に合わせた小さな照合スクリプトを追加し、月跨ぎ・重複ID・欠損usageを検査する。
非公開明細を公開せず、差額と未照合範囲を説明して判定する。明細待ちの現在はOpenを維持する。
詳細は[Issue #116](https://github.com/Ningensei848/kaname/issues/116)の更新済み計画を参照する。

## #127の実装範囲

記事本文からHTTPS画像候補を最大12件抽出し、alt・キャプション・周辺テキストを候補IDとともにLLMへ渡します。
画像自体は解析せず、候補にあるIDだけを最大6件選び、AI要約・対応する重要ポイント・資料の位置づけの直後へ配置します。
画像指定は要約文の字数とは別項目です。本文入力は20,000文字のまま、画像URLはLLM入力や元記事の語数へ加えません。
通常の収集で画像なしの旧Note・既存Batch台帳・成功Noteを変更しません。
ユーザー承認済みのGlucoFM 1件は、[専用の画像補完](operations.md#既存noteへの画像補完)で本文だけを再取得し、要約の再生成なしで2図を追加・本番配信済みです。ほかの旧Noteへの一括適用は行いません。

公開Noteに選んだ画像URLと配置を記録し、画像Markdownとの完全一致・位置・秘密の混入を検査します。
画像ファイルは取得・保存・Git同梱しません。Pagesは当該Noteにある画像のみ表示し、画像hostだけをCSPの画像通信へ追加します。
script・connect等の外部通信は引き続き許可しません。HTMLの画像には`referrerpolicy="no-referrer"`を設定します。
HTTP、data URL、認証付きURL、IP/ローカルhost、署名・token付きURL、入力打切り後の説明しかない画像は候補にしません。
元画像の変更・削除による表示の変化はNoteのhashやGit版では固定できません。

standard/Batchのmock実行、復旧と二重計上防止、公開snapshotのbytes一致、実Chromiumの画像表示を検証します。
Web検証では許可された画像レスポンスをローカルで代用し、出典サイトへ実通信せず、ほかの外部resourceは拒否します。
本番のGemini/GCS更新・workflow手動実行・Pages deployと画像入りの実Note受入は別に判定します。
