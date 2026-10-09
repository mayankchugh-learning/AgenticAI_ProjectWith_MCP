# DEPLOYMENT — Cloud Run (asia-east2, Hong Kong): staging and production

Target, as decided by the owner: **Google Cloud Run in `asia-east2`**, **staging and production as two services**, images in **Artifact Registry**, secrets in **Secret Manager**, deployed from **GitHub Actions with Workload Identity Federation (WIF)**. Nothing here was run against Google Cloud. Commands are for Git Bash; replace `<...>`. No secret values appear in this document.

Status marks: **verified** = I ran it in this repo (cited). **NOT VERIFIED** = written from the code, the existing workflow or Google Cloud knowledge, never run.

Assumptions I made (the owner did not state them; change them if wrong):
- **One GCP project** holds both services (`<project>`), with separate resources per environment, named with a `-staging` / `-prod` suffix.
- Service names: `meridian-ai-staging`, `meridian-ai-prod`.

## 0. Blockers and differences to settle before the first deploy

1. **Vertex AI Vector Search in `asia-east2`: NOT VERIFIED.** The app uses one region for Vertex (`GCP_REGION`, `rag/vector_store.py:15-19`), and the index, the index endpoint and `GCP_REGION` must all be in the same region. Before anything else, confirm that Vector Search (and the embedding model `text-embedding-005`, and the Gemini model) is offered in `asia-east2` (Google Cloud locations page, or `gcloud ai index-endpoints list --region=asia-east2` in a project with the API enabled). If it is not, Cloud Run can stay in Hong Kong while `GCP_REGION` and the index use another region (for example `asia-southeast1`); the only code-free change is the env var. Cross-region calls add latency and egress cost.
2. **The Gemini API key calls Google AI Studio, not a regional Vertex endpoint** (`rag/llm.py`, key in `settings.py:27`). The region choice does not control where those prompts are processed. If data-residency is a requirement, that is a separate decision (NOT VERIFIED).
3. **`.github/workflows/deploy.yml` does not match this target.** It is manual-only (`deploy.yml:3-5`), uses one environment (`:233`), a long-lived JSON key (`GCP_CREDENTIALS_JSON`, `:28`), `us-central1` (`:9`), `gcr.io` (`:11`), the default compute service account (`:213-216`) and a public service (`:230,248-252`). It must not be used for this target. Replacing it is a change to a billed deployment path and needs owner approval; section 7 gives the proposed workflow.
4. **The app has no authentication** (`docs/AUDIT.md` A-001). Staging is private. Production access (IAM/IAP, token, or public) is an open owner decision (plan item N1). Do not add `--allow-unauthenticated` to production until it is made.

## 1. Prerequisites, accounts and least-privilege access

Accounts and tools:
- One Google Cloud project with billing enabled. A person with project-admin rights does the one-time setup (section 6).
- A GitHub repository with two **GitHub Environments**: `staging` and `production`. Add required reviewers on `production`.
- A Gemini API key per environment (separate keys so one can be revoked alone).
- Local: `gcloud`, Docker (29.2.0 verified here), `git`.

Service accounts (all in `<project>`; roles are a starting point, NOT VERIFIED as sufficient, prove them in staging):

| Service account | Used by | Roles (scoped as narrowly as shown) |
|---|---|---|
| `meridian-run-staging` | staging container | `roles/aiplatform.user` (project; Vertex calls cannot be scoped lower); `roles/storage.objectAdmin` on the staging bucket only; `roles/secretmanager.secretAccessor` on the staging secret only |
| `meridian-run-prod` | production container | the same three roles, on the production bucket and secret only |
| `gha-deploy-staging` | GitHub Actions, `staging` environment | `roles/artifactregistry.writer` on the repository; `roles/run.developer` on service `meridian-ai-staging` only; `roles/iam.serviceAccountUser` on `meridian-run-staging` only |
| `gha-deploy-prod` | GitHub Actions, `production` environment | `roles/artifactregistry.reader` on the repository; `roles/run.developer` on service `meridian-ai-prod` only; `roles/iam.serviceAccountUser` on `meridian-run-prod` only |

