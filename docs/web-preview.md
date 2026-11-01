# 公開NoteのWeb preview

公開snapshotからの静的buildです。fixtureと実Git/Release入力をCIで検証し、Pages通常公開/切戻しまで受入済みです。
入力は生成Note群で、人力Vaultは使用しません。過去の初回受入値は[archive索引](archive/README.md)、現在の保証は[検証基準](verification.md)を参照してください。

## ローカルで確認する

Python 3.12のvenvを有効にし、rootで既存の`requirements.lock`と`requirements-browser.lock`を導入します。
Web用runtimeはNode 24 / npm 11です。Python本体・配布処理の依存lockは変更しません。

```bash
cd web
npm ci --ignore-scripts
npm run setup
npm run fixture
npm run build
npm run preview
# http://127.0.0.1:8765/kaname/
```

previewはloopbackだけで提供します。架空データには全ページでpreview表示と`noindex,nofollow`を付けます。
Note一覧、出典別・カテゴリ別・日付順、日本語検索、Note本文、出典リンク、AI生成/打切り表示を確認できます。
一覧・日付順は収集日時（UTC）の降順です。記事自体の公開日はNoteの出典情報に保持します。
トップ・日付順・出典/カテゴリ別の各一覧は24件ずつの静的ページです。トップの続きは `page/2`、他の一覧の続きはそのURLの `page/2` から参照でき、前後・ページ番号の通常リンクで移動します。ページの直接参照とJS無効時の移動も検証します。
初期のloadイベント後のidle時に、同じサイトの次ページHTMLだけを低優先度で先読みします。節約設定・2G/slow-2Gでは行わず、先読み先からさらにページを連鎖取得しません。
検索indexの取得とQuartz検索の初期化は、検索ボタンまたはCtrl/Cmd+Kを初めて使った時だけです。日本語tokenizer・順位付け・プレビュー・キーボード操作は固定したQuartz実装を使い、取得失敗時は再試行できます。
タグはWeb投影時にNFKC・小文字・空白のハイフン化と明示辞書で統一します。`#ai-egent` / `#ai-agent` / `#AIエージェント`、LLM/大規模言語モデル、RAG/検索拡張生成を同じタグで探せます。`#`で指定した別名は正規タグへ変換して入力欄にも表示します。通常の文章検索は書き換えず、タグを含む絞込みもQuartzへ渡します。C/C++/C#、RAG/GraphRAG、階層タグとハイフンタグは区別します。元Markdown・Note ID・dataset digestとWikiLink解決規則は変更しません。
検索キーワード/本文のWikiLinkは一意の公開Noteタイトルへ内部リンクし、未存在/同名ならGoogle検索へつなぎます。[検索リンク仕様](ns1-search-fallback.md)を参照してください。
本番のコンテンツや原文をfixtureと混同しません。

```bash
python3 -m playwright install chromium
npm run check:preview -- --screenshots /tmp/kaname-web-preview
npm run audit
```

ブラウザ検証はfixture専用です。desktop/mobileの幅、検索結果からの移動、全ローカルリンク、
Note本文・出典・打切り表示、元Markdownのhash、許可していない外部resource要求0を検証します。
画像付きNoteでは、公開Noteにある画像URLのレスポンスだけを検証内で代用して実Chromiumの表示を確認します。
検証は出典サイトへ画像を取得しに行きません。本番閲覧では当該Noteの画像hostへの画像通信が発生します。
SSGのHTML/検索index/CSS/JS/日本語フォントは同じartifactから配信します。CDN、analytics、コメント、
外部embed、動的OG生成は使いません。CSPで外部resource接続とframe/objectを制限します。
`/kaname/`用のbody属性を補い、Quartz v5.0.0とcommunity searchのbase pathの差を吸収します。

既存fixtureの内容が異なって`output_conflict`になった場合は、既存出力を保持して新しい名前を選びます。

```bash
npm run fixture -- --output .cache/fixture-new
npm run build -- --snapshot .cache/fixture-new --fixture
npm run check:preview -- --screenshots .cache/fixture-new-screenshots
```

