# GCP・GitHub 初期設定（管理者が一度実行）

以下は本番受入環境 `q4rs-project` / `Ningensei848/kaname` の確定値です。
別環境へ展開する場合は、プロジェクト・bucket・GitHub repositoryの値を置換してください。
この納品物からGitHub repositoryは作成していません。
実行用サービスアカウントにOwner/Editor/Storage Adminを与えません。

## 1. 変数とサービス

```bash
export TECHKB_PROJECT_ID='q4rs-project'
export TECHKB_BUCKET='kaname-q4rs-project-ningensei848'
export TECHKB_REPO='Ningensei848/kaname'
# GitHub API/設定から取得する不変の数値ID。repository移譲時も確認すること。
export TECHKB_REPO_ID='1258231039'
export TECHKB_OWNER_ID='20794309'
export TECHKB_BRANCH='main'
export TECHKB_REGION='asia-northeast1'
export TECHKB_SA="kaname-runner@${TECHKB_PROJECT_ID}.iam.gserviceaccount.com"

gcloud services enable storage.googleapis.com iam.googleapis.com \
  iamcredentials.googleapis.com sts.googleapis.com --project="$TECHKB_PROJECT_ID"

gcloud iam service-accounts create kaname-runner \
  --project="$TECHKB_PROJECT_ID" --display-name='Kaname runner'

gcloud storage buckets create "gs://${TECHKB_BUCKET}" \
  --project="$TECHKB_PROJECT_ID" --location="$TECHKB_REGION" \
  --uniform-bucket-level-access

gcloud storage buckets update "gs://${TECHKB_BUCKET}" --public-access-prevention
```

既存bucketの場合は新規作成を省略し、UBLAとPublic Access Prevention=enforcedを有効化します。
`allUsers` / `allAuthenticatedUsers` へのgrantを行わず、既存公開grantがあれば管理者が除去してください。

## 2. 最小カスタムロールをbucketだけへ付与

実装はbucket設定確認、objectのlist/get/create/overwriteだけを使います。
GCSで既存objectを置換するためにはdelete権限も必要です。

```bash
gcloud iam roles create kanameObjectWriter --project="$TECHKB_PROJECT_ID" \
  --title='Kaname bucket object writer' \
  --permissions='storage.buckets.get,storage.objects.list,storage.objects.get,storage.objects.create,storage.objects.delete' \
  --stage=GA

gcloud storage buckets add-iam-policy-binding "gs://${TECHKB_BUCKET}" \
  --member="serviceAccount:${TECHKB_SA}" \
  --role="projects/${TECHKB_PROJECT_ID}/roles/kanameObjectWriter"
```

プロジェクト全体へのStorage Object Adminは不要です。
他のIAM設定・bucket作成権限は実行用アカウントに与えません。

## 3. Workload Identity Federation

```bash
TECHKB_PROJECT_NUMBER="$(gcloud projects describe "$TECHKB_PROJECT_ID" --format='value(projectNumber)')"

gcloud iam workload-identity-pools create github-actions \
  --project="$TECHKB_PROJECT_ID" --location=global --display-name='Kaname GitHub Actions'

gcloud iam workload-identity-pools providers create-oidc github-repo \
  --project="$TECHKB_PROJECT_ID" --location=global \
  --workload-identity-pool=github-actions \
  --issuer-uri='https://token.actions.githubusercontent.com' \
  --attribute-mapping='google.subject=assertion.sub,attribute.repository_id=assertion.repository_id,attribute.repository_owner_id=assertion.repository_owner_id' \
  --attribute-condition="assertion.repository_id == '${TECHKB_REPO_ID}' && assertion.repository_owner_id == '${TECHKB_OWNER_ID}' && assertion.ref == 'refs/heads/${TECHKB_BRANCH}' && assertion.workflow_ref == '${TECHKB_REPO}/.github/workflows/daily.yml@refs/heads/${TECHKB_BRANCH}'"

gcloud iam service-accounts add-iam-policy-binding "$TECHKB_SA" \
  --project="$TECHKB_PROJECT_ID" --role=roles/iam.workloadIdentityUser \
  --member="principalSet://iam.googleapis.com/projects/${TECHKB_PROJECT_NUMBER}/locations/global/workloadIdentityPools/github-actions/attribute.repository_id/${TECHKB_REPO_ID}"
```

repository数値ID、owner数値ID、branch、workflowを制限します。
フォーク/別ブランチからのWIF利用は許可しません。Service Account JSONキーを作成しません。

## 4. GitHubのVariablesとSecret

新規または既存Private repositoryへコードを登録して、以下を設定します。

| 種別 | 名前 | 値 |
|---|---|---|
| Variable | `GCP_WORKLOAD_IDENTITY_PROVIDER` | `projects/137544258857/locations/global/workloadIdentityPools/github-actions/providers/github-repo` |
| Variable | `GCP_SERVICE_ACCOUNT` | `kaname-runner@q4rs-project.iam.gserviceaccount.com` |
| Variable | `GCS_BUCKET` | `kaname-q4rs-project-ningensei848`（gs://なし） |
| Secret | `GEMINI_API_KEY` | Gemini Developer APIキー |

APIキーは該当APIへの制限を設定し、Geminiの対象プロジェクトでモデル利用・請求状態を確認します。
コード/README/fixture/ログにキーを入力しないでください。
Gemini API Keyの認証とGCS WIFは別経路です。
workflowは依存のインストール・テストを認証前に行い、WIF認証後に収集を開始します。
デフォルトブランチにworkflowを置くとscheduleが有効になります。

## 5. 最初の実環境受入

1. sourceのrobots・利用条件を確認。
2. app.yamlの `max_calls_per_run` を最初だけ1へ減らしてcommit。
3. GitHub Actions → Daily TechKB → Run workflow。
4. logsと `runs/YYYY/MM/*.json` のstatus、失敗stage、usageを確認。
5. `notes/` の日本語・YAML・原文を確認。月次indexとpendingを確認。
6. 同一記事だけを対象に再実行し、LLM呼出ゼロでraw/content duplicateとなることを確認。
7. 実運用ではfeed更新や残pendingがあるため、再実行で新記事のLLM呼出が発生するのは正常。
8. 上限を30へ戻し、07:17 JSTのscheduled runを確認してPhase 1受入完了とする。

## ローカル読取りdry-run

ADCを使う場合は管理者が読取り権限を持つアカウントで
`gcloud auth application-default login` を実行し、`GCS_BUCKET` を指定します。
GCSStoreはbucket設定確認も行うため、読取り主体には `storage.buckets.get` とobject get/listが必要です。
本番writerと同時にローカル `run` を実行しないでください。

## 公式参照

- [WIFとdeployment pipelines](https://docs.cloud.google.com/iam/docs/workload-identity-federation-with-deployment-pipelines)
- [google-github-actions/auth](https://github.com/google-github-actions/auth)
- [Cloud Storage preconditions](https://docs.cloud.google.com/storage/docs/request-preconditions)
- [Public access prevention](https://docs.cloud.google.com/storage/docs/public-access-prevention)
- [Uniform bucket-level access](https://docs.cloud.google.com/storage/docs/uniform-bucket-level-access)
