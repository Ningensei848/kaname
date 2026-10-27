---
title: Cloudflare Workers AIにおけるGLM-5.3のKVキャッシュ露出問題とSGLangを用いた修正
title_original: Cross-request KV cache exposure in the GLM-5.3 Workers AI model, and
  our remediation with SGLang
source: https://blog.cloudflare.com/kv-cache-exposure-remediation/
publisher: Cloudflare Security Blog
author: []
published: '2026-10-26'
created: '2026-10-27'
description: 2026年9月8日、Knosticのセキュリティ研究者Gadi Evronからの指摘により、Cloudflare Workers AIで提供していたGLM-5.3モデルにおけるテナント分離の不具合が判明した。8月27日から9月9日までの間、681,280トークンを超える非常に長いプロンプトを送信した一部の顧客において、直前の他ユーザーのリクエストデータを含む応答が返される事象が155件発生した。原因は、SGLang推論エンジンの構成ミスによりKVキャッシュプール容量（681,280トークン）がモデルのコンテキスト長（1,048,576トークン）を下回っていたこと、および、制限を超えたリクエストが拒否された際にプレースホルダーへ置き換えられたものの、分散プリフィル・デコードモードのスケジューラが正常に処理せずデコード側が古いKVキャッシュを参照してしまったことの2点が重なったためである。Cloudflareは問題発覚後速やかにモデルを非公開にし、構成の修正とエンジンのパッチ適用を実施した。さらに、SGLang開発チームとの共同作業を通じて、上流への修正パッチの統合や、遅延解放、転送バッチの制限などのメモリ安全性に関する継続的なハードニングを導入した。
tags:
- clippings
- cybersecurity
- Cloudflare
- Workers-AI
- GLM-5-3
- SGLang
- KVキャッシュ
- 脆弱性
- セキュリティインシデント
canonical_url: https://blog.cloudflare.com/kv-cache-exposure-remediation/
source_language: en
category: cybersecurity
ai_model: gemini-3.5-flash-lite
raw_html_sha256: fadcf644e7b489ac162be0434d4bde248f89b398c9b912c808c1d9c9eafd8c92
content_sha256: 33d5037004fdb0f0d5072936d0a8361dd173ce7fe5b5ab3e03a6c197f523710d
llm_input_truncated: true
llm_input_max_chars: 20000
---

# Cloudflare Workers AIにおけるGLM-5.3のKVキャッシュ露出問題とSGLangを用いた修正

> [!warning] 要約対象の制限
> 入力上限により、変換後の本文の先頭20,000文字だけを要約しています。
> 記事後半の論点が含まれない場合があります。記事全体の確認には出典URLを参照してください。

> [!abstract] AI要約
> 2026年9月8日、Knosticのセキュリティ研究者Gadi Evronからの指摘により、[[Cloudflare Workers AI]]で提供していたGLM-5.3モデルにおけるテナント分離の不具合が判明した。8月27日から9月9日までの間、681,280トークンを超える非常に長いプロンプトを送信した一部の顧客において、直前の他ユーザーのリクエストデータを含む応答が返される事象が155件発生した。原因は、[[SGLang]]推論エンジンの構成ミスによりKVキャッシュプール容量（681,280トークン）がモデルのコンテキスト長（1,048,576トークン）を下回っていたこと、および、制限を超えたリクエストが拒否された際にプレースホルダーへ置き換えられたものの、分散プリフィル・デコードモードのスケジューラが正常に処理せずデコード側が古いKVキャッシュを参照してしまったことの2点が重なったためである。Cloudflareは問題発覚後速やかにモデルを非公開にし、構成の修正とエンジンのパッチ適用を実施した。さらに、[[SGLang]]開発チームとの共同作業を通じて、上流への修正パッチの統合や、遅延解放、転送バッチの制限などのメモリ安全性に関する継続的なハードニングを導入した。

## 重要ポイント

- GLM-5.3モデルにおいて681,280トークンを超える長文プロンプトを処理した際、他ユーザーのデータが混入するKVキャッシュ露出が発生した。
- KVキャッシュプールの容量不足と、[[SGLang]]エンジンの超過リクエスト処理におけるバッジ制御の不具合が原因である。
- Cloudflareは即座にモデルを非公開化して設定を修正し、[[SGLang]]のパッチ適用や上流へのコントリビューションを通じて再発防止策を講じた。

## 検索キーワード

- [[KV cache]]
- [[SGLang]]
- [[Cloudflare Workers AI]]
- [[Z.ai]]
- [[Mooncake]]

## 資料の位置づけ

本資料は、[[Cloudflare Workers AI]]環境における大規模言語モデルの運用上の脆弱性と、その根本原因および修正プロセスに関するセキュリティインシデントレポートである。[[SGLang]]推論エンジンを利用した分散プリフィル・デコード構成におけるKVキャッシュのメモリ安全性や、設定不整合に起因するデータ露出リスクへの対策を後から参照する際に有用である。

---

## 出典情報

- Title: Cross-request KV cache exposure in the GLM-5.3 Workers AI model, and our remediation with SGLang
- Publisher/Site: Cloudflare Security Blog
- Author: （取得なし）
- Published: 2026-10-26
- Clipped: 2026-10-27
- Domain: blog.cloudflare.com
- Original URL: `https://blog.cloudflare.com/kv-cache-exposure-remediation/`
- Original language: en
- Word count: 4160
- AI model: gemini-3.5-flash-lite
