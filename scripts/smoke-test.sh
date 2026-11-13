#!/bin/sh
# Usage: sh scripts/smoke-test.sh <dev|prod> <read|write>
set -eu

ENVIRONMENT="$1"
MODE="${2:-read}"
NS="ticket-$ENVIRONMENT"
PORT=18081
BASE="http://localhost:$PORT"

kubectl port-forward -n "$NS" service/web "$PORT":80 >/dev/null 2>&1 &
PF=$!
trap 'kill $PF 2>/dev/null || true' EXIT

echo "Waiting for $NS to answer..."
i=0
until curl -fsS "$BASE/api/health" >/dev/null 2>&1; do
  i=$((i + 1))
  if [ "$i" -ge 20 ]; then
    echo "FAIL: no answer from $BASE/api/health"
    exit 1
  fi
  sleep 2
done
echo "PASS: /api/health"

VERSION=$(curl -fsS "$BASE/api/version")
echo "$VERSION" | grep -q "\"env\":\"$ENVIRONMENT\"" || { echo "FAIL: wrong environment: $VERSION"; exit 1; }
echo "PASS: /api/version -> $VERSION"

if [ "$MODE" = "write" ]; then
  curl -fsS -X POST -H 'Content-Type: application/json' \
    -d '{"title":"smoke test","priority":"low"}' "$BASE/api/tickets" >/dev/null
  curl -fsS "$BASE/api/tickets" | grep -q "smoke test" || { echo "FAIL: ticket not found"; exit 1; }
  echo "PASS: create and read a ticket (database works)"
fi

echo "Smoke test passed for $NS" 
