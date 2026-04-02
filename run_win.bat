@echo off
REM FisTransfer — Windows Launcher
REM Run from the project root: run_win.bat

set VENV=%~dp0fistransfer_env

if not exist "%VENV%" (
    echo X Virtual environment not found at %VENV%
    echo   Create it with: python -m venv fistransfer_env
    echo   Then install:   fistransfer_env\Scripts\activate ^&^& pip install -r requirements_win.txt
    exit /b 1
)

echo Starting FisTransfer Windows Receiver...
echo.

call "%VENV%\Scripts\activate.bat"
python -m win
