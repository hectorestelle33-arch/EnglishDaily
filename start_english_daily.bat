@echo off
setlocal

cd /d C:\Users\10643\Documents\EnglishDaily

set "APP_URL=http://127.0.0.1:8501"
set "PORT_IN_USE="

for /f "tokens=5" %%a in ('netstat -ano ^| findstr /R /C:"127\.0\.0\.1:8501 .*LISTENING"') do (
    set "PORT_IN_USE=1"
)

if defined PORT_IN_USE (
    start "" "%APP_URL%"
    exit /b 0
)

start "" "%APP_URL%"
".venv313\Scripts\streamlit.exe" run app.py --server.port 8501 --server.address 127.0.0.1
