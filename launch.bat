@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONPATH=src
set STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
python -m streamlit run src\excel_utils\webui.py --server.port 8501 --server.headless true
pause
