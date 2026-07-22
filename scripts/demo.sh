#!/usr/bin/env bash
# Helper for `make demo`: seeds demo data against a running Notary server.
set -euo pipefail

BASE="${NOTARY_BASE_URL:-http://localhost:8000}"

echo "Seeding demo catalog via ${BASE}/v1/demo/catalog/seed ..."
curl -fsS -X POST "${BASE}/v1/demo/catalog/seed" \
  && echo "" \
  || { echo "Seed failed — is the server up?"; exit 1; }

echo ""
echo "Platform SPA: ${BASE}/app/"
