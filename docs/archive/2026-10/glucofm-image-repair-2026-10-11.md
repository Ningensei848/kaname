# GlucoFMの限定画像補完（2026-10-11）

ユーザー指定によりGlucoFM 1件を検証対象とします。画像なしの既存Noteは画像機能の導入前に公開された版です。
PR #133でGoogle Research本文selector、PR #136でMarkdown escape照合とmedia captionを修正しました。
PR #136とマージ後CIは成功しています。

## 固定計画とローカル検証

- Note ID: `eff25c6d47cbba54dd762e9318eeffd267970fbff2b9359427e3000d08ac7419`
- 元Note SHA256: `ce271417b252a109d5af1fc036af261bed3de5a8c56a738283d180c505723c8f`
- 再取得本文Markdown SHA256: `c5e5a0074f4fc0f1397f60359a7792f262596aab114dae21a854fb8806a70bb7`
- 補完後Note SHA256（実HTML再生）: `4884907c27c19e57d86f4a577b3fbc9ba3567c1d7f451233fd3e3eb039a02d16`

概要図をAI要約の直後、構成図を第1重要ポイントの直後に配置します。
画像ブロックと追加したfrontmatterだけを除くと、元Noteの全bytesと一致します。
要約・生成日・モデル・入力打切り表示・元本文hash・安定IDを維持します。
Gemini呼出しと画像ファイルのダウンロードは行いません。

専用補完の回帰では、プレビューの書込みゼロ、変更objectがNoteとreceiptの2つだけであること、
index/usageの不変、公開snapshot照合、receipt/Note保存失敗からの再開、競合・入力変更拒否を確認しました。
Actions入口では他modeとの併用拒否、通常収集/公開jobの除外、同じwriter lockを確認しました。

全Python回帰428件、設定検証、actionlint 1.7.12（shellcheck/pyflakesなし）が成功しました。

本番GCSプレビュー・適用・Pages配信は、この記録作成時点では未実施です。成功したrunと版を追記します。
