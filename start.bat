@echo off
setlocal
cd /d "%~dp0"
title Bulk Checker

rem The portable version (ZIP from GitHub Releases) ships Python in the python\ folder
if exist "python\python.exe" (
    echo Bulk Checker is opening in your browser. Close this window to stop it.
    "python\python.exe" -m streamlit run app.py
    pause
    exit /b
)

if not exist ".venv\Scripts\python.exe" (
    echo First run: setting things up, this takes a minute or two...
    py -3 -m venv .venv 2>nul || python -m venv .venv
    if errorlevel 1 (
        echo.
        echo Python was not found. Install it from https://www.python.org/downloads/
        echo and make sure to tick "Add Python to PATH" during installation.
        echo Or download the portable version from GitHub Releases, it doesn't need Python.
        pause
        exit /b 1
    )
)

rem Dependencies are only installed when requirements.txt changes.
fc /b requirements.txt .venv\installed-requirements.txt >nul 2>&1
if errorlevel 1 (
    echo Installing dependencies...
    ".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -q -r requirements.txt
    if errorlevel 1 (
        echo Installation failed.
        pause
        exit /b 1
    )
    copy /y requirements.txt .venv\installed-requirements.txt >nul
)

echo Bulk Checker is opening in your browser. Close this window to stop it.
".venv\Scripts\python.exe" -m streamlit run app.py
pause
