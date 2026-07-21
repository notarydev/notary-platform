# Frontend → Backend wiring handoff

This documents the state of the `/app` SPA (`static/app/`) so a backend agent can wire it to
real APIs. The frontend was rebuilt to be workflow-driven with real depth; several flows currently
run on **client-side placeholder data** and need backend support.

## Run model (unchanged, portable)
- FastAPI (`notary_platform`) serves the SPA at `/app` and the API at `/v1` on the same origin.
- Local: `make install && make run` → open `http://localhost:8000/app/`.
- The Emergent preview used gitignored shims (`/frontend`, `/backend`) to serve on :3000. Ignore them.

## What is REAL (already hits /v1)
- Home (`/v1/platform/home`), Verification Records, Incidents, Proofs, Scenarios, Readiness,
  Governance, Evidence, Settings, adapters registry, and the Harborline/Meridian golden-path
  seed (`POST /v1/demo/harborline-release-gate/seed`, `POST /v1/demo/catalog/seed`).

## What is CLIENT-SIDE / MOCKED (needs backend)
1. **Onboarding (Setup view)** — `renderOnb*` in `static/app/app.js`.
   - `saveOnbSystem()` creates systems in-memory with a fake token. Wire to a real
     "register AI system" endpoint returning `{system_id, ingest_token, endpoint}`.
   - `sendOnbTestRecord()` simulates a received record with `setTimeout`. Replace with:
     create/poll a real Verification Record (an endpoint already exists:
     `POST /v1/verification-records/from-snapshot`), and a "first record received" poll.
2. **Guided demo (Demo view)** — `renderDemo` + `demo*` functions + `NORTHSTAR`/`NORTHSTAR_EVENTS`.
   - Entirely client-side narrative (Northstar Air, inspired by Moffatt v. Air Canada 2024).
   - To make it live, seed a Northstar dataset and back these scenes with real objects:
     Verification Record `vr-northstar-001`, replay run, human label (`ESCALATE_TO_HUMAN`),
     mutation/fix verify, Proof of Mitigation, Scenario, Release Gate FAIL (v42) / PASS (v43),
     Proof of Readiness. A `POST /v1/demo/northstar/seed` mirroring the harborline seed is ideal.
3. **Replay player** — `renderReplayPlayer` animates `_replayEvents`. Feed it a record's real
   captured events + original/replayed decisions + verdict.

## Naming
- Visible "Harborline" → "Meridian Credit Union" (frontend copy + demo org name + preflight anchor).
- Internal ids/fn names and `/v1/demo/harborline-release-gate/*` path unchanged.

## Next frontend work (in progress)
- Standardize the whole app on the Northstar Air narrative (topbar org, Home hero, Setup examples)
  so Setup + Demo + list screens tell ONE coherent story.
