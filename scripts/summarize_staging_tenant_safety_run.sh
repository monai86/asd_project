#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROBE_DIR="${1:-${PROBE_DIR:-$ROOT_DIR/docs/release_artifacts/tenant_safety/probes}}"
OUTPUT_FILE="${2:-${OUTPUT_FILE:-}}"

if [[ ! -d "$PROBE_DIR" ]]; then
  echo "Probe directory not found: $PROBE_DIR" >&2
  exit 1
fi

shopt -s nullglob
META_FILES=("$PROBE_DIR"/*.meta.txt)
shopt -u nullglob

if [[ ${#META_FILES[@]} -eq 0 ]]; then
  echo "No probe meta files found in: $PROBE_DIR" >&2
  exit 1
fi

render_report() {
  echo "# Staging Tenant-Safety Run Summary"
  echo
  echo "| Scenario | Result | Expected | Actual | Meta file |"
  echo "|---|---|---|---|---|"

  for meta_file in "${META_FILES[@]}"; do
    scenario=""
    result=""
    expected_status=""
    status_code=""

    while IFS='=' read -r key value; do
      case "$key" in
        scenario) scenario="$value" ;;
        result) result="$value" ;;
        expected_status) expected_status="$value" ;;
        status_code) status_code="$value" ;;
      esac
    done <"$meta_file"

    echo "| ${scenario:-unknown} | ${result:-unknown} | ${expected_status:-?} | ${status_code:-?} | $(basename "$meta_file") |"
  done
}

if [[ -n "$OUTPUT_FILE" ]]; then
  render_report | tee "$OUTPUT_FILE"
else
  render_report
fi
