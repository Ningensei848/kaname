# 次に進める作業

2026-10-22 JST。旧A01〜A20は整理・改善・評価を完了した。[旧作業記録](archive/2026-10/completed-work-2026-10-21.md)と[旧監査一覧](archive/2026-10/completed-audit-2026-10-21.md)へ分離した。完了は各項目の受入範囲での判断であり、残余制約の解消を意味しない。

## 実行するタスク

| ID / 順序 | 内容・完了条件 | 状態 |
|---|---|---|
| N01 | 完了済み20項目を履歴へ改名・移動し、現行Docsのリンクと一時NTFS受入範囲を整合させる | 完了。現行24文書のリンク検査成功 |
| N02 / [#204](https://github.com/Ningensei848/kaname/issues/204) | トップ・日付順・出典/カテゴリ別一覧を静的ページ分割。全Noteへ重複/欠落なく到達でき、2ページ目以降の直接URL・戻る・4幅・JS無効も動作する。次ページだけを低優先度で先読みし、低速回線/節約設定では抑制。初期HTML/DOM/転送とブラウザ性能を同じ公開版で比較する | ローカル完了。24件/ページ、311 Note・61一覧の全受入。検索index/初期化も遅延。[反復計測](web-preview.md#初期表示の反復計測)で初期転送76.8%・LCP中央値71.7%減 |
| N03 / [#205](https://github.com/Ningensei848/kaname/issues/205) | タグの正規化・明示同義語をWeb検索とタグ導線に適用。ai-egent / ai-agent / AIエージェントで同じNote集合を返す。C/C++/C#などは区別。既存元Markdown/Note ID/datasetは変更しない。新規生成タグも同じ辞書で統一する | ローカル完了。27 Noteの実ブラウザで5別名の検索結果一致、通常検索保持、C++/C#の生成前変換を検証。元Note bytes不変 |
| N04 / [#206](https://github.com/Ningensei848/kaname/issues/206) | 現行パッケージ/CLI/import/環境変数/Actions/通知/Docsをkanameへ統一。旧同期state・Batch照合・通知markerを読める移行互換を残し、二重課金/通知や編集消失を防ぐ。履歴資料と過去の公開版を一括改変しない | ローカル完了。全Python/Web888件・旧識別子の回帰5件・新CLI導入/設定検証・Linux同期受入成功。[移行](naming-migration.md) |
| N05 | npm依存を再監査し、既知2 advisoryの修正可否と固定例外を確認。変更時はlock/integrityとWeb全受入を更新し、未知警告は拒否する | 10/21時点で完了。実監査は既知2件だけ、当時の最新版braces3.0.3/sprintf-js1.1.3に修正なし。lock/例外不変、Node7件成功 |
| N06 | 現在の7 sourceのhealth・保留・画像観測・GCS規模を読取り確認。公開版を固定して新機能の全Web受入とGit/Release同一性を確認し、根拠と未確認範囲を記録する | 完了。7 source healthy/保留0、593成功行、GCS audit問題0。固定311 NoteをGitと実Releaseで照合し、両入力の全Web受入成功 |

各実装では全元Markdown・秘密境界・検索・リンク/アンカー・画像・375/768/1024/1440pxの既存gateを維持する。ローカル実装/受入、本番配信、IssueのClosedを区別して記録する。通常生成設定を変更せず、追加の有料生成をタスク検証に使わない。

## 今回の実施結果と本番への反映

N01〜N06の実装・ローカル受入は完了。変更はレビュー用ブランチ `codex/pagination-tags-kaname` へ集約し、[ドラフトPR #207](https://github.com/Ningensei848/kaname/pull/207)で審査中。mainへのmerge/本番deployとIssueのCloseはまだ行っていない。#204〜#206はOpenのままである。反映時は[名称移行](naming-migration.md)の旧writer終了確認と、通常Checks/固定公開版の検証を行い、公開後の配信版を照合する。

- Python/Web888件、Node7件、初回Ctrl/Cmd+K・Ctrl/Cmd+Shift+Kの実ブラウザ4通り、設定検証、checksum固定actionlint、全現行Docsのpath/見出し検査、wheel62モジュール/新CLIを確認した。旧distributionを開発venvから除去し、リポジトリ外からの新CLI起動も成功。
- content `35356be99e8c687193b043c76ff77e4c136fb568`、dataset `4bd0b553f5fc591acc4fc3297000710fd5453258d4d99aa295e7d9752438100f`、311 Noteを固定。Git入力と実Release差分深度6の復元bytesが一致。各入力で61一覧・3,153検索リンク・画像付き186 Note/453画像要求・4幅・外部要求0を検証した。
- GCSは読取りだけで1,288 object/7,742,281 bytes、最大340,679 bytes。新しい画像観測のあるreportは1件/1記事で候補0・選択0。過去の未観測を0選択とみなさず、品質一般への結論は出さない。GCS書込み・新規Gemini呼出しは0。
- 任意の期間生成上限は有効化せず、standard・30件・入力20,000文字・出力2,048 tokensを維持した。実Vaultや本番stateの移行は行っていない。

## 残余制約と条件付きの作業

2026-10-25の継続作業は[残余制約の解消作業](remaining-constraints.md)で、全項目の完了条件・現在の証拠・未確認範囲を追跡する。全体は未完了である。

- [#116](https://github.com/Ningensei848/kaname/issues/116)：CSVの残高検算に加え、期間/project/JPY/SKU内訳、旧9 runの元モデル・方式、公式Catalogの9月・10月の換算レート/円単価を確認し保存usageと比較した。請求数量・調整/税・未観測期間の帰属が残り、完全照合は未完了。別期間のCSV/SKU内訳と公開価格/契約価格/実請求を区別する。
- Graph：現321 Noteでもタイトル解決は0辺。定義先を推定せず、具体的な検索語を2つ以上共有するNoteへの別の導線を実装し、69 Note・136辺のHTML/index/実移動をローカル受入済み。
- run間private cache・差分HTML build・DB移行：全state/runsを含むGCSは約7.9MB、監査7.695秒、最大RSS約113MiB。現321件の全Web3回も同じartifact/coverageで成功、全体中央値211.307秒。現規模では追加基盤を見送り、全件整合性と全体buildを維持する。
- 同期：現行の旧名移行をLinux/実Windowsの一時NTFSでも受入済み。実Vault/利用者プラグインは対象外。
- APIと保存：standard予約・応答保存・無課金復旧・不明応答の後続run停止を実装・ローカル受入済み。明示的な再試行は1件/正の費用上限と旧履歴保全が必須。API側の厳密なexactly-once課金は未立証。
- 全要約の事実確認：原典照合は21/321件、うち7件に用語/数量/精度/提供時期・機能制約の訂正候補。hash固定計画と履歴付き適用/中断復旧を実装した。残り300件の原典比較と本番訂正は未完了。実GCS/公開Markdownは変更していない。
- npm既知警告：旧2 advisoryは公式撤回、新規TOML警告は5.0.1へ更新して実監査0件。例外規則を削除し、fixtureと固定321件のGit/実Releaseの全Web受入も成功。

<a id="ns1-google-search-fallback"></a>

受入済みの検索リンクは[NS1仕様](ns1-search-fallback.md)。現在の保証は[検証基準](verification.md)、操作は[運用手順](operations.md)を正本とする。
