@echo off
chcp 65001 >nul
echo =========================================
echo   Excel Utils 环境安装 (Windows)
echo =========================================
echo.

:: 检查 Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 未找到 Python，请先安装
    echo    下载地址：https://www.python.org/downloads/
    echo    ⚠️ 安装时请勾选 "Add Python to PATH"
    pause
    exit /b 1
)

python --version
echo.

echo 正在安装依赖包...
python -m pip install duckdb pyyaml pandas openpyxl --quiet

if %errorlevel% equ 0 (
    echo ✅ 依赖安装完成
) else (
    echo ❌ 安装失败，请检查网络连接
    pause
    exit /b 1
)

echo.
echo =========================================
echo   安装成功！
echo =========================================
echo.
echo 使用方法：
echo   双击 run.bat 运行
echo   或将数据文件拖到 run.bat 上
echo.
pause
