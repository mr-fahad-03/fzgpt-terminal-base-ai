$ErrorActionPreference = "Stop"

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

if (-not (Get-Command pipx -ErrorAction SilentlyContinue)) {
  Write-Host "[install] Installing pipx..."
  Run-PythonModule "pip install --user pipx"
  Run-PythonModule "pipx ensurepath"
}

$env:PATH = "$HOME\\.local\\bin;$HOME\\AppData\\Roaming\\Python\\Python39\\Scripts;$HOME\\AppData\\Roaming\\Python\\Python310\\Scripts;$HOME\\AppData\\Roaming\\Python\\Python311\\Scripts;$HOME\\AppData\\Roaming\\Python\\Python312\\Scripts;" + $env:PATH

Write-Host "[install] Installing fzgpt..."
Run-PythonModule "pipx install --force `"$projectDir`""

Write-Host "[install] Installing voice dependencies..."
Run-PythonModule "pipx inject fzgpt faster-whisper numpy sounddevice"

Write-Host ""
Write-Host "[install] Completed successfully."
Write-Host "Next steps:"
Write-Host "  1) Open a new terminal window"
Write-Host "  2) Run: ollama pull qwen2.5-coder"
Write-Host "  3) Run: fzgpt doctor"
Write-Host "  4) Run: fzgpt"
