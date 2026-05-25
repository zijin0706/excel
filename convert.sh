#!/bin/bash
# Excel Utils - Mac Excel 转 CSV
cd "$(dirname "$0")"
echo "正在将 data/input/ 下的 .xlsx 文件转为 .csv ..."
echo ""
PYTHONPATH=src python3 -m excel_utils.xlsx2csv ./data/input ./data/input
echo ""
echo "转换完成，按任意键关闭..."
read -n 1
