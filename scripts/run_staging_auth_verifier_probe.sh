#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  bash scripts/run_staging_auth_verifier_probe.sh <scenario>

Scenarios:
  accepted_aal2_case_read
  missing_bearer_case_read
  wrong_org_case_read
  invitation_pending_case_read
  aal1_case_read
  inactive_membership_case_read

Required environment:
  STAGING_API_BASE_URL
  ORG_A_ID
  ORG_B_ID
  ORG_A_CASE_ID
  ORG_B_CASE_ID

Token environment by scenario:
  TOKEN_THERAPIST_A_ASSIGNED
  TOKEN_THERAPIST_AAL1
  TOKEN_THERAPIST_INVITATION_PENDING
  TOKEN_THERAPIST_INACTIVE_MEMBERSHIP

Additional environment:
  OUTPUT_DIR                    Optional. Defaults to docs/release_artifacts/auth_verifier/probes
  EXPECTED_STATUS               Required for invitation_pending_case_read, aal1_case_read, inactive_membership_case_read
  ALLOW_STATUS_MISMATCH         Optional. Set to 1 to avoid non-zero exit on unexpected status
EOF
}

require_env() {
  local name="$1"
  if [[ -z "${!name:-}" ]]; then
    echo "Missing required environment variable: $name" >&2
    exit 1
  fi
}

if [[ "${1:-}" == "" || "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

SCENARIO="$1"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_DIR="${OUTPUT_DIR:-$ROOT_DIR/docs/release_artifacts/auth_verifier/probes}"
TIMESTAMP="$(date +%Y-%m-%d_%H%M%S)"

require_env STAGING_API_BASE_URL
require_env ORG_A_ID
require_env ORG_B_ID
require_env ORG_A_CASE_ID
require_env ORG_B_CASE_ID

METHOD="GET"
TOKEN=""
ORG_ID=""
PATH_SUFFIX=""
EXPECTED_STATUS=""
SEND_AUTH_HEADER="true"

case "$SCENARIO" in
  accepted_aal2_case_read)
    require_env TOKEN_THERAPIST_A_ASSIGNED
    TOKEN="$TOKEN_THERAPIST_A_ASSIGNED"
    ORG_ID="$ORG_A_ID"
    PATH_SUFFIX="/cases/$ORG_A_CASE_ID"
    EXPECTED_STATUS="200"
    ;;
  missing_bearer_case_read)
    ORG_ID="$ORG_A_ID"
    PATH_SUFFIX="/cases/$ORG_A_CASE_ID"
    EXPECTED_STATUS="401"
    SEND_AUTH_HEADER="false"
    ;;
  wrong_org_case_read)
    require_env TOKEN_THERAPIST_A_ASSIGNED
    TOKEN="$TOKEN_THERAPIST_A_ASSIGNED"
    ORG_ID="$ORG_A_ID"
    PATH_SUFFIX="/cases/$ORG_B_CASE_ID"
    EXPECTED_STATUS="404"
    ;;
  invitation_pending_case_read)
    require_env TOKEN_THERAPIST_INVITATION_PENDING
    require_env EXPECTED_STATUS
    TOKEN="$TOKEN_THERAPIST_INVITATION_PENDING"
    ORG_ID="$ORG_A_ID"
    PATH_SUFFIX="/cases/$ORG_A_CASE_ID"
    EXPECTED_STATUS="$EXPECTED_STATUS"
    ;;
  aal1_case_read)
    require_env TOKEN_THERAPIST_AAL1
    require_env EXPECTED_STATUS
    TOKEN="$TOKEN_THERAPIST_AAL1"
    ORG_ID="$ORG_A_ID"
    PATH_SUFFIX="/cases/$ORG_A_CASE_ID"
    EXPECTED_STATUS="$EXPECTED_STATUS"
    ;;
  inactive_membership_case_read)
    require_env TOKEN_THERAPIST_INACTIVE_MEMBERSHIP
    require_env EXPECTED_STATUS
    TOKEN="$TOKEN_THERAPIST_INACTIVE_MEMBERSHIP"
    ORG_ID="$ORG_A_ID"
    PATH_SUFFIX="/cases/$ORG_A_CASE_ID"
    EXPECTED_STATUS="$EXPECTED_STATUS"
    ;;
  *)
    echo "Unknown scenario: $SCENARIO" >&2
    usage
    exit 1
    ;;
esac

mkdir -p "$OUTPUT_DIR"

BASE_URL="${STAGING_API_BASE_URL%/}"
URL="${BASE_URL}${PATH_SUFFIX}"
HEADERS_FILE="$OUTPUT_DIR/${TIMESTAMP}_${SCENARIO}.headers.txt"
BODY_FILE="$OUTPUT_DIR/${TIMESTAMP}_${SCENARIO}.body.txt"
META_FILE="$OUTPUT_DIR/${TIMESTAMP}_${SCENARIO}.meta.txt"

CURL_ARGS=(
  -sS
  -X "$METHOD"
  -D "$HEADERS_FILE"
  -o "$BODY_FILE"
  -w '%{http_code}'
  -H "X-Organization-Id: $ORG_ID"
)

if [[ "$SEND_AUTH_HEADER" == "true" ]]; then
  CURL_ARGS+=(-H "Authorization: Bearer $TOKEN")
fi

STATUS_CODE="$(curl "${CURL_ARGS[@]}" "$URL")"

RESULT="pass"
if [[ "$STATUS_CODE" != "$EXPECTED_STATUS" ]]; then
  RESULT="fail"
fi

cat >"$META_FILE" <<EOF
scenario=$SCENARIO
timestamp=$TIMESTAMP
method=$METHOD
url=$URL
organization_id=$ORG_ID
status_code=$STATUS_CODE
expected_status=$EXPECTED_STATUS
sent_auth_header=$SEND_AUTH_HEADER
result=$RESULT
headers_file=$(basename "$HEADERS_FILE")
body_file=$(basename "$BODY_FILE")
EOF

printf '%s\n' "$META_FILE"

if [[ "$RESULT" != "pass" && "${ALLOW_STATUS_MISMATCH:-0}" != "1" ]]; then
  echo "Scenario $SCENARIO expected status $EXPECTED_STATUS but received $STATUS_CODE" >&2
  exit 1
fi
