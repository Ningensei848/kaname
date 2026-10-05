---
title: 動的表面符号が切り拓く量子誤り訂正の新展開
title_original: Dynamic surface codes open new avenues for quantum error correction
source: https://research.google/blog/dynamic-surface-codes-open-new-avenues-for-quantum-error-correction/
publisher: Google Research
author: []
published: '2026-01-13'
created: '2026-10-05'
description: Google ResearchおよびGoogle Quantum AIチームの研究者らは、従来の静的な回路を超える新しい動的回路を用いた量子誤り訂正（QEC）の実験的デモンストレーションを発表しました。この動的サーフェイスコードは、サイクルごとに回路構成を交互に切り替えることで検出領域を時空内で変形させ、従来の静的回路における課題を回避します。具体的には、結合子数を削減できる「六角形（hexagonal）回路」、量子情報の漏洩による相関エラーを大きく低減する「ウォーキング（walking）回路」、そして非計算状態に依存しない「iSWAPゲート」を用いた回路の3つが検証されました。Willow超伝導プロセッサを用いた実験により、これらの手法がいずれも実用可能であることが示され、ハードウェアの設計制約を緩和しつつフォールトトレラントな量子コンピュータの実現へ向けて新たな可能性を開くものとなっています。
tags:
- clippings
- research
- 量子誤り訂正
- 動的回路
- サーフェイスコード
- 超伝導量子ビット
- Willow
- Google-Research
canonical_url: https://research.google/blog/dynamic-surface-codes-open-new-avenues-for-quantum-error-correction/
source_language: en
category: hardware
ai_model: gemini-3.5-flash-lite
raw_html_sha256: d7a08c642b88aa48c333a15c70e0e8af77c81eaae890fd5601752e917ca1ab86
content_sha256: e3c3210874d369f8e9d170408e3aedd0a4ea30e996fbce7ebe77c6c6441e48a1
llm_input_truncated: true
llm_input_max_chars: 20000
---

# 動的表面符号が切り拓く量子誤り訂正の新展開

> [!warning] 要約対象の制限
> 入力上限により、変換後の本文の先頭20,000文字だけを要約しています。
> 記事後半の論点が含まれない場合があります。記事全体の確認には出典URLを参照してください。

> [!abstract] AI要約
> Google ResearchおよびGoogle Quantum AIチームの研究者らは、従来の静的な回路を超える新しい動的回路を用いた量子誤り訂正（QEC）の実験的デモンストレーションを発表しました。この動的サーフェイスコードは、サイクルごとに回路構成を交互に切り替えることで検出領域を時空内で変形させ、従来の静的回路における課題を回避します。具体的には、結合子数を削減できる「六角形（hexagonal）回路」、量子情報の漏洩による相関エラーを大きく低減する「ウォーキング（walking）回路」、そして非計算状態に依存しない「iSWAPゲート」を用いた回路の3つが検証されました。Willow超伝導プロセッサを用いた実験により、これらの手法がいずれも実用可能であることが示され、ハードウェアの設計制約を緩和しつつフォールトトレラントな量子コンピュータの実現へ向けて新たな可能性を開くものとなっています。

## 重要ポイント

- 周期的に回路構成を変化させる動的サーフェイスコードにより、量子誤り訂正の柔軟性と性能を向上させた。
- 六角形（hexagonal）回路を用いることで、各量子ビットあたりの結合子数を4つから3つに削減しつつ誤り訂正に成功した。
- ウォーキング回路により、データと測定の役割を入れ替えて量子ビットの漏洩に起因する相関エラーを1桁以上削減した。
- iSWAPゲートを活用した動的回路の実証により、従来のCZゲート以外のエンタングルメントゲートの有効性を確認した。

## 検索キーワード

- [[Willow]]
- [[iSWAPゲート]]
- [[超伝導回路]]
- [[フォールトトレランス]]
- [[量子プロセッサ]]

## 資料の位置づけ

本資料は、Google Quantum AIチームによる量子誤り訂正技術の最新の研究成果について解説したものであり、静的サーフェイスコードの限界を克服するための動的回路の有用性を実験的に示すものです。ハードウェアのレイアウト制約の軽減、ゲートの選択肢の拡張、およびハードウェアと誤り訂正プロトコルの共同設計（コデザイン）に関心を持つ研究者や技術者にとって重要な参照資料となります。

---

## 出典情報

- Title: Dynamic surface codes open new avenues for quantum error correction
- Publisher/Site: Google Research
- Author: （取得なし）
- Published: 2026-01-13
- Clipped: 2026-10-05
- Domain: research.google
- Original URL: `https://research.google/blog/dynamic-surface-codes-open-new-avenues-for-quantum-error-correction/`
- Original language: en
- Word count: 2682
- AI model: gemini-3.5-flash-lite
