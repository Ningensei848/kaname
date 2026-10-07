# O1: 公開接続後の通常schedule受入

Issue #109の受入を、2026-10-07の自然な日次実行で確認した。
新しい定期実行、手動収集、有料API呼出し、GCS書込み、deployはこの受入作業から行っていない。

## 固定した版と実行

- [Daily TechKB run 37557574613](https://github.com/Ningensei848/kaname/actions/runs/37557574613): event=schedule、main。
- 実装commit: `a783aa2efd7adfe28b765051360a8eb132857b91`（R1を含む）。
- 開始: 2026-10-07 10:32 JST。設定時刻からの遅延は失敗扱いしない。
- content commit: `e3ef457f3edab5b4ca90601c922cc3b415d288ab`。
- Note数: 118。
- dataset digest: `22fe4c95ad6e3b25bcc24047ef6c9c4fb75eb30a1d730b1de2a3e0b2fa595898`。
- 配信artifact digest: `32883a42fc9b2f1eb91d5433a13127a58d170c311893526e0d763b08e5d990a2`。

## 工程ごとの証拠

| 工程 | 結果 |
|---|---|
| collect | standard収集成功。保存成功、LLM失敗0、usage不明0、failures空。通常収集のusage予約/保存と最終report保存が完了する実装経路を通過 |
| audit | 保存状態の検査成功、issues空 |
| cost/notify | 費用reportはsuccess、uncertain/incomplete standard runは0。必要通知の判定・送信工程成功 |
| export | 検証済み118件のsnapshotを生成、上記dataset digest一致 |
| publish | contentへのnon-force更新とfresh cloneの全bytes照合が成功 |
| Pages build | 同じcontent commitからbuild。artifact検証と実Chromium検査成功、external_requests=0 |
| Pages deploy | deploy成功。runnerの配信版照合が118件の全元Markdown hashを確認 |

collect、publish、pages/build、pages/deployの各jobはsuccess。
notify-publicationは障害がないためskip。請求明細との照合はO3であり、費用reportのsuccessを請求受入とは扱わない。

## デスクトップ側からの独立照合

既存の標準ライブラリだけの`web/verify_deployment.py`を公開HTTPSへ実行し、
固定content commit、dataset/artifact digest、fixture=false、Note数118、
全元Markdown、トップ、版表示、代表Note HTMLのhashを確認した。
さらに公開Git commitのmanifest bytesと配信`markdown/manifest.json`が一致し、
Gitの全118件のNote blobのhashがそのmanifestと一致することを確認した。
本文、認証情報、請求金額、非公開storage識別子はこの記録に転載しない。

O1の通常schedule受入は完了。R1取込済みと合わせ、R2（Issue #111）の開始条件を満たす。
Pages履歴版の実切戻し/復帰（O2）、実Batch成功保存（#94）、請求照合（O3）は独立した未受入として維持する。
