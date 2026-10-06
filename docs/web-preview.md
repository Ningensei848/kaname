# 公開NoteのWeb preview

工程2の静的buildです。CIは架空Note 3件で画面を検証します。
実GCSのexportと`content`branch配布、同じ配布commitの117件からのローカルWeb受入も完了しています。
GitHub Pagesのdeploy、日次公開は別工程で未受入です。人力Vaultは入力にしません。

## ローカルで確認する

Python 3.12のvenvを有効にし、rootで既存の`requirements.lock`と`requirements-browser.lock`を導入します。
Web用runtimeはNode 24 / npm 11です。Python本体・配布処理の依存lockは変更しません。

```bash
cd web
npm ci --ignore-scripts
npm run setup
python3 make_fixture.py
python3 build.py
python3 serve.py
# http://127.0.0.1:8765/kaname/
```

previewはloopbackだけで提供します。架空データには全ページでpreview表示と`noindex,nofollow`を付けます。
Note一覧、出典別・カテゴリ別・日付順、日本語検索、Note本文、出典リンク、AI生成/打切り表示を確認できます。
一覧・日付順は収集日時（UTC）の降順です。記事自体の公開日はNoteの出典情報に保持します。
既存のNoteタイトルに一意に対応する検索キーワードだけを内部リンクにし、未存在/同名の概念は文字で表示します。
本番のコンテンツや原文をfixtureと混同しません。

```bash
python3 -m playwright install chromium
python3 check_preview.py --screenshots /tmp/kaname-web-preview
npm run audit
```

ブラウザ検証はfixture専用です。desktop/mobileの幅、検索結果からの移動、全ローカルリンク、
Note本文・出典・打切り表示、元Markdownのhash、外部resource要求0を検証します。
SSGのHTML/検索index/CSS/JS/日本語フォントは同じartifactから配信します。CDN、analytics、コメント、
外部embed、動的OG生成は使いません。CSPで外部resource接続とframe/objectを制限します。
`/kaname/`用のbody属性を補い、Quartz v5.0.0とcommunity searchのbase pathの差を吸収します。

## 保存済み公開snapshotを入力にする

```bash
python3 build.py --snapshot /path/to/exported-public-snapshot
# 配布commitが確定した後だけ指定する。指定値のGit由来は後続の出版工程が保証する。
python3 build.py --snapshot /path/to/content-checkout --content-commit FULL_40_HEX
```

入力はexportの`manifest.json`と列挙された`notes/<id>.md`です。READMEとGit管理領域は探索・表示しません。
配布checkoutの固定`.gitattributes`だけは内容を検査し、SSG入力にはしません。
Note ID/hash、metadata、compact形式、整列順、dataset digest、余計なNote/運用ファイル、symlinkを再検査します。
Note bytesを捕捉してから表示用Markdownを作り、元Markdownは`markdown/notes/<id>.md`へ同じbytesで格納します。
各Noteから元Markdownへ移動でき、Note hashと「この公開版について」のdataset digestで照合できます。
commitの指定は表示用の値です。build単独では配布branchのcheckoutとの一致を証明しません。
[Git配布手順](git-distribution.md)に従い出版/deploy側で照合します。初回受入は実checkoutのHEADと指定値を照合済みです。
旧形式の打切りNoteに上限値・注意表示がない場合は、Webだけに上限未記録の注意を補います。元bytesは変更しません。

buildはcollection CLI、GCS、Gemini、Git pushを呼びません。Quartz子プロセスにAPI/GCS/GitHubの環境変数を継承せず、
pluginは固定済みのローカル配置だけを使います。OSの隔離sandboxを提供するわけではありません。
入力ディレクトリ全体をSSGへ渡さず、許可したNoteからの表示用ファイルと一覧ページだけを専用stagingへ渡します。
cache内の空の`.git` sentinelはglobが親repoのignoreを参照しないためのもので、checkoutではありません。

## artifactと失敗時の扱い

