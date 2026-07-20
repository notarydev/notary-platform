# Security And Deployment Readiness

Status: PRG-017 readiness gate

This checklist is for shared demo, design-partner pilot, and production-like deployments. It does not deploy infrastructure and does not authorize production changes by itself.

## Readiness Command

Run locally:

```bash
PYTHONPATH=src python3 -m notary_platform.security_readiness
```

Machine-readable output:

```bash
PYTHONPATH=src python3 -m notary_platform.security_readiness --json
```

## Required Before Shared Or Pilot Access

- `NOTARY_API_AUTH_TOKEN` is set from Secrets Manager or a secure runtime secret source.
- `NOTARY_COMMAND_CENTER_TOKEN` is set before exposing Command Center status endpoints.
- `NOTARY_VIZ_ORIGIN` lists exact shared origins; no wildcard and no localhost-only CORS for shared use.
- `NOTARY_USE_REMOTE_STORAGE=1` is set with `NOTARY_DATABASE_URL` and `NOTARY_EVIDENCE_BUCKET`.
- The evidence bucket must be the S3 Object Lock/WORM bucket documented in `infra/terraform/README.md`.
- `NOTARY_KMS_KEY_ARN` is set before claiming production-grade certificate sealing.
- `NOTARY_STORAGE_PROFILE=shared_demo` may be used for presenter-safe restart demos only. It is not immutable custody storage.

## Stop Rules

Stop and request an explicit decision before:

- changing AWS, Cloudflare, DNS, GitHub Actions, or production deployment settings;
- using real customer data;
- adding, printing, or rotating credentials;
- describing memory or shared-demo JSON storage as immutable evidence;
- describing local/dev signing as production-grade certificate sealing;
- expanding proof language into general AI safety, fairness, or compliance certification.

## Verification Evidence

PRG-017 readiness is satisfied when:

- the readiness command returns `status: pass` for the intended shared/pilot environment;
- auth, CORS, storage, signing, and Command Center token checks are all `passed`;
- deployment dry-runs/builds pass without production deploy;
- the demo preflight in `docs/demo/harborline-presenter-script.md` passes for the presenter path;
- any remaining stop boundary is either fixed or explicitly accepted in the release evidence pack.
