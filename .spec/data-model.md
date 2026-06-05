# `kaname` データモデル仕様書 (data-model.md)

## 1. SSoT (Single Source of Truth) YAML スキーマ

一元管理される情報源のメタデータリスト（ssot.yml）の厳格なスキーマを定義する。

```yaml
# ssot.yml の構造スキーマ
type: object
required:
  - ssot_sources
properties:
  ssot_sources:
    type: array
    items:
      type: object
      required:
        - id
        - name
        - url
        - description
      properties:
        id:
          type: string
          pattern: "^[a-z0-9_]+$"
          description: "システム内部で用いる一意の識別コード"
        name:
          type: string
          description: "組織・ソースの正式名称"
        url:
          type: string
          format: uri
          description: "クローリング対象の公式サイトメインURL"
        feed_url:
          type: string
          format: uri
          description: "RSS/Atom配信がある場合のXMLエンドポイントURL（任意）"
        description:
          type: string
          description: "組織の役割・解説文"
        meta_url:
          type: string
          format: uri
          description: "組織の概要が記載された副次的なURL（任意）"
        custom_extraction_instruction:
          type: string
          description: "このソースから情報抽出する際にLLMに与える固有のプロンプト（任意）"
```


## 2. 状態管理（べき等性検証用メタデータ）スキーマ

不要なLLMの呼び出し、コミット、PRの作成を機械的に防止するため、前回の処理結果を記録する軽量な変更検知ステート（crawler-state.json）のデータ構造。`crawler-state.json` は Git repository に commit せず、Cloud Storage の object として保存する。

Cloud Storage 推奨配置:

```text
gs://<KANAME_STATE_BUCKET>/<environment>/crawler-state.json
```

state 書き込みは generation precondition を用い、並行 Cloud Run Jobs による last-write-wins を防止する。

```json
{
	"$schema": "http://json-schema.org/draft-07/schema#",
	"title": "CrawlerState",
	"type": "object",
	"required": ["last_execution", "sources"],
	"properties": {
		"last_execution": {
			"type": "string",
			"format": "date-time",
			"description": "最後にクローラーが正常完了したUTC ISO-8601時刻"
		},
		"sources": {
			"type": "object",
			"additionalProperties": {
				"type": "object",
				"required": ["last_checked", "content_hash", "last_modified_header"],
				"properties": {
					"last_checked": {
						"type": "string",
						"format": "date-time"
					},
					"content_hash": {
						"type": "string",
						"description": "ビルトインFetchで取得した本文テキストのSHA-256ハッシュ値"
					},
					"last_modified_header": {
						"type": ["string", "null"],
						"description": "HTTPレスポンスのLast-Modifiedヘッダー値（条件付きGET要求用）"
					}
				}
			}
		}
	}
}
```


## 3. 階層分類トピックディレクトリ・パス決定モデル

トピックファイルの中間ディレクトリ決定、およびシステム制限である最大100フォルダ未満の保護を保証するための論理パス決定ワークフロー。

```mermaid
flowchart TD
    Start([トピック解説データ抽出完了]) --> Parse[Frontmatter プロパティ解析<br/>tags / SSoT ID]

    Parse --> ResolveCategory{カテゴリ解決}
    ResolveCategory -- "例: SSoT ID: 'digital_agency'" --> GovAgencies[カテゴリ: 'gov-agencies']
    ResolveCategory -- "例: Tag: 'incident'" --> Incidents[カテゴリ: 'incidents']

    GovAgencies --> CheckLimit{既存中間フォルダ総数チェック}
    Incidents --> CheckLimit

    CheckLimit -- "既存フォルダ総数 < 95件" --> CreateDir[新しいカテゴリ名でフォルダを自律新規作成<br/>例: topics/gov-agencies/]
    CheckLimit -- "既存フォルダ総数 ≥ 95件<br/>(上限保護発動)" --> ForceFallback[新規フォルダ作成を強制遮断<br/>代替共通フォルダ topics/misc/ または<br/>最も意味親和性の高い既存フォルダへ自動退避・集約]

    CreateDir --> Path[論理決定パスのマッピング<br/>例: topics/gov-agencies/Digital_Agency.md]
    ForceFallback --> Path
    Path --> End([パス決定完了])
```


## 4. Obsidian Flavored Markdown (OFM) メタプロパティ仕様

提案エージェント（Aegis-Writer）が出力・更新するすべてのトピック解説Markdownファイルは、ObsidianおよびQuartz v5に解釈可能な以下のYAML Frontmatterプロパティを保持しなければならない。

```markdown
---
title: "トピック正式名称"
aliases: ["名寄せ用別名1", "別名2"]
last_updated: yyyy-mm-ddThh:mm:ssZ
tags:
  - "cyber-intelligence"
  - "security-organization"
category: "gov-agencies" # 中間ディレクトリ分類名と厳密に1対1対応
status: "active"
sources:
  - "https://www.cyber.go.jp/"
---
# トピック正式名称

（ここから本文がOFM準拠で開始される）
```
