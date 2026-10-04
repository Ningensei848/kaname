# 公開NoteのGit配布とPages

この文書は[ADR-0001](adr/0001-generated-content-module-and-pages.md)を実装するための配布契約です。
`techkb export-notes`で公開snapshotを作れます。実GCSのexport受入、配布branch、Pages pipelineは未完了です。

## exportの操作と実装範囲

```bash
# ローカルの読取りsnapshot。出力は入力snapshotの外、新しいディレクトリへ
python -m techkb export-notes --state-dir /path/to/state-snapshot --output /path/to/public-snapshot

# GCSの既存成功Noteを読む。ADC/WIFを使用し、GEMINI_API_KEYは不要
python -m techkb export-notes --output /path/to/public-snapshot
```

HTTP記事取得、Gemini、GCS書込み、Vault操作、Git push、Pages deployは行いません。
成功indexからだけ選択し、pending、失敗row、未登録receipt、raw、run reportを入力Noteにしません。
全成功rowのNote/receiptが一致することを確かめ、選ばれた公開版は現行compact構造とfrontmatterの許可fieldで検査します。
元のNote bytesを保持し、IDや配布情報はmanifestへ書きます。
既存の12列indexと、thinking/truncation列を持つ現行indexを読み取れます。

exportはLinux/POSIXのdirectory fd、hard link、fsyncを使用します。配布MarkdownはOSに依存しません。
出力親ディレクトリは先に用意し、出力先自体は新しい名前を指定します。
全ファイルを一時領域に完成させ、上書きなしで配置し、最後に`manifest.json`を完了印として確定します。
同じ全ファイルを持つ出力への再実行は`unchanged: true`で、内容・mtimeを変更しません。
空ディレクトリ、編集済み出力、余計なファイル、symlink、入力snapshot内への出力は拒否します。
途中失敗でmanifestのない出力が残ったら、そのまま公開せず、新しい出力先で再実行します。自動削除しません。

GCSでは読取った世代とbytes、ローカルではbytesを再照合し、indexの増減も検査します。
変化を検出した試行は`snapshot_changed`で失敗します。収集/metadata更新が終わってから明示再実行してください。
この照合はGCSの複数object transactionや、ローカルファイルの外部変更を封じるlockを提供しません。
公開直前のartifact検証は後続のGit/Pages工程でも必要です。

安全な診断は固定codeのみで、タイトル・URL・Note本文・例外本文を出しません。
未知frontmatter、余分な本文section、危険なMarkdown/HTML、既知のAPI key/token/署名URL/private keyパターンを拒否します。
任意の秘密文字列の完全検出や、要約が記事と意味的に同一でないことの証明は行いません。

取り下げはmanifestの安定IDを指定します。未知IDや不正IDは拒否し、そのIDの全版を配布候補から外します。
除外理由は運用側に記録し、公開manifestへ運用台帳を持ち込まないようにします。

```bash
python -m techkb export-notes --state-dir /path/to/state-snapshot \
  --output /path/to/withdrawn-snapshot --exclude-note-id "$NOTE_ID"
```

## 配布snapshot

`Ningensei848/kaname`の`content`branchを、独立した生成Noteの履歴として使います。
利用側はこのbranchのcommitをgit submoduleで参照します。コード側の更新はそのまま配布更新にしません。

```text
content branch（予定）
  README.md                     # 生成Noteの利用方法・AI生成の表示
  manifest.json                 # schema version、dataset digest、Note ID/hash/path
  notes/<note-id>.md             # ObsidianとWebが共有する公開Note
```

全成功Noteを基本とし、同一source/canonical URLの複数成功版は最新の成功版を選びます。
初回配布以降の過去版は配布Git履歴で参照可能にします。初回配布前のGCS履歴を全版importすることは必須にしません。取り下げNoteは次snapshotから外し、除外理由を運用側で記録します。
現在のsnapshotからの除外だけでGit履歴から消去したとは扱いません。

