@echo off
cd /d "%~dp0"
set CONCURSO_FINDER_BACKEND_URL=http://127.0.0.1:8010
.venv\Scripts\python.exe -m app.main
