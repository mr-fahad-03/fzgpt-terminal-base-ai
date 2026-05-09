$ErrorActionPreference = "Stop"

$modelName = "qwen2.5-coder"
$projectDir = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

Write-Host "[install] fzgpt installer starting..."

if (Get-Command py -ErrorAction SilentlyContinue) {
  $python = "py"
  $pythonArgs = "-3"
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
  $python = "python"
  $pythonArgs = ""
} else {
  Write-Host "Python 3.9+ is required but was not found."
  exit 1
}

function Run-PythonModule([string]$moduleArgs) {
  if ($pythonArgs) {
    & $python $pythonArgs -m $moduleArgs
  } else {
    & $python -m $moduleArgs
  }
}

function Ensure-Pipx {
  if (-not (Get-Command pipx -ErrorAction SilentlyContinue)) {
    Write-Host "[install] Installing pipx..."
    Run-PythonModule "pip install --user pipx"
    Run-PythonModule "pipx ensurepath"
  }

  $env:PATH = "$HOME\\.local\\bin;$HOME\\AppData\\Roaming\\Python\\Python39\\Scripts;$HOME\\AppData\\Roaming\\Python\\Python310\\Scripts;$HOME\\AppData\\Roaming\\Python\\Python311\\Scripts;$HOME\\AppData\\Roaming\\Python\\Python312\\Scripts;" + $env:PATH
}

function Ensure-Ollama {
  if (Get-Command ollama -ErrorAction SilentlyContinue) {
    Write-Host "[install] Ollama already installed."
    return
  }

  if (Get-Command winget -ErrorAction SilentlyContinue) {
    Write-Host "[install] Installing Ollama with winget..."
    winget install -e --id Ollama.Ollama --accept-package-agreements --accept-source-agreements
    if (Get-Command ollama -ErrorAction SilentlyContinue) {
      return
    }
  }

  throw "Ollama installation failed. Install manually from https://ollama.com/download/windows"
}

function Start-Ollama {
  Write-Host "[install] Starting Ollama service..."
  Start-Process -FilePath "cmd.exe" -ArgumentList "/c","ollama serve" -WindowStyle Hidden
}

function Wait-OllamaApi {
  Write-Host "[install] Waiting for Ollama API on http://127.0.0.1:11434 ..."
  for ($i = 0; $i -lt 25; $i++) {
    try {
      Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -Method Get -TimeoutSec 2 | Out-Null
      Write-Host "[install] Ollama API is ready."
      return
    } catch {
      Start-Sleep -Seconds 2
    }
  }
  throw "Ollama API did not start in time. Try running: ollama serve"
}

function Pull-Model {
  Write-Host "[install] Pulling model $modelName (this can take time)..."
  ollama pull $modelName
}

Ensure-Pipx

Write-Host "[install] Installing fzgpt..."
Run-PythonModule "pipx install --force `"$projectDir`""

Write-Host "[install] Installing voice dependencies..."
Run-PythonModule "pipx inject fzgpt faster-whisper numpy sounddevice"

Ensure-Ollama
Start-Ollama
Wait-OllamaApi
Pull-Model

Write-Host ""
Write-Host "[install] Completed successfully."
Write-Host "Next steps:"
Write-Host "  1) Open a new terminal window"
Write-Host "  2) Run: fzgpt doctor"
Write-Host "  3) Run: fzgpt"
Write-Host ""
Write-Host "If SmartScreen blocked this script, run in PowerShell:"
Write-Host "  Unblock-File .\scripts\install.ps1"
Write-Host "  powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1"
