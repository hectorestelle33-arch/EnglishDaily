@echo off
setlocal

cd /d C:\Users\10643\Documents\EnglishDaily

start "" "http://127.0.0.1:8501"
".venv313\Scripts\streamlit.exe" run app.py --server.port 8501 --server.address 127.0.0.1

pause
