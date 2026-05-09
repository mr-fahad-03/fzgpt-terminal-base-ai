@echo off
setlocal enabledelayedexpansion

echo [install] fzgpt installer starting...

set "PROJECT_DIR=%~dp0.."

where py >nul 2>nul
if %errorlevel%==0 (
  set "PY_CMD=py -3"
) else (
  where python >nul 2>nul
  if %errorlevel%==0 (
    set "PY_CMD=python"
  ) else (
    echo Python 3.9+ is required but was not found.
    echo Install Python and run this installer again.
    exit /b 1
  )
)

echo [install] Using Python: %PY_CMD%

where pipx >nul 2>nul
if %errorlevel% neq 0 (
  echo [install] Installing pipx...
  %PY_CMD% -m pip install --user pipx
  %PY_CMD% -m pipx ensurepath
)

set "PATH=%USERPROFILE%\\.local\\bin;%USERPROFILE%\\AppData\\Roaming\\Python\\Python39\\Scripts;%USERPROFILE%\\AppData\\Roaming\\Python\\Python310\\Scripts;%USERPROFILE%\\AppData\\Roaming\\Python\\Python311\\Scripts;%USERPROFILE%\\AppData\\Roaming\\Python\\Python312\\Scripts;%PATH%"

echo [install] Installing fzgpt...
%PY_CMD% -m pipx install --force "%PROJECT_DIR%"

echo [install] Installing voice dependencies...
%PY_CMD% -m pipx inject fzgpt faster-whisper numpy sounddevice

echo.
echo [install] Completed successfully.
echo Next steps:
echo   1) Open a new terminal window
echo   2) Run: ollama pull qwen2.5-coder
echo   3) Run: fzgpt doctor
echo   4) Run: fzgpt
echo.
pause
