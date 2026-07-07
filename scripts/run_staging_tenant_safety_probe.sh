#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  bash scripts/run_staging_tenant_safety_probe.sh <scenario>

Scenarios:
  assigned_case_read
  cross_org_case_read
  unassigned_case_read
  supervisor_case_read
  org_admin_memberships
  tenant_isolation_smoke
  org_admin_case_read
  platform_break_glass
  platform_case_read
  revoke_membership

Required environment:
  STAGING_API_BASE_URL
  ORG_A_ID
  ORG_B_ID
  ORG_A_CASE_ID
  ORG_B_CASE_ID

Token environment by scenario:
  TOKEN_THERAPIST_A_ASSIGNED
  TOKEN_THERAPIST_A_UNASSIGNED
  TOKEN_SUPERVISOR_A
  TOKEN_ORG_ADMIN_A
  TOKEN_PLATFORM_OPERATOR_A

Additional environment:
  REVOCATION_MEMBERSHIP_ID   Required for revoke_membership
  OUTPUT_DIR                 Optional. Defaults to docs/release_artifacts/tenant_safety/probes
  ALLOW_STATUS_MISMATCH      Optional. Set to 1 to avoid non-zero exit on unexpected status
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
OUTPUT_DIR="${OUTPUT_DIR:-$ROOT_DIR/docs/release_artifacts/tenant_safety/probes}"
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

case "$SCENARIO" in
  assigned_case_read)
    require_env TOKEN_THERAPIST_A_ASSIGNED
    TOKEN="$TOKEN_THERAPIST_A_ASSIGNED"
    ORG_ID="$ORG_A_ID"
    PATH_SUFFIX="/cases/$ORG_A_CASE_ID"
    EXPECTED_STATUS="200"
    ;;
  cross_org_case_read)
    require_env TOKEN_THERAPIST_A_ASSIGNED
    TOKEN="$TOKEN_THERAPIST_A_ASSIGNED"
    ORG_ID="$ORG_A_ID"
    PATH_SUFFIX="/cases/$ORG_B_CASE_ID"
    EXPECTED_STATUS="404"
    ;;
  unassigned_case_read)
    require_env TOKEN_THERAPIST_A_UNASSIGNED
    TOKEN="$TOKEN_THERAPIST_A_UNASSIGNED"
    ORG_ID="$ORG_A_ID"
    PATH_SUFFIX="/cases/$ORG_A_CASE_ID"
    EXPECTED_STATUS="403"
    ;;
  supervisor_case_read)
    require_env TOKEN_SUPERVISOR_A
    TOKEN="$TOKEN_SUPERVISOR_A"
    ORG_ID="$ORG_A_ID"
    PATH_SUFFIX="/cases/$ORG_A_CASE_ID"
    EXPECTED_STATUS="200"
    ;;
  org_admin_memberships)
    require_env TOKEN_ORG_ADMIN_A
    TOKEN="$TOKEN_ORG_ADMIN_A"
    ORG_ID="$ORG_A_ID"
    PATH_SUFFIX="/organizations/current/memberships"
    EXPECTED_STATUS="200"
    ;;
  tenant_isolation_smoke)
    require_env TOKEN_ORG_ADMIN_A
    TOKEN="$TOKEN_ORG_ADMIN_A"
    ORG_ID="$ORG_A_ID"
    PATH_SUFFIX="/organizations/current/tenant-isolation-smoke"
    EXPECTED_STATUS="200"
    ;;
  org_admin_case_read)
    require_env TOKEN_ORG_ADMIN_A
    TOKEN="$TOKEN_ORG_ADMIN_A"
    ORG_ID="$ORG_A_ID"
    PATH_SUFFIX="/cases/$ORG_A_CASE_ID"
    EXPECTED_STATUS="403"
    ;;
  platform_break_glass)
    require_env TOKEN_PLATFORM_OPERATOR_A
    TOKEN="$TOKEN_PLATFORM_OPERATOR_A"
    ORG_ID="$ORG_A_ID"
    METHOD="POST"
    PATH_SUFFIX="/cases/$ORG_A_CASE_ID/break-glass-access"
    EXPECTED_STATUS="200"
    ;;
  platform_case_read)
    require_env TOKEN_PLATFORM_OPERATOR_A
    TOKEN="$TOKEN_PLATFORM_OPERATOR_A"
    ORG_ID="$ORG_A_ID"
    PATH_SUFFIX="/cases/$ORG_A_CASE_ID"
    EXPECTED_STATUS="403"
    ;;
  revoke_membership)
    require_env TOKEN_ORG_ADMIN_A
    require_env REVOCATION_MEMBERSHIP_ID
    TOKEN="$TOKEN_ORG_ADMIN_A"
    ORG_ID="$ORG_A_ID"
    METHOD="POST"
    PATH_SUFFIX="/organizations/current/memberships/$REVOCATION_MEMBERSHIP_ID/revoke"
    EXPECTED_STATUS="200"
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

STATUS_CODE="$(
  curl -sS \
    -X "$METHOD" \
    -D "$HEADERS_FILE" \
    -o "$BODY_FILE" \
    -w '%{http_code}' \
    -H "Authorization: Bearer $TOKEN" \
    -H "X-Organization-Id: $ORG_ID" \
    "$URL"
)"

RESULT="pass"
if [[ "$STATUS_CODE" != "$EXPECTED_STATUS" ]]; then
  RESULT="fail"
fi

BODY_ASSERT_RESULT="not_applicable"
BODY_ASSERT_DETAIL=""
if [[ "$SCENARIO" == "tenant_isolation_smoke" && "$STATUS_CODE" == "$EXPECTED_STATUS" ]]; then
  if python3 -c 'import json, sys
path = sys.argv[1]
with open(path, "r", encoding="utf-8") as handle:
    payload = json.load(handle)
checks = payload.get("checks", [])
if payload.get("status") != "passed":
    raise SystemExit(f"status={payload.get('"'"'status'"'"')}")
if not checks:
    raise SystemExit("checks=empty")
failed = [check.get("key", "unknown") for check in checks if not check.get("passed")]
if failed:
    raise SystemExit("failed_checks=" + ",".join(failed))
' "$BODY_FILE" >/dev/null 2>&1; then
    BODY_ASSERT_RESULT="pass"
  else
    BODY_ASSERT_RESULT="fail"
    BODY_ASSERT_DETAIL="tenant_isolation_smoke body must contain status=passed and all checks passed"
    RESULT="fail"
  fi
fi

cat >"$META_FILE" <<EOF
scenario=$SCENARIO
timestamp=$TIMESTAMP
method=$METHOD
url=$URL
organization_id=$ORG_ID
status_code=$STATUS_CODE
expected_status=$EXPECTED_STATUS
result=$RESULT
body_assert_result=$BODY_ASSERT_RESULT
body_assert_detail=$BODY_ASSERT_DETAIL
headers_file=$(basename "$HEADERS_FILE")
body_file=$(basename "$BODY_FILE")
EOF

printf '%s\n' "$META_FILE"

if [[ "$RESULT" != "pass" && "${ALLOW_STATUS_MISMATCH:-0}" != "1" ]]; then
  if [[ -n "$BODY_ASSERT_DETAIL" ]]; then
    echo "Scenario $SCENARIO failed body assertion: $BODY_ASSERT_DETAIL" >&2
  else
    echo "Scenario $SCENARIO expected status $EXPECTED_STATUS but received $STATUS_CODE" >&2
  fi
  exit 1
fi
