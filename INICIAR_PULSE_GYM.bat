@echo off
chcp 65001 >nul
title Pulse Gym v2 - Lanzador Completo
set "ROOT_DIR=%~dp0"
set "PGADMIN_DIR=%LOCALAPPDATA%\Programs\pgAdmin 4"

echo ============================================================================
echo   INICIANDO PULSE GYM V2 (POSTGRESQL 16 + BACKEND + FRONTEND + PGADMIN 4)
echo ============================================================================

:: 1. Iniciar PostgreSQL 16 en puerto 5432
"%ROOT_DIR%db\pgsql\bin\pg_ctl.exe" -D "%ROOT_DIR%db\pgdata" status >nul 2>&1
if errorlevel 1 (
    echo [1/4] Iniciando motor PostgreSQL 16 en localhost:5432...
    "%ROOT_DIR%db\pgsql\bin\pg_ctl.exe" -D "%ROOT_DIR%db\pgdata" -l "%ROOT_DIR%db\postgres.log" -w start
) else (
    echo [1/4] PostgreSQL 16 ya esta corriendo en localhost:5432.
)

:: 2. Iniciar Backend FastAPI (puerto 8000)
echo [2/4] Abriendo servidor Backend FastAPI (http://localhost:8000)...
start "Pulse Gym v2 - Backend API (8000)" /D "%ROOT_DIR%backend" cmd /k ".\.venv\Scripts\uvicorn.exe app.main:app --reload --port 8000"

:: 3. Iniciar Frontend Vite (puerto 5173)
echo [3/4] Abriendo servidor Frontend PWA (http://localhost:5173)...
start "Pulse Gym v2 - Frontend PWA (5173)" /D "%ROOT_DIR%frontend" cmd /k "npm run dev"

:: 4. Iniciar pgAdmin 4 en puerto 5050
echo [4/4] Iniciando pgAdmin 4 en http://127.0.0.1:5050 ...
start "Pulse Gym v2 - pgAdmin 4 (5050)" cmd /k "set PATH=%ROOT_DIR%db\pgsql\bin;%PGADMIN_DIR%\runtime;%PATH%&& set PGADMIN_SERVER_MODE=OFF&& set PGADMIN_DEFAULT_PORT=5050&& ""%PGADMIN_DIR%\python\python.exe"" -s ""%PGADMIN_DIR%\web\pgAdmin4.py"""

timeout /t 4 /nobreak >nul
start "" "http://127.0.0.1:5050"
start "" "http://localhost:5173"
start "" "http://localhost:8000/docs"
