#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CORE_GATE_SCRIPT="$ROOT_DIR/scripts/run_staging_tenant_safety_core_gate.sh"
SUMMARY_SCRIPT="$ROOT_DIR/scripts/summarize_staging_tenant_safety_run.sh"
RUN_STAMP="${RUN_STAMP:-$(date +%Y-%m-%d_%H%M%S)}"
if [[ -n "${PROBE_OUTPUT_DIR:-}" ]]; then
  PROBE_DIR="$PROBE_OUTPUT_DIR"
else
  PROBE_BASE_DIR="${PROBE_OUTPUT_BASE_DIR:-$ROOT_DIR/docs/release_artifacts/tenant_safety/probes}"
  PROBE_DIR="$PROBE_BASE_DIR/$RUN_STAMP"
fi
SUMMARY_FILE="${SUMMARY_FILE:-$ROOT_DIR/docs/release_artifacts/tenant_safety/tenant-safety-run-summary.md}"

usage() {
  cat <<'EOF'
Usage:
  bash scripts/run_staging_tenant_safety_bundle.sh

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
  PROBE_OUTPUT_DIR         Defaults to docs/release_artifacts/tenant_safety/probes
  SUMMARY_FILE             Defaults to docs/release_artifacts/tenant_safety/tenant-safety-run-summary.md
  REVOCATION_MEMBERSHIP_ID If set, the revocation probe is included by the core gate
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

mkdir -p "$PROBE_DIR"

echo "==> tenant-safety core gate"
OUTPUT_DIR="$PROBE_DIR" bash "$CORE_GATE_SCRIPT"

echo "==> tenant-safety combined summary"
bash "$SUMMARY_SCRIPT" "$PROBE_DIR" "$SUMMARY_FILE" >/dev/null

echo "Probe dir: $PROBE_DIR"
echo "Summary: $SUMMARY_FILE"
