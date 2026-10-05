@echo off
setlocal EnableDelayedExpansion
title Quantum Kavach Launcher
color 0A

REM =====================================================================
REM  Quantum Kavach - One-Click Launcher (SIH26141)
REM  Starts FastAPI backend + Next.js frontend, then opens browser.
REM =====================================================================

set "ROOT=%~dp0"
cd /d "%ROOT%"

set "BACKEND_PORT=8000"
set "FRONTEND_PORT=3000"
set "BACKEND_URL=http://localhost:%BACKEND_PORT%"
set "FRONTEND_URL=http://localhost:%FRONTEND_PORT%"
set "PY=%ROOT%backend\venv\Scripts\python.exe"

cls
echo.
echo  ============================================================
echo    ___  _   _    _    _   _ _____ _   _ __  __
echo   / _ \^| ^| ^| ^|  / \  ^| \ ^| ^|_   _^| ^| ^| ^|  \/  ^|
echo  ^| ^| ^| ^| ^| ^| ^| / _ \ ^|  \^| ^| ^| ^| ^| ^| ^| ^| ^|\/^| ^|
echo  ^| ^|_^| ^| ^|_^| ^|/ ___ \^| ^|\  ^| ^| ^| ^| ^|_^| ^| ^|  ^| ^|
echo   \__\_\\___//_/   \_\_^| \_^| ^|_^|  \___/^|_^|  ^|_^|
echo.
echo     _  __    ___     __  _    ____ _   _
echo    ^| ^|/ /   / \ \   / / / \  / ___^| ^| ^| ^|
echo    ^| ' /   / _ \ \ / / / _ \^| ^|   ^| ^|_^| ^|
echo    ^| . \  / ___ \ V / / ___ \ ^|___^|  _  ^|
echo    ^|_^|\_\/_/   \_\_/ /_/   \_\____^|_^| ^|_^|
echo.
echo    Quantum Threat Detection Dashboard  -  SIH26141
echo  ============================================================
echo.

REM ---------- 1. Check prerequisites ----------
echo  [1/6] Checking prerequisites...

where python >nul 2>&1
if errorlevel 1 (
  echo  [ERROR] Python not found. Install Python 3.10+ and add to PATH.
  pause & exit /b 1
)

where node >nul 2>&1
if errorlevel 1 (
  echo  [ERROR] Node.js not found. Install Node.js 18+ and add to PATH.
  pause & exit /b 1
)

if not exist "%ROOT%backend\main.py" (
  echo  [ERROR] backend\main.py not found.
  pause & exit /b 1
)
if not exist "%ROOT%frontend\package.json" (
  echo  [ERROR] frontend\package.json not found.
  pause & exit /b 1
)
echo  [OK] Python and Node.js found.

REM ---------- 2. Kill stale processes on our ports ----------
echo  [2/6] Clearing ports %BACKEND_PORT% and %FRONTEND_PORT%...

for /f "tokens=5" %%P in ('netstat -ano ^| findstr ":%BACKEND_PORT% " ^| findstr LISTENING 2^>nul') do (
  taskkill /F /PID %%P >nul 2>&1
)
for /f "tokens=5" %%P in ('netstat -ano ^| findstr ":%FRONTEND_PORT% " ^| findstr LISTENING 2^>nul') do (
  taskkill /F /PID %%P >nul 2>&1
)
timeout /t 1 /nobreak >nul
echo  [OK] Ports cleared.

REM ---------- 3. Setup Python venv + deps ----------
echo  [3/6] Setting up backend...

if not exist "%PY%" (
  echo        Creating Python virtual environment...
  pushd "%ROOT%backend"
  python -m venv venv
  popd
)
if not exist "%PY%" (
  echo  [ERROR] Failed to create venv.
  pause & exit /b 1
)

"%PY%" -m pip install --disable-pip-version-check -q -r "%ROOT%backend\requirements.txt" >nul 2>&1
if errorlevel 1 (
  echo  [WARN] Some pip packages may have failed. Trying to continue...
)
echo  [OK] Backend ready.

REM ---------- 4. Setup frontend deps ----------
echo  [4/6] Setting up frontend...

if not exist "%ROOT%frontend\node_modules\" (
  echo        Installing npm packages [first run, may take a minute]
  pushd "%ROOT%frontend"
  call npm install --loglevel=error
  popd
)
echo  [OK] Frontend ready.

REM ---------- 5. Launch both services ----------
echo  [5/6] Starting services...

start "Quantum Kavach Backend" /min cmd /c "cd /d "%ROOT%backend" && "%PY%" -u main.py"
echo        Backend starting on %BACKEND_URL%

start "Quantum Kavach Frontend" /min cmd /c "cd /d "%ROOT%frontend" && npm run dev"
echo        Frontend starting on %FRONTEND_URL%

REM ---------- 6. Wait for backend health, then open browser ----------
echo  [6/6] Waiting for backend to come online...

set "HEALTHY="
for /l %%i in (1,1,30) do (
  if not defined HEALTHY (
    curl -s -o nul "%BACKEND_URL%/health" >nul 2>&1
    if not errorlevel 1 (
      set "HEALTHY=1"
    ) else (
      timeout /t 1 /nobreak >nul
    )
  )
)

if defined HEALTHY (
  echo  [OK] Backend is healthy.
) else (
  echo  [WARN] Backend not responding yet. It may still be loading.
)

echo.
echo  Opening browser in 5 seconds...
timeout /t 5 /nobreak >nul
start "" "%FRONTEND_URL%"

echo.
echo  ============================================================
echo    Quantum Kavach is running!
echo.
echo    Frontend : %FRONTEND_URL%
echo    Backend  : %BACKEND_URL%
echo    API Docs : %BACKEND_URL%/docs
echo.
echo    Close the minimized service windows to stop.
echo  ============================================================
echo.
pause
endlocal
