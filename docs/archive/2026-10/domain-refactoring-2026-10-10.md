# 責務整理のローカル検証（2026-10-10）

## 基点と範囲

コード基点はローカル`3fcde9d93003d24f5cb2299c86743a1c5956d4f7`、
GitHub main `b38a6a17c6a6f7613d54415100d04713c3397131`と同じtree
`4d2d6360cab07ca7d7eefdf515d51d5c0ec98eed`です。
未追跡のHANDOFF.mdを保持し、ローカルの実装・検証まで完了しました。
PR作成・マージ・本番workflow実行・GCS/Gemini操作・Git push・Pages deployは行っていません。

## 変更

- Batch preflightを`techkb.batch`へ移し、スクリプトを薄いCLIにした。読取り専用・JSON・終了コード・安全な診断を維持。
- 画像Markdownの組立と配置をcomposerへ移した。画像候補処理と直接HTTPS表示は維持。
- 公開関連を`techkb.publication`パッケージへ集約した。公開importを遅延読込みし、snapshot検証と固定Git照合を公開ドメインに置いた。
- HTML後処理、artifact、Pages準備、配信版検査を`web/kaname_web`へ移し、workflowをnpm入口へ揃えた。
- npm経由の配信版検査に必要な固定Node runtimeをdeploy前に準備する。Pythonの配信後検査は追加パッケージ不要。
- 完了済み計画と過去の検証値を履歴へ保存し、現行正本とGCS障害復旧を整理した。

## 検証結果

| 検証 | 結果 |
|---|---|
| 変更前の全Python回帰 | 378 passed |
| Batchライブラリ化の対象回帰 | 39 passed |
| 画像組立分離の対象回帰 | 81 passed |
| 公開パッケージ化の対象回帰 | 131 passed |
| Web分離の対象回帰 | 146 passed |
| 最終の全Python回帰 | **382 passed**。実Chromium、保存障害/復旧、usage/Batch二重計上、公開拒否、隔離配信検証を含む |
| validate-config | success。3 sources |
| Web監査テスト | 4 passed |
| npm依存監査 | 既存レビュー済みbraces/sprintf advisoryだけを許容。依存更新なし |
| actionlint | 1.7.12、workflow構文・式の検査成功。任意のshellcheck/pyflakes連携は無効 |
| 変更前後のbytes比較 | 画像付きfixtureの全5ファイル（Note・README・manifest）、Quartz入力全13ファイルが完全一致 |
| fixture Web受入 | 画像付き3件、検索・リンク・元Markdown・4画面幅・画像・fixture表示がpassed。想定外通信0、許可画像request 2 |
| 固定公開Git版Web受入 | 118件、全元Markdown bytes/hash、commit/digest、検索・出典・内部リンク・4画面幅・非公開path拒否がpassed。外部request 0 |
| 配信版検査 | 固定118件のローカルHTTPに対するnpm入口と`python -I -S`の結果が一致 |
| パッケージ | wheelに新公開パッケージ7モジュールを収録。wheelから標準ライブラリだけの公開importが成功 |

GCS/Gemini/GitHub資格情報を外したnpm経由のWeb受入を行いました。
GCS認証・収集・audit・exportの各失敗で、公開artifact uploadとGit/Pages更新へ進まない4ケースを追加しました。
エラーを成功扱いするcontinue-on-errorは導入していません。

## 固定入力

公開Git入力はローカルに保持していたcontent履歴の
`e3ef457f3edab5b4ca90601c922cc3b415d288ab`（118件）です。
公開先の最新tipを取得したという主張ではありません。

- dataset digest: `22fe4c95ad6e3b25bcc24047ef6c9c4fb75eb30a1d730b1de2a3e0b2fa595898`
- Pages用ローカルartifact digest: `35f3c0002ef891fb778a29b0ac8dd5d9d4ff65a9f41ea1009348df99354849f5`
- 画像付きfixture dataset digest: `19d346e9da87e740bc540c2e0d99c9b04651fcb917768a23917c8b9c9912e2d0`
- fixture artifact digest: `16ea6f2e4e782ffb7eac7fbad218e3b53e61d8530a2eb7eb563c746748a9b2e2`

古いfixtureでoutput_conflictを検出し、その出力を保持して新しい名前へ生成しました。
`fixture --output`と`build --snapshot ... --fixture`を追加し、旧引数・既定値を維持しています。
既存venvはuv管理のため、wheel検証はuvの一時ビルド環境で実施しました。依存manifest/lockは変更していません。

## 結論

今回のローカル実装と検証は完了しました。継続する保証と未受入範囲は[現行の検証・受入](../../verification.md)、
後続作業は[次の作業](../../next-work.md)へ分けます。本番反映・画像入り実Note・実Batch成功保存の受入は別です。
