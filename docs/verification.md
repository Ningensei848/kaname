# 検証記録 — 2026-09-25

## 実施結果

| 検証 | 結果 |
|---|---|
| Python 3.12の独立venvに依存を導入 | 成功 |
| `python -m techkb validate-config` | 成功。3 sources、指定Geminiモデル |
| `python -m pytest -q` | **36 passed** |
| raw一致時の変換前skip | 成功 |
| 動的script差分/content一致時のGemini抑止 | 成功 |
| 同一URLの本文更新 | 成功、別Note生成 |
| 異なるURLの同一本文 | 成功、1回のLLM呼出 |
| Schema不正 | 成功登録なし・pending維持・自己修正なし |
| Note upload失敗 | 成功登録なし・receiptから再課金なしで復旧 |
| index upload失敗 | run失敗・既存Noteを増殖させず復旧 |
| 31記事/上限30 | 30記事処理、1記事pending |
| 全月TSV/TSV内TAB・改行/不正header | 成功 |
| CLIオフラインdry-run | 成功、GCS書込み・Gemini呼出ゼロ |
| CLIオフラインE2Eと再実行 | 成功、Note/TSV/pending/report生成、2回目のLLM呼出ゼロ |
| 実サイトdry-run | **外部DNS名前解決不可（gaierror）により失敗** |
| 実Gemini・GCS・WIF・GitHub Actions | **未実施（接続設定・認証情報未提供）** |

テストのHTTP通信にはhttpx.MockTransportを使用します。実際のRSS/Atom解析、HTML cleaner、
MarkItDown、Pydantic、Composer、状態更新、CLIを通しています。
Gemini応答とGCSはテスト用オブジェクトです。実課金は発生させていません。

実サイトdry-runでは3 sourceともfeed段階で名前解決エラーになりました。
発見0、取得0、LLM0、保存0、終了コード1。これは現環境での到達制約であり、
登録sourceの現時点の可用性や本番環境での取得成功を確認した結果ではありません。

## 本番受入で残る項目

- [ ] GCP project / 非公開bucket / custom IAM role / WIFを設定。
- [ ] GitHub repositoryとVariables/Secretsを設定。
- [ ] sourceの取得条件・robots・利用規約を確認。
- [ ] 実Gemini `gemini-3.5-flash-lite` + minimal + Structured Outputの成功。
- [ ] 実GCSへのNote/TSV/pending/report保存。
- [ ] workflow_dispatchから実行成功。
- [ ] 同一記事の実環境再実行でLLMを呼ばないこと。
- [ ] 07:17 JSTスケジュールによる日次実行成功。
- [ ] 生成Noteの日本語・原文・frontmatter品質をユーザーが確認。

これらが完了するまで「日次運用可能なMVP受入完了」とは判定しません。
受入後はdocs/roadmap.mdのPhase 2へ着手してください。

## 残余制約

- API応答後・receipt永続化前の強制終了、および通信timeoutでは厳密なexactly-once課金は保証不可。
- 30件はrun単位。手動再実行を含む日次hard capではない。
- 全HTML変換のため、本文外の可視広告・navigation更新によるcontent hash変更があり得る。
- GCS generation preconditionとbucket設定確認は実GCP未検証。
- Obsidianへの正式同期はPhase 2。現状はGCSにObsidian互換Markdownを保存するところまで。
