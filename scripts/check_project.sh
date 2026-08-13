#!/bin/bash
set -eo pipefail

select_python_runtime() {
    local candidate
    local candidates=()

    if [ -n "${LINGUALENS_PYTHON:-}" ]; then
        candidates+=("$LINGUALENS_PYTHON")
    fi
    candidates+=(".venv/bin/python")
    for candidate in .venv*/bin/python; do
        candidates+=("$candidate")
    done
    candidates+=("python3.12" "python3.13" "python3.11" "python3")

    for candidate in "${candidates[@]}"; do
        if { [ -x "$candidate" ] || command -v "$candidate" >/dev/null 2>&1; } \
            && "$candidate" "$(dirname "$0")/check_python_runtime.py" >/dev/null 2>&1; then
            printf '%s\n' "$candidate"
            return 0
        fi
    done
    return 1
}

if ! PYTHON_BIN="$(select_python_runtime)"; then
    echo "Error: LinguaLens requires Python >=3.11,<3.14; Python 3.12 is recommended." >&2
    exit 2
fi

"$PYTHON_BIN" "$(dirname "$0")/check_python_runtime.py"

# ANSI color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0;0m' # No Color

echo -e "${BLUE}=== Starting Project Verification Script ===${NC}"

echo -e "${BLUE}[0/7] Checking repository source-of-truth consistency...${NC}"
"$PYTHON_BIN" scripts/check_repo_consistency.py

echo -e "${BLUE}[1/7] Running local secret scan...${NC}"
"$PYTHON_BIN" scripts/security_scan.py

echo -e "${BLUE}[2/7] Using Python interpreter: $PYTHON_BIN${NC}"

# 1. Python Syntax & Import Validation
echo -e "${BLUE}[3/7] Running Python import validation checks...${NC}"
python_imports=(
    "app.main"
    "src.clinical_workflow"
    "src.clinical_workflow.models"
    "src.clinical_workflow.repository_interface"
    "src.clinical_workflow.mock_repository"
    "src.clinical_workflow.postgres_supabase_repository"
    "src.therapist_backend.app"
    "src.audio_pipeline.chat_formatter"
    "src.audio_pipeline.chatter_validator"
    "src.audio_pipeline.segmentation"
    "src.audio_pipeline.whisper_transcribe"
)

for mod in "${python_imports[@]}"; do
    echo -n "  Checking import of $mod... "
    if PYTHONPATH=apps/api:src "$PYTHON_BIN" -c "import $mod" >/dev/null 2>&1; then
        echo -e "${GREEN}OK${NC}"
    else
        echo -e "${RED}FAILED${NC}"
        echo -e "${RED}Error: Failed to import $mod. Check dependencies or syntax.${NC}"
        exit 1
    fi
done

# 2. Pytest Core Tests
echo -e "${BLUE}[4/7] Running core Python unit tests (excluding heavy audio)...${NC}"
if "$PYTHON_BIN" -c "import pytest" >/dev/null 2>&1; then
    PYTHONPATH=apps/api:src "$PYTHON_BIN" -m pytest -m "not audio"
    echo -e "${GREEN}✓ All core Python unit tests passed successfully.${NC}"
else
    echo -e "${RED}Error: pytest is not installed in the current Python environment.${NC}"
    exit 1
fi

echo -e "${BLUE}[5/7] Running API migration smoke check...${NC}"
PYTHONPATH=apps/api:src "$PYTHON_BIN" scripts/check_api_migrations.py

# 3. Maintained Frontend App Checks
apps=(
    "apps/lingualens-app"
)

for app in "${apps[@]}"; do
    echo -e "${BLUE}[6/7] Verifying frontend app: $app...${NC}"
    if [ -d "$app" ]; then
        (
            cd "$app"
            echo "  Installing locked Node modules for $app..."
            npm ci
            
            echo "  Running tests for $app..."
            if grep -q '"test":' package.json; then
                npm test
            else
                echo -e "${YELLOW}  [Skip] No 'test' script found in $app/package.json${NC}"
            fi
            
            echo "  Building production package for $app..."
            npm run build
            echo -e "${GREEN}  ✓ $app verified successfully.${NC}"
        )
    else
        echo -e "${RED}Error: Directory $app not found.${NC}"
        exit 1
    fi
done

echo -e "\n${GREEN}=== Success: All project verifications passed! ===${NC}"
exit 0
