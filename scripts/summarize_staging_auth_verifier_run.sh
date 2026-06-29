#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PREFLIGHT_META="${1:-${PREFLIGHT_META:-}}"
PROBE_DIR="${2:-${PROBE_DIR:-$ROOT_DIR/docs/release_artifacts/auth_verifier/probes}}"
OUTPUT_FILE="${3:-${OUTPUT_FILE:-}}"

if [[ -z "$PREFLIGHT_META" ]]; then
  echo "Missing preflight meta path. Pass it as arg1 or PREFLIGHT_META." >&2
  exit 1
fi

if [[ ! -f "$PREFLIGHT_META" ]]; then
  echo "Preflight meta file not found: $PREFLIGHT_META" >&2
  exit 1
fi

if [[ ! -d "$PROBE_DIR" ]]; then
  echo "Probe directory not found: $PROBE_DIR" >&2
  exit 1
fi

preflight_timestamp=""
preflight_url=""
preflight_status_code=""
expected_auth_mode=""
auth_mode_match=""
mock_mode_false_match=""
expected_required_aal=""
required_aal_match=""
preflight_result=""

while IFS='=' read -r key value; do
  case "$key" in
    timestamp) preflight_timestamp="$value" ;;
    url) preflight_url="$value" ;;
    status_code) preflight_status_code="$value" ;;
    expected_auth_mode) expected_auth_mode="$value" ;;
    auth_mode_match) auth_mode_match="$value" ;;
    mock_mode_false_match) mock_mode_false_match="$value" ;;
    expected_required_aal) expected_required_aal="$value" ;;
    required_aal_match) required_aal_match="$value" ;;
    result) preflight_result="$value" ;;
  esac
done <"$PREFLIGHT_META"

shopt -s nullglob
META_FILES=("$PROBE_DIR"/*.meta.txt)
shopt -u nullglob

if [[ ${#META_FILES[@]} -eq 0 ]]; then
  echo "No probe meta files found in: $PROBE_DIR" >&2
  exit 1
fi

render_report() {
  echo "# Staging Auth Verifier Run Summary"
  echo
  echo "## Preflight"
  echo
  echo "| Field | Value |"
  echo "|---|---|"
  echo "| Timestamp | ${preflight_timestamp:-unknown} |"
  echo "| URL | ${preflight_url:-unknown} |"
  echo "| HTTP status | ${preflight_status_code:-unknown} |"
  echo "| Expected auth mode | ${expected_auth_mode:-unknown} |"
  echo "| Auth mode match | ${auth_mode_match:-unknown} |"
  echo "| Mock mode false match | ${mock_mode_false_match:-unknown} |"
  echo "| Expected required AAL | ${expected_required_aal:-unknown} |"
  echo "| Required AAL match | ${required_aal_match:-unknown} |"
  echo "| Result | ${preflight_result:-unknown} |"
  echo "| Meta file | $(basename "$PREFLIGHT_META") |"
  echo
  echo "## Probes"
  echo
  echo "| Scenario | Result | Expected | Actual | Auth header | Meta file |"
  echo "|---|---|---|---|---|---|"

  for meta_file in "${META_FILES[@]}"; do
    scenario=""
    result=""
    expected_status=""
    status_code=""
    sent_auth_header=""

    while IFS='=' read -r key value; do
      case "$key" in
        scenario) scenario="$value" ;;
        result) result="$value" ;;
        expected_status) expected_status="$value" ;;
        status_code) status_code="$value" ;;
        sent_auth_header) sent_auth_header="$value" ;;
      esac
    done <"$meta_file"

    echo "| ${scenario:-unknown} | ${result:-unknown} | ${expected_status:-?} | ${status_code:-?} | ${sent_auth_header:-?} | $(basename "$meta_file") |"
  done
}

if [[ -n "$OUTPUT_FILE" ]]; then
  render_report | tee "$OUTPUT_FILE"
else
  render_report
fi
