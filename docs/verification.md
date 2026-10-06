# 現在の検証範囲と受入基準

現在の要求は[仕様書](specification.md)と[ADR-0001](adr/0001-generated-content-module-and-pages.md)を正本とします。
日次の作業記録・run別の件数・旧受入手順は[履歴](archive/README.md)へ整理しました。
この文書は現在の実装状態と完了の判定基準を示します。

## 現在の状態

Git配布の実装基点はmain `84313ed0542a7a478d7b05636d4eee5279492b0e`（PR #101取込後）です。
PR #101のChecks run `37209988391`と、取込後のmain run `37316866662`は成功しました。
既存198件に旧形式Noteの公開互換4件とGit配布15件を追加し、実Chromiumを含む全217件が成功しています。
架空Note 3件の実Chromium受入で検索、全ローカルリンク、元Markdown hash、375/768/1024/1440px、
AI/打切り表示、外部resource要求0を確認しています。手順・依存の未解消制約は[Web preview](web-preview.md)にあります。
実GCSからのexportと初回Git配布は受入済みです。Pages deployは未実施です。

| 領域 | 実装/検証 | 未完了 |
|---|---|---|
| standard収集 | Phase 1本番受入済み。既存日次workflow稼働 | 費用復旧・usage部分欠落・通知判定の指摘 |
| Batch | submit/復旧/安全な診断、固定SDKのoffline検証済み | 成功結果を実Noteへ保存しaudit/costで照合する本番受入 |
| 互換sync | PR #98取込済み。既存Note・候補・同時作成の保護を一時Vaultで検証 | Windows/NTFS、利用者環境。新しい標準経路の受入とは別 |
| browser/抽出/フィルタ/lifecycle | 実装とfixture検証済み | redirect policy修正、必要なsourceの実受入。raw retention未設定は適用不要 |
| 共通公開snapshot | export/manifest実装、43件のoffline検証。実GCS117件のexport受入 | 日次公開への接続 |
| Git配布 | bare出版/再実行/競合等15テスト、初回117件公開。一時submoduleの固定/明示更新を検証 | 利用者の実Vault・プラグイン・NTFSは対象外/未検証 |
| Web/Pages | Quartz 5.0.0の公開境界24テストと架空/実Noteのbrowser検証。同じ配布commitからbuild | 実NoteのPages deploy、継続更新と切戻しの受入 |

Pages照会は先の読取り時に404でした。404だけでは権限による非表示と不在を区別できません。
Git配布は実公開を照合していますが、Pages公開pipelineを稼働済みとする根拠はありません。
現在の収集成功をGit配布・Pages稼働と混同しません。

## 実Noteの配布受入

- 既存ADCでprivate GCSの成功index/Note/receiptを読取り。117件を選択し、314 objectの世代/bytesとindex一覧を再照合。
- 成功試行は628 read、2 index list。GCS書込み・追加LLM・記事取得は0。認証情報や本文を受入ログへ出さない。
- 初回失敗は旧compact形式の打切りNote4件による`invalid_compact_body`。限定的な互換判定で解消し、Note bytesは維持。
- 配布commitは`62ed7f08ec786e1067cc6eecd9bece5e078b8c5c`、Note数117、rootの配布ファイルは計120件。
- dataset digestは`d0734d9c3ffa8e23b070692d790ea9c5be09b8b46d5d166a59fdd59853f91e8c`。
- 同じsnapshotの再出版は`unchanged: true`で同じcommit。通常clone後のmanifest/全Note bytesも一致。
- Git checkoutのHEADと指定commitを照合してWeb build。全117件の元Markdown hash、実Chromiumの検索/Note/出典、内部リンク、4画面幅、外部resource要求0を確認。
- 受入したローカルartifact digestは`72d6acdad03643c2e5aca4dc5fda65fe079270b45761d757c071137758721e40`。
- 旧形式4件はWebに上限未記録の注意を表示し、元Markdownは保持。Pagesにdeployしたとは扱わない。

[公開Noteと固定版の取得手順](git-distribution.md)に実際のGitHub参照先を記載しています。
GCS writer/IAM/lifecycle、本体Vault、既存日次workflow、heartbeatは変更していません。
日次件数の記録ではなく、公開経路の初回受入証拠としてこの状態を保持します。

## 実Batchの直接原因

