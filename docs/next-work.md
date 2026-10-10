# 次の作業と優先順位

2026-10-10にREADME、現行仕様、未解決Issueと実装を照合した着手順です。
通常schedule、Pages切戻し・復帰、T0/O1/O2とR1〜R5は受入・取込済みです。
READMEの古い未完了記載を理由に再実装しません。進捗は[検証・受入](verification.md)と各Issueで区別します。

| 優先 | 作業 | 理由・開始条件 | 次に必要な判断 |
|---|---|---|---|
| P1 | [#127 記事画像](https://github.com/Ningensei848/kaname/issues/127) | 現在の要約から画像が失われる利用上の問題。HTML候補抽出・LLMの候補選択・Note配置・公開検査・Web表示を一貫して対応 | 出典URLから直接表示し、今後収集するNoteのみへ適用する方針はユーザー確認済み |
| P1 | README・方針・検証手順の整合性 | 完了済み作業を再着手しないため。画像による外部通信の許容範囲も明記 | 追加判断なし |
| P2 | [#94 実Batch受入](https://github.com/Ningensei848/kaname/issues/94) | offline実装・修正は完了。2026-10-10のmainでWIF/GCS読取り専用事前検査はready。本番成功Noteの保存・復旧・費用計上は未受入 | 既存の最大1件提出案と回収・再実行の操作範囲について個別承認。状態変更後は提出直前に再検査 |
| P2 | [#116 確定請求照合](https://github.com/Ningensei848/kaname/issues/116) | 費用推計と請求実額の差を説明する。2026-10-10にユーザーから確定明細がないことを確認したため、今回は待機 | 確定明細が利用できる時点で対象期間と非公開明細を指定 |
| P3 | Source Health Check | 最終成功・連続失敗・発見/処理件数を見えるようにし、sourceの劣化を判断できるようにする | 出力先・運用用途を設計時に確認 |
| P3 | Regression Corpus | 代表サイトの本文・画像抽出の変化を継続検出する | 代表sourceとfixtureの扱いを設計時に確認 |
| P4 | Parallel Processing | fetch/convertだけを並列化し、状態更新と課金処理の順序を維持する | 必要な処理時間・並列数を設計時に確認 |
| P4 | Knowledge Graph Quality | 表記揺れ・同義語・tags/WikiLinkの品質を評価する | 良否の評価例を確認 |
| 対象指定後 | browser source・利用者Vault/NTFSの受入 | 実装済み機能の環境別受入。人力Vaultの管理は利用側の責務 | 検証するsourceまたはVaultと操作範囲を確認 |

読取り専用事前検査の承認範囲と実結果は[Batch事前検査の受入記録](archive/2026-10/batch-preflight-acceptance-2026-10-10.md)にあります。

## #127の実装範囲

記事本文からHTTPS画像候補を最大12件抽出し、alt・キャプション・周辺テキストを候補IDとともにLLMへ渡します。
画像自体は解析せず、候補にあるIDだけを最大6件選び、AI要約・対応する重要ポイント・資料の位置づけの直後へ配置します。
画像指定は要約文の字数とは別項目です。本文入力は20,000文字のまま、画像URLはLLM入力や元記事の語数へ加えません。
画像なしの旧Note・既存Batch台帳・成功Noteの識別子とbytesは維持します。過去Noteの再取得・再生成は行いません。

公開Noteに選んだ画像URLと配置を記録し、画像Markdownとの完全一致・位置・秘密の混入を検査します。
画像ファイルは取得・保存・Git同梱しません。Pagesは当該Noteにある画像のみ表示し、画像hostだけをCSPの画像通信へ追加します。
script・connect等の外部通信は引き続き許可しません。HTMLの画像には`referrerpolicy="no-referrer"`を設定します。
HTTP、data URL、認証付きURL、IP/ローカルhost、署名・token付きURL、入力打切り後の説明しかない画像は候補にしません。
元画像の変更・削除による表示の変化はNoteのhashやGit版では固定できません。

standard/Batchのmock実行、復旧と二重計上防止、公開snapshotのbytes一致、実Chromiumの画像表示を検証します。
Web検証では許可された画像レスポンスをローカルで代用し、出典サイトへ実通信せず、ほかの外部resourceは拒否します。
本番のGemini/GCS更新・workflow手動実行・Pages deployと画像入りの実Note受入は別に判定します。
