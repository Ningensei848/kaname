# O2: Pagesの切戻し・復帰の実行準備

以下は実行前の準備記録。その後、個別承認を受けて[実切戻し・復帰の受入](pages-rollback-acceptance-2026-10-07.md)を完了した。

Issue #115。R5 / PR #123は取込済み。実装mainは
`73281c78bfe314e64165eb7df632f29a05e87da6`で、[Checks](https://github.com/Ningensei848/kaname/actions/runs/37624432215)も成功。
この記録は準備の証拠であり、実切戻し・復帰の受入成功ではない。
Pages操作は個別承認後に実行する。

## 固定した二つの版

公開URLは`https://ningensei848.github.io/kaname/`。
2026-10-07 21:56 JSTの確認で、content tipと現行配信commitはいずれも復帰版に一致した。
切戻し版はcontent履歴上の直前の成功祖先である。

| 項目 | 切戻し版 | 復帰版 |
|---|---|---|
| content commit | `4205590eb588f0e0ddc991ef478c1bb2033746da` | `e3ef457f3edab5b4ca90601c922cc3b415d288ab` |
| Note数 | 117 | 118 |
| dataset digest | `7c5b877882e32855634a1706ef3b7f924a915e31750355d545d970bf0001e08f` | `22fe4c95ad6e3b25bcc24047ef6c9c4fb75eb30a1d730b1de2a3e0b2fa595898` |
| 期待artifact digest（UTC） | `0f9e212bbf8861d1667d8e62746a589b854a8d7efd698fd971651a9008e909f2` | `32883a42fc9b2f1eb91d5433a13127a58d170c311893526e0d763b08e5d990a2` |
| 既知の配信成功run | [37434000683](https://github.com/Ningensei848/kaname/actions/runs/37434000683) | [37557574613](https://github.com/Ningensei848/kaname/actions/runs/37557574613) |

復帰版は切戻し版に比べてNoteが1件追加され、共通29件のNote bytesが更新されている。
切戻し中は公開Webにその117件の履歴版が表示される。
Gitのcontent履歴やGCSのNote/indexは変更しない。

## ローカル・現行配信の照合

Python 3.12.13 / Node 24.15.0 / 固定lock / 実Chromium。
各contentを独立したclean checkoutに固定し、最新mainの同じコードで順にbuildした。
記事取得、LLM、GCS読取り/書込み、公開Git更新、Pages deployはこの準備で行っていない。
公開HTTPSと公開Gitだけを読取り、本文や認証情報を記録に転載しない。

- 両版のbuild_pages.py / check_pages.pyが成功。
- 全元Markdown bytes/hash、全ローカルリンク、出典、検索、版表示、
  375/768/1024/1440px、非公開pathの404、外部resource要求0を確認。
- 各Git commitのmanifest bytesと、artifactに含むmanifestが一致。
  全117件/118件のGit Note blobとartifactの元Markdown bytes/hashも一致。
- UTCのローカルartifact digestは上記の既知の配信digestに両方とも一致。
- 復帰版site-manifestの版情報と全1,007ファイルのhash mapが現行配信manifestと一致。
- 現行HTTPSへ標準ライブラリだけのverify_deployment.pyを`python -I -S`で実行。
  上記復帰版のcommit/dataset/artifact/118件と全元Markdown配信がpassed。
- actionlintとdiff検査が成功。準備中にDaily/Pagesの実行中runはない。

ローカルの通常NodeはAsia/Tokyo、runnerはUTCである。
通常のローカルbuildでは一部HTMLの日付表示が異なり、artifact digestも異なる。
一例は同じ`2026-10-01T15:06:27.190Z`の表示がUTCでは10月1日、JSTでは10月2日になる。
CIと同じUTCで固定Nodeを起動する一時wrapperをPATHの先頭に置いて再buildした結果、
両版とも配信digestに一致した。repoのbuildコード、ホストのtimezone、依存は変更していない。

一時checkoutは`/tmp/kaname-o2-rollback-content`と`/tmp/kaname-r3-content`。
UTC artifactはignoredの`web/.cache/o2-rollback-utc-artifact`と
`web/.cache/o2-restore-utc-artifact`へ保存した。

## 承認後の実行手順

実施候補は**2026-10-07 22:10〜23:00 JST（13:10〜14:00 UTC）**。
次の通常scheduleは10月8日07:17 JSTのため、この候補枠とは重ならない。
scheduleには遅延があり得るので、開始直前に実行中・queued・waitingのDaily/Pagesも確認する。
枠内に承認・事前確認がそろわなければ着手せず、次の枠を提示する。
新しい定期実行、既存scheduleの停止、heartbeatの再開は行わない。

1. mainのbuild/workflow依存が準備時と一致することを確認する。
   この準備文書だけのmergeは許容するが、実装が変わっていれば再buildして計画を更新する。
   content tip・配信commit/dataset/artifact/118件が上記復帰版のままであり、
   Daily/Pagesの競合する実行がないことを再確認する。
   contentや配信版が変わっていれば、旧復帰先のまま開始しない。
2. `main`の**Publish Notes to Pages**（pages.yml）を手動実行し、
   `content_commit=4205590eb588f0e0ddc991ef478c1bb2033746da`を明示する。
   daily.ymlやpublish_onlyは使わない。build/deployとrunnerの配信版照合の結果を確認する。
3. 独立したHTTPS照合で、切戻し版の固定commit/dataset/artifact/117件、
   Git manifest bytes、全元Markdown hashを確認する。期待値不一致を成功扱いにしない。
4. 同じ`main`のpages.ymlへ
   `content_commit=e3ef457f3edab5b4ca90601c922cc3b415d288ab`を明示して復帰する。
   build/deployと独立HTTPS照合で固定commit/dataset/artifact/118件を確認する。
5. public content tipが変更されていないことも確認し、各run ID、実装commit、
   content commit/dataset/artifact/件数、配信照合結果を月別archiveへ追記する。
   現行受入文書には状態変更だけを反映し、両版の配信照合成功後にIssue #115を閉じる。

通常は切戻しと復帰の2回のPages実行になる。記事取得・LLM・GCS更新・Git履歴の巻戻しは0。
`kaname-pages`の直列化とmain限定、既存のbuild/deploy権限を維持する。

## 復帰を優先する失敗対応

切戻しrunが失敗しても、deployが始まった場合や配信版が不明な場合は、
上記の固定復帰commitで復帰を実行し、実際の配信版まで確認する。
切戻しの配信照合が不成功の場合も復帰を優先し、O2の成功とはしない。
復帰runが失敗した場合は同じ固定復帰commitで再試行する。
新たなcontent版の生成、GCS/Gitの巻戻し、別の復帰先への自動変更は行わない。
復帰先の配信照合が成功するまでIssueを閉じない。

**準備時点で未実施:** 個別承認、実切戻しdeploy、実復帰deployとその配信照合。
準備完了だけでこれらの完了条件にはチェックを付けない。
