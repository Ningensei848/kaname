> 履歴資料：当時の判断・検証・作業記録です。現在の仕様は[仕様書](../../specification.md)、現状は[検証・受入](../../verification.md)を参照してください。本文の過去の状態を現在の実装状況として扱わないでください。

# Phase 2実装計画

Phase 1は2026-10-03に定期runとGCS照合を完了。Phase 2はroadmapの8項目を対象にします。

1. 本文抽出・決定的フィルタ・HTML一覧からの発見・Playwrightをsource設定で選択可能にする。
2. Vaultへの同期でローカル編集を保護し、実測usageの費用集計、連続失敗通知、source単位のraw保存期間を追加する。
3. standardを維持して非同期Gemini Batchを追加し、ジョブ永続化・再開・部分失敗・重複課金抑止を検証する。
4. CLI・設定・運用手順・検証結果をREADMEへ反映する。

既存sourceはHTTP/RSS・全HTML変換・standardのまま。本文抽出の切替はcontent hashが変わるため明示的な設定変更で行います。
Geminiモデル・minimal・20,000文字・原文非保存・AWS News無効・非公開GCSを維持します。
Batchの実サービス確認は非同期完了を待つ必要があり、fixture検証と区別して記録します。
VaultパスはCLIで明示。raw削除ルールは計画確認後に管理者が適用し、未設定sourceや旧rawへ削除を広げません。
Quartzによる公開SSGはPhase 2の範囲外です。Vault同期を土台に、公開対象・配信先を決めて別途実装します。
