#!/bin/bash
# ============================================================
#   FisTransfer — Mac One-Click Setup
# ============================================================
#   Run after cloning the repo:
#     chmod +x setup_mac.sh && ./setup_mac.sh
# ============================================================

set -e

echo ""
echo "============================================================"
echo "  FisTransfer — Mac Setup"
echo "  Gesture-controlled screen & file transfer"
echo "============================================================"
echo ""

# ── Step 1: Check Python ──────────────────────────────────────
echo "[1/5] Checking Python..."
if ! command -v python3 &> /dev/null; then
    echo "  ERROR: Python 3 not found!"
    echo "  Install with: brew install python3"
    exit 1
fi
python3 --version
echo "       OK!"
echo ""

# ── Step 2: Create virtual environment ────────────────────────
echo "[2/5] Creating virtual environment..."
if [ ! -d "fistransfer_env" ]; then
    python3 -m venv fistransfer_env
    echo "       Created: fistransfer_env/"
else
    echo "       Already exists, skipping."
fi
echo ""

# ── Step 3: Install dependencies ──────────────────────────────
echo "[3/5] Installing dependencies..."
source fistransfer_env/bin/activate

pip install --upgrade pip -q
pip install mediapipe opencv-python numpy mss pyautogui -q

echo "       All packages installed!"
echo ""

# ── Step 4: Download model ────────────────────────────────────
echo "[4/5] Downloading MediaPipe hand model..."
mkdir -p models

if [ ! -f "models/hand_landmarker.task" ]; then
    echo "       Downloading hand_landmarker.task (~7.8 MB)..."
    curl -L -o models/hand_landmarker.task \
        https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task
    echo "       Model downloaded!"
else
    echo "       Model already exists, skipping."
fi
echo ""

# ── Step 5: Camera Permission ─────────────────────────────────
echo "[5/5] Camera permission"
echo ""
echo "============================================================"
echo "  IMPORTANT: macOS needs camera access!"
echo "  When prompted, click 'Allow' to grant camera access."
echo ""
echo "  If the camera doesn't work:"
echo "    System Settings → Privacy & Security → Camera"
echo "    Enable access for Terminal (or your terminal app)"
echo "============================================================"
echo ""

# ── Done! ─────────────────────────────────────────────────────
echo ""
echo "============================================================"
echo "  SETUP COMPLETE!"
echo "============================================================"
echo ""
echo "  To start FisTransfer:"
echo ""
echo "    source fistransfer_env/bin/activate"
echo "    python -m mac"
echo ""
echo "  Or run:  ./run_mac.sh"
echo ""
echo "  Before running, edit config.py:"
echo "    MAC_IP = \"your.mac.ip\"     (run: ifconfig en0)"
echo "    WIN_IP = \"your.windows.ip\" (run: ipconfig on Windows)"
echo ""
echo "  Gestures:"
echo "    🤜 Closed FIST (0.5s)   = Send your screenshot"
echo "    🖐  Open PALM (0.3s)     = Accept incoming screenshot"
echo "    🤏 PINCH (0.3s)          = Pick up selected Finder file"
echo "    🤏→🖐 Release pinch     = Accept incoming file"
echo ""
echo "    Press 'm' to toggle hand-cursor control"
echo "    Press 'q' to quit"
echo ""
echo "============================================================"
