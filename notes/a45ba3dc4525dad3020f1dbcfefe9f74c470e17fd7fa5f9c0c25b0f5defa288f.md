---
title: アングルを変える新しい写真編集：Googleフォトの自動フレーム機能で写真を再構成する
title_original: 'It''s all about the angle: Your photos, re-composed'
source: https://research.google/blog/its-all-about-the-angle-your-photos-re-composed/
publisher: Google Research
author: []
published: '2026-04-22'
created: '2026-10-09'
description: Googleの研究チームは、撮影後の写真の視点やアングルを再構築して再構成する新しい画像編集アプローチを発表し、Googleフォトの自動フレーム（Auto
  frame）機能に導入した。この手法は、従来のトリミングやズームと異なり、2Dの写真を3Dシーンとして解釈する。まず3Dポイントマップ推定モデルを用いてシーンの幾何学的形状、被写体の顔や身体、元のカメラの焦点距離を推定する。次に、古典的な3Dレンダリングによりカメラの姿勢や焦点距離を調整して新しい視点を生成し、隠れていた背景領域を生成型潜在拡散モデル（Latent
  Diffusion Model）で補完・修復する。さらに、機械学習モデルによって被写体の顔の位置や向き、広角レンズ特有のパースペクティブ歪みを検出し、自動で自然で魅力的なプロ
  proporción に補正する。これにより、人物を含む写真をワンアクションで自然に再構成し、撮影後にカメラ位置を引いたような効果を実現している。
tags:
- clippings
- research
- Google-Photos
- Generative-AI
- 3D-Computer-Vision
- Latent-Diffusion-Models
- Image-Editing
- Camera-Calibration
canonical_url: https://research.google/blog/its-all-about-the-angle-your-photos-re-composed/
source_language: en
category: ai-llm
ai_model: gemini-3.5-flash-lite
raw_html_sha256: dbe15f9fd55108ee6b9529cf63c2f531687e0389489b83676c7b3957fb6445a5
content_sha256: 9338686172c67d092ad722b47d6bfb12d775e05aefdf3b761e8fd751da24a397
llm_input_truncated: false
llm_input_max_chars: 20000
---

# アングルを変える新しい写真編集：Googleフォトの自動フレーム機能で写真を再構成する

> [!abstract] AI要約
> Googleの研究チームは、撮影後の写真の視点やアングルを再構築して再構成する新しい画像編集アプローチを発表し、Googleフォトの自動フレーム（Auto frame）機能に導入した。この手法は、従来のトリミングやズームと異なり、2Dの写真を3Dシーンとして解釈する。まず3Dポイントマップ推定モデルを用いてシーンの幾何学的形状、被写体の顔や身体、元のカメラの焦点距離を推定する。次に、古典的な3Dレンダリングによりカメラの姿勢や焦点距離を調整して新しい視点を生成し、隠れていた背景領域を生成型潜在拡散モデル（Latent Diffusion Model）で補完・修復する。さらに、機械学習モデルによって被写体の顔の位置や向き、広角レンズ特有のパースペクティブ歪みを検出し、自動で自然で魅力的なプロ proporción に補正する。これにより、人物を含む写真をワンアクションで自然に再構成し、撮影後にカメラ位置を引いたような効果を実現している。

## 重要ポイント

- Googleフォトの自動フレーム機能に、撮影後の視点やアングルを3Dベースで再構成する新しい画像編集アプローチが導入された
- 2段階の処理を採用し、第1段階で3Dポイントマップ推定とカメラパラメータの調整を行い、第2段階で生成型潜在拡散モデルを用いて隠れた背景を補完する
- 広角レンズ特有のパースペクティブ歪みを自動検出し、自然なプロポーションに補正することでポートレートを最適化する

## 検索キーワード

- [[Google Photos]]
- [[Google DeepMind]]
- [[Latent Diffusion Model]]
- [[Camera Resectioning]]
- [[Auto frame]]

## 資料の位置づけ

本資料は、Google ResearchおよびGoogle DeepMindが開発した、Googleフォト向けの3D認識・生成AIを活用した新しい画像編集技術について解説した公式ブログ記事である。従来の切り抜きや拡大では対応できなかった撮影アングルの変更やパースペクティブ歪みの補正を、単一の写真から自動で行う技術的背景とその仕組みを学ぶことができる。画像処理、コンピュータビジョン、および生成AIを活用したコンシュー向け機能の実現に関心のある読者にとって参照価値が高い。

---

## 出典情報

- Title: It's all about the angle: Your photos, re-composed
- Publisher/Site: Google Research
- Author: （取得なし）
- Published: 2026-04-22
- Clipped: 2026-10-09
- Domain: research.google
- Original URL: `https://research.google/blog/its-all-about-the-angle-your-photos-re-composed/`
- Original language: en
- Word count: 2296
- AI model: gemini-3.5-flash-lite
