#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

say() {
  printf "\n[install] %s\n" "$1"
}

ensure_python() {
  if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
  elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
  else
    echo "Python is required but was not found. Install Python 3.9+ and run again."
    exit 1
  fi
}

ensure_pipx() {
  if command -v pipx >/dev/null 2>&1; then
    return
  fi

  say "Installing pipx"
  "$PYTHON_BIN" -m pip install --user pipx
  "$PYTHON_BIN" -m pipx ensurepath || true

  export PATH="$HOME/.local/bin:$HOME/Library/Python/3.9/bin:$HOME/Library/Python/3.10/bin:$HOME/Library/Python/3.11/bin:$HOME/Library/Python/3.12/bin:$PATH"

  if ! command -v pipx >/dev/null 2>&1; then
    echo "pipx was installed but is not on PATH yet."
    echo "Close and reopen terminal, then run this installer again."
    exit 1
  fi
}

install_fzgpt() {
  say "Installing fzgpt"
  pipx install --force "$PROJECT_DIR"

  say "Installing voice dependencies"
  pipx inject fzgpt faster-whisper numpy sounddevice || true
}

print_next_steps() {
  say "Install complete"
  cat <<STEPS
Next steps:
1) Open a new terminal window
2) Run: ollama pull qwen2.5-coder
3) Run: fzgpt doctor
4) Run: fzgpt

Optional macOS dependencies:
- brew install ollama portaudio
- brew services start ollama
STEPS
}

ensure_python
ensure_pipx
install_fzgpt
print_next_steps
