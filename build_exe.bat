@echo off
REM ============================================================
REM   FisTransfer — Build Windows .exe
REM ============================================================
REM   Run this file ONCE on a Windows machine to compile the
REM   entire project into a single "FisTransfer.exe" file.
REM
REM   After building, you can copy the "FisTransfer.exe" from
REM   the "dist" folder to ANY Windows computer and run it
REM   without installing Python or anything else!
REM ============================================================

echo.
echo  ============================================================
echo    Building FisTransfer.exe for Windows...
echo  ============================================================
echo.

REM ── Step 1: Ensure venv is active ─────────────────────────────
if exist "fistransfer_env\Scripts\activate.bat" (
    echo  [1/4] Activating virtual environment...
    call fistransfer_env\Scripts\activate.bat
) else (
    echo  ERROR: Virtual environment not found!
    echo  Run "setup_windows.bat" first to install dependencies before building.
    pause
    exit /b 1
)

REM ── Step 2: Install PyInstaller ───────────────────────────────
echo.
echo  [2/4] Installing PyInstaller...
pip install pyinstaller -q
if %errorlevel% neq 0 (
    echo  ERROR: Failed to install PyInstaller.
    pause
    exit /b 1
)

REM ── Step 3: Run PyInstaller build ─────────────────────────────
echo.
echo  [3/4] Compiling to a single .exe file...
echo        ^(This might take a minute or two^)

REM We use --onefile to create a single standalone executable.
REM We use --add-data to bundle the MediaPipe task model into the .exe.
pyinstaller --clean --name "FisTransfer" --onefile ^
    --add-data "models/hand_landmarker.task;models" ^
    --collect-all "mediapipe" ^
    --hidden-import="cv2" ^
    --hidden-import="numpy" ^
    --hidden-import="mss" ^
    --hidden-import="pyautogui" ^
    win/main.py

if %errorlevel% neq 0 (
    echo.
    echo  ERROR: Build failed! Check the output above.
    pause
    exit /b 1
)

REM ── Step 4: Finish up ─────────────────────────────────────────
echo.
echo  [4/4] Build complete!
echo.
echo  ============================================================
echo    SUCCESS! 
echo  ============================================================
echo.
echo    Your standalone portable app is located here:
echo       dist\FisTransfer.exe
echo.
echo    You can now copy "FisTransfer.exe" to any Windows machine.
echo    The user will simply double-click it to run.
echo.
echo    IMPORTANT: The firewall ports ^(5005, 5006, 5007^) must 
echo    still be allowed on the other Windows machine.
echo.
pause
