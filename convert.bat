@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo =========================================
echo   Excel 转 CSV 工具
echo =========================================
echo.
echo 正在将 data\input\ 下的 .xlsx 文件转为 .csv ...
echo.

set PYTHONPATH=src
python -m excel_utils.xlsx2csv .\data\input .\data\input

echo.
echo 转换完成，按任意键关闭...
pause >nul
