# 本番Note品質確認 — 2026-10-01

本書はPhase 1受入のための人手確認資料です。2026-10-01に本番GCSを読取り、
成功index 6件と対応するcompact Noteを原記事と照合しました。
初回照合は読取りのみでした。その後、PR #89の機能で既存5件の著者・公開日表記を更新しました。
Gemini呼出し・workflow実行は行っていません。

## 判定

- 構造整合性: 成功。成功index 6件、pending 108件、audit issues 0件。
- 日本語: 6件とも自然で、中心的な主張に明白な事実誤認は見つかりませんでした。
- frontmatter: YAML、URL、publisher、hash、category、modelは整合しています。
- 出典情報: タイトル、サイト、URL、言語は原記事と一致しています。
- 重要ポイント・検索キーワード・資料の位置づけ: おおむね記事内容と対応しています。
- 出典metadata更新: 既存5件へ適用済み。著者欠落を解消し、公開日をindexの日付部分に統一しました。
- 受入判定: ユーザー最終確認待ち。入力上限20,000文字を維持する方針は確認済みです。

## 初回照合時の6件（metadata更新前）

| 作成日 | 記事 | 評価 |
|---|---|---|
| 2026-09-27 | Copilot runtimeのRust移行 | 要約と主要数値は原記事に一致。著者Stephen Toubが欠落。公開日は原記事表示と1日ずれるRSS timestamp。 |
| 2026-09-28 | diff・terminal・browser | 3パネルと開発ループの説明は正確。著者Kayla Cinnamonが欠落。 |
| 2026-09-28 | canvas custom workflow | `/create-canvas`、双方向UI、再利用の説明は正確。著者Kayla Cinnamonが欠落。 |
| 2026-09-29 | Marketing ops as code | Issue起点のイベント自動化を正確に要約。著者Tomoko Tanakaが欠落。 |
| 2026-09-30 | When chat is the wrong UI | chat UIの限界とcanvasの説明は正確。著者Burke Hollandが欠落。 |
| 2026-10-01 | code・RAG・Skills/MCP | コードレビューと採用判断の記述は正確。著者GPSは取得済み。ただしタイトルにあるRAGとSkills/MCPが要約・重要ポイントから欠落。 |

9月作成の5件は著者抽出機能の適用前に保存されたため、初回照合時には
frontmatterが `author: []`、出典情報が `取得なし` でした。現行コードを現在の6記事へ適用すると、
Stephen Toub、Kayla Cinnamon、Tomoko Tanaka、Burke Holland、GPSを取得できることを確認しました。
`refresh-metadata` の本番計画モードでは更新予定5件、変更なし1件、著者取得不能0件、失敗0件でした。
その後 `--apply` により5 Note/receiptの更新に成功し、1件は変更なし、失敗0件でした。
適用後auditは成功行6件、pending 108件、issues 0件です。要約本文・hash・index・pendingの不変も確認済みです。
公開日はRSS timestampの先頭10文字で統一しており、記事画面のタイムゾーンや更新日とは異なる場合があります。

全6件が `llm_input_truncated: true` です。最新記事の変換後Markdownは30,876文字、
LLM入力上限は20,000文字でした。`Skills killed MCP` は20,274文字目、`RAG is dead` は
21,118文字目にあり、いずれも入力範囲外です。このため、タイトルの主要論点が要約から落ちています。

## 代表Note（2026-10-01）

```yaml
---
title: コードを読むべきか、RAGは死んだのか、SkillsはMCPを殺したのか
title_original: Should you read the code, is RAG dead, and did Skills kill MCP?
source: https://github.blog/ai-and-ml/should-you-read-the-code-is-rag-dead-and-did-skills-kill-mcp/
publisher: GitHub Blog
author:
- '[[GPS]]'
published: '2026-09-18'
created: '2026-10-01'
source_language: en
category: ai-llm
ai_model: gemini-3.5-flash-lite
llm_input_truncated: true
---
```

AI要約は、生成コードを読む責任、リスクに応じたレビュー深度、採用時に求められる
AI利用の判断力を説明しています。重要ポイントも同じ2論点に集中しています。
原記事後半には、SkillsとMCPは競合せず異なる問題を解くこと、RAGは依然有効であること、
fine-tuningとコード品質の関係が続きますが、現在のNoteには含まれていません。

検索キーワードは `GitHub Podcast`、`Generative AI`、`Code Review` で、記録された範囲には
対応します。ただしタイトル全体の検索性には `RAG`、`Skills`、`MCP` が不足しています。
資料の位置づけは記事をAIツールと生成コードレビューの考察として正しく説明しています。

## 利用条件の確認範囲

6件はすべてGitHub Blogの記事です。各記事ページに個別ライセンス表記は確認できませんでした。
robots.txtによる取得可否と、本文をGeminiへ送信して要約を保存する権利判断は別です。
Google Researchは今回の成功Noteに含まれていないため、Note品質の実例確認はできていません。

## 受入前に決めること

1. **完了:** `refresh-metadata` で既存5件の著者と日付表記をNote/receiptへ反映し、整合性を確認。
2. **2026-10-01のユーザー方針: 入力上限20,000文字を維持する。** 後半の要約欠落はこの制限に伴うもので、打切り時は新規Noteに注意表示と生成時の上限値を残す。既存Noteは自動更新しない。将来の緩和は `llm.max_input_chars` の設定変更と品質・usageの再確認で行う。
3. 本資料の日本語要約・重要ポイント・検索キーワード・資料の位置づけ・出典・frontmatterをユーザーが最終確認する。
4. [利用条件の確認資料](source-usage-review-2026-10-01.md)で取得・Gemini送信・要約保存をユーザーが最終判断する。
5. 上限30件への復帰PRは実装済み。上記確認後にmergeし、上限30件のscheduled runで最終受入を行う。
