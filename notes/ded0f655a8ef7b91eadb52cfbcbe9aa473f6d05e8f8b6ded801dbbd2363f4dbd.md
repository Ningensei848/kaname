---
title: 動的表面コードによる量子誤り訂正の新展開
title_original: Dynamic surface codes open new avenues for quantum error correction
source: https://research.google/blog/dynamic-surface-codes-open-new-avenues-for-quantum-error-correction/
publisher: Google Research
author: []
published: '2026-01-13'
created: '2026-10-07'
description: Google Quantum AIチームの研究者らは、物理的な操作の固定された静的回路ではなく、回路構成を動的に切り替える新しい量子誤り訂正（QEC）手法の実験的実証を発表した。従来の表面コードでは単一の静的回路を使用していたが、動的回路ではサイクルごとに回路構造を変化させることで、結合子の削減、相関エラーの抑制、異なる量子ゲートの活用を実現している。具体的には、結合子数を削減できる「ヘキサゴナル（六角形）回路」、データ量子ビットと測定量子ビットの役割を定期的に入れ替えてリークによる相関エラーを大幅に削減する「ウォーキング回路」、非計算状態に依存しない「iSWAPゲート」を用いた誤り訂正の3種類の回路をGoogleのWillowプロセッサ上で実証した。これらの手法は、ハードウェア設計の複雑さ軽減やドロップアウト回避への道をひらき、耐量子計算の実現に向けた新たな選択肢を提供する。
tags:
- clippings
- research
- 量子計算
- 量子誤り訂正
- 超伝導量子回路
- 動的回路
- Google-Quantum-AI
- Willow
canonical_url: https://research.google/blog/dynamic-surface-codes-open-new-avenues-for-quantum-error-correction/
source_language: en
category: hardware
ai_model: gemini-3.5-flash-lite
raw_html_sha256: 541e846bc4646a55892df5f330c05e0bc938dbaa6047b28757729b273dabe893
content_sha256: 4f2cf0f97fdf900c2ffb5e995ac87c25d30744ec0946632366887b30eb07a6ed
llm_input_truncated: true
llm_input_max_chars: 20000
---

# 動的表面コードによる量子誤り訂正の新展開

> [!warning] 要約対象の制限
> 入力上限により、変換後の本文の先頭20,000文字だけを要約しています。
> 記事後半の論点が含まれない場合があります。記事全体の確認には出典URLを参照してください。

> [!abstract] AI要約
> Google Quantum AIチームの研究者らは、物理的な操作の固定された静的回路ではなく、回路構成を動的に切り替える新しい量子誤り訂正（QEC）手法の実験的実証を発表した。従来の表面コードでは単一の静的回路を使用していたが、動的回路ではサイクルごとに回路構造を変化させることで、結合子の削減、相関エラーの抑制、異なる量子ゲートの活用を実現している。具体的には、結合子数を削減できる「ヘキサゴナル（六角形）回路」、データ量子ビットと測定量子ビットの役割を定期的に入れ替えてリークによる相関エラーを大幅に削減する「ウォーキング回路」、非計算状態に依存しない「iSWAPゲート」を用いた誤り訂正の3種類の回路をGoogleのWillowプロセッサ上で実証した。これらの手法は、ハードウェア設計の複雑さ軽減やドロップアウト回避への道をひらき、耐量子計算の実現に向けた新たな選択肢を提供する。

## 重要ポイント

- Google Researchは、サイクルごとに回路構成を切り替える「動的表面コード」を用いた量子誤り訂正の実験的実証を報告した。
- ヘキサゴナル回路により、量子ビットあたりの結合子数を4つから3つに削減しながら従来の静的回路と同等の性能を維持できることを示した。
- ウォーキング回路ではデータと測定の役割を入れ替えることで、リークに起因する時間相関エラーを1桁以上削減することに成功した。
- CZゲートの代わりにiSWAPゲートを用いた誤り訂正回路の実証により、異なるゲートセットの適用可能性を確認した。

## 検索キーワード

- [[Willow]]
- [[表面コード]]
- [[iSWAPゲート]]
- [[量子ビット]]

## 資料の位置づけ

本資料は、Google Quantum AIチームによる量子誤り訂正（QEC）の最新研究成果をまとめた技術ブログ記事である。従来の静的表面コードの制約を克服する動的回路の具体的なアプローチ（ヘキサゴナル、ウォーキング、iSWAP）とその実証データを詳細に解説しており、超伝導量子プロセッサにおけるハードウェアと誤り訂正プロトコルの共同設計に関心を持つ研究者や技術者にとって高い参照価値がある。

---

## 出典情報

- Title: Dynamic surface codes open new avenues for quantum error correction
- Publisher/Site: Google Research
- Author: （取得なし）
- Published: 2026-01-13
- Clipped: 2026-10-07
- Domain: research.google
- Original URL: `https://research.google/blog/dynamic-surface-codes-open-new-avenues-for-quantum-error-correction/`
- Original language: en
- Word count: 2682
- AI model: gemini-3.5-flash-lite
