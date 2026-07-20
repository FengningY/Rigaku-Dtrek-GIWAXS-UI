@echo off
setlocal

set "APP_DIR=%~dp0"
set "ENV_NAME=rigaku-giwaxs"
set "CONDA_BAT="
set "PYTHON_EXE=%APP_DIR%.venv\Scripts\python.exe"

if exist "%PYTHON_EXE%" (
    "%PYTHON_EXE%" "%APP_DIR%Rigaku_Dtrek_UI.py"
    if errorlevel 1 (
        echo.
        echo The UI did not start. Check the local .venv installation described in the README.
        pause
    )
    goto :end
)

for %%P in (
    "%USERPROFILE%\miniconda3\condabin\conda.bat"
    "%USERPROFILE%\anaconda3\condabin\conda.bat"
    "%USERPROFILE%\miniforge3\condabin\conda.bat"
    "%ProgramData%\miniconda3\condabin\conda.bat"
    "%ProgramData%\Anaconda3\condabin\conda.bat"
) do (
    if not defined CONDA_BAT if exist "%%~fP" set "CONDA_BAT=%%~fP"
)

if not defined CONDA_BAT (
    for /f "delims=" %%P in ('where conda.bat 2^>nul') do if not defined CONDA_BAT set "CONDA_BAT=%%P"
)

if not defined CONDA_BAT (
    echo Conda was not found. Install Miniconda or Anaconda, then follow the README installation steps.
    pause
    exit /b 1
)

call "%CONDA_BAT%" run -n "%ENV_NAME%" python "%APP_DIR%Rigaku_Dtrek_UI.py"
if errorlevel 1 (
    echo.
    echo The UI did not start. Confirm that the "%ENV_NAME%" environment is installed.
    pause
)

:end
endlocal
