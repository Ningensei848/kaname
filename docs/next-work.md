# 次の作業と実装計画

2026-10-10にGitHubの全12 Issue、main `e0dae2b0c0f26a7a88b68130bcf3b92c7390796a`、
コード・回帰・受入記録を照合しました。判定とGitHub操作の証拠は[Issue整理記録](archive/2026-10/issue-triage-2026-10-10.md)に保存しています。
通常schedule、Pages切戻し/復帰、R1〜R5、責務整理、画像対応と`source-health`は実装済みです。
機能の実装完了と、実環境での成功保存・画像表示・請求照合の受入を区別します。

## Issueの状態

| Issue | 状態 | 判定 |
|---|---|---|
| [#127 記事画像](https://github.com/Ningensei848/kaname/issues/127) | Closed | 候補抽出・選択・配置・字数との分離・公開/Web表示はPR #128/#131で実装済み。画像入り実Noteの本番受入は後続 |
| [#129 workflow失敗通知](https://github.com/Ningensei848/kaname/issues/129) | Closed | 失敗usage回収・台帳complete・audit/費用確認済みの通知として整理。schema逸脱の原因と成功保存は#94へ集約 |
| [#94 実Batch受入](https://github.com/Ningensei848/kaname/issues/94) | Open | Batch実装は存在するが、適合応答の実Note成功保存・再実行の受入が未完了 |
| [#116 確定請求照合](https://github.com/Ningensei848/kaname/issues/116) | Open・明細待ち | 推計/復旧/重複抑止は実装済み。確定明細と対応付けた照合は未実施 |

#108〜#115の8件は既にClosedです。今回の照会で未実装に戻す理由はありません。
未実装の回帰corpus、並列取得/変換、graph品質は既存バックログですが、対応するOpen Issueはまだありません。

## 着手順と単位

1. #94の追加課金なしの送信契約切分けを行う。原因が確認できた箇所だけ最小修正する。
2. 回帰corpusを実装する。#94がAPI側の調査・個別承認待ちになった場合も進められる。
3. corpusを基点にHTTP取得・変換を限定並列化し、状態更新と課金処理を単一の処理経路に保つ。
4. graph品質の評価とQuartz投影を改善する。
5. #94の実提出、画像入り実Note、source healthの本番読取りは、それぞれの開始条件が揃った時点で受入する。
   #116は確定明細が利用可能になった時点で進め、他の実装を待機させない。

切分け結果/最小修正、corpus、並列化、graph改善はそれぞれ独立した差分・PRにします。
今回のIssue整理では新機能の実装、新規有料処理、本番workflow起動は行いません。

## #94: Batch原因切分けと成功保存の受入

**現在の証拠:** 個別承認した最大1 job・1 requestは提出済みですが、`title_ja`欠落・未知field・`images`型不一致で拒否されました。
追加提出0の失敗usage回収と台帳completeは完了しています。移設後の[実GCS preflight](https://github.com/Ningensei848/kaname/actions/runs/38051568566)はready、
audit障害・未決済・未計上・未完了/不確実usageは0です。生成側の逸脱原因は未確定です。

**実装する順序:**

1. 既存の固定SDK送信・合成不適合応答の回帰を基点に、同じmetadata/本文のstandardとBatchの実SDK HTTP payloadを比較する。
   `gemini.py`、`batch.py`、`prompts/enrich.txt`、`tests/test_batch_sdk.py`を対象に、system instruction、schema、MIME、thinking、出力上限の差とAPI側の限界を整理する。
2. [公式Batch API](https://ai.google.dev/gemini-api/docs/batch-api)のgenerateContent系統と固定SDKに合わせ、schema参照・配列・必須fieldを照合する。
   [構造化出力の仕様](https://ai.google.dev/gemini-api/docs/structured-output)にはschemaの対応範囲とアプリ側検証があるため、別API系統の設定例やschema変換を無条件に採用しない。
   既存回帰でschema送信は確認済みであり、`$ref`やBatch非対応を根拠なしに原因としない。
3. 送信側の差異が確認できた場合だけ最小修正する。schema、候補ID/配置の検証、保存失敗後の有料処理停止、元価格・usage・receipt復旧を維持する。
   API側の逸脱しか確認できない場合は、観測した限界を記録する。model/SDK変更、schema緩和、盲目的な再提出で成功扱いしない。
4. 新規実提出が必要になった場合、最新preflight・対象選択・費用見積・GCS保存/回収/再実行・Git/Pages・通知の操作範囲を提示し、新しい個別承認を得る。
   最大1 job・1 requestを一度だけ提出し、待機・回収・再実行は追加提出0に固定する。曖昧なtimeoutや不適合応答では停止する。

**完了条件:** 適合応答のledger/receipt/Note bytes/index、元語数・打切り・画像選択、安定課金IDを照合し、audit/costが整合すること。
追加提出0の再実行で重複保存・二重計上0を確認し、実Note成功保存の受入証拠を残して#94をCloseする。
原文、未知field名、運用識別子、認証情報は公開しません。[過去の失敗回収](archive/2026-10/batch-acceptance-2026-10-10.md)を成功保存と混同しません。

## #116: 確定請求照合

**開始条件:** 確定明細と対象期間が利用可能であること。現時点は明細待ちで、架空データを使って本番照合済みにしません。

**実施する順序:**

1. 請求側の時間帯・通貨・model/modeの集約粒度を確認し、原文を非公開の作業資料として扱う。
2. 既存`cost-report`と保存済みrun/usageを読取り、UTC日/月、model、standard/Batch、保存時の価格、入力/出力/thinking counts、安定課金IDを対応付ける。
3. 既知usage、partial/unknown、未計上item、請求側の調整・粒度、GCS/Actions等の推計対象外を非公開の照合表で分ける。
   Batchの現行観測日計上と請求側の時点の違いを説明する。
4. 手作業で不足する場合だけ、実明細の形式に合わせた小さな読取り専用スクリプトを追加する。
   月跨ぎ、重複ID、欠損usage、元価格、確定/未確定の境界を検証する。請求連携や汎用import基盤を先に作らない。

**完了条件:** 対象期間の差額と未照合範囲を説明し、公開可能な要約だけを記録すること。
不明usageが残る場合は完全照合済みとしません。有料処理・請求連携・GCS書込みは追加しません。

## 未実装: 回帰corpus

**目的:** 実サイトに似た構造変化による本文・画像抽出の後退を、課金/通信なしで検出する。
既存fixtureは`tests/fixtures/article.html`と個別テスト内の合成HTMLで、代表ケースを一覧管理するcorpusは未実装です。

**実装する順序:**

1. `tests/fixtures/corpus/`に合成・匿名化したHTMLとcatalogを追加する。
   日本語RSS記事、本文selector付き一覧/詳細、コード・表、figure/相対・lazy画像、入力打切り、広告/危険URLの代表ケースから始める。
2. caseごとにbase URL、source設定、期待本文/正規化Markdown、canonical URL、語数、画像候補/ID・切詰め境界を記録する。
3. `extraction.py`→`html_cleaner.py`→`converter.py`→`normalize.py`と`images.py`を、現行パイプラインの順序で通すoffline回帰runnerを追加する。
   実サイトの保存本文やLLM応答を無断でfixtureへ転載しない。
4. pytest/既存Checksに組込み、case単位で差分を出す。期待値の自動上書きは行わず、抽出改善でhashが変わる差分は理由とともにレビューする。

**完了条件:** 全caseを外部通信・Gemini・GCSなしで再現でき、本文/語数/候補の後退が検出されること。
既存Noteを再生成せず、既存の公開・復旧回帰も成功すること。

## 未実装: HTTP取得・変換の並列化

**開始条件:** corpusと現在の保存障害/課金/再実行の基点が通ること。
最初はHTTP sourceだけを対象とし、Playwright経路は現行の直列実行を保ちます。

**実装する順序:**

1. `pipeline.py`の取得・本文抽出・変換・画像候補処理を、GCS/状態/LLMを触らない処理へ抽出する。
   並列数は既定1で従来互換とし、最初のopt-inは2。workerごとのConverterと、上限付き投入queueを使う。
2. `fetcher.py`/`browser_fetcher.py`に対応するhost単位の待機・robots・redirect/retry制御を確認する。
   `last_request`とrobots cacheをそのまま競合するworkerへ共有せず、同じhostへの間隔を一か所で管理する。
   各redirect先の許可host/DNS検査と既存HTTP上限を維持する。
3. 取得結果を元のcandidate順で単一のwriterへ戻す。重複判定、raw保存、Gemini/Batch提出、usage/receipt/Note/index/pending/report更新はwriterだけが行う。
   workerにはstore/Geminiを渡さず、有料呼出し上限とBatch予約を並列化しない。
4. 保存失敗時は新しい投入と後続有料処理を止める。順序が逆転する取得、同一本文/URL、host間隔、保存中断、再実行を検証する。
   合成遅延で並行取得を確認し、並列数1/2でNote bytes・課金ID・提出件数・状態が同一になることを照合する。

**完了条件:** 取得/変換の同時進行が確認でき、writerは一つ、queueは有限、同host間隔は守られること。
保存障害後の追加有料処理0、二重保存/二重計上0、既存manifest/ID/bytesの契約を維持すること。

## 未実装: Knowledge Graph品質

**現在の実装:** `composer.concept`は表示文字の整形、`site.project_content`は既存Note titleが一意に一致するWikiLinkだけをリンク化します。
別名・表記揺れの評価と解決は未実装です。

**実装する順序:**

1. 合成の評価例を用意し、同義表記、異なる概念、曖昧な略語、重複titleを分ける。`C`/`C++`/`C#`等を誤統合しないケースを含める。
   現状の一意解決・未解決・曖昧リンクとtagのばらつきを読取り専用で測る。
2. 明示的なalias対応表と比較用の正規化keyを設計する。表示名と比較keyを分離し、曖昧なalias/collisionは自動解決しない。
3. 最初の変更は`site.py`のQuartz投影で、既存Noteへ一意に解決できるものだけ改善する。
   元Markdown/Note ID/dataset digestを変えず、リンク先のない概念を架空Noteとして増やさない。
4. tag/WikiLink評価、snapshot bytes、全内部リンク・検索・browser受入を検証する。
   生成Noteの語彙やpromptを変える案は、この評価後の別差分とし、過去Noteを再生成しない。

**完了条件:** 固定評価例で誤リンク/誤統合0、意図したaliasの一意解決が増え、公開リンクが壊れないこと。
追加LLM判定を使わず、既存Note bytesとdataset digestを保持すること。

## 実装済み機能の後続受入

- **画像入り実Note:** #127の機能は完了。次の承認された収集で画像候補がある実Noteを対象に、LLM選択・配置・字数との分離、GCS→Git→Pagesのbytes/hashと許可画像表示を確認する。
  候補がない/選択0の場合は受入を完了扱いしない。新規有料収集を必要とする場合は対象と費用・操作範囲の個別承認後に行う。
  出典HTTPSの直接表示を維持し、外部画像の内容・存続はGit版で固定されません。
- **Source Health:** 読取り専用CLIと回帰は実装済みで、再実装しない。実GCS受入は既存WIF境界に合わせた読取り専用入口で実施し、source別count・pending・完了/streak・旧runのnullを照合する。
  新規LLM・GCS保存を伴わず、本番読取りを実施していない現時点はoffline検証済みと記録する。
- **browser source/Vault/NTFS:** 指定sourceまたは利用者環境が決まってから、その範囲だけ受入する。

責務整理のPR #131/#132、main CI、固定124件版のPages更新・全元Markdown照合と読取り専用Batch preflightは完了しています。
証拠は[本番受入記録](archive/2026-10/domain-refactoring-production-2026-10-10.md)、現在の保証は[検証・受入](verification.md)を参照してください。