Design points:
- Production's deployer can **read but not write** the registry, so production only ever receives an image that was built and tested in staging.
- Neither deployer can create projects, buckets, indexes, secrets or IAM bindings. Those are done once by the human admin.
- There are no service-account key files anywhere: GitHub authenticates through WIF and the containers use their attached service account (`GCP_SERVICE_ACCOUNT_PATH` is for local runs only, `settings.py:33,58-65`).
- Do not use the default compute service account (as `deploy.yml` does).
- Granting `run.developer` on a service requires that the service already exists, so the first deploy of each service is done by the admin (section 6 step 9).

## 2. Environments and how they differ

| | staging | production |
|---|---|---|
| Cloud Run service | `meridian-ai-staging` | `meridian-ai-prod` |
| Region | `asia-east2` | `asia-east2` |
| Runtime service account | `meridian-run-staging` | `meridian-run-prod` |
| `ENVIRONMENT` value | `staging` | `production` (label only; nothing reads it, `settings.py:22`) |
| Access | private (`--no-allow-unauthenticated`); call with an identity token | owner decision pending (section 0 item 4) |
| `--max-instances` | 1 | 3 (same as `deploy.yml:232`) |
| `--min-instances` | 0 | 0 (set 1 later if cold starts matter; billed while idle) |
| Bucket | `<project>-meridian-staging` | `<project>-meridian-prod` |
| Vector index + endpoint | `financial-docs-staging` / `-endpoint-staging` | `financial-docs-prod` / `-endpoint-prod` |
| Secret | `GOOGLE_API_KEY_STAGING` | `GOOGLE_API_KEY_PROD` |
| GitHub deployment | automatic on merge to `main` | after manual approval of the same image |
| Data | disposable test PDFs | real documents |

## 3. Environment variables and secrets

Names come from `backend/config/settings.py` and `.env.example`. Missing values do not fail startup; they fail on first use (`settings.py:1-6`). `PORT` is read by the image command (`Dockerfile`, last line); Cloud Run sets it.

| Variable | Purpose | Secret? | Where it lives |
|---|---|---|---|
| `GOOGLE_API_KEY` | Gemini API key | **Yes** | Secret Manager: `GOOGLE_API_KEY_STAGING` / `GOOGLE_API_KEY_PROD`, injected with `--update-secrets=GOOGLE_API_KEY=<secret>:latest` |
| `GCP_PROJECT_ID` | project for Vertex and Storage | No | Cloud Run env var |
| `GCP_REGION` | **Vertex** region, must match the index (section 0 item 1) | No | Cloud Run env var (`asia-east2` if supported) |
| `GCS_BUCKET_NAME` | uploads and shutdown log upload | No | Cloud Run env var |
| `GCS_PREFIX` | upload folder prefix, `uploads/` | No | Cloud Run env var |
| `VECTOR_SEARCH_INDEX_ID` | Vertex index id | No | Cloud Run env var |
| `VECTOR_SEARCH_INDEX_ENDPOINT_ID` | Vertex endpoint id | No | Cloud Run env var |
| `VERTEX_LLM_MODEL_NAME` | chat model (default `gemini-3.8-flash`) | No | Cloud Run env var |
| `VERTEX_EMBEDDING_MODEL_NAME` | embedding model (default `text-embedding-005`, 768 dims, `settings.py:39`) | No | Cloud Run env var |
| `LLM_TEMPERATURE` | optional, default 0.0 | No | Cloud Run env var |
| `ENVIRONMENT` | label | No | Cloud Run env var |
| `GCP_SERVICE_ACCOUNT_PATH` | local key file path | points to a secret file | **never set on Cloud Run** |
| `PORT` | listen port, default 8080 | No | set by Cloud Run |

