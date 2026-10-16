# 履歴の保全先

2026-10-16の整理で、完了済み計画・受入記録・引継ぎ61件を現行ツリーから外した。
元ファイルは専用branch [codex/archive/pre-housekeeping-2026-10-16](https://github.com/Ningensei848/kaname/tree/codex/archive/pre-housekeeping-2026-10-16) に保全している。
保全commitは [abaef1fcbd4421ea6d55776921961e7b6a1932d5](https://github.com/Ningensei848/kaname/commit/abaef1fcbd4421ea6d55776921961e7b6a1932d5)。
branch名が変わっても固定commitの元pathから参照できる。以下のblob SHAは整理前のGit object IDである。

履歴内の未完了表記・認証状態・予算残額・次の指示は当時の情報で、現在の状態/保証や操作承認ではない。
未完了事項は[監査一覧](../repository-audit.md)、仕様・操作は[文書の入口](../README.md)を参照する。

## 完了済みの計画・作業記録

| 元path | Git blob SHA |
|---|---|
| [docs/daily-ci-reuse.md](https://github.com/Ningensei848/kaname/blob/codex/archive/pre-housekeeping-2026-10-16/docs/daily-ci-reuse.md) | `37840fa63b566e6c3710a9d2000e183069ac28dc` |
| [docs/daily-performance.md](https://github.com/Ningensei848/kaname/blob/codex/archive/pre-housekeeping-2026-10-16/docs/daily-performance.md) | `e6c6f7820c7528a1e51962246321ed3a3cd20705` |
| [docs/four-source-activation.md](https://github.com/Ningensei848/kaname/blob/codex/archive/pre-housekeeping-2026-10-16/docs/four-source-activation.md) | `f75f111faf111a61c748e5dc0d45041eaf9a0f95` |
| [docs/gcs-read-performance.md](https://github.com/Ningensei848/kaname/blob/codex/archive/pre-housekeeping-2026-10-16/docs/gcs-read-performance.md) | `18cabcbd2c3c0311333ef37d0859c5438454f0fd` |
| [docs/implementation-plan.md](https://github.com/Ningensei848/kaname/blob/codex/archive/pre-housekeeping-2026-10-16/docs/implementation-plan.md) | `5862aee3565c0e4b82a9592f3e52dde8dec97108` |
| [docs/refactoring-plan.md](https://github.com/Ningensei848/kaname/blob/codex/archive/pre-housekeeping-2026-10-16/docs/refactoring-plan.md) | `8f3e030039f0910e07bc57a8feba7520b22dece6` |
| [docs/roadmap.md](https://github.com/Ningensei848/kaname/blob/codex/archive/pre-housekeeping-2026-10-16/docs/roadmap.md) | `985ec956f3daf4e182f6f654bfc2574a5c1418eb` |
| [docs/source-onboarding.md](https://github.com/Ningensei848/kaname/blob/codex/archive/pre-housekeeping-2026-10-16/docs/source-onboarding.md) | `b3065d831ed8b60440bf233543c757d9e22d97c0` |
| [docs/source-recovery.md](https://github.com/Ningensei848/kaname/blob/codex/archive/pre-housekeeping-2026-10-16/docs/source-recovery.md) | `beedd9bb96eaef20415a48819d1f8fe0299d4139` |
| [docs/web-transport-performance.md](https://github.com/Ningensei848/kaname/blob/codex/archive/pre-housekeeping-2026-10-16/docs/web-transport-performance.md) | `97fe37e4d45f36186521584c65562b708717e5bb` |
| [docs/web-validation-performance.md](https://github.com/Ningensei848/kaname/blob/codex/archive/pre-housekeeping-2026-10-16/docs/web-validation-performance.md) | `e48c96bb6e9e88115dd8d2f1666a50a6c228e126` |

## 過去の証拠・引継ぎ

旧F1〜F7、R1〜R5、Batch/画像/NS1/公開/性能改善の証拠をまとめて保全した。
再現scriptも履歴の一部であり、現行のpassing suiteではない。

| 元path | Git blob SHA |
|---|---|
| [acceptance-note-quality-2026-10-01.md](https://github.com/Ningensei848/kaname/blob/codex/archive/pre-housekeeping-2026-10-16/docs/archive/2026-10/acceptance-note-quality-2026-10-01.md) | `f2512f3abb2a78d5ad60cad15835181e676b7057` |
| [actions-cost-evidence-2026-10-11.json](https://github.com/Ningensei848/kaname/blob/codex/archive/pre-housekeeping-2026-10-16/docs/archive/2026-10/actions-cost-evidence-2026-10-11.json) | `c70087b77233d3d52f872de098aec88d9bb52b3b` |
| [article-images-2026-10-10.md](https://github.com/Ningensei848/kaname/blob/codex/archive/pre-housekeeping-2026-10-16/docs/archive/2026-10/article-images-2026-10-10.md) | `962861c26e84177b283449d1e2ff828423e20e50` |
| [batch-acceptance-2026-10-10.md](https://github.com/Ningensei848/kaname/blob/codex/archive/pre-housekeeping-2026-10-16/docs/archive/2026-10/batch-acceptance-2026-10-10.md) | `dba43807839f50f23e44fc96caca2cd611131010` |
| [batch-acceptance-preparation-2026-10-07.md](https://github.com/Ningensei848/kaname/blob/codex/archive/pre-housekeeping-2026-10-16/docs/archive/2026-10/batch-acceptance-preparation-2026-10-07.md) | `4dcbff9d39c792c8f4fa37b0f117b14db4c62b13` |
| [batch-images-type-diagnosis-2026-10-11.md](https://github.com/Ningensei848/kaname/blob/codex/archive/pre-housekeeping-2026-10-16/docs/archive/2026-10/batch-images-type-diagnosis-2026-10-11.md) | `000b2933a643e646e181b49c7660569f472c111d` |
| [batch-preflight-acceptance-2026-10-10.md](https://github.com/Ningensei848/kaname/blob/codex/archive/pre-housekeeping-2026-10-16/docs/archive/2026-10/batch-preflight-acceptance-2026-10-10.md) | `eb43611bab35c1ee3cb58d0a6fd0a72e44f0171a` |
| [batch-preflight-workflow-fix-2026-10-08.md](https://github.com/Ningensei848/kaname/blob/codex/archive/pre-housekeeping-2026-10-16/docs/archive/2026-10/batch-preflight-workflow-fix-2026-10-08.md) | `b562b30a4a7f6132df7b919751118166c1a04e81` |
| [batch-prompt-contract-acceptance-2026-10-11.md](https://github.com/Ningensei848/kaname/blob/codex/archive/pre-housekeeping-2026-10-16/docs/archive/2026-10/batch-prompt-contract-acceptance-2026-10-11.md) | `292bb8183d5b92158c4205e6f3e2a70f2c3a2e7b` |
| [daily-ci-reuse-acceptance-2026-10-15.json](https://github.com/Ningensei848/kaname/blob/codex/archive/pre-housekeeping-2026-10-16/docs/archive/2026-10/daily-ci-reuse-acceptance-2026-10-15.json) | `6ecde8e3e2b2d52e90f73d901c090be47c2778d5` |
| [daily-performance-after-2026-10-12.json](https://github.com/Ningensei848/kaname/blob/codex/archive/pre-housekeeping-2026-10-16/docs/archive/2026-10/daily-performance-after-2026-10-12.json) | `6aa4f6fab4086cd4e569bda315895579b1491ca4` |
| [daily-performance-before-2026-10-12.json](https://github.com/Ningensei848/kaname/blob/codex/archive/pre-housekeeping-2026-10-16/docs/archive/2026-10/daily-performance-before-2026-10-12.json) | `18ea1ac07239d6a211f2387de337002f5f0d15be` |
| [domain-refactoring-2026-10-10.md](https://github.com/Ningensei848/kaname/blob/codex/archive/pre-housekeeping-2026-10-16/docs/archive/2026-10/domain-refactoring-2026-10-10.md) | `5d2d48fced938611d0aabb980107379371d8e416` |
| [domain-refactoring-production-2026-10-10.md](https://github.com/Ningensei848/kaname/blob/codex/archive/pre-housekeeping-2026-10-16/docs/archive/2026-10/domain-refactoring-production-2026-10-10.md) | `480112e448dfc6f649eb76f4bda568aa4e1df68d` |
| [gcs-read-acceptance-2026-10-15.json](https://github.com/Ningensei848/kaname/blob/codex/archive/pre-housekeeping-2026-10-16/docs/archive/2026-10/gcs-read-acceptance-2026-10-15.json) | `1fb0ab28c459a834613123a7817883e85b1292db` |
| [gcs-read-local-2026-10-15.json](https://github.com/Ningensei848/kaname/blob/codex/archive/pre-housekeeping-2026-10-16/docs/archive/2026-10/gcs-read-local-2026-10-15.json) | `5dc156c9f10eecf82c9b1070ee8b471699d94ef4` |
| [glucofm-image-repair-2026-10-11.md](https://github.com/Ningensei848/kaname/blob/codex/archive/pre-housekeeping-2026-10-16/docs/archive/2026-10/glucofm-image-repair-2026-10-11.md) | `3e96b1f60e28e04d322ac361e01ec7eec85603fb` |
| [google-research-body-extraction-2026-10-10.md](https://github.com/Ningensei848/kaname/blob/codex/archive/pre-housekeeping-2026-10-16/docs/archive/2026-10/google-research-body-extraction-2026-10-10.md) | `feb0531ee6f5f241107121ef0943c9161113adfd` |
| [handoff-review-2026-10-04.md](https://github.com/Ningensei848/kaname/blob/codex/archive/pre-housekeeping-2026-10-16/docs/archive/2026-10/handoff-review-2026-10-04.md) | `6fa6ca5b402b1f2f15339b459a4c81a3dce85a99` |
| [image-candidate-text-matching-2026-10-11.md](https://github.com/Ningensei848/kaname/blob/codex/archive/pre-housekeeping-2026-10-16/docs/archive/2026-10/image-candidate-text-matching-2026-10-11.md) | `9349f0bbe456e705a54b1bd8f2ea9dbfe6100d58` |
| [new-only-acceptance-2026-10-12.json](https://github.com/Ningensei848/kaname/blob/codex/archive/pre-housekeeping-2026-10-16/docs/archive/2026-10/new-only-acceptance-2026-10-12.json) | `25facd122d742db622acec124acc8f8237f5d013` |
| [ns1-plan-2026-10-12.md](https://github.com/Ningensei848/kaname/blob/codex/archive/pre-housekeeping-2026-10-16/docs/archive/2026-10/ns1-plan-2026-10-12.md) | `f8d2cb9adf963617ec56f226c5a9433273401db0` |
| [output-recovery-acceptance-2026-10-13.json](https://github.com/Ningensei848/kaname/blob/codex/archive/pre-housekeeping-2026-10-16/docs/archive/2026-10/output-recovery-acceptance-2026-10-13.json) | `b36771ab051f8bfc41cc57dd80659b226be32880` |
| [p1-p4-implementation-2026-10-11.md](https://github.com/Ningensei848/kaname/blob/codex/archive/pre-housekeeping-2026-10-16/docs/archive/2026-10/p1-p4-implementation-2026-10-11.md) | `bfc04c814e81e2f880dceff9af69213f7f996a60` |
| [pages-rollback-acceptance-2026-10-07.md](https://github.com/Ningensei848/kaname/blob/codex/archive/pre-housekeeping-2026-10-16/docs/archive/2026-10/pages-rollback-acceptance-2026-10-07.md) | `45dbc7838337ed57786a287ece226744610062d2` |
| [pages-rollback-preparation-2026-10-07.md](https://github.com/Ningensei848/kaname/blob/codex/archive/pre-housekeeping-2026-10-16/docs/archive/2026-10/pages-rollback-preparation-2026-10-07.md) | `3a733667495531ed86ee9aec315cdd95ea4c8762` |
| [phase2-implementation-plan.md](https://github.com/Ningensei848/kaname/blob/codex/archive/pre-housekeeping-2026-10-16/docs/archive/2026-10/phase2-implementation-plan.md) | `07e527329fdbe6cd6d17cfc7b0694ed55bc43f2d` |
| [project-review-2026-10-04.md](https://github.com/Ningensei848/kaname/blob/codex/archive/pre-housekeeping-2026-10-16/docs/archive/2026-10/project-review-2026-10-04.md) | `2ce30834309421e5b915ae68ee860e3047fd06b2` |
| [publication-implementation-plan.md](https://github.com/Ningensei848/kaname/blob/codex/archive/pre-housekeeping-2026-10-16/docs/archive/2026-10/publication-implementation-plan.md) | `737af06cd70892a3fe5ef210cee180382f96cf69` |
| [refactoring-handoff-2026-10-06.md](https://github.com/Ningensei848/kaname/blob/codex/archive/pre-housekeeping-2026-10-16/docs/archive/2026-10/refactoring-handoff-2026-10-06.md) | `791c8fb371ae33632906540f6c4a350494fcde76` |
| [refactoring-plan-r1-r5.md](https://github.com/Ningensei848/kaname/blob/codex/archive/pre-housekeeping-2026-10-16/docs/archive/2026-10/refactoring-plan-r1-r5.md) | `3af8f96c9fe08d31c89c4e912159d8208dba33c4` |
| [refactoring-r1-2026-10-06.md](https://github.com/Ningensei848/kaname/blob/codex/archive/pre-housekeeping-2026-10-16/docs/archive/2026-10/refactoring-r1-2026-10-06.md) | `1a9d62d4e4d5c6caa2c762cbc3a5461ae0032207` |
| [refactoring-r2-2026-10-07.md](https://github.com/Ningensei848/kaname/blob/codex/archive/pre-housekeeping-2026-10-16/docs/archive/2026-10/refactoring-r2-2026-10-07.md) | `4a94d0a1b839cd7b51b210525b45964d1d1950d0` |
| [refactoring-r3-2026-10-07.md](https://github.com/Ningensei848/kaname/blob/codex/archive/pre-housekeeping-2026-10-16/docs/archive/2026-10/refactoring-r3-2026-10-07.md) | `a68582dfe572d780661f3c49d6998ed608ec48a1` |
| [refactoring-r4-2026-10-07.md](https://github.com/Ningensei848/kaname/blob/codex/archive/pre-housekeeping-2026-10-16/docs/archive/2026-10/refactoring-r4-2026-10-07.md) | `53cd11120886c6b298d551048b266f5a70481e48` |
| [refactoring-r5-2026-10-07.md](https://github.com/Ningensei848/kaname/blob/codex/archive/pre-housekeeping-2026-10-16/docs/archive/2026-10/refactoring-r5-2026-10-07.md) | `cf49832b97eebbddbb1e50ca905cf8f7459cccbd` |
| [release-distribution-acceptance-2026-10-13.json](https://github.com/Ningensei848/kaname/blob/codex/archive/pre-housekeeping-2026-10-16/docs/archive/2026-10/release-distribution-acceptance-2026-10-13.json) | `f215ca74c62006d39617dd9ec7ef87d86d070b2e` |
| [release-gcs-independent-acceptance-2026-10-13.json](https://github.com/Ningensei848/kaname/blob/codex/archive/pre-housekeeping-2026-10-16/docs/archive/2026-10/release-gcs-independent-acceptance-2026-10-13.json) | `9d902946a63b92647750f0a985d238c3607f4b94` |
| [review-prompt-2026-10-04.md](https://github.com/Ningensei848/kaname/blob/codex/archive/pre-housekeeping-2026-10-16/docs/archive/2026-10/review-prompt-2026-10-04.md) | `b97344a0ba508079c050099cdbdc58191f9263bd` |
| [review-remediation-2026-10-04.md](https://github.com/Ningensei848/kaname/blob/codex/archive/pre-housekeeping-2026-10-16/docs/archive/2026-10/review-remediation-2026-10-04.md) | `d784cab46929f0e5fab6b1aac06bd0b741f8fc2d` |
| [review-reproductions-2026-10-04.py](https://github.com/Ningensei848/kaname/blob/codex/archive/pre-housekeeping-2026-10-16/docs/archive/2026-10/review-reproductions-2026-10-04.py) | `5a7960e3e9906a95bccf02bbb6881e6503a6cb2f` |
| [schedule-acceptance-2026-10-07.md](https://github.com/Ningensei848/kaname/blob/codex/archive/pre-housekeeping-2026-10-16/docs/archive/2026-10/schedule-acceptance-2026-10-07.md) | `549ddc1f1dd15280d0035695611ba467e07b107a` |
| [source-usage-review-2026-10-01.md](https://github.com/Ningensei848/kaname/blob/codex/archive/pre-housekeeping-2026-10-16/docs/archive/2026-10/source-usage-review-2026-10-01.md) | `91e94e13b419c8e00d592dd865acf5cabcc05515` |
| [verification-before-domain-refactoring-2026-10-10.md](https://github.com/Ningensei848/kaname/blob/codex/archive/pre-housekeeping-2026-10-16/docs/archive/2026-10/verification-before-domain-refactoring-2026-10-10.md) | `3b2f9795c7c39dfd1a054679e90cfbbe94b93654` |
| [verification.md](https://github.com/Ningensei848/kaname/blob/codex/archive/pre-housekeeping-2026-10-16/docs/archive/2026-10/verification.md) | `3f0ddb5b02dec22be30af86793d5e604da30a8a5` |
| [web-transport-acceptance-2026-10-13.json](https://github.com/Ningensei848/kaname/blob/codex/archive/pre-housekeeping-2026-10-16/docs/archive/2026-10/web-transport-acceptance-2026-10-13.json) | `1396046d7f6730ffa5ad5104c029532903460712` |
| [web-transport-local-2026-10-13.json](https://github.com/Ningensei848/kaname/blob/codex/archive/pre-housekeeping-2026-10-16/docs/archive/2026-10/web-transport-local-2026-10-13.json) | `315b8e1e8da225fc67e86d9c913dd77f7d86a0ad` |
| [web-validation-acceptance-2026-10-13.json](https://github.com/Ningensei848/kaname/blob/codex/archive/pre-housekeeping-2026-10-16/docs/archive/2026-10/web-validation-acceptance-2026-10-13.json) | `5cc583a8436bc7fa56da1bfaf6e05d93edd7423b` |
| [web-validation-failed-attempt-2026-10-13.json](https://github.com/Ningensei848/kaname/blob/codex/archive/pre-housekeeping-2026-10-16/docs/archive/2026-10/web-validation-failed-attempt-2026-10-13.json) | `224cd1ba6717e57d741a72f40b9ca73139868dd8` |
| [web-validation-local-2026-10-13.json](https://github.com/Ningensei848/kaname/blob/codex/archive/pre-housekeeping-2026-10-16/docs/archive/2026-10/web-validation-local-2026-10-13.json) | `d306c7c2e0da4401f312fdf0987478bcd37b55d8` |

## 現行文書から外した重複進捗

今回短縮したREADME/next-work/verification/日次公開/Release配布/新規限定/検索/Graph/出力復旧などの旧全文も、同じ保全commitの元pathに残る。
[整理前の文書一覧](https://github.com/Ningensei848/kaname/blob/codex/archive/pre-housekeeping-2026-10-16/docs/README.md)と[旧履歴索引](https://github.com/Ningensei848/kaname/blob/codex/archive/pre-housekeeping-2026-10-16/docs/archive/README.md)から辿れる。
仕様/操作として今も必要な説明は現行文書へ維持した。失敗時の未完了事項は監査一覧へ引き継いだ。

## 復元する

```bash
git fetch origin codex/archive/pre-housekeeping-2026-10-16
# 必要なpathだけ現在の作業ブランチへ復元する。mainへの自動適用はしない。
git restore --source=FETCH_HEAD -- docs/archive/2026-10/対象ファイル.md
```

専用archive branchはこの整理の保全先であり、通常のmerged作業branch削除の対象へ混ぜない。
新しい日次記録はmainへ蓄積せず、保存が必要な証拠だけarchive branchへ追記して索引を更新する。

## 完了した画像補完計画

GlucoFMの単発計画は[元configの保全版](https://github.com/Ningensei848/kaname/blob/codex/archive/pre-housekeeping-2026-10-16/config/image-repairs/eff25c6d47cbba54dd762e9318eeffd267970fbff2b9359427e3000d08ac7419.json)を参照。
現行の実configからは除去し、schema/workflow回帰だけを `tests/fixtures/image-repair-plan.json` に固定した。
