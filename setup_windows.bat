@echo off
REM ============================================================
REM   FisTransfer — Windows One-Click Setup
REM ============================================================
REM   Run this script after cloning the repo.
REM   It sets up everything you need to start receiving.
REM
REM   Usage: Double-click this file or run in Command Prompt:
REM          setup_windows.bat
REM ============================================================

echo.
echo  ============================================================
echo    FisTransfer — Windows Setup
echo    Gesture-controlled screen ^& file transfer
echo  ============================================================
echo.

REM ── Step 1: Check Python ──────────────────────────────────────
echo  [1/6] Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo  ERROR: Python is not installed or not in PATH!
    echo  Download Python from: https://www.python.org/downloads/
    echo  Make sure to check "Add Python to PATH" during install.
    echo.
    pause
    exit /b 1
)
python --version
echo         OK!
echo.

REM ── Step 2: Create virtual environment ────────────────────────
echo  [2/6] Creating virtual environment...
if not exist "fistransfer_env" (
    python -m venv fistransfer_env
    echo         Created: fistransfer_env\
) else (
    echo         Already exists, skipping.
)
echo.

REM ── Step 3: Activate venv and install dependencies ────────────
echo  [3/6] Installing dependencies...
call fistransfer_env\Scripts\activate.bat

pip install --upgrade pip -q
pip install mediapipe opencv-python numpy mss pyautogui -q

if %errorlevel% neq 0 (
    echo.
    echo  ERROR: Failed to install dependencies!
    echo  Try running manually:
    echo    fistransfer_env\Scripts\activate.bat
    echo    pip install mediapipe opencv-python numpy mss pyautogui
    echo.
    pause
    exit /b 1
)
echo         All packages installed!
echo.

REM ── Step 4: Download hand_landmarker.task model ───────────────
echo  [4/6] Downloading MediaPipe hand model...
if not exist "models" mkdir models

if not exist "models\hand_landmarker.task" (
    echo         Downloading hand_landmarker.task ^(~7.8 MB^)...
    curl -L -o models\hand_landmarker.task https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task
    if %errorlevel% neq 0 (
        echo.
        echo  ERROR: Download failed! Check your internet connection.
        echo  Manual download:
        echo    https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task
        echo  Save to: models\hand_landmarker.task
        echo.
        pause
        exit /b 1
    )
    echo         Model downloaded!
) else (
    echo         Model already exists, skipping.
)
echo.

REM ── Step 5: Firewall rules ────────────────────────────────────
echo  [5/6] Firewall setup required!
echo.
echo  ============================================================
echo    IMPORTANT: Open Windows PowerShell as ADMINISTRATOR
echo    and run these 3 commands:
echo  ============================================================
echo.
echo    New-NetFirewallRule -DisplayName "FisTransfer Signal" -Direction Inbound -LocalPort 5005 -Protocol TCP -Action Allow
echo.
echo    New-NetFirewallRule -DisplayName "FisTransfer Transfer" -Direction Inbound -LocalPort 5006 -Protocol TCP -Action Allow
echo.
echo    New-NetFirewallRule -DisplayName "FisTransfer Files" -Direction Inbound -LocalPort 5007 -Protocol TCP -Action Allow
echo.
echo  ============================================================
echo    Or temporarily disable Windows Firewall for testing:
echo    Windows Security ^> Firewall ^> Turn off
echo  ============================================================
echo.
pause

REM ── Step 6: Configure IP ──────────────────────────────────────
echo.
echo  [6/6] Network configuration
echo.
echo  ============================================================
echo    Find your Windows IP by running:   ipconfig
echo    Find your Mac IP by running:       ifconfig en0
echo.
echo    Then edit config.py and set:
echo      MAC_IP = "your.mac.ip"
echo      WIN_IP = "your.windows.ip"
echo  ============================================================
echo.

REM ── Done! ─────────────────────────────────────────────────────
echo.
echo  ============================================================
echo    SETUP COMPLETE!
echo  ============================================================
echo.
echo    To start FisTransfer:
echo.
echo      1. Open Command Prompt in this folder
echo      2. Run:
echo           fistransfer_env\Scripts\activate.bat
echo           python -m win
echo.
echo    Or just double-click: run_win.bat
echo.
echo    Gestures:
echo      Closed FIST ^(0.5s^)    = Send your screenshot
echo      Open PALM ^(0.3s^)      = Accept incoming screenshot
echo      PINCH ^(0.3s^)          = Pick up selected file
echo      Release PINCH          = Accept incoming file
echo.
echo      Press 'm' to toggle hand-cursor control
echo      Press 'q' to quit
echo.
echo  ============================================================
echo.
pause
