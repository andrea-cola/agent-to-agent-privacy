#!/usr/bin/env bash
# Concord Demo Script — run against a live or local instance.
# Usage: ./demo.sh [BASE_URL]
set -euo pipefail

BASE="${1:-http://localhost:8000}"
echo -e "\n\033[1;33m=== CONCORD DEMO ===\033[0m  $BASE\n"

# 1. Negotiate — PII-heavy payload, cross-border EU→US
echo -e "\033[1;36m[1] POST /v1/negotiate\033[0m"
echo "(waiting up to 120s for cold start...)"
RESULT=$(curl -s --max-time 120 -X POST "$BASE/v1/negotiate" \
  -H 'Content-Type: application/json' \
  -d '{
    "sender_profile": "finance-agent-01",
    "recipient_profile": "analytics-agent-07",
    "persona": "gdpr_safe",
    "payload": "Customer Mario Rossi, mario.rossi@example.it, located in Milano, IBAN IT60X0542811101000000123456, card 4539 1488 0343 6467. Medical diagnosis: type-2 diabetes, treatment: metformin. Secret key: sk-live-9fJ2kXyz. National ID: RSSMRA85M01F205Z."
  }')

TID=$(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['transfer_id'])")
echo "$RESULT" | python3 -m json.tool
echo

# 2. Rehydrate — sender restores masked tokens
echo -e "\033[1;36m[2] POST /v1/rehydrate (authorized)\033[0m"
REDACTED=$(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['outbound_payload'])")
curl -s --max-time 30 -X POST "$BASE/v1/rehydrate" \
  -H 'Content-Type: application/json' \
  -d "{\"transfer_id\": \"$TID\", \"text\": $(echo "$REDACTED" | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read().strip()))'), \"agent_id\": \"finance-agent-01\"}" | python3 -m json.tool
echo

# 3. Rehydrate — unauthorized agent gets 403
echo -e "\033[1;36m[3] POST /v1/rehydrate (unauthorized → 403)\033[0m"
curl -s --max-time 30 -X POST "$BASE/v1/rehydrate" \
  -H 'Content-Type: application/json' \
  -d "{\"transfer_id\": \"$TID\", \"text\": \"ignored\", \"agent_id\": \"unauthorized-agent\"}" | python3 -m json.tool
echo

# 4. Attestation — signed audit record
echo -e "\033[1;36m[4] GET /v1/attestation/$TID\033[0m"
curl -s --max-time 30 "$BASE/v1/attestation/$TID" | python3 -m json.tool
echo

echo -e "\033[1;32mDone.\033[0m"
