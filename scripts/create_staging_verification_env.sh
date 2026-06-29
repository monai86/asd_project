#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  bash scripts/create_staging_verification_env.sh [slug]

Optional environment:
  OUTPUT_DIR  Defaults to docs/release_artifacts/staging_env
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEMPLATE_PATH="$ROOT_DIR/docs/templates/STAGING_VERIFICATION_ENV_TEMPLATE.env"
OUTPUT_DIR="${OUTPUT_DIR:-$ROOT_DIR/docs/release_artifacts/staging_env}"
DATE_STAMP="$(date +%Y-%m-%d)"
TIME_STAMP="$(date +%H%M%S)"
SLUG="${1:-staging-verification}"
OUTPUT_PATH="$OUTPUT_DIR/${DATE_STAMP}_${TIME_STAMP}_${SLUG}.env"

if [[ ! -f "$TEMPLATE_PATH" ]]; then
  echo "Template not found: $TEMPLATE_PATH" >&2
  exit 1
fi

mkdir -p "$OUTPUT_DIR"

if [[ -e "$OUTPUT_PATH" ]]; then
  echo "Refusing to overwrite existing file: $OUTPUT_PATH" >&2
  exit 1
fi

cp "$TEMPLATE_PATH" "$OUTPUT_PATH"

if git -C "$ROOT_DIR" rev-parse --short HEAD >/dev/null 2>&1; then
  COMMIT_SHA="$(git -C "$ROOT_DIR" rev-parse --short HEAD)"
  {
    printf '# Generated: %s %s\n' "$DATE_STAMP" "$TIME_STAMP"
    printf '# Commit: %s\n' "$COMMIT_SHA"
    printf '# Fill placeholders before running verifier bundles.\n\n'
    cat "$OUTPUT_PATH"
  } >"$OUTPUT_PATH.tmp"
  mv "$OUTPUT_PATH.tmp" "$OUTPUT_PATH"
fi

echo "$OUTPUT_PATH"
