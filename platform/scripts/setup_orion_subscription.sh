#!/usr/bin/env bash
# Idempotent: register the Orion -> QuantumLeap subscription so that NGSI
# entity updates are persisted as time series in CrateDB.
#
# Safe to re-run: a 409 from Orion (subscription already exists) is treated
# as success.

set -euo pipefail

ORION_URL="${ORION_URL:-http://localhost:1026}"
QL_URL="${QL_URL:-http://localhost:8668}"
FIWARE_SERVICE="${FIWARE_SERVICE:-iot}"
FIWARE_SERVICEPATH="${FIWARE_SERVICEPATH:-/}"

wait_for() {
  local name="$1" url="$2" retries=30
  echo "Waiting for ${name} at ${url} ..."
  for _ in $(seq 1 "${retries}"); do
    if curl -fsS "${url}" >/dev/null 2>&1; then
      echo "  ${name} is up."
      return 0
    fi
    sleep 2
  done
  echo "ERROR: ${name} did not become ready in time." >&2
  return 1
}

wait_for "Orion"       "${ORION_URL}/version"
wait_for "QuantumLeap" "${QL_URL}/version"

QL_NOTIFY_URL="http://quantumleap:8668/v2/notify"

echo "Checking for existing Orion -> QuantumLeap subscriptions (service=${FIWARE_SERVICE}) ..."
existing_ids=$(curl -fsS \
  -H "fiware-service: ${FIWARE_SERVICE}" \
  -H "fiware-servicepath: ${FIWARE_SERVICEPATH}" \
  "${ORION_URL}/v2/subscriptions" \
  | python3 -c "
import json, sys
url = '${QL_NOTIFY_URL}'
ids = [s['id'] for s in json.load(sys.stdin) if s.get('notification', {}).get('http', {}).get('url') == url]
print(' '.join(ids))
")

# shellcheck disable=SC2206
existing_arr=(${existing_ids})

if [ "${#existing_arr[@]}" -ge 1 ]; then
  echo "Subscription already exists (${#existing_arr[@]} found); keeping the first, deleting any duplicates."
  for id in "${existing_arr[@]:1}"; do
    echo "  Deleting duplicate ${id}"
    curl -fsS -X DELETE \
      -H "fiware-service: ${FIWARE_SERVICE}" \
      -H "fiware-servicepath: ${FIWARE_SERVICEPATH}" \
      "${ORION_URL}/v2/subscriptions/${id}" >/dev/null
  done
  exit 0
fi

echo "Registering Orion -> QuantumLeap subscription ..."
http_code=$(curl -s -o /tmp/sub.out -w "%{http_code}" \
  -X POST "${ORION_URL}/v2/subscriptions" \
  -H 'Content-Type: application/json' \
  -H "fiware-service: ${FIWARE_SERVICE}" \
  -H "fiware-servicepath: ${FIWARE_SERVICEPATH}" \
  -d '{
    "description": "Notify QuantumLeap of all entity attribute changes",
    "subject": {
      "entities": [{"idPattern": ".*"}]
    },
    "notification": {
      "http": { "url": "'"${QL_NOTIFY_URL}"'" },
      "attrsFormat": "normalized"
    },
    "throttling": 0
  }')

case "${http_code}" in
  201) echo "Subscription created." ;;
  *)
    echo "ERROR: unexpected HTTP ${http_code} from Orion:" >&2
    cat /tmp/sub.out >&2
    exit 1
    ;;
esac
