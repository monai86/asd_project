#!/usr/bin/env bash
set -euo pipefail

# Build a sanitized static bundle for the Project Atlas dashboard.
# The dashboard source reads ../data, ../reports, and ../artifacts when served
# from the repo root. A public host should publish only the files needed for
# the presentation, so this script rewrites those paths to local ./ folders.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="${ROOT_DIR}/dist/public_atlas"

rm -rf "${OUT_DIR}"
mkdir -p \
  "${OUT_DIR}/data" \
  "${OUT_DIR}/reports/metrics" \
  "${OUT_DIR}/reports/figures" \
  "${OUT_DIR}/artifacts"

cp "${ROOT_DIR}/project_dashboard/index.html" "${OUT_DIR}/index.html"
cp "${ROOT_DIR}/project_dashboard/styles.css" "${OUT_DIR}/styles.css"
cp "${ROOT_DIR}/project_dashboard/app.js" "${OUT_DIR}/app.js"

cp "${ROOT_DIR}/data/combined_features.csv" "${OUT_DIR}/data/combined_features.csv"
cp "${ROOT_DIR}/data/longitudinal_features.csv" "${OUT_DIR}/data/longitudinal_features.csv"

find "${ROOT_DIR}/reports/metrics" -maxdepth 1 -type f -name "*.csv" -exec cp {} "${OUT_DIR}/reports/metrics/" \;
find "${ROOT_DIR}/reports/figures" -maxdepth 1 -type f -name "*.png" -exec cp {} "${OUT_DIR}/reports/figures/" \;

cp "${ROOT_DIR}/artifacts/model_card.json" "${OUT_DIR}/artifacts/model_card.json"
cp "${ROOT_DIR}/artifacts/feature_schema.json" "${OUT_DIR}/artifacts/feature_schema.json"

perl -0pi -e 's#\.\./data/#./data/#g; s#\.\./reports/#./reports/#g; s#\.\./artifacts/#./artifacts/#g' \
  "${OUT_DIR}/index.html" \
  "${OUT_DIR}/app.js"

cat > "${OUT_DIR}/_headers" <<'HEADERS'
/*
  X-Content-Type-Options: nosniff
  Referrer-Policy: no-referrer
  Permissions-Policy: camera=(), microphone=(), geolocation=()
HEADERS

cat > "${OUT_DIR}/README.txt" <<'README'
Public Project Atlas build.

This bundle intentionally includes only dashboard assets, derived CSVs,
figures, and non-executable metadata. Raw CHAT transcripts, uploaded audio,
and the executable joblib model bundle are not copied.
README

echo "Built ${OUT_DIR}"
