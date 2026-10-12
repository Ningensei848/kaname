---
title: 写真の再構成：アングルを調整する新しい3D認識型画像編集手法
title_original: 'It''s all about the angle: Your photos, re-composed'
source: https://research.google/blog/its-all-about-the-angle-your-photos-re-composed/
publisher: Google Research
author: []
published: '2026-04-22'
created: '2026-10-12'
description: Google Researchは、撮影済みの写真の視点を自動で修正・再構成する新しい機械学習アプローチを発表した。本手法は、標準的な2D写真を3Dシーンとして解釈し、カメラの内部パラメータおよび外部パラメータを調整する2段階の編集プロセスを採用している。第一段階では、単眼深度と2Dセマンティック情報を用いてシーンの3Dポイントマップを推定し、カメラの姿勢や焦点距離を変更する。第二段階では、仮想カメラの移動によって生じる背景の欠損部分を、生成型潜在拡散モデル（Latent
  Diffusion Model）を用いて補完し、自然な新しい視点を生成する。これにより、広角レンズによる歪みの修正やポートレートのフレーミング最適化が可能となる。本機能は、Google
  Photosの「Auto frame」機能の一部として既に導入されており、人物が含まれる対象写真に対してシームレスな自動調整を提供する。
tags:
- clippings
- research
- Google-Photos
- 画像編集
- 生成AI
- 3D再構築
- 潜在拡散モデル
- 機械学習
canonical_url: https://research.google/blog/its-all-about-the-angle-your-photos-re-composed/
source_language: en
category: ai-llm
ai_model: gemini-3.5-flash-lite
raw_html_sha256: 5e7b10cbc86cfa132d9ff72060c0eecb2eb79ea1d806182f28b2bc5ff40a55a1
content_sha256: b50897279461ffd3d959ffc246e98c42a77a72a5b4465c733dfaea2b5a9d4bc6
llm_input_truncated: false
llm_input_max_chars: 20000
article_images:
- image_id: img-1
  url: https://storage.googleapis.com/gweb-research2023-media/images/Reangle-2.width-1250.png
  alt: Reangle-2
  after: summary
---

# 写真の再構成：アングルを調整する新しい3D認識型画像編集手法

> [!abstract] AI要約
> Google Researchは、撮影済みの写真の視点を自動で修正・再構成する新しい機械学習アプローチを発表した。本手法は、標準的な2D写真を3Dシーンとして解釈し、カメラの内部パラメータおよび外部パラメータを調整する2段階の編集プロセスを採用している。第一段階では、単眼深度と2Dセマンティック情報を用いてシーンの3Dポイントマップを推定し、カメラの姿勢や焦点距離を変更する。第二段階では、仮想カメラの移動によって生じる背景の欠損部分を、生成型潜在拡散モデル（Latent Diffusion Model）を用いて補完し、自然な新しい視点を生成する。これにより、広角レンズによる歪みの修正やポートレートのフレーミング最適化が可能となる。本機能は、Google Photosの「[[Auto frame]]」機能の一部として既に導入されており、人物が含まれる対象写真に対してシームレスな自動調整を提供する。

![Reangle-2](<https://storage.googleapis.com/gweb-research2023-media/images/Reangle-2.width-1250.png>)

## 重要ポイント

- 撮影済みの2D写真を3Dシーンとして解釈し、カメラの視点やアングルを自動で再構成する技術を開発した。
- 3Dポイントマップ推定モデルによる空間ジオメトリの再構築と、生成型潜在拡散モデルによる背景の補完という2段階のパイプラインを採用している。
- 広角レンズによる歪みの修正やポートレートの不自然なプロサイズの改善を自動で行うことができる。
- Google Photosの「[[Auto frame]]」機能の一部としてすでに実装され、ユーザーはワンアクションで最適な構図の画像を利用できる。

## 検索キーワード

- [[Google DeepMind]]
- [[Latent diffusion model]]
- [[Auto frame]]
- [[Camera resectioning]]
- [[3D point map]]

## 資料の位置づけ

この記事は、Google Researchが開発しGoogle Photosに導入された、3D認識と生成AIを活用した新しい写真の視点・構図修正技術の仕組みについて解説しています。画像編集において従来のクロップやズームの限界を超え、撮影後のアングル変更や歪み補正を実現するアルゴリズムの技術的背景を知るための資料として参照価値があります。

---

## 出典情報

- Title: It's all about the angle: Your photos, re-composed
- Publisher/Site: Google Research
- Author: （取得なし）
- Published: 2026-04-22
- Clipped: 2026-10-12
- Domain: research.google
- Original URL: `https://research.google/blog/its-all-about-the-angle-your-photos-re-composed/`
- Original language: en
- Word count: 1089
- AI model: gemini-3.5-flash-lite