既存jobをGETする読取り診断で、STOP/textあり、必須`title_ja`欠落と未知fieldの`extra_forbidden`を確認しました。
schema検証で拒否されたことが保存0の直接原因です。生成側が逸脱した理由と未知field名は未確認です。
診断の元例外型を保持するF2はPR #97で対応済み。schema要件は維持し、自動再生成は追加していません。
後続standardで同候補が保存されても、元Batchの保存成功を意味しません。
元の台帳/billingと読取りrunの証拠は[履歴の検証記録](archive/2026-10/verification.md)にあります。

## 継続する確定指摘

| 指摘 | 状態 | 完了条件 |
|---|---|---|
| F1: Vault編集消失 | PR #98対応済み。互換syncの契約 | in-place/rename/新規作成/candidate編集を保持。利用側環境は別検証 |
| F2: Batch元例外の欠落 | PR #97対応済み、実GET診断済み | 型と安全なcodeを保持。原文/秘密/例外本文を出さない |
| F3: browser redirect先の事後検査 | 未修正 | resource/robotsの各hopを通信前に判定。未許可hostへの要求0 |
| F4: 部分欠落usageを完全扱い | 未修正 | 既知countを保持し、不明な課金countをpartialとして表示 |
| F5: receipt後の中断で費用欠落 | 未修正 | 再課金0・usage欠落0・費用重複0、日/月と単価履歴を保持 |
| F6: 未検証sourceのstreakリセット | 未修正 | 実際の復旧だけでresetし、未処理sourceは維持 |
| F7: 文書と実装の不整合 | 今回の改訂で状態/schema/通知の説明を更新 | 現行文書と実装・受入状態を照合し、履歴はarchiveへ分離 |

元のfile/line、条件、影響、再現、最小修正案は[全体レビュー](archive/2026-10/project-review-2026-10-04.md)に保存しました。
[レビュー再現ケース](archive/2026-10/review-reproductions-2026-10-04.py)は未修正指摘を実証する手動用で、
通常のpassing test suiteとは別です。audit失敗のIssue対象化は通知仕様として工程5で定義します。

## 新しい配布・Webの受入

1. 同じ入力snapshotから同じNote bytes/manifest digestを生成し、追加LLM・記事取得・GCS更新が0。
2. index/Note/receiptと世代が一致し、不完全な読取り、余計なファイル、原文/秘密/危険な埋込みを拒否。
3. タイトル変更・本文更新・metadata更新でNote ID/URLを維持し、最新成功版を決定的に選択。
4. Git配布は完全snapshotのみをcommit。変更なし再実行、競合、途中失敗で履歴/公開版を破壊しない。
5. 一時親repoで特定commitのsubmodule参照と明示更新を検証。dirty/未管理ファイルを消さない。
6. Pagesは同じ配布commitから構築。検索・source/category・出典・AI/打切り表示、base pathと内部リンクが正しい。
7. 人力Vault、archive、運用state/receipt/認証情報がartifactに入らず、build/deployへ収集Secretを渡さない。
8. 実Web URLと配布commit/digestを提示し、GitとWebの元Note hash一致を照合。
9. build/deploy失敗時は前の成功版を維持。同じ版で再試行/切戻しでき、再課金なし。

実際の人力Vaultへの組込みやプラグイン導入を、このセッションの受入条件には含めません。
公開とBatchとsource別の実取得はそれぞれ独立して判定します。

## Pages workflowの公開前受入

固定Git commitのclean tree/blob照合、公開artifactのcommit/digest/元Markdown照合を実装しました。
17件のテストでdirty/ignored/untracked/symlink、別commit、非公開tree、fixture/版/digest不一致、
artifact改変/余計なfile、path重複を拒否することを確認しました。
配信版確認はHTTP serverを使い、古いcommit/Note数の不一致、配信HTML/Note bytesの改変、404を拒否することも検証しました。
実content `62ed7f08ec786e1067cc6eecd9bece5e078b8c5c`の117件をPages用artifactへbuildし、
dataset digest `d0734d9c3ffa8e23b070692d790ea9c5be09b8b46d5d166a59fdd59853f91e8c`、
全元Markdown bytes、全HTMLローカルリンク、検索/出典/画面幅、外部resource要求0を検証しました。
クラウドでは導入済みsystem Chromium、CIではPlaywright固定Chromiumを使います。
Pages workflow/Checksの構文はactionlintで検証済みです。

ローカル受入は初回GitHub Pages deploy・公開URL確認を含みません。Pages設定の確認、mainへのmerge、
手動workflow実行と公開site-manifestの照合が残っています。日次公開は未接続です。
手順と権限は[Pages公開手順](pages.md)を参照してください。
