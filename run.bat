@echo off
cd /d "%~dp0"

set CONFIG=config.yaml
if not "%~1"=="" set CONFIG=%~1

if not exist "%CONFIG%" (
    echo ERROR: Config file not found: %CONFIG%
    pause
    exit /b 1
)

set PY_CMD=
where python >nul 2>&1
if %errorlevel% equ 0 set PY_CMD=python
if "%PY_CMD%"=="" (
    where python3 >nul 2>&1
    if %errorlevel% equ 0 set PY_CMD=python3
)
if "%PY_CMD%"=="" (
    echo ERROR: Python not found
    echo Please run setup.bat first
    pause
    exit /b 1
)

echo =========================================
echo   Excel Utils
echo =========================================
echo.
echo Config: %CONFIG%
echo.

set PYTHONPATH=src
%PY_CMD% -m excel_utils.main "%CONFIG%"

echo.
echo Done.
pause
