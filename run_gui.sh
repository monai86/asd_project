#!/bin/bash
# LinguaLens Desktop GUI Launcher shortcut
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

if [ -f "$ROOT_DIR/.venv312/bin/python" ]; then
    PYTHON_BIN="$ROOT_DIR/.venv312/bin/python"
elif [ -f "$ROOT_DIR/.venv/bin/python" ]; then
    PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
else
    PYTHON_BIN="python3"
fi

export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES
"$PYTHON_BIN" scripts/lingualens_gui.py "$@"
