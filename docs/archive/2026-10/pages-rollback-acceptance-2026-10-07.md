# O2: Pagesの履歴版切戻しと現行版復帰の受入

Issue #115。ユーザーの個別承認後、2026-10-07 22:13〜22:22 JSTに
固定した117件版へ切戻し、固定した118件版へ復帰した。両版の配信照合も成功した。
実行前の固定版・ローカル検証・失敗対応は[準備記録](pages-rollback-preparation-2026-10-07.md)にある。

## 実行と固定した版

両runはmainのpages.ymlへのworkflow_dispatch。実装commitは
`73281c78bfe314e64165eb7df632f29a05e87da6`（R5取込後）で同一。
実行前にmain/content/配信版の一致と、Daily/Pagesの競合runがないことを再確認した。
既存の認証済みGitHub CLI設定を利用し、新しい認証・Secret・IAM権限は追加していない。

| 項目 | 切戻し | 復帰 |
|---|---|---|
| run | [37626878359](https://github.com/Ningensei848/kaname/actions/runs/37626878359) | [37627470274](https://github.com/Ningensei848/kaname/actions/runs/37627470274) |
| content commit | `4205590eb588f0e0ddc991ef478c1bb2033746da` | `e3ef457f3edab5b4ca90601c922cc3b415d288ab` |
| Note数 | 117 | 118 |
| dataset digest | `7c5b877882e32855634a1706ef3b7f924a915e31750355d545d970bf0001e08f` | `22fe4c95ad6e3b25bcc24047ef6c9c4fb75eb30a1d730b1de2a3e0b2fa595898` |
| artifact digest | `0f9e212bbf8861d1667d8e62746a589b854a8d7efd698fd971651a9008e909f2` | `32883a42fc9b2f1eb91d5433a13127a58d170c311893526e0d763b08e5d990a2` |
| dispatch時刻（UTC） | 13:13:57 | 13:18:33 |
| runner配信照合成功（UTC） | 13:15:59 | 13:20:40 |
| デスクトップ独立照合成功（UTC） | 13:17:12 | 13:22:03 |

いずれも準備で固定した期待digestに一致する。
Pages実行は上記2回のみで、再実行・別版への変更は必要なかった。

## 工程別の受入

- 両build jobが成功。cleanなcontentの固定commitと公開snapshotを検査し、
  固定依存からartifactをbuild。全元Markdown・検索・リンク・出典・版表示・
  375/768/1024/1440px・非公開pathの404を実Chromiumで検証し、外部resource要求0。
- 両deploy jobが成功。Pages APIのdeployだけでなく、runnerのverify_deployment.pyが
  commit/dataset/artifact/件数と全元Markdownの配信照合に成功。
- デスクトップでも標準ライブラリだけのverify_deployment.pyを`python -I -S`から実行。
  固定した期待値で両版の公開HTTPSを検査し、全117件/118件の元Markdown hashを照合。
  配信manifest bytesは各Git commitのmanifest bytesと一致し、
  その全Note hashは各commitのGit Note blobと一致した。
- 復帰後のsite-manifestの版情報と全1,007ファイルのhash mapは、切戻し前の配信manifestと一致。
  現行配信は118件版へ戻っている。

## 維持した運用境界

実行前・切戻し後・復帰後のpublic content tipは
`e3ef457f3edab5b4ca90601c922cc3b415d288ab`のまま。
mainも実行中は上記実装commitのまま。Git履歴の巻戻し・force push・公開Git更新は0。
daily.ymlの収集/公開専用モードは使わず、記事取得・追加LLM・GCS読取り/書込みは0。
build/deployの既存job権限、Secret境界、main限定とkaname-pagesの直列化を維持した。
scheduleの停止・新しい定期実行・heartbeat再開は行っていない。

O2の切戻し/復帰受入は完了。実Batch #94、請求照合O3 #116、
利用者Vault/NTFSと実browser sourceは別の受入として残る。
