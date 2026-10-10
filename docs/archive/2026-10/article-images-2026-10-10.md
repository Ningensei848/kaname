# 記事画像の実装・offline受入（2026-10-10）

対象は#127。基点mainは`0d15d36776a3de9b7c4e2bad2a32a93be0c706de`です。
ユーザー確認により、今後収集するNoteに出典のHTTPS画像を直接表示します。
過去Noteの再取得・再生成、画像ファイルの保存・転載は行いません。

## 実装

- 元のHTML本文から相対/lazy画像URLを解決し、alt・キャプション・周辺テキストを候補IDでLLMへ渡します。
- 本文入力の打切り後にしか根拠がない候補、広告領域・追跡pixel、危険な画像URLを除外します。画像の意味的な選択はテキストを根拠にLLMが行います。
- 画像指定は要約文と別schema fieldです。候補URLをモデルに生成させず、既知IDと存在する配置先だけを受け入れます。
- standard/Batchが共通のNote作成を使い、Batchは回収に必要な候補ID/URL/altだけを台帳に保持します。
- 公開検査は任意の`article_images`と画像Markdown・配置の一致を要求します。旧Noteは元のbytesを保持します。
- WebはNoteごとの画像hostのみをCSPで許可し、未登録画像/srcsetを拒否、no-referrerとlazy loadingを設定します。
- READMEのschedule・切戻し・R1〜R5の古い進捗を修正し、[次の作業](../../next-work.md)に優先順位と開始条件を記録しました。

## 検証結果

- 変更前:337件成功、実Chromiumの4件は実行ファイル欠落で失敗。既存venvが参照する一時Python 3.12.13とChromiumを復元し、4件も成功。依存manifest/lockは変更していません。
- 変更後:設定検証成功、全**368件成功**。画像配置・語数・standard/Batch保存・二重計上防止・秘密/認証/ローカルhost拒否・公開/HTML/CSP境界を含みます。
- 画像なしの通常/打切りNoteについて、基点mainのcomposerと生成path・全bytesが一致。
- 架空Note3件:固定Quartzでbuild成功。実Chromiumの画像表示・検索・全ローカルリンク・元Markdown hash・4画面幅が成功。
  画像リクエストは許可されたURLに対する幅1200pxの代用SVGで応答し、実際の出典サイトへの画像取得は0、未許可resource要求0。
- 公開contentの固定版`d39c2cacd087185be85c8c3564e4bd646d324cfc`、**124件**:Pages build/公開前検査/実Chromium受入成功。全元Note bytes/hashを維持し、外部resource要求0。
  dataset digest:`e28d6c2bb9d3d744a3f064fc2738730e70a5cf9e8c002abf4e83076156f5c6e8`。

## 未実施

本番Geminiでの候補選択、有料Batch提出、GCS書込み、Gitのcontent更新、Pages deploy、既存Noteの画像追加は行っていません。
offline/Web受入と、画像入りの実Noteの本番受入を区別します。
画像の視覚的内容は解析しません。元画像の可用性とbytesは出典側に依存し、Git版やNote hashでは固定しません。
