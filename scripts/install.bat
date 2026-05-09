@echo off
setlocal enabledelayedexpansion

set "MODEL_NAME=qwen2.5-coder"
set "PROJECT_DIR=%~dp0.."

echo [install] fzgpt installer starting...

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

call :ensure_ollama
if errorlevel 1 goto :install_done

call :start_ollama
call :wait_ollama
if errorlevel 1 goto :install_done

call :pull_model

:install_done
echo.
echo [install] Completed.
echo Next steps:
echo   1) Open a new terminal window
echo   2) Run: fzgpt doctor
echo   3) Run: fzgpt
echo.
echo If SmartScreen blocked script execution earlier, click "More info" then "Run anyway".
echo.
pause
exit /b 0

:ensure_ollama
where ollama >nul 2>nul
if %errorlevel%==0 (
  echo [install] Ollama is already installed.
  exit /b 0
)

echo [install] Ollama not found. Trying winget install...
where winget >nul 2>nul
if %errorlevel%==0 (
  winget install -e --id Ollama.Ollama --accept-package-agreements --accept-source-agreements
  where ollama >nul 2>nul
  if %errorlevel%==0 exit /b 0
)

echo [install] winget installation did not complete.
echo Please install Ollama manually from https://ollama.com/download/windows
exit /b 1

:start_ollama
echo [install] Starting Ollama service...
start "ollama" /B cmd /c "ollama serve"
exit /b 0

:wait_ollama
echo [install] Waiting for Ollama API on http://127.0.0.1:11434 ...
for /L %%i in (1,1,20) do (
  powershell -NoProfile -Command "try { Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/tags' -Method Get -TimeoutSec 2 | Out-Null; exit 0 } catch { exit 1 }"
  if !errorlevel! EQU 0 (
    echo [install] Ollama API is ready.
    exit /b 0
  )
  timeout /t 2 >nul
)

echo [install] Ollama API did not start in time.
echo Try running this manually: ollama serve
exit /b 1

:pull_model
echo [install] Pulling model %MODEL_NAME% (this can take time)...
ollama pull %MODEL_NAME%
if %errorlevel% neq 0 (
  echo [install] Model pull failed. You can retry later with:
  echo   ollama pull %MODEL_NAME%
  exit /b 1
)
echo [install] Model %MODEL_NAME% is ready.
exit /b 0
