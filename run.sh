#!/bin/bash
# Excel Utils - Mac 一键运行脚本
# 使用方式：
#   双击运行（使用默认 config.yaml）
#   终端运行：bash run.sh config_用户匹配.yaml

cd "$(dirname "$0")"

CONFIG="${1:-config.yaml}"

if [ ! -f "$CONFIG" ]; then
    echo "❌ 配置文件不存在: $CONFIG"
    echo "   请确保配置文件在当前目录下"
    exit 1
fi

echo "正在执行匹配任务..."
echo "配置文件: $CONFIG"
echo ""

PYTHONPATH=src python3 -m excel_utils.main "$CONFIG"

echo ""
echo "执行完毕，按任意键关闭..."
read -n 1
