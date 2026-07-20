# Final Rehearsal Evidence Pack

Status: PRG-018

Build the local evidence pack:

```bash
PYTHONPATH=src python3 -m notary_platform.evidence_pack --output-dir artifacts/final-evidence-pack
```

The command writes:

- `harborline-preflight.json`
- `security-readiness.json`
- `blocked-gate.json`
- `passing-gate.json`
- `readiness-certificate.json`
- `readiness-certificate-verification.json`
- `architecture-summary.json`
- `limitations.json`
- `rehearsal-manifest.json`

## Rehearsal Script

1. Run the evidence-pack command.
2. Confirm `harborline-preflight.json` has `status: pass`.
3. Confirm `blocked-gate.json` has `status: fail`.
4. Confirm `passing-gate.json` has `status: pass`.
5. Confirm `readiness-certificate-verification.json` has `signature_valid: true`.
6. Confirm `security-readiness.json` is either `pass` for a configured shared/pilot environment or `blocked` with accepted local/demo stop boundaries.
7. Record screenshots or video of:
   - platform home Harborline path;
   - source Verification Record;
   - blocked Release Gate;
   - passing Release Gate;
   - readiness certificate verification;
   - public website Harborline + pilot sections;
   - Command Center Program panel.

## Claim Boundary

This pack supports a demo/pilot rehearsal for the Harborline tested scenario. It does not certify general AI safety, fairness, compliance, production deployment, or live GRC integrations.
