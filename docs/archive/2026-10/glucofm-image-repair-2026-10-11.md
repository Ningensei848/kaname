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

## 実GCSプレビューと適用

[PR #137](https://github.com/Ningensei848/kaname/pull/137)をmain `8fbbefb994510e6dfb50329cf1ad4b083559fcab`へ取り込みました。
[PR CI](https://github.com/Ningensei848/kaname/actions/runs/38098129171)と
[main CI](https://github.com/Ningensei848/kaname/actions/runs/38098250430)はPython/Webともsuccessです。

| 操作 | run | 結果 |
|---|---|---|
| preview | [38098262203](https://github.com/Ningensei848/kaname/actions/runs/38098262203) | planned 1 / updated 0 / images 2、要約bytes一致 |
| apply | [38098661785](https://github.com/Ningensei848/kaname/actions/runs/38098661785) | updated 1 / images 2、previewとNote bytes一致 |

両runのauditはsuccess、success_rows 306 / pending 62 / truncated_rows 250 / issuesなしです。
収集、Batch preflight、Git公開、Pages、通知jobはすべてskipしました。
Gemini clientを作らず、API keyも渡していません。既存usage/課金IDを更新する処理はありません。
実画像URLはHEADのみで200/image/pngを確認し、バイナリは取得・保存していません。

## Git/Pages公開と独立照合

[公開専用run 38099019826](https://github.com/Ningensei848/kaname/actions/runs/38099019826)はsuccessです。
Collect、費用/通知state更新、Batch診断をskipし、audit/export、Git更新、Pages build/deployと配信版照合を完了しました。

- content commit: `9b186a1497c5e625c291c9579a552ecf45977c66`
- dataset digest: `6d61bc75a077364aaf2ee8bc5b9a8b51220193332ec098d7d4ab4484f82c3bbf`
- artifact digest: `b6ab79f4adbeaea8da69b839ccb7bb8254620ff7747d60709c7a6cbe03ec1373`
- Note数124。GlucoFM以外の123件のhashは不変。
- Git差分は`manifest.json`と対象NoteのMarkdownだけ。

export manifestと事前計算した期待manifestが全項目一致しました。
配信MarkdownはGCS適用artifactと一致し、画像追加だけを除くと元公開Noteの全bytesに戻ります。
HTMLの2図は計画のURLと一致し、`no-referrer`、当該画像hostだけのCSPを確認しました。

Pages buildでは実content全124件のQuartz/Chromium受入が成功しました。
許可画像だけを代用するCI検査に加え、配信ページの実画像をローカルChromiumで読み込みました。
375/1440pxで両図ともnaturalWidth 1250、画面幅内に表示され、想定外resourceとJavaScriptエラーは0です。
アプリ内ブラウザは接続環境の制約で利用できず、既存Chromiumで検証しました。
画像保存機能やGit同梱は追加していません。

配信後検証は独立の`python -I -S web/verify_deployment.py`でも全124件成功しました。
これでGlucoFM 1件の要約を維持した画像補完と、GCS→Git→Pagesの配信を受入完了とします。
新規LLMによる画像選択・ほかの旧Noteへの一括適用・実Batch成功保存は別の受入です。
