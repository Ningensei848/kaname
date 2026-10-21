# NS1: 検索キーワード・本文のGoogle検索フォールバック

2026-10-12 JST。実装・ローカル/CI・本番Pagesまで受入完了です。#161の完了証拠は以下に集約しています。

## 利用時の挙動

検索キーワードと本文のWikiLinkは、公開manifestに同じタイトルのNoteが一意にあれば内部Noteへ移動します。一致なし・同名複数・公開除外なら、表示語句のGoogle検索を別タブで開きます。検索リンクは↗とアクセシブルなGoogle検索の説明で識別できます。ページ表示・ビルド時のGoogle通信はありません。APIキーや追加LLM呼出しも不要です。

別名表示では検索語に対象名、表示には別名を使います。内部Noteの見出し指定は維持し、Noteが未解決ならNote名だけを検索します。存在しない内部見出しは検索へ隠さず、Webリンク監査が拒否します。コードspan・fence・indented code・エスケープ・URL・Markdownリンク・画像・Wiki埋込みは変換しません。

解決規則は従来どおりタイトル完全一致です。Graph Qualityの正規化/同義語は評価案であり、公開リンクに自動適用しません。同名から任意のNoteを選ぶことや、タイトル部分一致で推定することもありません。

## 新規Noteの本文

既存のrelated_conceptsを候補とし、新規NoteのAI要約・重要ポイント・資料の位置づけに現れる語句を共通composerでWikiLinkにします。長い候補を優先し、ASCII識別子の途中・バージョン名の一部は一致させません。3文字未満、AI/API/data/model等の一般語、概念名の安全な形式に適合しない候補は本文でリンク化しません。安全なMarkdown escapingを維持し、LLMが記述した既存リンク・URL・画像alt・コードには重ねて挿入しません。

保存されたdescriptionとLLM出力は記法を付ける前の文です。要約字数・本文入力上限・出力上限・Batch schemaを変えません。standard/Batchとも同じ組立てと公開検証を使い、画像の配置・receipt/index一致を維持します。

公開Note検証は従来のplain本文と、候補に基づく正確なリンク付き本文だけを認めます。任意の外部Markdownリンク、未宣言のWikiLink、別名の挿入、HTMLを許容する検証緩和は行いません。旧Noteの保存bytes・Note ID・manifest schemaは維持し、本文への自動付与は新規Noteからです。

## 受入状態

本文/検索語のWikiLink、内部Note優先、未解決時検索、保護構文と元Markdown不変をCI・本番Pagesで受入済み。
[整理前の全文・受入証拠](https://github.com/Ningensei848/kaname/blob/codex/archive/pre-housekeeping-2026-10-16/docs/ns1-search-fallback.md)は専用branchへ保全した。Graph正規化の適用とは別の機能である。
