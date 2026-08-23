@echo off
setlocal
set "ROOT=%~dp0"
set "PID_FILE=%ROOT%data\contract-check-agent.pid"

if not exist "%PID_FILE%" (
  echo No contract-check-agent service PID was found.
  exit /b 0
)

powershell -NoProfile -Command "$serverProcessId = Get-Content -LiteralPath '%PID_FILE%'; $process = Get-Process -Id $serverProcessId -ErrorAction SilentlyContinue; if ($process) { Stop-Process -Id $serverProcessId -Force }; Remove-Item -LiteralPath '%PID_FILE%' -Force"
echo contract-check-agent stopped.
