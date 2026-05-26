@echo off
cd /d "%~dp0"
call backend\venv\Scripts\activate.bat
python -m uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --reload
pause

