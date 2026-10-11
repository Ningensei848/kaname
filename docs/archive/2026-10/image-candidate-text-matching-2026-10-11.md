# 画像候補のMarkdown照合とcaption抽出

2026-10-11の修正。前回（2026-10-10）に取得した実HTML4件を、同じ本文selector・20,000文字上限で再生した。

## 原因と変更

HTMLのaltにあるunderscoreなどはMarkItDown変換でエスケープされるため、HTMLの文字列との直接照合では候補から外れた。
照合用の入力だけCommonMarkのASCII句読点エスケープを戻し、inline emphasisを除いた照合経路も使う。
候補のalt、URL、本文Markdown、hash、出力Noteの組立は変更しない。literalなescaped punctuationは保持する。
Google Researchのcaptionは各画像の最寄り`.dynamic_media`内の`.caption p`から取得し、無関係な隣のcaptionを使わない。
inline要素間に空白を挿入せず、括弧内の強調等も本文の表記へ対応させる。
候補の説明は実際に入力された範囲と照合し、打切り後のcaptionしかない画像を追加しない。

## 保存済み実HTMLの再生結果

| 記事 | 本文文字数 | 修正前候補 | 修正後候補 | captionのある候補 |
|---|---:|---:|---:|---:|
| [GlucoFM](https://research.google/blog/glucofm-foundation-model-for-continuous-glucose-monitoring/) | 16,130 | 8 | 8 | 8 |
| [Better work / workers](https://research.google/blog/does-better-work-always-mean-better-workers/) | 11,437 | 2 | 2 | 2 |
| [ConvApparel](https://research.google/blog/convapparel-measuring-and-bridging-the-realism-gap-in-user-simulators/) | 12,158 | 0 | 5 | 5 |
| [Research breakthroughs / applications](https://research.google/blog/accelerating-the-magic-cycle-of-research-breakthroughs-and-real-world-applications/) | 18,383 | 0 | 0 | 0 |

GlucoFMは8候補、Better workは2候補を維持し、全候補へcaptionを渡せた。ConvApparelは除外されていた5図すべてが候補になった。
動画previewの3個の空src placeholderは引き続き候補にしない。候補最大12件・LLM選択最大6件・出典HTTPS URL直接表示を維持する。

## 回帰と境界

- underscore、literal asterisk/backslash、角括弧、記号を含むaltを、実Converter出力から検証した。
- captionのinline emphasis・括弧と、無関係なcaptionへの誤対応を検証した。
- エスケープ照合とmedia caption追加後も入力打切りを維持した。
- standard/Batch両方で8候補のcaptionを実際のLLMリクエストへ渡すことを確認した。
- URL・配置の拒否、usage・receipt復旧、公開bytes・Webの回帰を維持した。
- 設定検証成功、全Python回帰393件成功。

既存Noteの画像補完はこのライブラリ修正とは別の更新工程であり、ここでGemini/GCS操作や本番公開は実施していない。
