# R4: Webの版情報とartifact検査の共通化

Issue #113。基点mainは`870bcc216c15e3f951a8b8e4bd48bc786532c944`（R3 / PR #121取込後）。

## 変更と維持する契約

- 内部モジュール`_web_validation.py`へ、版/fixture判定、digest形式、artifact path、
  hash manifest、Note集合と元Markdown bytesの一致判定を共通化した。
- `site.py`、`pages.py`、`web/check_pages.py`が同じ検証関数を使う。
  `site.digest_value` / `site.artifact_path`は既存importの入口として残す。
- `web/verify_deployment.py`はURL検査とHTTP取得を保持し、取得したbytesの検証を
  transport非依存のreaderを受け取る関数へ分離した。版/hashの判定自体は純粋関数である。
- 共通モジュールとその依存は標準ライブラリのみ。deploy jobの既存checkoutの`src`を読み、
  package install、YAML、BeautifulSoup、Playwright、収集認証を要求しない。
- 元の検査順、固定error code、HTTP要求順序、Cache-Control、20秒timeout、20 MiBの応答上限、
  `verify` / `digest`の既存入口、CLI引数/JSON/終了コードを維持する。
  HTTP 404等の取得例外も元の型で伝播する。
- 余計なfile、危険path、symlink、fixture/commit/digestの不一致を拒否する境界は維持する。
  依存lock、workflow、Secret/IAM、CLI/storage schema、Note ID/Pages URLには変更がない。

## ローカル検証

Python 3.12.13 / Node 24.15.0、既存固定依存、実Chromium。
通常sandbox起動制約のため、承認されたexec_command経路で実行した。

| 時点 | 検証 | 結果 |
|---|---|---|
| 共通化前 | site / pages対象suite | 41 passed（9.20s） |
| 最終差分 | 同じ対象suite | 41 passed（7.30s） |
| 最終差分 | 全Python回帰、実Chromiumを含む | 273 passed（31.34s） |
| 共通化後 | Web audit.test.mjs / 固定依存監査 | 4 tests passed / reviewed braces・sprintfの既知advisoryのみ |
| 最終差分 | 基点mainとの生成/配信比較 | projection・sealed artifact/marker bytesが一致。配信16ケースの結果/例外/HTTP順序・header・timeoutが一致 |

既存HTTPテストに`python -I -S web/verify_deployment.py`の実行を追加した。
site-packagesとPYTHONPATHを使わないisolated Pythonで、HTTP fixtureに対する検証とJSON出力が成功する。
既存の古い配信版、改変Note/homepage、件数違い、404の拒否も成功した。
移動したdigest/path判定の関数本体は構文木が同一。共通モジュールのstdlib依存も確認した。

比較16ケースは成功、fixture、旧commit、dataset/artifact/hash map不一致、homepage/Note改変、
件数違い、404、応答上限超過、不正URL/版入力、snapshot dataset、不正Note path、Note hash不一致を含む。
HTTPはfixture readerで代替し、実公開サービスや収集には要求を送らない。

## Artifactとブラウザ受入

- 架空3件のfixture dataset digest:
  `ad2d8f71bdc82f5c79d589f6781ea7e68e5330789ccb0d1df683bf236ebe3df0`。
- 同fixtureのartifact digest:
  `d52bb7a64f47cfcfbb07e4689576c4323b3a66d5fa6b6e0fb7f733e35e4fcfcc`。
- 固定content commit: `e3ef457f3edab5b4ca90601c922cc3b415d288ab`、118 Notes。
- dataset digest: `22fe4c95ad6e3b25bcc24047ef6c9c4fb75eb30a1d730b1de2a3e0b2fa595898`。
- ローカルartifact digest: `35f3c0002ef891fb778a29b0ac8dd5d9d4ff65a9f41ea1009348df99354849f5`。
  R3の同じ固定版とartifact bytesが一致する。
- fixture/固定実contentの実Chromium受入はともにpassed。全元Markdown hash、
  検索、全ローカルリンク、出典、版表示、375/768/1024/1440px、
  非公開pathの404、外部resource要求0を確認した。
- artifactとscreenshotsはignoredの`web/.cache` / `web/public`へ保存。
  deploy、追加LLM、GCS変更、依存更新は行っていない。

`git diff --check`成功。未管理`HANDOFF.md`のbytesは保持した。
CI成功とレビュー/取込後にR5（#114）へ進む。
