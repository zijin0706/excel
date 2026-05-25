@echo off
chcp 65001 >nul
cd /d "%~dp0"

set CONFIG=config.yaml
if not "%~1"=="" set CONFIG=%~1

if not exist "%CONFIG%" (
    echo ❌ 配置文件不存在: %CONFIG%
    pause
    exit /b 1
)

echo =========================================
echo   Excel Utils - 数据匹配工具
echo =========================================
echo.
echo 执行完毕会自动显示结果
echo.

set PYTHONPATH=src
python -m excel_utils.main "%CONFIG%"

echo.
echo 按任意键关闭...
pause >nul
