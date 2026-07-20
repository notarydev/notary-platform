# Demo Release Manifest

Canonical "release truth" for the Notary demo (platform + SDK + website).
This file is the single source of reconciliation. Update it on every
main-state change. It is intentionally read-only truth, not a changelog.

> Scope freeze: no new features. Only reconcile platform, SDK, website,
> demo guide, and deploy/readiness status.

## Repository main SHAs (verified via `git fetch --prune && git reset --hard origin/main`)

| Repo | main SHA | Branch state |
|------|----------|--------------|
| notary-platform | `a3fcb10` | ahead of last reported failing SHA `1f64b72` (lint fix landed) |
| notary-sdk | `59280be` | matches reported SHA |
| GetNotary.ai | `a01bd5c` | matches reported SHA (supersedes stale local `d15bbc8`) |

## Commands run (exact)

### notary-platform
```
PYTHONPATH=src python3 -m notary_platform.demo_preflight
PYTHONPATH=src python3 -m notary_platform.evidence_pack --output-dir artifacts/final-evidence-pack
python3 -m ruff check src tests
python3 -m mypy src
python3 -m pytest tests/test_auth.py tests/test_certificates.py tests/test_demo_preflight.py tests/test_evidence_pack.py tests/test_ingestion.py tests/test_live_status.py tests/test_platform_static_app.py tests/test_release_gate_cli.py tests/test_release_gate_vertical.py tests/test_replay.py tests/test_security_readiness.py tests/test_shared_demo_storage.py tests/test_verification.py tests/test_viz.py
```
Also (full CI job, `ubuntu-latest` / Python 3.12):
```
ruff check .
mypy src
make topology
pytest -q --ignore=tests/test_ui_vertical.py
```

### notary-sdk
```
PYTHONPATH=src python3 -m pytest tests
```

### GetNotary.ai
```
npm ci
npm run check:site-sync     # NEW: fails CI if site.html != Worker HTML
npx wrangler deploy --dry-run
```

## Pass / Fail status

| Check | Repo | Status |
|-------|------|--------|
| demo_preflight | platform | PASS |
| evidence_pack | platform | PASS |
| ruff check | platform | PASS (was FAILING on `1f64b72`, fixed in `a3fcb10`) |
| mypy src | platform | PASS |
| pytest (backend + verticals, UI excluded) | platform | PASS (126 passed) |
| ruff check | sdk | PASS |
| mypy src | sdk | PASS |
| pytest | sdk | PASS (57 passed) |
| site sync check | website | PASS (site.html == Worker HTML) |
| wrangler deploy --dry-run | website | PASS (uploads cleanly) |

### CI failure that was fixed
- **Failing check:** `notary-platform` GitHub Actions `verify` job → `Ruff` step.
- **Root cause:** `scripts/harborline_demo_preflight.py` had an unsorted/blank-line
  import block (Ruff I001). `ruff check .` exited non-zero.
- **Fix:** commit `a3fcb10` removed the redundant blank line. Pushed to main.

## Known limitations

- **Playwright/browser UI tests are excluded from CI** (`--ignore=tests/test_ui_vertical.py`).
  Full UI vertical tests require Chromium on the runner; they are not run in CI
  by design. Do not delete them; they remain for local manual runs.
- **`make topology` writes `topology.json`** into the repo on every run. The CI
  step executes the command (exit 0); it does not assert a clean tree. Treat
  `topology.json` as a generated artifact.
- **`evidence_pack` writes to `artifacts/final-evidence-pack`**; ensure this path
  is writable/ignored in CI to avoid dirty-tree failures.
- **Security readiness / shared-pilot readiness** is "blocked by design" in
  local/demo mode and is intentionally NOT required for CI green.
- **SDK claim scope** is intentionally narrowed to explicit/manual/context/decorator
  capture, HMAC/Merkle sealing, and local verification. No broader claims.

## Website source-of-truth

- **`src/index.js` is canonical.** The Cloudflare Worker serves the HTML embedded
  inline in `src/index.js` (a JS template literal). `wrangler deploy` ships this.
- **`site.html` is reference / generated only.** It is the unescaped render of the
  Worker HTML (`npm run sync:site` regenerates it; backticks/`$` unescaped).
- **Guardrail added:** `npm run check:site-sync` (`.github/workflows/ci.yml`)
  fails CI if the two diverge, so a stale `site.html` can never be trusted as
  "current copy."
- **Rendered-content verification:** before any real deploy, confirm the actual
  served HTML (Worker output), not just `wrangler deploy --dry-run`.

## Live status

| Surface | Live? | Notes |
|---------|-------|-------|
| `getnotary.ai` reflects current website copy | YES (after deploy) | site.html == Worker HTML at `a01bd5c`; deploy is gated by sync check |
| `api.getnotary.ai` | SEPARATE CHECKLIST | NOT solved by code reconciliation. This is deploy/DNS/cloud (ECS + ALB + ACM + Route53). Tracked outside this manifest. |

## Stale branches / PRs to close or label `superseded`

Local `git fetch --prune` surfaced these remote branches that are not main and
should be reviewed for closure (they predate the fast-forwarded main):

- `origin/codex/prg-008-harborline-website`
- `origin/codex/prg-008-website-claim-alignment`
- `origin/codex/prg-014-website-harborline-positioning`
- `origin/codex/prg-015-design-partner-pilot-offer`
- `origin/codex/create-scaffold-branch-and-setup-files`
- `origin/scaffold/initial-setup`
- `origin/agents/general-tapir`

> Action: once main is verified, close or label these `superseded` so reviewers
> stop reviewing stale branches. Do NOT merge without rebase onto current main.

## Reconciliation procedure (run before any diagnosis)

```
git fetch origin --prune
git checkout main
git reset --hard origin/main
```
Repeat per repo. The earlier stale `d15bbc8` note was a warning that local
state was not fully fresh — always start from a pruned, hard-reset main.
