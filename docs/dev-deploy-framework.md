# Dev & Deploy Framework (Notary demo)

Standing operating procedure for any agent (Codex, OpenCode, human) working on the
Notary demo. The point is to stop the same three classes of confusion from
recurring: **stale local state**, **two render sources**, and **wrong deploy
assumptions** (region / arch / immutable tags).

> Scope freeze for the demo: platform + SDK + website only. Do not touch DNS,
> secrets, CORS, remote storage, or KMS unless explicitly approved.

---

## 0. Message for Codex (paste this before any diagnosis or deploy)

```
You are working on the Notary demo across three repos:
  - notary-platform  (API + SPA, deploys to api.getnotary.ai via ECS/Fargate)
  - notary-sdk       (Python SDK, no live deploy)
  - GetNotary.ai     (marketing site, deploys to getnotary.ai via Cloudflare Worker)

Before you diagnose or change ANYTHING, follow the Reconciliation Protocol below.
The biggest mistakes last time were:
  1. Trusting a stale local `main` (reported d15bbc8, real was a01bd5c).
  2. Comparing the raw escaped template in src/index.js to site.html — they
     LOOK different but are the same once backticks/$ are unescaped.
  3. Assuming the ECS infra was in another AWS account / us-east-1. It is in the
     SAME account (447633181871) but us-east-2. Always set --region us-east-2.
  4. Building the Docker image on Apple-Silicon (arm64) — ECS needs linux/amd64,
     or tasks fail with CannotPullContainerError.
  5. Thinking `ecs update-service --force-new-deployment` swaps the image. It does
     NOT. The task def pins a tag; you must register a NEW task-def revision.
  6. ECR tags are IMMUTABLE — never reuse a tag; use a timestamped tag each deploy.
  7. We test in LIVE. Platform's final destination is always api.getnotary.ai;
     website's is always getnotary.ai. Local runs are a pre-check only — the real
     gate is the live URL showing current main content. Never call a repo "ready"
     from localhost alone.

Use the canonical files as source of truth:
  - notary-platform/docs/demo/demo-release-manifest.md  (single release truth)
  - notary-platform/infra/deploy-api.sh                 (platform deploy runbook)
  - GetNotary.ai/scripts/check-site-sync.js             (website source-of-truth guard)
Do not start feature work. Reconcile, verify, deploy, report.
```

---

## 1. Reconciliation Protocol (run BEFORE diagnosing)

For **every** repo, fresh from origin, no assumptions:

```bash
git fetch origin --prune
git checkout main
git reset --hard origin/main
git status --porcelain        # must be empty (clean tree)
```

Then record the real SHA. Never trust a previously cached SHA — the `d15bbc8`
vs `a01bd5c` mismatch happened because local state was not fully fresh.

---

## 1b. Live is the test environment

We do **all** testing against the live surfaces, not just local runs. The final
destination of each repo IS its test target — there is no separate staging
environment for the demo:

| Repo | Live destination (the only place we verify) | What "passing" means |
|------|----------------------------------------------|----------------------|
| notary-platform | `https://api.getnotary.ai` | `/health` ok + `app.js` contains `Harborline` / `Blocked Gate` / `Passing Gate`; `demo_preflight` run **against the live URL** passes end-to-end |
| notary-sdk | installed from source in consumers (no live service) | `pytest` green locally + SDK claims stay narrow |
| GetNotary.ai | `https://getnotary.ai` (and `www.getnotary.ai`) | live page contains `Harborline`, `Design-partner pilot`, `Apply for design-partner pilot`, `Stop repeating AI failures` |

Implications:
- **Local runs are a pre-check, not proof.** A green local `demo_preflight` or
  `wrangler deploy --dry-run` is necessary but not sufficient. The real gate is
  the live URL returning current content.
- After every platform deploy, verify **against `api.getnotary.ai`**, not
  `localhost`. After every website deploy, verify **against `getnotary.ai`**.
- If a live surface is stale, that is a deploy gap to close — not something to
  work around by pointing tests at localhost. The demo is "done" only when the
  live URLs show current main content.
- Never report a repo as "ready" based on local checks alone. Report the live
  verification result.

## 2. Repository source-of-truth map

