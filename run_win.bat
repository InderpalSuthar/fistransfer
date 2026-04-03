@echo off
REM ============================================================
REM   FisTransfer — Windows Launcher
REM   Double-click to start receiving!
REM ============================================================

echo.
echo  ============================================================
echo    FisTransfer — Windows
echo    Gesture-controlled screen ^& file transfer
echo  ============================================================
echo.

REM Activate virtual environment
if exist "fistransfer_env\Scripts\activate.bat" (
    call fistransfer_env\Scripts\activate.bat
) else (
    echo  ERROR: Virtual environment not found!
    echo  Run setup_windows.bat first.
    echo.
    pause
    exit /b 1
)

REM Check model file
if not exist "models\hand_landmarker.task" (
    echo  ERROR: MediaPipe model not found!
    echo  Run setup_windows.bat first.
    echo.
    pause
    exit /b 1
)

REM Launch
python -m win

echo.
echo  FisTransfer stopped.
pause
