# Knowledge Graph Quality

2026-10-12 JST。表記揺れ・同義語・タグ・検索キーワードのWikiLink品質を、検証済みの公開snapshotで読取り専用評価します。

## 実行と判定

```bash
python -m kaname graph-quality --public-snapshot /path/to/public-content
python -m kaname graph-quality --public-snapshot /path/to/public-content --details
```

manifest、元Markdown hash、Note IDと公開Note構造を既存の`load_snapshot`で検証してから評価します。GCS・Gemini・記事取得のclientを作らず、snapshotや保存Noteを変更しません。`--apply`、`--state-dir`、LLM override、配布repo指定は拒否します。API費用は発生しません。

既定JSONは件数とdataset digestだけです。`--details`は公開Note ID・語句・表記群・リンク判定も含むため、共有前に内容を確認してください。`status: success`は評価処理の成功であり、すべての語がリンク解決済みという意味ではありません。

| 指標 | 意味 |
|---|---|
| occurrences | タグ・検索キーワードの延べ件数 |
| normalized_duplicates | 同一Note内で正規化後に重複する件数 |
| variant_groups | 全Noteで同じ正規化キーを持つ異表記の組数 |
| current_links | 現行Webと同じ完全一致のタイトル解決。resolved/self/unresolved/ambiguous別 |
| proposed_links | 正規化・明示同義語をタイトル/語句に適用した場合の解決候補 |
| current_edges / proposed_edges | 自分以外の一意なNoteへ解決できる有向辺の数。同じNote対は一度だけ計上 |
| ambiguous_title_groups | 正規化後の同名に複数の公開Noteが存在する組数 |
| applied | 常にfalse。正規化案を保存・公開リンクへ適用しない |

対象はcompact Noteの「検索キーワード」節のWikiLinkとfrontmatter tagsです。著者・出典URL・画像・コード記述を概念辺へ数えません。本文へのWikiLink付与と未解決時のGoogle検索は[NS1](ns1-search-fallback.md)で対応済みです。タグのWeb検索正規化は[Web仕様](web-preview.md)へ分け、概念辺の正規化評価を自動適用しません。

## 正規化案と評価例

NFKC、大文字小文字のcasefold、連続空白の統一だけを表記比較に使います。記号は保持し、部分一致・stemming・fuzzy推定を行いません。
明示同義語はLLM / large language model(s) / 大規模言語モデルと、RAG / retrieval-augmented generation / retrieval augmented generation / 検索拡張生成の2群です。意味を推定して辞書を増やさず、辞書変更は評価例をレビューし`normalizer_version`を更新します。

| 良い一致 | 区別して保持する例 |
|---|---|
| LLM / ｌｌｍ / 大規模言語モデル | C / C++ / C# |
| RAG / 検索拡張生成 | RAG / GraphRAG |
| 全角Ｃ＋＋ / C++、結合文字 / 合成文字 | Java / JavaScript、GPT-4 / GPT-4o |
| Model Context Protocolの大小文字・連続空白 | cloud/security / cloud-security |

一意な公開タイトルだけを解決候補とします。同名複数・正規化衝突はambiguousで、任意のNoteを選びません。自分自身への参照はselfとして分け、Note間の辺に加えません。除外されたNoteはmanifestに存在しないため解決候補になりません。

## 固定公開246件の再評価

2026-10-16、content `510dc54a82ebeed360a6f91e07261d45b01f6a75`、dataset `e6562e1b47b4a3baea3e7de573c2d7810d896cda4099050cb17dcf9596863cff` を読取り専用CLIで再評価した。全249ファイルの前後SHA-256とGitの固定版が一致した。

| 指標 | 結果 |
|---|---:|
| Note | 246 |
| タグ / 検索語の延べ件数 | 2,094 / 1,184 |
| Note内の正規化後重複（タグ / 検索語） | 1 / 0 |
| 異表記群（タグ / 検索語） | 4 / 6 |
| 現行 / 提案の解決済み検索語 | 0 / 0 |
| 未解決検索語 | 1,184 |
| 現行 / 提案の内部辺 | 0 / 0 |
| 正規化後の曖昧タイトル群 | 0 |

技術語と記事タイトルが一致しないため、辞書/表記正規化だけの自動適用を採用しない。タグ重複1件も既存Noteの自動書換えや再生成の理由としない。NS1の検索fallbackは本番受入済みで、内部の概念辺とは区別する。
過去の125件/612語の評価は[整理前の全文](https://github.com/Ningensei848/kaname/blob/archive/pre-housekeeping-2026-10-16/docs/graph-quality.md)へ保全している。

## 共通検索語によるNote間の導線

タイトル完全一致で「その概念の定義先」を推測する規則は追加しません。代わりに、検索キーワードを2つ以上共有する公開NoteへのリンクをWebに表示します。表示にも共有語を添え、記事間の因果関係や内容の正しさを保証する辺とは区別します。タグや本文から語を推定せず、NFKC/casefoldと上記2群の明示同義語だけを使います。

一般語・3文字未満・公開版の10%超（下限3 Note）で出る語は関連づけに使いません。共有語数の多い順、出現頻度合計の小さい順、安定Note ID順で最大3件を選びます。自分自身・公開除外Note・1語だけの一致を除き、同じ公開版なら順序を固定します。元Markdown/Note ID/datasetは変更せず、Google検索fallbackも維持します。

`graph-quality`の `shared_keyword_edges` と `shared_keyword_notes` がこの別の関係の件数です。`current_edges` / `proposed_edges` と `applied:false` は従来のタイトル解決/正規化案だけを表します。`--details`に共有語と到達先IDを含めます。Web受入では全リンク・共有語・contentIndex上の辺を照合し、実際の移動と戻る・4幅も検証します。

2026-10-25のcontent `406a716ef2462de01cc50faf09542c3e741c9b79`、dataset `595c002b1b9d60e1b9b5752cc62bf9edd98d158ede94176fe437d81f8a788733` の321 Noteでは検索語1,534件、タイトルによる現行/提案の辺は引き続き0です。共有語による導線は69 Note・136有向辺です。語句だけで記事を定義先に選ぶ方式を採用したという意味ではありません。
