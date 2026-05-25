#!/bin/bash
# Excel Utils - Mac 一键安装脚本
# 双击运行或在终端执行: bash setup.sh

echo "========================================"
echo "  Excel Utils 环境安装"
echo "========================================"
echo ""

# 检查 Python3
if ! command -v python3 &> /dev/null; then
    echo "❌ 未找到 python3，正在安装..."
    echo "   请先在 https://www.python.org/downloads/ 下载 Python"
    echo "   或通过 Homebrew 安装: brew install python@3.12"
    exit 1
fi

echo "✅ 找到 Python: $(python3 --version)"
echo ""

# 安装依赖
echo "正在安装依赖包..."
python3 -m pip install duckdb pyyaml pandas openpyxl --quiet

if [ $? -eq 0 ]; then
    echo "✅ 依赖安装完成"
else
    echo "❌ 安装失败，请检查网络连接"
    exit 1
fi

echo ""
echo "========================================"
echo "  安装成功！"
echo "========================================"
echo ""
echo "使用方法："
echo "  1. 双击 run.sh 运行"
echo "  2. 或在终端执行: bash run.sh config.yaml"
echo ""
