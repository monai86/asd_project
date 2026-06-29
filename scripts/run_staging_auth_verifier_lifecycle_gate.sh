#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROBE_SCRIPT="${PROBE_SCRIPT:-$ROOT_DIR/scripts/run_staging_auth_verifier_probe.sh}"
SUMMARY_SCRIPT="${SUMMARY_SCRIPT:-$ROOT_DIR/scripts/summarize_staging_auth_verifier_probes.sh}"
RUN_STAMP="${RUN_STAMP:-$(date +%Y-%m-%d_%H%M%S)}"
if [[ -n "${OUTPUT_DIR:-}" ]]; then
  PROBE_DIR="$OUTPUT_DIR"
else
  PROBE_BASE_DIR="${OUTPUT_BASE_DIR:-$ROOT_DIR/docs/release_artifacts/auth_verifier/probes}"
  PROBE_DIR="$PROBE_BASE_DIR/$RUN_STAMP"
fi
SUMMARY_FILE="$PROBE_DIR/${RUN_STAMP}_lifecycle_gate_summary.md"
DENY_STATUS="${EXPECTED_DENY_STATUS:-403}"

if [[ ! -x "$PROBE_SCRIPT" && ! -f "$PROBE_SCRIPT" ]]; then
  echo "Probe script not found: $PROBE_SCRIPT" >&2
  exit 1
fi

if [[ ! -x "$SUMMARY_SCRIPT" && ! -f "$SUMMARY_SCRIPT" ]]; then
  echo "Summary script not found: $SUMMARY_SCRIPT" >&2
  exit 1
fi

mkdir -p "$PROBE_DIR"

SCENARIOS=(
  invitation_pending_case_read
  aal1_case_read
  inactive_membership_case_read
)

for scenario in "${SCENARIOS[@]}"; do
  echo "==> $scenario"
  EXPECTED_STATUS="$DENY_STATUS" OUTPUT_DIR="$PROBE_DIR" bash "$PROBE_SCRIPT" "$scenario"
done

bash "$SUMMARY_SCRIPT" "$PROBE_DIR" "$SUMMARY_FILE" >/dev/null

echo "Lifecycle auth-verifier probes passed."
echo "Summary: $SUMMARY_FILE"
