# fzgpt

`fzgpt` is a local AI terminal assistant powered by open-source models via Ollama.

## Features

- Interactive CLI session: `fzgpt`
- Colored terminal theme with a 3D-style startup logo
- Voice + typed workflow in one terminal session
- Safe action gate for any file mutation or shell command
- Local config at `~/.config/fzgpt/config.toml`
- Session logs and undo backups at `~/.local/share/fzgpt/`

## Quick Install (Non-Technical)

### macOS (easiest)

1. Open the `fzgpt` folder.
2. Double-click `install.command`.
3. Follow the messages in terminal.

Or run:

```bash
bash scripts/install.sh
```

### Windows (easiest)

1. Open the `fzgpt\\scripts` folder.
2. Double-click `install.bat`.

Or run PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1
```

### Linux

```bash
bash scripts/install.sh
```

## Manual Install

If you prefer manual setup:

```bash
cd fzgpt
pipx install .
```

For voice support:

```bash
pipx inject fzgpt 'faster-whisper>=1.0.3' 'numpy>=1.26.0' 'sounddevice>=0.4.6'
```

On macOS, install microphone dependency:

```bash
brew install portaudio
```

Text-to-speech works with either:

- `piper` (if installed), or
- built-in macOS `say` (fallback)

Install Ollama and pull a model (required):

```bash
ollama pull qwen2.5-coder
```

## Usage

```bash
fzgpt
fzgpt --voice
fzgpt --typed
fzgpt doctor
fzgpt config set model qwen2.5-coder
```

Inside interactive mode:

- Type your request and press Enter
- Use `/voice` to capture microphone input and transcribe with Whisper
- Use `/sh <command>` to run a shell command with approval
- Use `/quit` to exit

Any mutating action requires approval:

```text
Approve? (y/n)
```
