# ADR-0001: LLM生成Noteを独立した公開モジュールとして配布する

- 状態: 採用
- 決定日: 2026-10-04（JST）
- 起点: ユーザーの新要求。git submoduleを基本とし、同じ公開Note群をVaultとPagesで参照する選択を確認済み
- 実装状態: 収集基盤・互換sync・公開snapshot export・Git配布・Web buildは実装済み。117件のGit初回公開を受入。同じ配布版の117件をPagesへ初回公開し、公開URLの元Markdown hashを照合済み。日次公開は未接続

## 背景

従来は、非公開GCSのNoteを人のObsidian Vaultへコピーし、ローカル編集を保護しながら同期する構成でした。
公開SSGはそのVault同期の後に扱う別課題で、旧Phase 2/3の順序に従う計画でした。

新要求では、人力で組み立てる本体Vaultと、日々変わるLLM生成リソースを分けます。
kanameは本体Vaultに対してsubmoduleとして参照でき、同時に独立したGitHub Pagesとして読める必要があります。
ユーザーはLLMが集めたNoteの公開を許容し、人力Vaultの公開範囲は別リポジトリで決めると明示しました。
この要求を従来のコピー同期・非公開要約だけの構想より優先します。

## 決定

1. **kanameの公開生成Noteを独立したGitの版として配布する。**
   同じ`Ningensei848/kaname`内の配布専用`content`branchを標準とします。
   `main`はコード・設定・現行文書を持ち、`content`は公開Noteと配布manifestを持ちます。
   別の人力Vaultリポジトリは本セッションで作成・設定・変更しません。
2. **その同じ公開Note snapshotをgit submoduleとGitHub Pagesの入力にする。**
   Vault向けとWeb向けに独立した要約を生成せず、同じNote識別子・内容hashを共有します。
   利用側はsubmoduleのcommitを固定でき、Pagesは新しい成功公開版へ進めます。
   両者が常に同時更新とは限りませんが、同じ版を指定すれば同じNoteを参照できます。
3. **LLM生成領域と人力領域の編集責任を分ける。**
   kanameが更新するのは自らの配布成果物だけです。人の注釈・構成・リンクは利用側で保持します。
   利用側のdirtyなsubmoduleや未管理ファイルを強制更新・削除しません。
   コミュニティプラグインの選択・設定・公開対象の選定は利用側の責務です。
4. **公開対象は有効なcompact生成Note群とする。**
   原則として成功Noteを全件配布し、Webだけの個別選別を標準にしません。
   原文、raw HTML、state、receipt、run report、認証情報、人力Vaultを公開snapshotへ入れません。
   GCSは非公開の収集・復旧元のまま維持し、bucketを公開する方式は採用しません。
5. **既存の収集と公開を分ける。**
   exportとPages buildは保存済みNoteを使い、LLM再生成・記事再取得・GCS更新を行いません。
   失敗した収集や不完全なexportで成功公開版を上書きしません。
   実Batch受入や人力Vaultの準備は、standardの成功Noteを使うPages着手の前提にしません。

## 旧仕様からの変更

| 従来 | 新しい標準 |
|---|---|
| 人力Vaultへのコピー同期が主な閲覧経路 | 公開生成NoteのGit履歴を配布し、利用側がsubmoduleで参照 |
| 要約は非公開GCSで利用 | GCS運用状態は非公開、生成NoteはGit/Pagesで公開 |
| Quartz公開はVault同期後の別課題 | 同じ配布snapshotから独立したPagesを作り、人力Vaultに依存しない |
| Phase 2完了後にだけ後続機能へ着手 | 新しい配布・Web工程を優先し、既存の品質/復旧課題は別の受入軸で継続 |

`techkb sync --vault`とPR #98の編集保護は互換経路として残します。
生成モジュールの自動更新に候補の手動統合を要求する旧sync方式は使いません。
互換syncをsubmodule checkoutへ向けず、標準Git更新も利用側の変更があれば停止する契約にします。
既存CLI、日次収集、GCS IAM/lifecycle、heartbeatはこのADR改訂で変更しません。

## 結果と留意点

本体Vaultの人力編集をkanameの生成更新から切り離し、独立したWeb参照も提供できます。
生成Noteの版と引用元を追跡し、利用側は取り込む時期を選べます。
配布branch、export manifest、安定Note識別子、Pages build/deployが新たな責務です。
Git配布とWeb buildの受入状態は[検証・受入](../verification.md)で管理し、日次の作業履歴をADRへ追加しません。
公開履歴に載せた情報は、現在版から取り下げてもGit履歴から消えた保証にはなりません。
公開するのは生成要約であり、元記事の権利がkanameへ移ることを意味しません。

## 比較した案

- 既存Vaultへのコピーを主経路にする案: 編集責任が混ざり、独立した配布版を固定しにくいため互換用途へ限定。
- 人力Vault全体からPagesを作る案: 人力Vaultの公開判断・構成に依存するため採用しない。
- 別の生成データrepoを作る案: 将来の容量・アクセス制御で必要になれば再検討。まず本repoの専用branchで履歴を分離。
- GCS bucketを匿名公開する案: 運用状態との境界を持てないため採用しない。

## 検証と参照

同じsnapshot digest/Note hashを使うこと、submoduleが通常のGitとして版を固定できること、
Pagesがそのsnapshotだけから再構築できることを受入条件とします。
具体的な契約と工程は[仕様書](../specification.md)、[公開・配布](../publication.md)、[実装計画](../implementation-plan.md)へ記載します。

- [Gitのsubmoduleモデル](https://git-scm.com/docs/gitsubmodules): 独立した履歴を持つrepoを親から特定commitで参照する
- [GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages): 静的サイトの配信先
- [Pagesのcustom workflow](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages): build成果物とdeployの分離
