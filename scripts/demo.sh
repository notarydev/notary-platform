#!/usr/bin/env bash
# Helper for `make demo`: seeds a demo scenario against a running Notary server.
# Usage: scripts/demo.sh [SCENARIO_ID]
set -euo pipefail

SCENARIO_ID="${1:-lending-denial}"
BASE="http://localhost:8000"

echo "Seeding scenario '${SCENARIO_ID}' via ${BASE}/v1/demo/lending-seed ..."
curl -fsS -X POST "${BASE}/v1/demo/lending-seed?scenario_id=${SCENARIO_ID}" \
  && echo "" \
  || { echo "Seed failed — is the server up? (see /tmp/notary-demo.log)"; exit 1; }

echo ""
echo "Dashboard is available at:"
echo "  ${BASE}/dashboard?scenario_id=${SCENARIO_ID}"
