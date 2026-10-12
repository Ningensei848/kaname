---
title: 動的表面コードが切り拓く新しい量子誤り訂正のアプローチ
title_original: Dynamic surface codes open new avenues for quantum error correction
source: https://research.google/blog/dynamic-surface-codes-open-new-avenues-for-quantum-error-correction/
publisher: Google Research
author: []
published: '2026-01-13'
created: '2026-10-12'
description: Google Quantum AIは、従来の静的な表面コードとは異なり、誤り検出領域をサイクルごとに変化させる「動的回路」を用いた量子誤り訂正の実験的実証についてNature
  Physics誌に発表した。従来の静的回路では、ハードウェアの接続制約や、計算部分空間から漏れ出す「リーク」といった課題が存在していた。これに対し、本研究では「六角格子（hexagonal）」「ウォーキング（walking）」「iSWAP」という3種類の新しい動的回路をWillowプロセッサー上で実証した。六角格子回路では各量子ビットの結合数を4つから3つに削減しつつ、従来と同等の誤り率改善を達成した。ウォーキング回路ではデータ量子ビットと測定量子ビットの役割を周期的に入れ替えることで、リークによる相関エラーを1桁以上削減することに成功した。さらに、CZゲートの代わりにiSWAPゲートを用いた誤り訂正コードの動作も確認され、将来のデバイス設計の選択肢を広げている。これらの動的回路のアプローチは、ハードウェアの故障やドロップアウトを回避し、障害耐性のある量子コンピュータの実現に向けた新たな道を開くものである。
tags:
- clippings
- research
- Quantum-Error-Correction
- Willow
- Google-Quantum-AI
- Surface-Code
- Dynamic-Circuits
- Superconducting-Qubits
- iSWAP
canonical_url: https://research.google/blog/dynamic-surface-codes-open-new-avenues-for-quantum-error-correction/
source_language: en
category: ai-llm
ai_model: gemini-3.5-flash-lite
raw_html_sha256: 05d9e074ef6533a2ec0ea19dce90013124b1369e05ccc88e4ce5fbeb00872444
content_sha256: e6bee0a94dc2468bad4ade00283a0ae53cd43be359f483a5c6426abc2e5609b9
llm_input_truncated: false
llm_input_max_chars: 20000
article_images:
- image_id: img-1
  url: https://storage.googleapis.com/gweb-research2023-media/images/DynamicSC1_Example.width-1250.png
  alt: DynamicSC1_Example
  after: summary
- image_id: img-2
  url: https://storage.googleapis.com/gweb-research2023-media/images/DynamicSC2_DetectingRegionsHERO.width-1250.png
  alt: DynamicSC2_DetectingRegionsHERO
  after: key_point_1
- image_id: img-3
  url: https://storage.googleapis.com/gweb-research2023-media/images/DynamicSC3_Hex.width-1250.png
  alt: DynamicSC3_Hex
  after: key_point_2
- image_id: img-4
  url: https://storage.googleapis.com/gweb-research2023-media/images/DynamicSC4_Walking.width-1250.png
  alt: DynamicSC4_Walking
  after: key_point_3
- image_id: img-5
  url: https://storage.googleapis.com/gweb-research2023-media/images/DynamicSC5_iSWAP.width-1250.png
  alt: DynamicSC5_iSWAP
  after: key_point_4
---

# 動的表面コードが切り拓く新しい量子誤り訂正のアプローチ

> [!abstract] AI要約
> [[Google Quantum AI]]は、従来の静的な表面コードとは異なり、誤り検出領域をサイクルごとに変化させる「動的回路」を用いた量子誤り訂正の実験的実証についてNature Physics誌に発表した。従来の静的回路では、ハードウェアの接続制約や、計算部分空間から漏れ出す「リーク」といった課題が存在していた。これに対し、本研究では「六角格子（hexagonal）」「ウォーキング（walking）」「[[iSWAP]]」という3種類の新しい動的回路を[[Willow]]プロセッサー上で実証した。六角格子回路では各量子ビットの結合数を4つから3つに削減しつつ、従来と同等の誤り率改善を達成した。ウォーキング回路ではデータ量子ビットと測定量子ビットの役割を周期的に入れ替えることで、リークによる相関エラーを1桁以上削減することに成功した。さらに、CZゲートの代わりに[[iSWAP]]ゲートを用いた誤り訂正コードの動作も確認され、将来のデバイス設計の選択肢を広げている。これらの動的回路のアプローチは、ハードウェアの故障やドロップアウトを回避し、障害耐性のある量子コンピュータの実現に向けた新たな道を開くものである。

![DynamicSC1\_Example](<https://storage.googleapis.com/gweb-research2023-media/images/DynamicSC1_Example.width-1250.png>)

## 重要ポイント

- 動的回路を用いた表面コードの実験的実証により、誤り検出領域のタイリングをサイクルごとに変化させる柔軟な誤り訂正を実現した。

![DynamicSC2\_DetectingRegionsHERO](<https://storage.googleapis.com/gweb-research2023-media/images/DynamicSC2_DetectingRegionsHERO.width-1250.png>)
- 六角格子回路により、量子ビットあたりの結合数を3つに減らして設計・製造プロセスを簡素化しつつ、距離3から5へのスケーリングで誤り率の改善を確認した。

![DynamicSC3\_Hex](<https://storage.googleapis.com/gweb-research2023-media/images/DynamicSC3_Hex.width-1250.png>)
- データと測定の役割を入れ替えるウォーキング回路を用いることで、リークに起因する時間相関エラーを1桁以上削減した。

![DynamicSC4\_Walking](<https://storage.googleapis.com/gweb-research2023-media/images/DynamicSC4_Walking.width-1250.png>)
- 従来のCZゲートの代わりに[[iSWAP]]ゲートを使用した誤り訂正コードを[[Willow]]プロセッサーで動作させ、新たなゲートの適用可能性を示した。

![DynamicSC5\_iSWAP](<https://storage.googleapis.com/gweb-research2023-media/images/DynamicSC5_iSWAP.width-1250.png>)

## 検索キーワード

- [[surface code]]
- [[Willow]]
- [[iSWAP]]
- [[hexagonal lattice]]
- [[quantum error correction]]
- [[Google Quantum AI]]

## 資料の位置づけ

本資料は、Google Researchによる量子誤り訂正（QEC）の最新の実験的成果をまとめた技術ブログ記事である。従来の静的表面コードの制約を克服する動的回路の具体的な種類とその性能について、[[Willow]]プロセッサーを用いた実証結果を交えて解説している。将来の耐障害型量子コンピュータに向けたハードウェアとプロトコルの共設計や、回路設計の自由度を広げる技術的背景を後から参照する際に価値がある。

---

## 出典情報

- Title: Dynamic surface codes open new avenues for quantum error correction
- Publisher/Site: Google Research
- Author: （取得なし）
- Published: 2026-01-13
- Clipped: 2026-10-12
- Domain: research.google
- Original URL: `https://research.google/blog/dynamic-surface-codes-open-new-avenues-for-quantum-error-correction/`
- Original language: en
- Word count: 1589
- AI model: gemini-3.5-flash-lite
