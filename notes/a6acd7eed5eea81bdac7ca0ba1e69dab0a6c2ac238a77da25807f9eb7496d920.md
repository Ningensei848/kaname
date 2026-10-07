---
title: 'ReviewBench: AIコードレビューのためのオープンベンチマーク'
title_original: 'ReviewBench: An open benchmark for AI code review'
source: https://github.blog/ai-and-ml/github-copilot/reviewbench-an-open-benchmark-for-ai-code-review/
publisher: GitHub Blog
author:
- '[[Michelle Zhou, Alejandro Carderera de Diego]]'
published: '2026-10-05'
created: '2026-10-07'
description: 'GitHubブログで公開された記事「ReviewBench: An open benchmark for AI code review」では、GitHubにおける1億件以上の実際のプルリクエストをモデルにして構築された、エージェント型コードレビュー向けの新しいオフラインベンチマーク「ReviewBench」が紹介されています。AIコードレビューの品質測定が難しいという課題に対処するため、言語、リポジトリサイズ、プルリクエストの規模の分布を再現し、マルチソースのゴールデンセット、一貫した評価基準、シニアエンジニアによる独立した検証を取り入れています。これにより、精度の高いオフライン評価が可能になり、GitHub
  Copilotコードレビュー（CCR）のプロダクト実験の方向性を予測する精度が向上したと述べられています。'
tags:
- clippings
- software-development
- ReviewBench
- AIコードレビュー
- GitHub-Copilot
- ベンチマーク
- 生成AI
- コード品質
canonical_url: https://github.blog/ai-and-ml/github-copilot/reviewbench-an-open-benchmark-for-ai-code-review/
source_language: en
category: ai-llm
ai_model: gemini-3.5-flash-lite
raw_html_sha256: 74614ae43bfa3ad0e073152e1dae8e902a04f14026d7dacc9d72967f82b7aee9
content_sha256: 247fb63e7ec439c33d0d43528a6f034a4a7635b8197b322daf761372e27a7ff0
llm_input_truncated: true
llm_input_max_chars: 20000
---

# ReviewBench: AIコードレビューのためのオープンベンチマーク

> [!warning] 要約対象の制限
> 入力上限により、変換後の本文の先頭20,000文字だけを要約しています。
> 記事後半の論点が含まれない場合があります。記事全体の確認には出典URLを参照してください。

> [!abstract] AI要約
> GitHubブログで公開された記事「ReviewBench: An open benchmark for AI code review」では、GitHubにおける1億件以上の実際のプルリクエストをモデルにして構築された、エージェント型コードレビュー向けの新しいオフラインベンチマーク「ReviewBench」が紹介されています。AIコードレビューの品質測定が難しいという課題に対処するため、言語、リポジトリサイズ、プルリクエストの規模の分布を再現し、マルチソースのゴールデンセット、一貫した評価基準、シニアエンジニアによる独立した検証を取り入れています。これにより、精度の高いオフライン評価が可能になり、GitHub Copilotコードレビュー（CCR）のプロダクト実験の方向性を予測する精度が向上したと述べられています。

## 重要ポイント

- 1億件以上の実際のGitHubプルリクエストに基づいて構築されたコードレビューエージェント向けの新しいオフラインベンチマーク「ReviewBench」が発表された。
- マルチソースのゴールデンセットや一貫した評価基準を採用し、シニアエンジニアによる独立した検証を受けている。
- ReviewBenchを用いたオフライン評価により、Copilotコードレビュー（CCR）のプロダクト実験の改善予測精度が向上した。

## 検索キーワード

- [[ReviewBench]]
- [[GitHub Copilot]]
- [[プルリクエスト]]
- [[LLM]]

## 資料の位置づけ

本資料は、AIによるコードレビューエージェントの性能を評価するための新しい標準的ベンチマーク「ReviewBench」の概要と構築背景を説明した解説記事です。AIコードレビューの精度や品質を客観的に測定・比較したい開発者や、エージェント型コードレビューの導入・検証手法に関心を持つ技術者にとって参照価値があります。

---

## 出典情報

- Title: ReviewBench: An open benchmark for AI code review
- Publisher/Site: GitHub Blog
- Author: Michelle Zhou, Alejandro Carderera de Diego
- Published: 2026-10-05
- Clipped: 2026-10-07
- Domain: github.blog
- Original URL: `https://github.blog/ai-and-ml/github-copilot/reviewbench-an-open-benchmark-for-ai-code-review/`
- Original language: en
- Word count: 4883
- AI model: gemini-3.5-flash-lite