Note IDはsource IDと正規化canonical URLから安定して決めます。
IDは`[source_id, canonical_url]`をUTF-8/非ASCII維持/空白なしのJSONにしたSHA-256（64桁hex）です。
URLの正規化は既存の`normalize_url`と設定のtracking parametersを使い、意味のあるqueryの順序は保持します。
最新版はUTC換算の`processed_at`が大きい版、同時刻なら`content_sha256`の辞書順で大きい版です。
衝突/不整合は停止します。title・metadata・入力の並び順でIDを変更しません。
manifestのNote hashは公開Markdown bytesのSHA-256、dataset digestは整列したNote ID/hash集合から計算します。
manifest schema versionは1、Note一覧はID順です。digestの入力は`[[id, sha256], ...]`を
`ensure_ascii=False, sort_keys=True, indent=2`でJSON化して末尾改行を付けたUTF-8 bytesです。
各Note entryにはID/path/hash/source ID/canonical URL/title/category/processed_at/published/truncationを持ちます。
dataset digestはNote集合の照合用で、manifest全体やGit commitのhashではありません。
入力本文hash・Note hash・Git commitを混同しません。manifest自身へそのGit commitを書き込む循環も作りません。
export時の壁時計だけでdataset digestやNoteを変更しません。

exportは成功indexと対応Note/receiptの整合性を確認し、公開対象のNoteだけを新しいstagingへ書きます。
GCSの世代と読取り状態を照合し、収集中の変化があれば混在版を公開せず再試行します。
manifestに列挙したファイル以外の混入、秘密、原文セクション、危険な埋込みを検査します。
GCSのbucket名・世代記録・運用台帳を公開manifestの内容にしません。
stagingの完全なsnapshotだけをcommitし、現在の配布版を途中生成物へ進めません。

## submodule向け契約

通常のGit cloneと特定commitのcheckoutでNote/manifestを利用できることを条件にします。
Git履歴に依存しない再配布archiveを作る場合も、同じdataset digestを含めます。
本体Vaultのrepo名・path・プラグインはここで指定しません。
利用側がGit/submodule対応のプラグインを選ぶ際に、manifestと生成領域の境界を説明できる資料を提供します。
プラグインがsubmoduleを扱えることは利用側で確認します。

利用側の親repoは特定commitを保持でき、公開側が更新されても勝手に追従させません。
検証では一時的な親repoで参照の固定/明示更新を確認し、実際の人力Vaultには操作しません。
dirtyな生成領域や未管理ファイルを強制削除しないことを、利用側の更新方法を選ぶ条件にします。
kanameは第三者プラグインの動作を保証せず、選択した更新方法の編集保護は利用側で確認します。
互換`techkb sync --vault`はsubmodule checkoutへ実行せず、Git配布とコピー同期を重ねません。

## Pages向け契約

同じ`content`commitを固定入力として、`main`側の固定SSG設定でHTMLをbuildします。
Quartzを第一候補とし、[Markdown/Obsidian機能](https://quartz.jzhao.xyz/)と
[Pages配信](https://quartz.jzhao.xyz/hosting#github-pages)をfixtureで確認してからversionとpluginを固定します。
想定するproject Pagesのbase pathは`/kaname/`です。現在そのURLでの提供は確認できていません。

初期の閲覧要件は一覧、日付/source/category、検索、Note本文、出典、AI生成/入力打切り表示です。
Note IDに基づく安定URLと内部リンクを使い、未存在の関連概念へ架空のNoteリンクを作りません。
Pages上に配布commit/dataset digestを表示し、同じ版のMarkdownを追跡できるようにします。
公開前のpreviewとlink検査はsynthetic fixtureから開始します。

SSGはmanifestが許可したNote群だけを入力とし、人力Vault、repo root、archive、state、receiptを探索しません。
buildはGCS/LLMの認証情報を受け取らず、GCS読取りはexport工程へ限定します。
配信artifactは生成HTML/CSS/JS等だけを含み、Git管理領域やリンクされた運用データを混ぜません。
[GitHub公式のcustom workflow](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)
に従い、build/artifact/deployを分け、失敗したbuildでは前の成功サイトを維持します。

## workflowと復旧

既存WIFはmainの`daily.yml`に限定されています。新しいexportを別workflowへ移しただけでは利用できません。
まず既存の認証済み読取り経路でsnapshotを作る構成を検討し、権限拡張を前提にしません。
Git配布への書込み権限とPages deploy権限は、その工程にだけ限定して実装PRで示します。
site buildへのGemini Secret継承や収集writer権限の追加は不要です。

収集成功、export成功、Git配布成功、Pages deploy成功は別の状態として記録します。
deployが失敗しても同じ配布commitから再buildでき、LLMを再呼出ししません。
生成領域の削除/取り下げは完全snapshotの差分として扱い、人力Vaultのファイルは触りません。
公開版を切り戻す場合は過去の配布commitを指定し、元のGCS/indexを巻き戻しません。
