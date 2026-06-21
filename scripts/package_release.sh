#!/bin/bash
set -e

# Go to the root directory of the project
cd "$(dirname "$0")/.."

VERSION=$(python3 - <<'PY'
from pathlib import Path
import re

text = Path("PROJECT_STATUS.md").read_text(encoding="utf-8")
match = re.search(r"Current maintained version:\s*`([^`]+)`", text)
if not match:
    raise SystemExit("Could not determine current maintained version from PROJECT_STATUS.md")
print(match.group(1))
PY
)
OUTPUT_ZIP="asd-project-release-${VERSION}.zip"

echo "Packaging release ${VERSION} into ${OUTPUT_ZIP}..."

# Check if zip command exists
if ! command -v zip &> /dev/null; then
    echo "Error: 'zip' command not found. Please install zip."
    exit 1
fi

# Remove existing zip if it exists
if [ -f "$OUTPUT_ZIP" ]; then
    rm "$OUTPUT_ZIP"
fi

# Run zip excluding the requested folders
zip -r "$OUTPUT_ZIP" . \
    -x "node_modules/*" \
    -x "*/node_modules/*" \
    -x ".venv/*" \
    -x "*/.venv/*" \
    -x ".git/*" \
    -x "dist/*" \
    -x "*/dist/*" \
    -x ".pytest_cache/*" \
    -x "*/.pytest_cache/*" \
    -x ".wrangler/*" \
    -x "*/.wrangler/*" \
    -x "*__MACOSX*" \
    -x "*.DS_Store" \
    -x "$OUTPUT_ZIP"

echo "Release package created successfully: $OUTPUT_ZIP"