| Repo | Canonical source | Render/deploy target | Guard |
|------|------------------|----------------------|-------|
| notary-platform | `src/` + `static/app/` | ECR `notary-api` → ECS `notary-dev-api` (us-east-2) → ALB `notary-dev-alb` → `api.getnotary.ai` | `demo_preflight` end-to-end |
| notary-sdk | `src/` | PyPI / local install (no live deploy) | `pytest` |
| GetNotary.ai | `src/index.js` (Worker serves it) | Cloudflare Worker → `getnotary.ai` | `npm run check:site-sync` |

**Website rule:** `src/index.js` is canonical. `site.html` is the *unescaped
render* of the Worker HTML (backticks/`$` unescaped). They are equal once
unescaped. Never hand-edit `site.html` as if it were source — regenerate it:
`npm run sync:site`. CI fails if they diverge.

---

## 3. Verification matrix (all must be GREEN before deploy)

### notary-platform
```bash
PYTHONPATH=src python3 -m notary_platform.demo_preflight
PYTHONPATH=src python3 -m notary_platform.evidence_pack --output-dir artifacts/final-evidence-pack
ruff check .
mypy src
pytest -q --ignore=tests/test_ui_vertical.py     # Playwright UI tests excluded by design
```

### notary-sdk
```bash
PYTHONPATH=src python3 -m pytest tests
```

### GetNotary.ai
```bash
npm ci
npm run check:site-sync      # fails if site.html != Worker HTML
npx wrangler deploy --dry-run
```

---

## 4. Deploy protocol

### Website (low-risk, no secrets/DNS changes)
```bash
git fetch origin --prune && git checkout main && git reset --hard origin/main
npm ci
npm run check:site-sync
npx wrangler deploy
# verify
curl -s https://getnotary.ai | grep -E "Harborline|Design-partner pilot|Apply for design-partner pilot|Stop repeating AI failures"
```

### Platform API (AWS ECS/Fargate, us-east-2)
Use the runbook: `infra/deploy-api.sh` (already hardened for the gotchas below).
Manual equivalent:
```bash
REGION=us-east-2
# 1. ECR login
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin <acct>.dkr.ecr.$REGION.amazonaws.com
# 2. Build for amd64 + push with a UNIQUE (timestamped) tag — ECR tags immutable
docker buildx build --platform linux/amd64 -t <acct>.dkr.ecr.$REGION.amazonaws.com/notary-api:main-<sha>-<ts> --push .
# 3. Register a NEW task-def revision pointing at that image
#    (strip read-only fields, set containerDefinitions[0].image = new URI)
# 4. Update service to the new TD + force redeploy
aws ecs update-service --region $REGION --cluster notary-dev --service notary-dev-api \
  --task-definition <new-td-arn> --force-new-deployment
# 5. Wait for 1/1 RUNNING on the new image, old task drained
# 6. Verify
curl -s https://api.getnotary.ai/health                                   # {"status":"ok"}
curl -s https://api.getnotary.ai/app/app.js | grep -E "Harborline|Blocked Gate|Passing Gate"
```

**Gotchas (learned the hard way):**
- Region is **us-east-2**, not the AWS CLI default. Always pass `--region us-east-2`.
- Build **linux/amd64** even on Apple-Silicon; otherwise `CannotPullContainerError`.
- ECR tags are **immutable** → always a new unique tag per deploy.
- `--force-new-deployment` alone does **not** change the image; register a new
  task-def revision that pins the new image tag.

### SDK
No live deploy. Ship via PyPI or install from source in consumers.

---

## 5. After deploy — update the manifest

`notary-platform/docs/demo/demo-release-manifest.md` is the single release
truth. After any main change or deploy, update:
- repo main SHAs,
- pass/fail table,
- live-status table (which surfaces are now live with current content),
- known limitations.

Do not widen product claims, DNS, secrets, CORS, storage, or KMS scope.

---

## 6. Stale branches hygiene

Old draft PRs/branches make it impossible to know what is canonical. After main
is verified, close or label `superseded` any branch not on main. Current stale
branches to review: `codex/prg-008-*`, `codex/prg-014-*`, `codex/prg-015-*`,
`codex/create-scaffold-branch-and-setup-files`, `scaffold/initial-setup`,
`agents/general-tapir`.

---

## 7. One-line mental model

> Fresh-pull → verify green → deploy with correct region/arch/tag → confirm LIVE
> (api.getnotary.ai / getnotary.ai) → record in manifest. Never trust cached state.
> Never hand-edit generated files. Never assume the image swapped without a new
> task-def revision. Live is the test environment — localhost is only a pre-check.
