@echo off
REM Double-click this file to start the Real Income by State Explorer.
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo Python is not installed. Install it from https://www.python.org/downloads/ and tick "Add python.exe to PATH".
    pause
    exit /b 1
)

if not exist .venv (
    echo Setting up for the first time. This takes a minute or two...
    python -m venv .venv
)

call .venv\Scripts\activate.bat
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt
if errorlevel 1 (
    echo Installing the app's packages failed. Check your internet connection and try again.
    pause
    exit /b 1
)

echo Starting the app. It will open in your browser. Close this window to stop it.
python -m streamlit run app.py
pause
