#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEMPLATE_PATH="$ROOT_DIR/docs/templates/STAGING_AUTH_VERIFIER_EVIDENCE_TEMPLATE.md"
OUTPUT_DIR="${OUTPUT_DIR:-$ROOT_DIR/docs/release_artifacts/auth_verifier}"
DATE_STAMP="$(date +%Y-%m-%d)"
TIME_STAMP="$(date +%H%M%S)"
SLUG="${1:-staging-auth-verifier}"
OUTPUT_PATH="$OUTPUT_DIR/${DATE_STAMP}_${TIME_STAMP}_${SLUG}.md"

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
  sed -i.bak "s/^- Commit:$/- Commit: ${COMMIT_SHA}/" "$OUTPUT_PATH"
  rm -f "$OUTPUT_PATH.bak"
fi

sed -i.bak "s/^- Date:$/- Date: ${DATE_STAMP}/" "$OUTPUT_PATH"
rm -f "$OUTPUT_PATH.bak"

echo "$OUTPUT_PATH"
