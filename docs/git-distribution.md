# 公開NoteのGit配布と利用

公開先は同じrepositoryの`content`branchです。コード・設定・workflowは`main`に置き、
配布branchは`README.md`、固定`.gitattributes`、`manifest.json`、`notes/<id>.md`だけを保持します。
原文・state・receipt・pending・認証情報・人力Vaultは配布しません。

## 公開版を読む

[Note一覧](https://github.com/Ningensei848/kaname/tree/content/notes)からMarkdownを参照できます。
初回公開版はcommit `62ed7f08ec786e1067cc6eecd9bece5e078b8c5c`、117件です。
dataset digestは`d0734d9c3ffa8e23b070692d790ea9c5be09b8b46d5d166a59fdd59853f91e8c`です。
現在のbranchと固定した過去版は別です。固定版は[commitのtree](https://github.com/Ningensei848/kaname/tree/62ed7f08ec786e1067cc6eecd9bece5e078b8c5c/notes)で参照できます。

```bash
git clone --single-branch --branch content https://github.com/Ningensei848/kaname.git generated-notes
git -C generated-notes checkout --detach 62ed7f08ec786e1067cc6eecd9bece5e078b8c5c
```

固定`.gitattributes`はtext変換・filter・ident・working-tree-encodingを無効にし、
通常のclone/checkoutで元Noteのbytesを保持します。ローカルのattributes上書きや外部エディタの保存後は
manifestのSHA-256で再検査してください。NTFSと利用者のプラグインの実受入を完了したという意味ではありません。

## 出版処理

exportは[配布契約](publication.md)に従ってGCSまたは読取りsnapshotから作ります。
`publish-notes`は検証済みsnapshotを**ローカルのbare repository**へ出版します。
GCS/Gemini認証、記事取得、remote push、利用側のcheckoutやVaultの操作は行いません。

```bash
git init --bare --initial-branch=content /path/to/distribution.git
python -m techkb publish-notes \
  --public-snapshot /path/to/public-snapshot \
  --distribution-repo /path/to/distribution.git
```

返却値はNote件数、dataset digest、tree、commit、`unchanged`です。
callerのREADMEや`.git`は取り込まず、固定した公開README/attributesと検証済みmanifest/Noteだけをcommitします。
既存`content`があれば、公開snapshotとして再検証します。コードや余計なファイルを持つbranch、
symbolic ref、非bare repository、symlink、入出力pathの重なりは拒否します。
Git hooks、署名、環境変数によるGit設定の注入を使用せず、index/working treeを持ちません。

同じ全treeならcommitを増やしません。変更時は前のcommitをparentにし、最後のref更新だけを
旧commit指定のcompare-and-swapで行います。途中失敗や競合は前の公開版または競合勝者を保持します。
到達しないGit objectが残る場合はあります。履歴を捨てるforce pushや自動reset/cleanは提供しません。

remote公開は別操作です。既存remoteの`content`の有無とcommitを先に確認し、
更新時はその版をローカルbareへ通常のfetchで取り込んでから出版します。初回の「branchなし」と読取り失敗を混同しません。
公開対象のcommit/tree/digestを確認して、**`refs/heads/content`だけを通常のnon-force push**で進めます。
remote競合時は停止し、相手の版を検査してから再計画します。盲目的な再pushやforceは行いません。

```bash
# CONTENT_COMMITはpublish-notesが返した検証済み40桁commit
git --git-dir=/path/to/distribution.git push git@github.com:Ningensei848/kaname.git \
  "$CONTENT_COMMIT:refs/heads/content"
```

公開後にremoteのcommit、manifest、Note数/hashを照合します。Git公開とPages deployの成功は別に判定します。
取り下げは次snapshotからの除外です。既存Git履歴の抹消は行いません。

## submoduleの参照と編集保護

利用側は通常のgit submoduleとして`content`の特定commitを親repoへ記録できます。
生成側の新commitやfetchだけでは、親repoに記録した参照は更新されません。
次の版を受け入れるときだけ、利用者がcheckoutし、親repoのgitlinkをcommitします。
kanameは実際の人力Vaultのrepo/pathを参照・変更しません。

更新前には生成領域のtracked/untracked/**ignored**ファイルを含む状態を確認し、
人手の変更があれば停止して領域外へ保全する運用・プラグインを選びます。
`git status --porcelain --untracked-files=all --ignored`が空であることは、この確認の一部です。
通常のcheckoutは重なる変更を拒否しますが、重ならない変更は持ち越し、ignoredファイルを上書きし得ます。
Gitの拒否だけを「すべての編集を保護する」保証とは扱いません。
外部エディタとの共通lockもないため、更新中の編集禁止と選択したプラグインの動作確認が必要です。
force/reset/cleanやdirty状態での自動更新を採用せず、人手の注釈は生成領域の外へ置きます。

検証では一時親repoで参照固定、明示更新、重なるtracked/untracked編集のcheckout拒否を確認しています。
利用者のコミュニティプラグイン、実Vault、Windows/NTFSは未検証です。
互換`techkb sync --vault`はsubmoduleの更新に流用しません。

## Webとの同一性

Web buildはこのbranchの固定commitをcheckoutし、公開snapshotを再検証して入力にします。
`--content-commit`の指定だけではGit由来を証明できません。checkoutのHEADと指定値の一致、
tracked tree、manifest/Note hashを出版・deploy側で照合する必要があります。
初回版では実際のGit checkoutからbuildし、117件の元Markdownと配布版が同じbytesであることを確認しました。
Pages deploy workflowと公開前検証を実装しました。同じ117件の初回Pages公開と公開URLのhash照合は完了しました。日次自動公開を接続しました。[実行受入](daily-publication.md)を参照してください。[Pages手順](pages.md)を参照してください。[Web手順](web-preview.md)と[受入](verification.md)を参照してください。
