---
title: Cloudflareがアカウント不要で使える保護付きQuick Tunnelsを発表
title_original: 'Protected Quick Tunnels: simple accountless authentication for your
  next dev project'
source: https://blog.cloudflare.com/protected-quick-tunnels/
publisher: Cloudflare Security Blog
author: []
published: '2026-10-02'
created: '2026-10-16'
description: Cloudflareは、開発者がローカル環境のサービスを公開するための「Quick Tunnels」に、アカウント不要でメール認証を追加できる新機能「Protected
  Quick Tunnels」を発表しました。従来、Quick Tunnelsはリンクを知っていれば誰でもアクセスできる状態でしたが、cloudflaredの2026.9.3以降で「--allowed-mail」フラグを使用することで、許可されたメールアドレスやドメインを持つユーザーのみにアクセスを制限できるようになります。訪問者はCloudflare
  AccessのワンタイムPINでメールアドレスの所有権を証明し、cloudflaredがローカル環境で許可リストとの照合を行います。認証ブローカーはステートレスに動作し、ゲストリストやポリシーは開発者のマシン上にのみ保持されるため、プライバシーが保護されます。この機能はAIコーディングエージェントからの利用にも最適化されており、Wranglerやエージェントの設定ファイルから簡単に組み込むことができます。
tags:
- clippings
- cybersecurity
- Cloudflare
- Quick-Tunnels
- cloudflared
- Cloudflare-Access
- セキュリティ
- 認証
- 開発者ツール
canonical_url: https://blog.cloudflare.com/protected-quick-tunnels/
source_language: en
category: cybersecurity
ai_model: gemini-3.5-flash-lite
raw_html_sha256: f1603c3ad9bafa083a32b67c5f53dee37917f806808ba40316e8ab0f982f0317
content_sha256: c02b5006828fb3340d656ea1d98b3dfa16503bc46f55d834fe145a4146993016
llm_input_truncated: false
llm_input_max_chars: 20000
article_images:
- image_id: img-1
  url: https://blog.cloudflare.com/_image?href=https%3A%2F%2Fblog.cloudflare.com%2F_emdash%2Fapi%2Fmedia%2Ffile%2F01M3WEQPPSBFQSKRNK84673MEC.png&w=715&h=352&f=webp&fit=cover&position=center
  alt: Four-step flow. A visitor opens your link, Cloudflare Access verifies their
    email with a one-time PIN, cloudflared on your machine checks it against your
    allowed emails, and only invited visitors reach your app.
  after: summary
---

# Cloudflareがアカウント不要で使える保護付きQuick Tunnelsを発表

> [!abstract] AI要約
> Cloudflareは、開発者がローカル環境のサービスを公開するための「Quick Tunnels」に、アカウント不要でメール認証を追加できる新機能「Protected Quick Tunnels」を発表しました。従来、Quick Tunnelsはリンクを知っていれば誰でもアクセスできる状態でしたが、cloudflaredの2026.9.3以降で「--allowed-mail」フラグを使用することで、許可されたメールアドレスやドメインを持つユーザーのみにアクセスを制限できるようになります。訪問者はCloudflare AccessのワンタイムPINでメールアドレスの所有権を証明し、cloudflaredがローカル環境で許可リストとの照合を行います。認証ブローカーはステートレスに動作し、ゲストリストやポリシーは開発者のマシン上にのみ保持されるため、プライバシーが保護されます。この機能はAIコーディングエージェントからの利用にも最適化されており、[[Wrangler]]やエージェントの設定ファイルから簡単に組み込むことができます。

![Four-step flow. A visitor opens your link, Cloudflare Access verifies their email with a one-time PIN, cloudflared on your machine checks it against your allowed emails, and only invited visitors reach your app.](<https://blog.cloudflare.com/_image?href=https%3A%2F%2Fblog.cloudflare.com%2F_emdash%2Fapi%2Fmedia%2Ffile%2F01M3WEQPPSBFQSKRNK84673MEC.png&w=715&h=352&f=webp&fit=cover&position=center>)

## 重要ポイント

- cloudflared 2026.9.3以降で--allowed-mailフラグを使用することにより、アカウント不要でQuick Tunnelsのアクセスを特定のメールアドレスやドメインに制限可能になる。
- 訪問者はCloudflare Access経由でワンタイムPINを入力し、メールアドレスの所有権を証明することで認証を行う。
- ゲストリストや許可ポリシーはクラウド側に保存されず開発者のマシン上で処理されるため、プライバシーが強固に保護される。
- AIコーディングエージェントの指示ファイルや[[Wrangler]]からも簡単に組み込むことができ、安全なプレビュー環境の共有を自動化できる。

## 検索キーワード

- [[Cloudflare Tunnel]]
- [[Cloudflare Workers]]
- [[Model Context Protocol]]
- [[Wrangler]]

## 資料の位置づけ

本資料は、Cloudflareが提供する開発者向け機能「Quick Tunnels」のセキュリティ強化に関する公式ブログ記事である。アカウント不要の手軽さを維持したまま、不正アクセスを防ぐためのメール認証を導入する仕組みと設計思想について解説しており、AIエージェントによる開発ワークフローでセキュアなプレビュー環境を構築したいエンジニアにとって有用な参照情報となる。

---

## 出典情報

- Title: Protected Quick Tunnels: simple accountless authentication for your next dev project
- Publisher/Site: Cloudflare Security Blog
- Author: （取得なし）
- Published: 2026-10-02
- Clipped: 2026-10-16
- Domain: blog.cloudflare.com
- Original URL: `https://blog.cloudflare.com/protected-quick-tunnels/`
- Original language: en
- Word count: 1796
- AI model: gemini-3.5-flash-lite
