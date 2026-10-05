---
title: アングルがすべて：写真の構図を再構築する新しい画像編集手法
title_original: 'It''s all about the angle: Your photos, re-composed'
source: https://research.google/blog/its-all-about-the-angle-your-photos-re-composed/
publisher: Google Research
author: []
published: '2026-04-22'
created: '2026-10-02'
description: Google Researchが発表した新しい画像編集手法は、撮影後に写真の視点を変更し、自然な構図に再構築することを可能にします。この手法は、Google
  Photosの「Auto frame」機能に統合されています。従来の切り抜きやズームとは異なり、単一の2D写真を3Dシーンとして解釈し、3Dポイントマップ推定モデルと生成AIモデル（潜在拡散モデル）を組み合わせることで、カメラの位置や姿勢、焦点距離を調整します。これにより、写っていなかった背景の補完や、広角レンズによる顔の歪みの補正を自動で行い、被写体の比率を自然に保った新しい視点を提供します。本機能はGoogle
  DeepMindとGoogle Platforms & Devicesの共同チームによって開発されました。
tags:
- clippings
- research
- Google-Photos
- Generative-AI
- 3D-Scene-Estimation
- Latent-Diffusion-Model
- Image-Editing
- Computer-Vision
canonical_url: https://research.google/blog/its-all-about-the-angle-your-photos-re-composed/
source_language: en
category: ai-llm
ai_model: gemini-3.5-flash-lite
raw_html_sha256: c15065b5a11441b3b5232ed42d084e1451420fd571961e4dc44292133c8f1475
content_sha256: 8e567bfac6f1a9e0768dc8927e7c38eabf1709a30e1160a324734fe99d7eab15
llm_input_truncated: false
llm_input_max_chars: 20000
---

# アングルがすべて：写真の構図を再構築する新しい画像編集手法

> [!abstract] AI要約
> Google Researchが発表した新しい画像編集手法は、撮影後に写真の視点を変更し、自然な構図に再構築することを可能にします。この手法は、Google Photosの「Auto frame」機能に統合されています。従来の切り抜きやズームとは異なり、単一の2D写真を3Dシーンとして解釈し、3Dポイントマップ推定モデルと生成AIモデル（潜在拡散モデル）を組み合わせることで、カメラの位置や姿勢、焦点距離を調整します。これにより、写っていなかった背景の補完や、広角レンズによる顔の歪みの補正を自動で行い、被写体の比率を自然に保った新しい視点を提供します。本機能はGoogle DeepMindとGoogle Platforms & Devicesの共同チームによって開発されました。

## 重要ポイント

- 撮影済みの2D写真を3Dシーンとして解釈し、カメラのパラメータ（位置、姿勢、焦点距離）を動的に変更して視点を修正する。
- 3Dポイントマップ推定モデルにより、顔や体の形状を正確に再構築し、アイデンティティの保存や歪みの補正を行う。
- 生成AIの潜在拡散モデルを活用し、視点移動によって生じた背景の欠損部分を自然に補完する。
- Google Photosの「Auto frame」機能に統合され、ユーザーはワンアクションで最適な構図の写真を得ることができる。

## 検索キーワード

- [[Google Photos]]
- [[Google DeepMind]]
- [[Auto frame]]
- [[Latent Diffusion Model]]
- [[3D Point Map Estimation]]

## 資料の位置づけ

本資料は、Google Researchが開発しGoogle Photosに導入された、3D認識と生成AIを組み合わせた新しい画像編集・再構成技術について解説した公式ブログ記事です。画像編集における従来の2D的な切り抜きやズームの限界を克服し、撮影後のアングル変更や歪み補正を実現する仕組みを技術的に理解したい場面で参照価値があります。

---

## 出典情報

- Title: It's all about the angle: Your photos, re-composed
- Publisher/Site: Google Research
- Author: （取得なし）
- Published: 2026-04-22
- Clipped: 2026-10-02
- Domain: research.google
- Original URL: `https://research.google/blog/its-all-about-the-angle-your-photos-re-composed/`
- Original language: en
- Word count: 2284
- AI model: gemini-3.5-flash-lite
