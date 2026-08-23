@echo off
setlocal
set "ROOT=%~dp0"
set "PYTHON=%ROOT%.venv\Scripts\python.exe"
set "PID_FILE=%ROOT%data\contract-check-agent.pid"

if not exist "%PYTHON%" (
  echo Python virtual environment was not found. Run the installation command in README.md once.
  exit /b 1
)

powershell -NoProfile -Command "try { Invoke-WebRequest -UseBasicParsing -TimeoutSec 1 'http://127.0.0.1:22215/' ^| Out-Null; exit 0 } catch { exit 1 }"
if not errorlevel 1 goto open_browser

powershell -NoProfile -Command "$root = '%ROOT%'; $process = Start-Process -FilePath ($root + '.venv\Scripts\python.exe') -ArgumentList '-m','uvicorn','app.main:app','--host','127.0.0.1','--port','22215' -WorkingDirectory $root -WindowStyle Hidden -PassThru; Set-Content -LiteralPath ($root + 'data\contract-check-agent.pid') -Value $process.Id"
timeout /t 2 /nobreak >nul

:open_browser
start "" "http://127.0.0.1:22215/"
