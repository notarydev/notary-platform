# Harborline Pilot Demo Presenter Script

Status: local/sandbox only

## Preflight

Run the automated preflight before every dry run:

```bash
PYTHONPATH=src python3 -m notary_platform.demo_preflight
```

For a machine-readable report:

```bash
PYTHONPATH=src python3 -m notary_platform.demo_preflight --json
```

The preflight validates:

- the FastAPI app health endpoint;
- the deterministic Harborline seed endpoint;
- Verification Record, replay, mutation, proof, scenario, Release Gate, and certificate signature evidence;
- the blocked before-fix gate and passing after-fix gate;
- the platform app presenter path.

## Local Demo Run

Start the app locally:

```bash
make run
```

Open:

```text
http://localhost:8000/app/
```

Use the home screen Harborline path:

1. Click `Seed Harborline Path`.
2. Open the Verification Record and show `HLCU-PL-0427`, original `DENY`, replayability, and the human label.
3. Open `Blocked Gate` and show the before-fix agent fails because expected `UNDERWRITING_REVIEW` but got `DENY`.
4. Open `Passing Gate` and show the fixed agent passes, scenario results are present, evidence refs are present, and the readiness certificate is attached.
5. State the claim scope: the proof is limited to the sealed Harborline personal-loan cassette and tested scenario. It does not certify general AI safety or production GRC integrations.

## Dry-Run Evidence Checklist

Record three successful local dry runs by saving the preflight JSON output and noting the presenter path used:

```bash
PYTHONPATH=src python3 -m notary_platform.demo_preflight --json > /tmp/harborline-preflight-run-1.json
PYTHONPATH=src python3 -m notary_platform.demo_preflight --json > /tmp/harborline-preflight-run-2.json
PYTHONPATH=src python3 -m notary_platform.demo_preflight --json > /tmp/harborline-preflight-run-3.json
```

Each run should report:

- `status: pass`;
- `blocked_gate_status: fail`;
- `passing_gate_status: pass`;
- a non-empty Verification Record ID, Scenario ID, and readiness certificate ID.

## Stop Boundaries

Do not deploy, connect production data, use real customer records, or claim broad AI safety certification during this demo. Stop and ask for a decision before changing cloud configuration, credentials, production storage, or claim language.
