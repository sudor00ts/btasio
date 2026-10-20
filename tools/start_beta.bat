@echo off
cd /d "%~dp0"
echo btasio beta hub
echo.
python beta_hub.py
if errorlevel 1 (
  echo.
  echo Error. Asegurate de tener Python instalado.
  echo Descargalo de https://www.python.org/downloads/
  pause
)
pause