成功出力は`web/public/<artifact-digest>/`で、`site-manifest.json`を最後に配置します。
manifestには各配信fileのhash、artifact digest、dataset digest、fixture表示、指定commitを記録します。
digestはNote集合と静的artifactで別々です。入力Noteの壁時計更新は行いません。
HTMLは固定したSSG/plugin/fontで生成しますが、Quartz footerの年等を含むため、異なる環境・時点での
静的artifactの完全一致までは保証しません。元Note bytesとdataset digestの一致を基準にします。

途中失敗は新しい未完了出力にとどまり、以前の成功artifactと`last-build.json`の参照を維持します。
同一出力への再実行はhash一致なら`unchanged`、編集/追加/空出力や別版は拒否します。自動上書き/削除はしません。
入力snapshot内への出力も拒否します。途中失敗の未完了出力は再利用せず、別の新しい`--output`で再実行します。
buildとsetupの共有cacheはexclusive lockで競合を拒否します。強制終了後のlockは、プロセスが終了したことを
確認してから管理者が扱い、処理中のlockを盲目的に消しません。出力はLinux/POSIXのhard link/fsyncを使います。
cacheと出力は同一filesystemに置きます。既存出力やcacheを人が編集する領域として使いません。

preview serverは完了manifestと各hashを検証し、捕捉した配信bytesだけを提供します。
ファイルが後から増えても公開されません。非公開state、receipt、root文書、source mapは許可出力ではありません。
現在のChecksでは収集権限なしでfixtureだけをbuild/検証し、静的previewと画面をActions artifactへ保存します。
deploy workflow、production dispatch、Pages設定、WIF/IAMの変更はこの工程に含めません。

## 固定依存と残る制約

Quartz **5.0.0**、commit `ab346fa66a895e12d63a308e70ce330ba795822a`の公式source archiveを使用します。
`web/package-lock.json`が全npm依存とarchiveのintegrityを固定します。
`web/quartz.lock.json`はkaname独自のengine/plugin一覧・version・取得URL・integrity照合用です。
Quartz公式のGit plugin lock形式ではありません。公式の自動plugin install/updateをbuildで使用しません。
日本語フォントは`@fontsource/noto-sans-jp` 5.3.0（OFL）をローカル配信し、ライセンスも同梱します。
Quartz/pluginと主要frontend runtimeのライセンスは`static/licenses/`へ同梱します。

監査で見つかったxmldom/sharp/toml/KaTeXは、`overrides`で修正版を固定して実buildを検証しています。
一方、[bracesの深いglobによるstack exhaustion](https://github.com/advisories/GHSA-vfj7-8cjw-p6xm)には、
確認時点で公開npm最新版3.0.3にも警告が残ります。braces→micromatch→fast-glob→globbyの4件のhigh表示は
この1 advisoryの伝播です。解消済み/警告0とは扱いません。
ここではSSGが使うglobは固定文字列で、ignorePatternsは空、入力filenameは生成したID/slugのみです。
Note本文・frontmatterからglobを渡す経路を追加しません。Node buildに180秒のtimeoutを設けています。
`sprintf-js`にも[精度指定によるDoS](https://github.com/advisories/GHSA-hp3w-g68c-fv3c)の警告があり、確認時点の公開最新版1.1.3にも修正がありません。
依存経路はQuartz → gray-matter → js-yaml 3.15.2 → argparse 1.0.10 → sprintf-js 1.0.3です。
js-yamlのライブラリ入口はargparseを読み込まず、argparseを使うのは`bin/js-yaml.js`のCLIだけです。
このビルドはgray-matterから`safeLoad`を呼び、YAML CLIやsprintfのformat指定にNote本文を渡しません。
この固定version・配置の警告だけを既知の制約として許可します。YAML CLIの利用や依存経路の変更時には再レビューが必要です。
KaTeXは修正版0.18.2に固定します。`node --test audit.test.mjs`で未知の警告・配置/version変更を拒否することを検証します。
`npm run audit`は上記2 advisoryだけを既知の制約として許し、別の警告・audit取得失敗をCIで失敗にします。
glob/ignore設定の拡張や依存更新時には、この到達性判断を見直し、修正版が出たら更新してください。
