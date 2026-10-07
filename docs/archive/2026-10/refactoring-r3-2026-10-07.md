# R3: 公開Note検証・整合読取り・installの分離

Issue #112。基点mainは`20e49f0c52b08c27ea1e8907030cb6068fefb2c9`（R2 / PR #120取込後）。

## 変更と互換入口

- `_public_note.py`: frontmatter、秘密/埋込み、compact本文、旧打切り形式の限定的互換判定。
- `_publication_snapshot.py`: local snapshot読取り、index/Note/receipt整合、最新成功版の選択、世代/bytes/index一覧の再検査。
- `_snapshot_install.py`: 既存出力の一致判定と、排他的なsnapshot配置。
- `_publication_common.py`: 同じ例外型、固定コード、path検査、bytes/digest、配布用定数を共有。
- `publication.py`: 既存importの互換入口とexportの調整。出力先の事前検査→snapshot読取り→配置の順序を維持する。

既存17関数/クラスの本体は構文木比較で同一。
配置処理本体も、返却する`unchanged`の包装を互換入口へ移した点だけを正規化すると構文木が同一である。
indexの最終再検査、世代によるABA拒否、Note/receiptのbytes一致、dir fd/O_NOFOLLOW、
fsync、ディレクトリ差替えの検査、manifestを最後に配置する完了判定を維持する。
CLI/storage path/schema/Note ID/Pages URL、依存lock、workflow、権限に変更はない。

## 回帰検証

Python 3.12.13、既存固定依存、実Chromiumを使用。
通常sandbox起動制約のため、承認されたexec_command経路でローカル実行した。

| 時点 | 検証 | 結果 |
|---|---|---|
| 抽出前 | publication / distribution / remote_publication / site / pages | 104 passed（18.60s） |
| 抽出後 | 同じ対象suite | 104 passed（19.18s） |
| 抽出後 | 全Python回帰、実Chromiumを含む | 273 passed（35.90s） |
| 抽出後 | 基点mainとの19ケース比較 | 全Note/manifest bytes、dataset digest、例外型/コード、read/list順序一致。storage書込み0 |

19ケースは通常/打切り/旧compact/最新revisionの選択/withdrawal、unknown・不正exclusion、
Note/receipt欠落・不一致・不正JSON、原文追加・秘密pattern、空snapshot、重複header/hash、
世代/bytes変更、新index追加を含む。MemoryStoreと固定fixtureだけを使い、実GCSやLLMには接続しない。
既存の障害注入テストで配置中断、出力競合、symlink/FIFO、ディレクトリ差替え、
追加API/記事取得/GCS書込み0を確認した。テストの変更・追加は不要だった。

## 固定公開版のartifact受入

- 固定content commit: `e3ef457f3edab5b4ca90601c922cc3b415d288ab`、118 Notes。
- dataset digest: `22fe4c95ad6e3b25bcc24047ef6c9c4fb75eb30a1d730b1de2a3e0b2fa595898`。
- ローカルartifact digest: `35f3c0002ef891fb778a29b0ac8dd5d9d4ff65a9f41ea1009348df99354849f5`。
- 出力先: `web/.cache/r3-pages-artifact`（ignored）。Pages deployは行わない。
- `check_pages.py`の実Chromium受入はpassed。全118件の元Markdown hash、全ローカルリンク/出典、
  検索、版表示、375/768/1024/1440px、非公開pathの404、外部resource要求0を確認した。

初回の出力先`/tmp`はbuild元と別ファイルシステムで、hard linkによる配置に失敗した。
完了manifestのない出力を再試行で正しく拒否し、build元と同じファイルシステムの新規出力先でbuildを完了した。
このローカル検証条件の変更によるソース修正はない。

`git diff --check`成功。未管理`HANDOFF.md`のbytesを保持した。
CI成功とレビュー/取込後にR4（#113）へ進む。
