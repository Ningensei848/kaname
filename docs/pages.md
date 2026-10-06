# 固定した公開Note版をGitHub Pagesへ配信する

`pages.yml`は`content`の固定commitからbuildし、検証済みの公開artifactだけをGitHub Pagesへ渡します。
実装・ローカル検証・GitHub上の初回deployと公開URLの受入を完了しました。
公開URL: [kaname](https://ningensei848.github.io/kaname/)。[初回deploy run](https://github.com/Ningensei848/kaname/actions/runs/37430216275)が成功しています。
日次収集への接続はまだ行いません。

## 権限と設定

Repository Settings → Pages → Build and deploymentのSourceを **GitHub Actions** にします。
URLはQuartzの固定設定と同じ`https://ningensei848.github.io/kaname/`を使います。
custom domainや別base pathはこのworkflowの対象外で、設定が一致しなければdeploy前に停止します。
`github-pages` environmentの保護規則があれば、それに従ってdeployを承認します。
workflowはPagesを自動有効化せず、GCP/WIF、Gemini Secret、GCS IAMを変更しません。

| job | 権限 | 入力/出力 |
|---|---|---|
| build | `contents: read`, `pages: read` | 固定Git snapshot → 検証済み公開artifact |
| deploy | `contents: read`, `pages: write`, `id-token: write` | Pages専用artifact → Pages URL |

build/deployは`main`からの手動実行またはreusable workflow呼出しだけを許します。
PRのChecksでは実`content`からbuild・ブラウザ検証を行いますが、deploy権限を持ちません。
site buildにGCS/Gemini認証や収集writer権限を渡しません。

## 初回公開と再実行

workflowを含むPRをmainへmergeした後、Actions → **Publish Notes to Pages** → Run workflowを使います。
`content_commit`が空なら実行時に取得した`content`のtipを固定します。
明示指定は40桁の小文字SHAで、取得した`content`履歴の祖先commitに限ります。
入力値をshellコードへ直接展開せず、ref名、別branch、未配布commitを拒否します。

```bash
gh workflow run pages.yml --ref main \
  -f content_commit=62ed7f08ec786e1067cc6eecd9bece5e078b8c5c
```

buildはcheckoutのHEAD/clean状態（ignored/untrackedも含む）、Git treeのfile名/mode、
README/attributes、manifest/Note hash、各Git blobと元bytesを照合します。
`build_pages.py`はsealed artifactの`fixture: false`、配布commit、dataset digest、全元Markdownを再照合し、
manifestに許可された公開fileだけをupload用ディレクトリへ配置します。`.git`やrepo rootをuploadしません。
`check_pages.py`は全HTMLのローカルリンク・全Noteの出典、検索からNoteへの移動、元Markdown取得、
375/768/1024/1440px表示、版/digest表示、外部resource要求0、私的pathの404を検査します。

buildのsummaryにcommit/dataset digest/artifact digest/Note数を記録します。
`upload-pages-artifact`と`deploy-pages`はGitHub公式Actionを使います。
deploy後は公開`site-manifest.json`の配布commit/dataset/artifact digestとfixture判定を取得し、
トップ/版表示/manifest/全元Markdown/代表Note HTMLの配信bytesをhashで照合します。CDN反映を最大12回確認します。
Pages APIでのdeploy成功と公開版確認は別のstepです。確認失敗は成功扱いにしません。

途中build/検証失敗ではdeploy jobへ進まず、前の成功サイトを保持します。
Pages障害時は同じcommitを指定してこのworkflowを再実行します。GCS更新、記事取得、LLM呼出しはありません。
切戻しも過去の`content_commit`を指定するだけで、Git配布履歴やGCS/indexは巻き戻しません。
公開workflowは`kaname-pages`で直列化し、進行中のdeployをキャンセルしません。

## ローカル受入

Python 3.12、Node 24/npm 11、固定Python/npm lock、Playwright/Chromiumが必要です。
rootでPython依存を導入し、`web/`で`npm ci --ignore-scripts && npm run setup`を実行します。
別の作業用ディレクトリへ`content`をcloneし、commitを固定します。人力Vaultを使用しません。

```bash
# CONTENT_CHECKOUTはcleanなcontentのcheckout。CONTENT_COMMITはそのHEAD。
cd web
python build_pages.py --content "$CONTENT_CHECKOUT" \
  --content-commit "$CONTENT_COMMIT" --output .cache/pages-artifact
python check_pages.py --content "$CONTENT_CHECKOUT" \
  --content-commit "$CONTENT_COMMIT" --artifact .cache/pages-artifact
```

upload先は新しいディレクトリにします。同一artifactの再実行は`unchanged`、別版や編集済み出力は拒否します。
別版の検証には新しい`--output`を指定してください。成功版や処理中lockを自動削除しません。
初回Git配布commit `62ed7f08ec786e1067cc6eecd9bece5e078b8c5c`の117件で、元Note bytes/検索/リンク/画面幅を検証済みです。
初回deployでは公開URLの配布commit/dataset/artifact digest、トップ/版表示/manifest/全117件の元Markdown/代表Note HTMLのhashを照合しました。
配布commitは上記初回版、dataset digestは`d0734d9c3ffa8e23b070692d790ea9c5be09b8b46d5d166a59fdd59853f91e8c`です。
継続更新や切戻しの実運用受入は、初回公開とは別です。

## 次の工程：日次公開

初回Pages受入は完了しました。F4/F5（usage部分欠落・中断後の費用復旧）の修正を済ませてから接続します。
既存`daily.yml`のWIF条件を保ったまま、収集成功/audit成功後だけ読取りexportを行い、
独立したGit配布jobで`content`への通常non-force pushとremote照合を実行する計画です。
GITHUB_TOKENでのcontent pushが別workflowを自動起動するとは想定せず、
今回のreusable `pages.yml`に検証済みcommitを明示的に渡します。
収集/配布/deployのconcurrencyとIssue通知を分離し、更新なし、収集失敗、公開失敗を区別します。
現時点の公開障害はActionsの失敗状態/summaryで確認します。日次Issue通知への連携は未実装です。
