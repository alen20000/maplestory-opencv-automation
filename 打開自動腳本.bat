@echo off
:: 檢查並自動要求系統管理員權限
fltmc >nul 2>&1 || (
    echo 正在請求系統管理員權限...
    powershell -Command "Start-Process '%~dpnx0' -Verb RunAs"
    exit /b
)

:: 切換到腳本所在目錄並執行
cd /d "%~dp0"
python auto_suup.py
pause