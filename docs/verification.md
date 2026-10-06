# 現在の検証範囲と受入基準

現在の要求は[仕様書](specification.md)と[ADR-0001](adr/0001-generated-content-module-and-pages.md)を正本とします。
日次の作業記録・run別の件数・旧受入手順は[履歴](archive/README.md)へ整理しました。
この文書は現在の実装状態と完了の判定基準を示します。

## 現在の状態

Pages実装の基点はmain `c1fc0b2a24277ecc651593d313b4bc669be148cf`（PR #103取込後）です。
PR #103のChecks run `37429603386`が成功し、実Chromiumを含む全234テストと実contentのWeb受入が通っています。
架空Note 3件の実Chromium受入で検索、全ローカルリンク、元Markdown hash、375/768/1024/1440px、
AI/打切り表示、外部resource要求0を確認しています。手順・依存の未解消制約は[Web preview](web-preview.md)にあります。
実GCSからのexportと初回Git配布は受入済みです。117件のPages初回deployと公開URLのhash照合も受入済みです。

| 領域 | 実装/検証 | 未完了 |
|---|---|---|
| standard収集 | Phase 1本番受入済み。既存日次workflow稼働 | F4/F5/F6はoffline修正検証済み。invoice照合 |
| Batch | submit/復旧/安全な診断、固定SDKのoffline検証済み | 成功結果を実Noteへ保存しaudit/costで照合する本番受入 |
| 互換sync | PR #98取込済み。既存Note・候補・同時作成の保護を一時Vaultで検証 | Windows/NTFS、利用者環境。新しい標準経路の受入とは別 |
| browser/抽出/フィルタ/lifecycle | 実装とfixture検証済み | 必要なbrowser sourceの実受入。raw retention未設定は適用不要 |
| 共通公開snapshot | export/manifest実装、43件のoffline検証。実GCS117件のexport受入 | 通常scheduleの連続実行受入 |
| Git配布 | bare出版/再実行/競合等15テスト、初回117件公開。一時submoduleの固定/明示更新を検証 | 利用者の実Vault・プラグイン・NTFSは対象外/未検証 |
| Web/Pages | Quartz 5.0.0の公開境界24テストと架空/実Noteのbrowser検証。同じ配布commitからbuild | 通常scheduleの連続実行と切戻しの実運用受入 |

PagesのSourceはGitHub Actions、`github-pages` environmentのdeploy対象はmainです。
[初回deploy run](https://github.com/Ningensei848/kaname/actions/runs/37430216275)のbuild/deployが成功し、
[公開URL](https://ningensei848.github.io/kaname/)から全117件の元Markdownを取得してhashを照合しました。
収集成功、Git配布、Pages初回公開は確認済みです。日次公開pipelineを接続し、
F4/F5/F6と公開競合・通知の回帰を含む全264テストをクラウドで確認しました。
公開専用run `37434000683`で既存WIFのaudit/export、Git更新、Pages build/deployが成功。
最新成功版117件の公開manifest bytesと全元Markdown hashをクラウドでも照合しました。
通常scheduleの初回連続実行は未確認です。[日次公開手順](daily-publication.md)にcommit/digestを記録しています。

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
| F3: browser redirect先の事後検査 | 修正・HTTP/実Chromiumで検証 | resource/robotsの各hopを通信前に判定。未許可hostへの要求0 |
| F4: 部分欠落usageを完全扱い | 修正・offline検証済み | 既知countを保持し、不明な課金countをpartialとして表示 |
| F5: receipt後の中断で費用欠落 | 修正・障害注入検証済み | 再課金0・usage欠落0・費用重複0、日/月と単価履歴を保持 |
| F6: 未検証sourceのstreakリセット | 修正・offline検証済み | 実際の復旧だけでresetし、未処理sourceは維持 |
| F7: 文書と実装の不整合 | 今回の改訂で状態/schema/通知の説明を更新 | 現行文書と実装・受入状態を照合し、履歴はarchiveへ分離 |

元のfile/line、条件、影響、再現、最小修正案は[全体レビュー](archive/2026-10/project-review-2026-10-04.md)に保存しました。
[レビュー再現ケース](archive/2026-10/review-reproductions-2026-10-04.py)は未修正指摘を実証する手動用で、
通常のpassing test suiteとは別です。F4/F5/F6の修正後の検証は現行test suiteを使います。
audit失敗はstage別Issue通知の対象です。

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

初回GitHub Pages deploy・公開URL確認はrun `37430216275`で完了しました。
配布commitは上記117件の初回版、artifact digestは`165b9d3aff24fec0a95ff3acfe71edfcf6ed5584ba6b25746acb3b99b388f7a8`です。
公開site-manifestのcommit/dataset/artifact digest/fixture判定と、トップ/版表示/manifest/全元Markdown/代表Note HTMLのhashを照合しています。
日次公開の受入状態は[日次公開手順](daily-publication.md)で管理します。実切戻しは未検証です。
追加の公開URLブラウザ検査は、クラウドのsystem Chromiumがproxyの証明書を信頼せず`ERR_CERT_AUTHORITY_INVALID`となり未完了です。
TLS検証は無効化していません。同一artifactのブラウザ検証はCIで成功し、公開URLのHTTPS/hash照合はrunnerとクラウドの標準HTTPクライアントで成功しています。
手順と権限は[Pages公開手順](pages.md)を参照してください。

## Browser redirect policyの修正

HTTP Fetcherに呼出しごとのhost制限を追加し、初回document・resource・robots.txtのredirect先をDNS/HTTP通信前に検査します。
許可したCDNへのredirectも転送先のrobotsを検査します。実Chromiumとmock transportで許可外hostへの要求0を確認。
通常HTTP sourceのredirect契約は維持し、本番browser sourceの追加有効化は行いません。

F3修正後のクラウド検証は全270テスト成功（実Chromiumを含む）。依存manifest/lockと本番source設定は変更なし。
