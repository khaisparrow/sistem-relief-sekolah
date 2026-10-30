@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0mula.ps1"
if errorlevel 1 (
  echo.
  echo App belum dapat dimulakan. Baca mesej ralat di atas dan PANDUAN.md.
  pause
)
