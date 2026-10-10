---
title: 'ReviewBench: AIコードレビューのためのオープンなベンチマーク'
title_original: 'ReviewBench: An open benchmark for AI code review'
source: https://github.blog/ai-and-ml/github-copilot/reviewbench-an-open-benchmark-for-ai-code-review/
publisher: GitHub Blog
author:
- '[[Michelle Zhou, Alejandro Carderera de Diego]]'
published: '2026-10-05'
created: '2026-10-10'
description: GitHubは、代表的なプルリクエスト、マルチソースのグラウンドツルース、較正された評価、本番環境に合わせた指標に基づいて構築されたコードレビューエージェント向けのオープンなベンチマーク「ReviewBench」を発表した。従来のAIコードレビューの品質測定には、ラベルの品質、網羅性、現実世界の反映度における課題が存在していた。ReviewBenchは、GitHub上の1億件以上の実際のプルリクエストをモデルに、言語、リポジトリサイズ、サイズ分布を追従しており、シニアエンジニアによる独立した検証を受けている。これにより、オフライン評価の信頼性が向上し、本番環境でのユーザー体験の改善を予測しやすくなるとしている。
tags:
- clippings
- software-development
- ReviewBench
- GitHub-Copilot
- Code-Review
- AI
- Machine-Learning
- Benchmark
canonical_url: https://github.blog/ai-and-ml/github-copilot/reviewbench-an-open-benchmark-for-ai-code-review/
source_language: en
category: ai-llm
ai_model: gemini-3.5-flash-lite
raw_html_sha256: b54f83f3129d14c67f9921e822c8de2d4fb3f5687d53bed4492e6dc19bdb7043
content_sha256: 6f3b4845ac54615812e4faf336b3f55c3f1d7e77cf7628d712a2d9a19bc7acf0
llm_input_truncated: true
llm_input_max_chars: 20000
---

# ReviewBench: AIコードレビューのためのオープンなベンチマーク

> [!warning] 要約対象の制限
> 入力上限により、変換後の本文の先頭20,000文字だけを要約しています。
> 記事後半の論点が含まれない場合があります。記事全体の確認には出典URLを参照してください。

> [!abstract] AI要約
> GitHubは、代表的なプルリクエスト、マルチソースのグラウンドツルース、較正された評価、本番環境に合わせた指標に基づいて構築されたコードレビューエージェント向けのオープンなベンチマーク「ReviewBench」を発表した。従来のAIコードレビューの品質測定には、ラベルの品質、網羅性、現実世界の反映度における課題が存在していた。ReviewBenchは、GitHub上の1億件以上の実際のプルリクエストをモデルに、言語、リポジトリサイズ、サイズ分布を追従しており、シニアエンジニアによる独立した検証を受けている。これにより、オフライン評価の信頼性が向上し、本番環境でのユーザー体験の改善を予測しやすくなるとしている。

## 重要ポイント

- GitHub上の1億件以上の実際のプルリクエストをモデルにし、言語やリポジトリサイズなどの分布を忠実に再現したオープンなコードレビューベンチマーク「ReviewBench」を公開した。
- マルチソースのゴールデンセット、一貫した評価基準、シニアエンジニアによる独立した検証を取り入れている。
- Copilotコードレビュー（CCR）のオフライン評価において、本番実験の方向性をより正確に予測できるようになり、ユーザーにとって意味のある改善を担保できるようになった。

## 検索キーワード

- [[GitHub Copilot]]
- [[Generative AI]]
- [[LLM]]
- [[Software Development]]

## 資料の位置づけ

本資料は、GitHubが開発・公開したAIコードレビューエージェント向けのオフライン評価ベンチマーク「ReviewBench」の概要と背景について解説した公式ブログ記事である。AIコードレビューツールの性能測定における課題を解決し、現実世界のプルリクエストに基づいた信頼性の高い評価手法を探求する場面や、自社のコードレビューシステムの検証を行う際に参照価値がある。

---

## 出典情報

- Title: ReviewBench: An open benchmark for AI code review
- Publisher/Site: GitHub Blog
- Author: Michelle Zhou, Alejandro Carderera de Diego
- Published: 2026-10-05
- Clipped: 2026-10-10
- Domain: github.blog
- Original URL: `https://github.blog/ai-and-ml/github-copilot/reviewbench-an-open-benchmark-for-ai-code-review/`
- Original language: en
- Word count: 4916
- AI model: gemini-3.5-flash-lite
