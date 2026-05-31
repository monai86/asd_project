#!/bin/bash
set -eo pipefail

# ANSI color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0;0m' # No Color

echo -e "${BLUE}=== Starting Project Verification Script ===${NC}"

# Check Python environment
if [ -d ".venv" ]; then
    echo -e "${BLUE}[1/5] Activating Python virtual environment...${NC}"
    # shellcheck disable=SC1091
    source .venv/bin/activate
else
    echo -e "${YELLOW}[Warning] .venv directory not found. Using system Python.${NC}"
fi

# 1. Python Syntax & Import Validation
echo -e "${BLUE}[2/5] Running Python import validation checks...${NC}"
python_imports=(
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
    if python -c "import $mod" >/dev/null 2>&1; then
        echo -e "${GREEN}OK${NC}"
    else
        echo -e "${RED}FAILED${NC}"
        echo -e "${RED}Error: Failed to import $mod. Check dependencies or syntax.${NC}"
        exit 1
    fi
done

# 2. Pytest Core Tests
echo -e "${BLUE}[3/5] Running core Python unit tests (excluding heavy audio)...${NC}"
if python -c "import pytest" >/dev/null 2>&1; then
    pytest -m "not audio"
    echo -e "${GREEN}✓ All core Python unit tests passed successfully.${NC}"
else
    echo -e "${RED}Error: pytest is not installed in the current Python environment.${NC}"
    exit 1
fi

# 3. Frontend App Checks
apps=(
    "therapist-clinician-app"
    "public-screening"
    "presentation-dashboard"
)

for app in "${apps[@]}"; do
    echo -e "${BLUE}[4/5] Verifying frontend app: $app...${NC}"
    if [ -d "$app" ]; then
        (
            cd "$app"
            echo "  Installing Node modules for $app..."
            npm install
            
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
