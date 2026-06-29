#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_VALIDATOR_SCRIPT="$ROOT_DIR/scripts/validate_staging_verification_env.sh"
AUTH_BUNDLE_SCRIPT="$ROOT_DIR/scripts/run_staging_auth_verifier_bundle.sh"
TENANT_BUNDLE_SCRIPT="$ROOT_DIR/scripts/run_staging_tenant_safety_bundle.sh"
PACKET_SCRIPT="$ROOT_DIR/scripts/assemble_staging_evidence_packet.sh"

AUTH_SUMMARY_FILE="${AUTH_SUMMARY_FILE:-$ROOT_DIR/docs/release_artifacts/auth_verifier/verifier-run-summary.md}"
TENANT_SUMMARY_FILE="${TENANT_SUMMARY_FILE:-$ROOT_DIR/docs/release_artifacts/tenant_safety/tenant-safety-run-summary.md}"
PACKET_SLUG="${PACKET_SLUG:-staging-review-packet}"

usage() {
  cat <<'EOF'
Usage:
  bash scripts/run_staging_review_bundle.sh

Required environment:
  STAGING_API_BASE_URL
  ORG_A_ID
  ORG_B_ID
  ORG_A_CASE_ID
  ORG_B_CASE_ID
  TOKEN_THERAPIST_A_ASSIGNED
  TOKEN_THERAPIST_A_UNASSIGNED
  TOKEN_SUPERVISOR_A
  TOKEN_ORG_ADMIN_A
  TOKEN_PLATFORM_OPERATOR_A

Optional environment:
  STAGING_APP_URL             Included in the assembled packet when provided
  OPERATOR_NAME               Included in the assembled packet when provided
  REVIEWER_NAME               Included in the assembled packet when provided
  AUTH_SUMMARY_FILE           Defaults to docs/release_artifacts/auth_verifier/verifier-run-summary.md
  TENANT_SUMMARY_FILE         Defaults to docs/release_artifacts/tenant_safety/tenant-safety-run-summary.md
  PACKET_SLUG                 Defaults to staging-review-packet
  EXPECTED_DENY_STATUS        Passed through to lifecycle verifier gate when lifecycle tokens exist
  REVOCATION_MEMBERSHIP_ID    Enables revocation probe in tenant-safety bundle

Lifecycle verifier checks are skipped unless all three tokens are present:
  TOKEN_THERAPIST_INVITATION_PENDING
  TOKEN_THERAPIST_AAL1
  TOKEN_THERAPIST_INACTIVE_MEMBERSHIP
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

require_env STAGING_API_BASE_URL
require_env ORG_A_ID
require_env ORG_B_ID
require_env ORG_A_CASE_ID
require_env ORG_B_CASE_ID
require_env TOKEN_THERAPIST_A_ASSIGNED
require_env TOKEN_THERAPIST_A_UNASSIGNED
require_env TOKEN_SUPERVISOR_A
require_env TOKEN_ORG_ADMIN_A
require_env TOKEN_PLATFORM_OPERATOR_A

echo "==> staging env validation"
bash "$ENV_VALIDATOR_SCRIPT"

echo "==> auth verifier bundle"
bash "$AUTH_BUNDLE_SCRIPT"

echo "==> tenant-safety bundle"
bash "$TENANT_BUNDLE_SCRIPT"

echo "==> staging evidence packet"
PACKET_PATH="$(
  AUTH_VERIFIER_SUMMARY="$AUTH_SUMMARY_FILE" \
  TENANT_SAFETY_SUMMARY="$TENANT_SUMMARY_FILE" \
  STAGING_API_URL="${STAGING_API_BASE_URL:-}" \
  STAGING_APP_URL="${STAGING_APP_URL:-}" \
  OPERATOR_NAME="${OPERATOR_NAME:-}" \
  REVIEWER_NAME="${REVIEWER_NAME:-}" \
  bash "$PACKET_SCRIPT" "$PACKET_SLUG"
)"

echo "Verifier summary: $AUTH_SUMMARY_FILE"
echo "Tenant safety summary: $TENANT_SUMMARY_FILE"
echo "Staging packet: $PACKET_PATH"
