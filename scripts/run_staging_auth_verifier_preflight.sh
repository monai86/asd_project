#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  bash scripts/run_staging_auth_verifier_preflight.sh

Required environment:
  STAGING_API_BASE_URL

Optional environment:
  OUTPUT_DIR              Defaults to docs/release_artifacts/auth_verifier/preflight
  EXPECTED_AUTH_MODE      Defaults to supabase
  EXPECTED_REQUIRED_AAL   Defaults to aal2
  ALLOW_STATUS_MISMATCH   Set to 1 to avoid non-zero exit on failed checks
EOF
}

require_env() {
  local name="$1"
  if [[ -z "${!name:-}" ]]; then
    echo "Missing required environment variable: $name" >&2
    exit 1
  fi
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_DIR="${OUTPUT_DIR:-$ROOT_DIR/docs/release_artifacts/auth_verifier/preflight}"
TIMESTAMP="$(date +%Y-%m-%d_%H%M%S)"
EXPECTED_AUTH_MODE="${EXPECTED_AUTH_MODE:-supabase}"
EXPECTED_REQUIRED_AAL="${EXPECTED_REQUIRED_AAL:-aal2}"

require_env STAGING_API_BASE_URL

mkdir -p "$OUTPUT_DIR"

BASE_URL="${STAGING_API_BASE_URL%/}"
URL="$BASE_URL/settings"
HEADERS_FILE="$OUTPUT_DIR/${TIMESTAMP}_settings.headers.txt"
BODY_FILE="$OUTPUT_DIR/${TIMESTAMP}_settings.body.json"
META_FILE="$OUTPUT_DIR/${TIMESTAMP}_settings.meta.txt"

STATUS_CODE="$(
  curl -sS \
    -D "$HEADERS_FILE" \
    -o "$BODY_FILE" \
    -w '%{http_code}' \
    "$URL"
)"

BODY_COMPACT="$(tr -d '\n\r\t ' < "$BODY_FILE")"

RESULT="pass"
AUTH_MODE_MATCH="false"
MOCK_MODE_MATCH="false"
REQUIRED_AAL_MATCH="false"

if [[ "$STATUS_CODE" == "200" ]]; then
  if [[ "$BODY_COMPACT" == *"\"auth_mode\":\"${EXPECTED_AUTH_MODE}\""* ]]; then
    AUTH_MODE_MATCH="true"
  fi
  if [[ "$BODY_COMPACT" == *"\"mock_mode\":false"* ]]; then
    MOCK_MODE_MATCH="true"
  fi
  if [[ "$BODY_COMPACT" == *"\"required_app_aal\":\"${EXPECTED_REQUIRED_AAL}\""* ]]; then
    REQUIRED_AAL_MATCH="true"
  fi
fi

if [[ "$STATUS_CODE" != "200" || "$AUTH_MODE_MATCH" != "true" || "$MOCK_MODE_MATCH" != "true" || "$REQUIRED_AAL_MATCH" != "true" ]]; then
  RESULT="fail"
fi

cat >"$META_FILE" <<EOF
timestamp=$TIMESTAMP
url=$URL
status_code=$STATUS_CODE
expected_auth_mode=$EXPECTED_AUTH_MODE
auth_mode_match=$AUTH_MODE_MATCH
mock_mode_false_match=$MOCK_MODE_MATCH
expected_required_aal=$EXPECTED_REQUIRED_AAL
required_aal_match=$REQUIRED_AAL_MATCH
result=$RESULT
headers_file=$(basename "$HEADERS_FILE")
body_file=$(basename "$BODY_FILE")
EOF

printf '%s\n' "$META_FILE"

if [[ "$RESULT" != "pass" && "${ALLOW_STATUS_MISMATCH:-0}" != "1" ]]; then
  echo "Preflight failed. Inspect $META_FILE and $BODY_FILE" >&2
  exit 1
fi
