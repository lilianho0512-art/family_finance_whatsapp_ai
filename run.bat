@echo off
cd /d %~dp0
if not exist venv (
    python -m venv venv
)
call venv\Scripts\activate
pip install -r requirements.txt
python health_check.py
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
pause
