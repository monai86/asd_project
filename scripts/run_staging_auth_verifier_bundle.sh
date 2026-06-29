#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PREFLIGHT_SCRIPT="$ROOT_DIR/scripts/run_staging_auth_verifier_preflight.sh"
CORE_GATE_SCRIPT="$ROOT_DIR/scripts/run_staging_auth_verifier_core_gate.sh"
LIFECYCLE_GATE_SCRIPT="$ROOT_DIR/scripts/run_staging_auth_verifier_lifecycle_gate.sh"
SUMMARY_SCRIPT="$ROOT_DIR/scripts/summarize_staging_auth_verifier_run.sh"
RUN_STAMP="${RUN_STAMP:-$(date +%Y-%m-%d_%H%M%S)}"
PREFLIGHT_DIR="${PREFLIGHT_OUTPUT_DIR:-$ROOT_DIR/docs/release_artifacts/auth_verifier/preflight}"
if [[ -n "${PROBE_OUTPUT_DIR:-}" ]]; then
  PROBE_DIR="$PROBE_OUTPUT_DIR"
else
  PROBE_BASE_DIR="${PROBE_OUTPUT_BASE_DIR:-$ROOT_DIR/docs/release_artifacts/auth_verifier/probes}"
  PROBE_DIR="$PROBE_BASE_DIR/$RUN_STAMP"
fi
SUMMARY_FILE="${SUMMARY_FILE:-$ROOT_DIR/docs/release_artifacts/auth_verifier/verifier-run-summary.md}"
EXPECTED_DENY_STATUS="${EXPECTED_DENY_STATUS:-403}"

usage() {
  cat <<'EOF'
Usage:
  bash scripts/run_staging_auth_verifier_bundle.sh

Required environment:
  STAGING_API_BASE_URL
  ORG_A_ID
  ORG_B_ID
  ORG_A_CASE_ID
  ORG_B_CASE_ID
  TOKEN_THERAPIST_A_ASSIGNED

Optional environment:
  PREFLIGHT_OUTPUT_DIR   Defaults to docs/release_artifacts/auth_verifier/preflight
  PROBE_OUTPUT_DIR       Defaults to docs/release_artifacts/auth_verifier/probes
  SUMMARY_FILE           Defaults to docs/release_artifacts/auth_verifier/verifier-run-summary.md
  EXPECTED_DENY_STATUS   Defaults to 403

Lifecycle gate is skipped unless all three tokens are present:
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

mkdir -p "$PREFLIGHT_DIR" "$PROBE_DIR"

echo "==> preflight"
PREFLIGHT_META="$(PREFLIGHT_OUTPUT_DIR="$PREFLIGHT_DIR" bash "$PREFLIGHT_SCRIPT")"

echo "==> core gate"
OUTPUT_DIR="$PROBE_DIR" bash "$CORE_GATE_SCRIPT"

if [[ -n "${TOKEN_THERAPIST_INVITATION_PENDING:-}" && -n "${TOKEN_THERAPIST_AAL1:-}" && -n "${TOKEN_THERAPIST_INACTIVE_MEMBERSHIP:-}" ]]; then
  echo "==> lifecycle gate"
  EXPECTED_DENY_STATUS="$EXPECTED_DENY_STATUS" OUTPUT_DIR="$PROBE_DIR" bash "$LIFECYCLE_GATE_SCRIPT"
else
  echo "==> lifecycle gate skipped (missing one or more lifecycle tokens)"
fi

echo "==> combined summary"
bash "$SUMMARY_SCRIPT" "$PREFLIGHT_META" "$PROBE_DIR" "$SUMMARY_FILE" >/dev/null

echo "Preflight meta: $PREFLIGHT_META"
echo "Probe dir: $PROBE_DIR"
echo "Summary: $SUMMARY_FILE"
