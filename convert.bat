@echo off
cd /d "%~dp0"

echo =========================================
echo   Excel to CSV Converter
echo =========================================
echo.

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

echo Converting .xlsx files in data\input\ to .csv ...
echo.

set PYTHONPATH=src
%PY_CMD% -m excel_utils.xlsx2csv .\data\input .\data\input

echo.
echo Done.
pause
