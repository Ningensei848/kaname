# Google Researchの本文抽出検証

検証日時: 2026-10-10T22:20:47+09:00。

## 変更と確認方法

Google Researchだけに`extract_main: true`と`content_selector: .blog-detail-wrapper`を設定した。
本文の複数rich-text sectionと別sectionの図・キャプションをまとめて保持し、navigation、sidebar、関連投稿を除く。
`main`には関連投稿、個々の`.rich-text`には図が含まれないため、それらを本文の境界にしない。
Gemini入力上限20,000文字、画像候補・選択の契約、既存Note、GCS形式、HTTP/robots方針は変更しない。

実HTTP Fetcher/SourceFetcherで公開RSSから先頭・中間・末尾の3記事と、報告されたGlucoFMを取得した。
各記事でselectorは1箇所に一致し、選択領域外に本文用`.rich-text`ブロックがないことを確認した。
画像バイナリを取得せず、HTML/Markdownと候補をローカルで比較した。Gemini/GCS呼出し、収集run、content更新、Pages deployは行っていない。

## 実記事の結果

| 記事 | 全ページ文字数 | 本文文字数 | 本文img | 変更前候補 | 変更後候補 |
|---|---:|---:|---:|---:|---:|
| [GlucoFM](https://research.google/blog/glucofm-foundation-model-for-continuous-glucose-monitoring/) | 28,223 | 16,130 | 8 | 6 | 8 |
| [Better work / workers](https://research.google/blog/does-better-work-always-mean-better-workers/) | 21,135 | 11,437 | 2 | 4 | 2 |
| [ConvApparel](https://research.google/blog/convapparel-measuring-and-bridging-the-realism-gap-in-user-simulators/) | 22,717 | 12,158 | 5 | 1 | 0 |
| [Research breakthroughs / applications](https://research.google/blog/accelerating-the-magic-cycle-of-research-breakthroughs-and-real-world-applications/) | 28,682 | 18,383 | 3 | 1 | 0 |

全4件で本文が入力上限内に収まった。GlucoFMでは本文の8図すべてが候補になり、先頭図のhero/body重複と関連記事画像を除いた。
図を最終Noteへ何枚掲載するかは既存のLLM選択契約（最大6件）による。画像選択の強制や旧Note補完をこの変更の受入とは扱わない。

### 候補抽出に残る別の問題

ConvApparelは本文内の5個のimgタグを保持しているが、alt内のunderscoreがMarkdownでエスケープされ、
既存`article_images`の文字列照合に一致しないため候補0件となる。これは本文抽出によるタグ欠落ではない。
Research breakthroughsの3個のimgは`src`が空の動画preview placeholderであり、出典画像URL候補にはならない。
これらとGoogle Researchの`.caption p`への対応、LLMの選択0件の診断、既存Note補完は別の改善項目として残す。

## 回帰検証

- synthetic fixtureは実サイトのDOM構造（分割本文・picture・独立media/caption block・同じmain内の関連投稿）を再現し、記事原文や画像bytesを含めない。
- navigationが20,000文字の入力枠を使い切る再現から、本文の先頭・中間・末尾と8枚の候補が残ることを検証した。
- standard/Batch両方で最後の図を選ぶmock応答を与え、本文がLLM入力へ届き、図がNoteへ配置され、truncated=falseとなることを検証した。
- navigationだけの変更では同一本文として重複判定され、追加のLLM呼出し/Batch提出がないことを確認した。
- selector不一致はpendingに残り、LLM呼出しとNote保存がないことを確認した。
- `python -m techkb validate-config`: 成功。
- `python -m pytest -q`: 386件成功。
- 本番のLLM画像選択・画像入り実Note公開はこの検証に含めない。

## 取得HTMLのSHA-256

- GlucoFM: `2ef653449f53ec44c9c0abd61a1062bd88c71c312336ba334ae3d908675d501f`
- Better work / workers: `b651e78ca3910f8cbc92569b3696d8aeafd91dc4e165e5359ff162c316ad4bc8`
- ConvApparel: `6b622a9d83a45dbb19d0b50ffc192651c359cf221b142ff3d9995094f2d5564a`
- Research breakthroughs / applications: `d9af1ecd7dae80532769619129de4f8571bfdfed527b30e8bde00574f61561e2`

本文抽出の切替でcontent hashは変わり得る。通常収集を実行して旧Noteを再生成するのではなく、
既存Noteの修復はreceipt/index/公開snapshotの整合性を保つ独立手順で扱う。
