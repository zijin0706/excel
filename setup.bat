@echo off
title Excel Utils Setup

echo =========================================
echo   Excel Utils - Setup (Windows)
echo =========================================
echo.

echo [1/3] Checking Python...
echo.

where python >nul 2>&1
if %errorlevel% equ 0 (
    set PY_CMD=python
) else (
    where python3 >nul 2>&1
    if %errorlevel% equ 0 (
        set PY_CMD=python3
    ) else (
        echo ERROR: Python not found
        echo.
        echo Please install Python first:
        echo   https://www.python.org/downloads/
        echo.
        echo IMPORTANT: Check "Add Python to PATH" during installation
        echo.
        pause
        exit /b 1
    )
)

echo Python found:
%PY_CMD% --version
echo.

echo [2/3] Upgrading pip...
%PY_CMD% -m pip install --upgrade pip --quiet
echo Done.
echo.

echo [3/3] Installing packages...
echo This may take a few minutes...
echo.
%PY_CMD% -m pip install duckdb pyyaml pandas openpyxl streamlit

if %errorlevel% equ 0 (
    echo.
    echo =========================================
    echo   Setup Complete!
    echo =========================================
    echo.
    echo Usage:
    echo   double-click run.bat     (command line)
    echo   double-click launch.bat  (web interface)
    echo.
) else (
    echo.
    echo ERROR: Installation failed
    echo Please check your internet connection
    echo.
    echo Or try running manually:
    echo   %PY_CMD% -m pip install duckdb pyyaml pandas openpyxl streamlit
    echo.
)

pause
