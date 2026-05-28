#!/bin/bash
cd "$(dirname "$0")"
PYTHONPATH=src STREAMLIT_BROWSER_GATHER_USAGE_STATS=false python3 -m streamlit run src/excel_utils/webui.py --server.port 8501 --server.headless true