`--fixture`は指定したsynthetic snapshotをpreviewとして表示し、Pages用の公開検査では拒否されます。
`audit`は依存脆弱性監査、`check:preview`/`check:pages`はリンク・画面・画像・版の受入です。
HTML後処理と成果物検証は`kaname_web`が担当します。
既定fixtureは27 Noteで、ページ境界とタグ別名検索を含みます。以前の3 Note fixtureは保持し、新規の `--output` を指定して作り直してください。
新規生成Noteでも、タグの安全な文字への置換前に同じ辞書を適用します。C++は `c-plus-plus`、C#は `c-sharp` としてCと区別します。旧処理ですでに記号を失ったタグの意味は推測して補完しません。

## 保存済み公開snapshotを入力にする

```bash
npm run build -- --snapshot /path/to/exported-public-snapshot
# 配布commitが確定した後だけ指定する。指定値のGit由来は後続の出版工程が保証する。
npm run build -- --snapshot /path/to/content-checkout --content-commit FULL_40_HEX
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
現在のChecksでは収集権限なしでfixtureと実contentのGit/Release両入力を検証し、静的previewと画面をActions artifactへ保存します。
Pages専用workflowとproduction dispatchの手順は[Pages手順](pages.md)に分離しています。
Checksでは実contentの公開前検証も行いますが、deploy権限は付けません。WIF/IAMは変更しません。

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

2026-10-16の再監査でもbraces3.0.3とsprintf-js1.1.3に修正版はなく、実lockの警告は上記2 advisoryの伝播9件でした。
既知例外は9 packageの固定version/単一node配置と親子の伝播辺を確認し、新version・新配置・新親・不完全な監査応答を拒否します。
既存の固定glob/生成filename・YAMLライブラリ経路の制約は維持します。

2026-10-21の実npm監査も既知2 advisoryだけで、公開最新版はbraces3.0.3/sprintf-js1.1.3でした。lockと例外は拡大せず、Nodeの監査/検索起動hook検査7件を通しています。

## 初期表示の反復計測

`python scripts/benchmark_frontend.py --before <旧artifact> --after <新artifact> --output <JSON>` は同じNote集合・content commitの検証済み成果物を比較します。375px、cold cache、150ms RTT、下り1.6Mbps、CPU 4倍制限のChromiumで各3回測定し、HTML/DOM/転送量・DCL/FCP/LCP/CLSを返します。次ページの先読み転送は初期転送と分けます。Lighthouse/PageSpeedや実利用者のCore Web Vitalsの測定とは区別してください。

2026-10-22、同じ311 Note・content `35356be99e8c687193b043c76ff77e4c136fb568` を変更前main `b5e540f` と変更後で比較しました。旧コードも別の一時ツリーから同じ固定npm依存でbuildしています。

| 指標 | 変更前 | 変更後 |
|---|---:|---:|
| トップHTML bytes | 524,274 | 50,352 |
| 表示後DOM要素 / Noteカード | 1,958 / 311 | 246 / 24 |
| 初期転送 bytes（各回同値） | 5,660,493 | 1,311,306 |
| LCP中央値（範囲）、秒 | 17.272（8.556–17.624） | 4.892（4.752–5.044） |
| DOMContentLoaded中央値、秒 | 38.993 | 4.916 |
| 初期の検索index要求 | 1 | 0 |

初期転送は76.8%、この条件のLCP中央値は71.7%減りました。変更後の次ページ先読み49,854 bytesは上表の初期転送から分けています。初回の検索操作ではindex取得・構築の待ち時間が発生し、準備中表示を出します。Ctrl/Cmd+KとCtrl/Cmd+Shift+Kの通常/タグ検索も、読み込み後に同じモードで開きます。測定したartifactは旧 `5e41db6d4e7cc64a25e6e62753b1ab7a75411b91d32fe260adb1c8fc8582922c`、新 `0e890be3e2546859d3d7b89a5109f46cb40c0d2c42e82835c2766c29bd1cf1fc` です。日次build/検査/deploy時間や本番CDNの速度保証へは拡張しません。
