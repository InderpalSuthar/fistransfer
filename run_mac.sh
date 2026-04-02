#!/bin/bash
# FisTransfer — Mac Launcher
# Run from the project root: ./run_mac.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="$SCRIPT_DIR/fistransfer_env"

if [ ! -d "$VENV" ]; then
    echo "❌ Virtual environment not found at $VENV"
    echo "   Create it with: python3 -m venv fistransfer_env"
    echo "   Then install:   source fistransfer_env/bin/activate && pip install -r requirements_mac.txt"
    exit 1
fi

echo "🤜 Starting FisTransfer Mac Sender..."
echo ""

source "$VENV/bin/activate"
python -m mac
