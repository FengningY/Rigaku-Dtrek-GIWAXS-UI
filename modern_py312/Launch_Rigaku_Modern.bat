@echo off
setlocal

set "APP_DIR=%~dp0"
set "PYTHON_EXE=%APP_DIR%.venv\Scripts\pythonw.exe"

if not exist "%PYTHON_EXE%" (
    echo A local Python 3.12 virtual environment was not found.
    echo Follow README.md to create .venv and install requirements_py312.txt.
    pause
    exit /b 1
)

start "Rigaku dTREK GIWAXS" "%PYTHON_EXE%" "%APP_DIR%Rigaku_modern_UI.py"
endlocal