GitHub side (Settings, Environments): the workflow needs only identifiers, none of them secret keys. Store as **environment variables** (not secrets) on each GitHub Environment: `GCP_PROJECT_ID`, `GCP_REGION`, `WIF_PROVIDER` (full provider resource name), `DEPLOYER_SA` (the environment's deployer email). The Gemini key is **not** stored in GitHub; it lives only in Secret Manager.

Rules:
- Real values live only in Secret Manager and the Cloud Run configuration. The image contains none (verified: no `.env*` or `.git` in the image, `docs/setup-log.md` 2026-10-09).
- Never pass the key through `--set-env-vars`; it would be visible in the service description.
- Rotation: add a new secret version, then create a new revision, because `:latest` is resolved at revision start.

## 4. Build and artifact

Registry path: `asia-east2-docker.pkg.dev/<project>/meridian/meridian-ai:<tag>`

Tags, immutable, never deploy `latest`:
- `<git-sha>` (full 40-char SHA; short form is acceptable for humans) — the tag that is deployed.
- `v<MAJOR>.<MINOR>.<PATCH>` — added on release. `app_version` (`settings.py:24`, `1.0.0`) is not linked to the image, so bump both by hand.

Enable **immutable tags** on the repository so a tag can never be overwritten: `--immutable-tags` at repository creation (flag spelling NOT VERIFIED).

Base images are pinned in the `Dockerfile` (`node:20.19.5-alpine3.22`, `python:3.12.10-slim-bookworm`); the image runs as uid 10001 and has a `HEALTHCHECK` (Cloud Run ignores it and uses its own probes, section 6).

Local build (verified, `docs/setup-log.md` 2026-10-09):
```bash
SHA=$(git rev-parse HEAD)
docker build -t meridian-ai:$SHA .
```
Push (by GitHub Actions, not by hand; manual form NOT VERIFIED):
```bash
gcloud auth configure-docker asia-east2-docker.pkg.dev
docker tag meridian-ai:$SHA asia-east2-docker.pkg.dev/<project>/meridian/meridian-ai:$SHA
docker push asia-east2-docker.pkg.dev/<project>/meridian/meridian-ai:$SHA
```
Build once. Staging and production deploy the **same image digest**; production never rebuilds.

## 5. Pre-deployment checklist

Run from the repo root. These run in the workflow's `test` job (section 7) and locally.

| # | Check | Command | Status today |
|---|---|---|---|
| 1 | Backend tests | `./.venv/Scripts/python.exe -m pytest backend/tests -q` | 9 passed, no network (verified) |
| 2 | Frontend tests | `cd frontend; npm test` | 16 passed (verified) |
| 3 | Frontend type check | `cd frontend; npx tsc --noEmit -p tsconfig.app.json` | exit 0 (verified) |
| 4 | Frontend lint | `cd frontend; npm run lint` | **fails**: 9 errors, 7 warnings (verified). Do not make it a blocking CI step until the owner decides; run it as report-only |
| 5 | Python lint / types | none configured | not available |
| 6 | Dependency scan | `npm audit` in `frontend/` (report only, never `audit fix`); Python scanner (for example `pip-audit`) not installed | 33 npm findings (verified); Python NOT VERIFIED |
| 7 | Image scan | Artifact Analysis scanning on the repository, or Trivy in CI | NOT VERIFIED, not set up |
| 8 | Image builds, starts, healthy | `docker build`, `docker run --env-file .env -p 8080:8080`, wait for `healthy`, `curl localhost:8080/api/health` | passed 2026-10-09 (verified) |
| 9 | Migrations | **none**: no database. State = Vertex index + bucket objects | n/a |
| 10 | Health endpoint | `GET /api/health` returns `{"status":"ok"}` (`endpoints.py:51`), no Google call | verified in container |
| 11 | Target resources exist | index/endpoint ids set, bucket and secret exist, secret has a version | check by hand (section 6) |

## 6. First-time setup (once per project; do staging first)

Done by a human admin with a local `gcloud`. Each step says what it creates and what it may cost. Prices change and I give no figures (NOT VERIFIED); use the Google Cloud pricing pages and the calculator.

```bash
P=<project>; R=asia-east2; REPO=<github-owner>/<github-repo>
gcloud config set project $P
PN=$(gcloud projects describe $P --format='value(projectNumber)')
```

1. **Enable APIs.** Free. `run`, `artifactregistry`, `secretmanager`, `aiplatform`, `storage`, `logging`, `monitoring`, `iam`, `iamcredentials`, `sts`, `cloudresourcemanager`.
   ```bash
   gcloud services enable run.googleapis.com artifactregistry.googleapis.com secretmanager.googleapis.com \
     aiplatform.googleapis.com storage.googleapis.com logging.googleapis.com monitoring.googleapis.com \
     iam.googleapis.com iamcredentials.googleapis.com sts.googleapis.com cloudresourcemanager.googleapis.com
   ```
2. **Artifact Registry repository.** Billed for stored image size (and cross-region egress when pulled outside `asia-east2`).
   ```bash
   gcloud artifacts repositories create meridian --repository-format=docker --location=$R
   ```
3. **Service accounts.** Free.
   ```bash
   for n in meridian-run-staging meridian-run-prod gha-deploy-staging gha-deploy-prod; do
     gcloud iam service-accounts create $n; done
   gcloud projects add-iam-policy-binding $P --member serviceAccount:meridian-run-staging@$P.iam.gserviceaccount.com --role roles/aiplatform.user
   gcloud projects add-iam-policy-binding $P --member serviceAccount:meridian-run-prod@$P.iam.gserviceaccount.com --role roles/aiplatform.user
   ```
4. **Buckets**, one per environment. Billed per stored GB. Public access blocked.
   ```bash
   for e in staging prod; do
     gcloud storage buckets create gs://$P-meridian-$e --location=$R --uniform-bucket-level-access --public-access-prevention
     gcloud storage buckets add-iam-policy-binding gs://$P-meridian-$e \
       --member serviceAccount:meridian-run-$e@$P.iam.gserviceaccount.com --role roles/storage.objectAdmin
   done
   ```
   Consider a lifecycle rule to delete old `logs/` objects (logs hold user content, `docs/OPERATIONS.md` section 2).
5. **Vector Search index, endpoint, deployed index**, one set per environment. **The costly step.** Index creation takes about 25-30 minutes and deployment up to 45 (`deploy.yml:100,159`). A deployed index is billed **per hour while deployed, even with no traffic**; undeploy staging's when not in use. Complete section 0 item 1 first. Exact commands and the 768-dimension, `STREAM_UPDATE` config: `deploy.yml:68-189` (adapt names, region, bucket; it also seeds the index with `generate_json.py`). Record the printed index and endpoint ids for each environment.
6. **Secrets.** Secret Manager is cheap; Gemini usage is the real cost. Read the key from a protected file so it never reaches shell history, then delete the file.
   ```bash
   for e in STAGING PROD; do gcloud secrets create GOOGLE_API_KEY_$e --replication-policy=automatic; done
   gcloud secrets versions add GOOGLE_API_KEY_STAGING --data-file=<path-to-staging-key-file>
   gcloud secrets versions add GOOGLE_API_KEY_PROD    --data-file=<path-to-prod-key-file>
   gcloud secrets add-iam-policy-binding GOOGLE_API_KEY_STAGING --member serviceAccount:meridian-run-staging@$P.iam.gserviceaccount.com --role roles/secretmanager.secretAccessor
   gcloud secrets add-iam-policy-binding GOOGLE_API_KEY_PROD    --member serviceAccount:meridian-run-prod@$P.iam.gserviceaccount.com    --role roles/secretmanager.secretAccessor
   ```
   Secret Manager replication is `automatic` here; if data location matters, use a user-managed policy limited to `asia-east2` (NOT VERIFIED).
7. **Workload Identity Federation.** Free. Lets GitHub Actions obtain short-lived credentials with no stored key. The condition restricts it to your repository.
   ```bash
   gcloud iam workload-identity-pools create github --location=global
   gcloud iam workload-identity-pools providers create-oidc github-actions --location=global \
     --workload-identity-pool=github --issuer-uri=https://token.actions.githubusercontent.com \
     --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.environment=assertion.environment" \
     --attribute-condition="assertion.repository=='$REPO'"
   POOL=projects/$PN/locations/global/workloadIdentityPools/github
   # Each deployer may be impersonated only from its own GitHub Environment:
   gcloud iam service-accounts add-iam-policy-binding gha-deploy-staging@$P.iam.gserviceaccount.com \
     --role roles/iam.workloadIdentityUser --member "principalSet://iam.googleapis.com/$POOL/attribute.environment/staging"
   gcloud iam service-accounts add-iam-policy-binding gha-deploy-prod@$P.iam.gserviceaccount.com \
     --role roles/iam.workloadIdentityUser --member "principalSet://iam.googleapis.com/$POOL/attribute.environment/production"
   ```
   `WIF_PROVIDER` for GitHub is `projects/$PN/locations/global/workloadIdentityPools/github/providers/github-actions`. The attribute-mapping, condition and member syntax are NOT VERIFIED; follow the current `google-github-actions/auth` documentation. Because the pool trusts one repo, anyone who can run a job in the `production` GitHub Environment can deploy production: protect that environment with required reviewers.
8. **Registry access for the deployers.**
   ```bash
   gcloud artifacts repositories add-iam-policy-binding meridian --location=$R --member serviceAccount:gha-deploy-staging@$P.iam.gserviceaccount.com --role roles/artifactregistry.writer
   gcloud artifacts repositories add-iam-policy-binding meridian --location=$R --member serviceAccount:gha-deploy-prod@$P.iam.gserviceaccount.com    --role roles/artifactregistry.reader
   ```
   The Cloud Run service agent must also be able to pull from the repository; in the same project this normally works without extra grants (NOT VERIFIED).
9. **First deploy of each service (creates it).** Billed per request and CPU/memory only while handling requests; `--min-instances 0` costs near nothing idle. Needs a pushed image: run the workflow's build job first, or push by hand (section 4).
   ```bash
   gcloud run deploy meridian-ai-staging --region $R --image asia-east2-docker.pkg.dev/$P/meridian/meridian-ai:<git-sha> \
     --port 8080 --min-instances 0 --max-instances 1 --no-allow-unauthenticated \
     --service-account meridian-run-staging@$P.iam.gserviceaccount.com \
     --set-env-vars "ENVIRONMENT=staging,GCP_PROJECT_ID=$P,GCP_REGION=$R,GCS_BUCKET_NAME=$P-meridian-staging,GCS_PREFIX=uploads/,VECTOR_SEARCH_INDEX_ID=<id>,VECTOR_SEARCH_INDEX_ENDPOINT_ID=<id>" \
     --update-secrets "GOOGLE_API_KEY=GOOGLE_API_KEY_STAGING:latest"
   ```
   Add Cloud Run probes after the first deploy: startup and liveness on `GET /api/health` (flag syntax NOT VERIFIED; see `gcloud run deploy --help`). Repeat for `meridian-ai-prod` with `--max-instances 3`, `ENVIRONMENT=production`, its own bucket, ids, secret and service account, and the access setting decided in section 0 item 4.
10. **Per-service deploy rights** (needs the service to exist, hence after step 9):
    ```bash
    gcloud run services add-iam-policy-binding meridian-ai-staging --region $R --member serviceAccount:gha-deploy-staging@$P.iam.gserviceaccount.com --role roles/run.developer
    gcloud run services add-iam-policy-binding meridian-ai-prod    --region $R --member serviceAccount:gha-deploy-prod@$P.iam.gserviceaccount.com    --role roles/run.developer
    gcloud iam service-accounts add-iam-policy-binding meridian-run-staging@$P.iam.gserviceaccount.com --member serviceAccount:gha-deploy-staging@$P.iam.gserviceaccount.com --role roles/iam.serviceAccountUser
    gcloud iam service-accounts add-iam-policy-binding meridian-run-prod@$P.iam.gserviceaccount.com    --member serviceAccount:gha-deploy-prod@$P.iam.gserviceaccount.com    --role roles/iam.serviceAccountUser
    ```

## 7. Routine deployment and promotion (GitHub Actions)

Proposed workflow, **not in the repo yet** (adding it replaces the current `deploy.yml` path and needs owner approval). Shape, NOT VERIFIED:

```yaml
# .github/workflows/release.yml  (proposed)
on:
  push: { branches: [main] }          # staging: automatic
  workflow_dispatch:                  # production: manual run
    inputs: { image_sha: { description: "SHA already deployed to staging", required: true } }
permissions: { contents: read, id-token: write }   # id-token is required for WIF

jobs:
  test:        # backend pytest, frontend npm test, tsc; npm audit as report-only
  build-stage: # needs: test. environment: staging
    # google-github-actions/auth@v2 with workload_identity_provider + service_account (no JSON key)
    # docker build, docker push :<github.sha>, then gcloud run deploy meridian-ai-staging --image ...:<sha>
    # verify: identity-token curl to /api/health on the new revision
  promote:     # only on workflow_dispatch. environment: production (required reviewers = approval gate)
    # auth as gha-deploy-prod; gcloud run deploy meridian-ai-prod --image ...:<image_sha> --no-traffic --tag candidate
    # verify the candidate URL, then update-traffic --to-revisions <new>=100
```
Pin third-party actions to a full commit SHA rather than a tag (supply-chain hygiene, NOT VERIFIED which versions to pin).

Routine staging deploy: merge to `main`; the pipeline runs section 5, builds `:$SHA`, deploys to staging and checks health. Then run section 8 on staging.

Promote to production: run the workflow with the staging-verified SHA and approve the `production` environment. The prod deployer can only read the image, so it cannot deploy anything that was not built by the staging pipeline. Manual equivalent (NOT VERIFIED):
```bash
gcloud run deploy meridian-ai-prod --region $R --image asia-east2-docker.pkg.dev/$P/meridian/meridian-ai:<sha> --no-traffic --tag candidate  # plus the same flags as step 9
# verify the candidate URL, then:
gcloud run services update-traffic meridian-ai-prod --region $R --to-revisions <new-revision>=100
```
Use a partial split first (for example `=10`) if you want a canary.

## 8. Post-deployment verification

1. Health: `curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" https://<service-url>/api/health` returns `{"status":"ok"}` (omit the header only if the service is public).
2. Config: `GET /api/status` shows project, region, bucket and index ids set, no blanks or `NA` (`endpoints.py:62-90`). It is unauthenticated inside the app; do not make a service public just to call it.
3. Smoke test, cheapest first:
   - free: the SPA page loads;
   - small cost: one short question against a tiny test document in the RAG tab (one embedding call, one Gemini call);
   - do **not** use the audit endpoint for smoke tests: three agents plus a memo, the most expensive call.
4. Logs:
   - `gcloud run services logs read meridian-ai-staging --region $R --limit 50`, or Logs Explorer with `resource.type="cloud_run_revision"` and `resource.labels.service_name="meridian-ai-staging"`. The app writes JSON lines to stdout (`custom_logger.py:46-54`).
   - A copy is uploaded to `gs://<bucket>/logs/<timestamp>.log` only at shutdown (`custom_logger.py:71-105`), so it is not live.
   - Logs contain full user questions, answers and memos (`docs/OPERATIONS.md` section 2); restrict who can read them.

## 9. Monitoring and alerting

Watch (Cloud Run metrics and logs, per service):
- request count, 5xx rate, p95 latency, instance count, restarts;
- Gemini quota/API errors in logs (route errors surface as HTTP 500, `HTTPException(500)` pattern);
- Vector Search: is the index still deployed (hourly cost), query volume;
- bucket size of `uploads/` and `logs/`;
- request volume on a service with no authentication: unexpected spikes are the main cost-abuse signal.

Alerts (Cloud Monitoring, notification channel = your email; NOT VERIFIED): 5xx rate above a threshold for 5 minutes; request count far above normal; instance count at the max for 10 minutes; production revision not serving.

**Budget alert (required).** Vector Search, Gemini and Cloud Run are all paid. Needs billing-account permission:
```bash
gcloud billing budgets create --billing-account <BILLING_ACCOUNT_ID> --display-name "meridian" \
  --budget-amount <amount><CURRENCY> --filter-projects projects/$P \
  --threshold-rule percent=0.5 --threshold-rule percent=0.9 --threshold-rule percent=1.0
```
Flag spelling NOT VERIFIED (`gcloud billing budgets create --help`). Because both environments share a project, the budget cannot separate them; use a resource label (for example `env=staging|prod`) on services, buckets and indexes and filter the billing report by label. A budget **notifies only; it does not stop spending**. The real limits are a Gemini API key quota cap and `--max-instances`.

## 10. Rollback

Application rollback (fast, no rebuild; Cloud Run keeps old revisions):
```bash
gcloud run revisions list --service meridian-ai-prod --region $R
gcloud run services update-traffic meridian-ai-prod --region $R --to-revisions <previous-revision>=100
```
Or re-run the promote workflow with the previous good SHA. Immutable tags make this reliable (section 4). Rolling back traffic does not undo a secret rotation: if the release came with a new key version, also disable the bad version (`gcloud secrets versions disable ...`, NOT VERIFIED).

What cannot be rolled back:
- **Vector index contents.** Ingesting PDFs adds datapoints (`rag/data_ingestion.py`); a code rollback leaves them. Removal needs `gcloud ai indexes remove-datapoints` with the ids (syntax at `deploy.yml:187`) and a record of which ids were added.
- **Uploaded files and logs in the bucket.** Deleting is permanent and needs approval.
- **Embedding-model or dimension changes.** The index is 768-dimension (`settings.py:39`); switching models means a new index and full re-ingestion, so there is no code-only rollback after that.
- **Gemini spend and anything already sent to Google.**
- **Data migrations.** None exist (no database). If one is ever added, write the down-migration and take a backup before deploying.

Emergency stop for a cost spike or abuse (keeps data): remove public invoker access (`gcloud run services remove-iam-policy-binding ... --member allUsers --role roles/run.invoker`) and/or lower `--max-instances`; both NOT VERIFIED here.
