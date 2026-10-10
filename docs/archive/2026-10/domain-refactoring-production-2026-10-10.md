# 責務整理のPR・本番受入（2026-10-10）

[ローカル実装・検証](domain-refactoring-2026-10-10.md)の完了後、ユーザーから
「PR作成・マージ・本番更新まで承認」を受けて実施しました。
対象は実装PR、CI、固定公開Git版のPages更新・配信照合と、読取り専用Batch preflightです。
新規の有料収集・Batch提出、画像保存、既存Note再生成、依存更新、IAM/Secret変更は行っていません。

## PRとCI

- 実装: [PR #131](https://github.com/Ningensei848/kaname/pull/131)、main取込commit `ec8724a93826a86e7f07d4db01140dc5682ce36f`。
- [PR CI 38051225542](https://github.com/Ningensei848/kaname/actions/runs/38051225542): success。
- [main CI 38051390433](https://github.com/Ningensei848/kaname/actions/runs/38051390433): success。
- 両CIでPython 382件、設定検証、画像付きfixture 3件、最新固定content 124件のQuartz/Chromium受入が成功。
- fixtureは許可画像request 2、想定外通信0。実contentは外部resource request 0。
- 変更前後の124件版でdataset digestとartifact digestが同一。Note集合と静的成果物の両方を維持。

## Pages本番更新

[Pages run 38051565697](https://github.com/Ningensei848/kaname/actions/runs/38051565697)をmainから一度起動し、
build・deploy・配信版検証がすべてsuccessでした。GCS/Gemini資格情報を使わず、公開Git版だけからbuildしています。

| 項目 | 固定値 |
|---|---|
| content commit | `d39c2cacd087185be85c8c3564e4bd646d324cfc` |
| Note件数 | 124 |
| dataset digest | `e28d6c2bb9d3d744a3f064fc2738730e70a5cf9e8c002abf4e83076156f5c6e8` |
| artifact digest | `d3b8f81b1e624fd954d308bf65359c882455948c1dc6bc3b46bf15e797512f7a` |
| runner配信照合 | 2026-10-10 12:22:12 UTCにpassed |
| デスクトップ独立照合 | 2026-10-10 12:24:02 UTCにpassed |

公開URLは[kaname Pages](https://ningensei848.github.io/kaname/)です。
runnerはnpm入口、デスクトップは`.venv/bin/python -I -S web/verify_deployment.py`から公開HTTPSを照合しました。
commit/dataset/artifact/件数と全124件の元Markdown hashが一致し、
配信manifest bytesは固定Git版のmanifest bytesと一致、全NoteのGit blob hashとも一致しました。
更新前後のcontent commit、Note件数、dataset/artifact digestは同じです。

## 読取り専用Batch preflight

[Daily run 38051568566](https://github.com/Ningensei848/kaname/actions/runs/38051568566)を
同じmainから`batch_preflight=true`だけ指定して一度起動しました。判定はready、blockersなしです。
移設後の`techkb.batch.preflight(store, app)`が既存WIFと実GCSで成功しました。

| 項目 | 結果 |
|---|---|
| 検査時刻（UTC） | 2026-10-10T12:26:23.788947+00:00 |
| audit | success |
| audit障害 | 0 |
| 成功index行 | 306 |
| pending候補 | 62 |
| 未決済Batch台帳 | 0 |
| 未計上Batch item | 0 |
| 未完了standard usage | 0 |
| 不確実usageのrun | 0 |

成功index行と公開Note件数は異なる指標です。readyは検査時点の既存状態の判定であり、有料提出の承認や成功保存の受入を意味しません。
`batch-preflight`だけがsuccess、collect/publish/pages/notify-publicationはすべてskippedでした。
Gemini操作、記事取得、GCS書込み、export、Git更新、通知は実行していません。

## 運用境界

contentの履歴を更新・巻戻しせず、最新tipを固定してPagesだけを再ビルド・配信しました。
既存のWIF、job権限、GCS writerロック、Pages直列化を維持しています。
有料収集・再提出、GCS保存、通知、schedule変更は今回の操作に含めません。
画像入り実Note、実Batchの成功保存、請求照合は別の未受入範囲です。

今回のPR・本番受入は完了しました。現行状態は[検証・受入](../../verification.md)、
独立した未完了作業は[次の作業](../../next-work.md)で追跡します。
