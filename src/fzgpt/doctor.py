from __future__ import annotations

import shutil
import sys

import requests

from .config import AppConfig
from .voice import check_voice_stack


def _print_check(name: str, ok: bool, detail: str = "") -> None:
    status = "PASS" if ok else "WARN"
    print(f"[{status}] {name}: {detail}")


def run_doctor(config: AppConfig) -> int:
    print("fzgpt doctor report")
    print("-" * 40)

    py_ok = sys.version_info >= (3, 9)
    _print_check("Python", py_ok, sys.version.split()[0])

    ollama_bin = shutil.which("ollama")
    _print_check("Ollama binary", bool(ollama_bin), ollama_bin or "not found")

    api_ok = False
    model_ok = False
    api_detail = "unreachable"
    try:
        resp = requests.get(f"{config.ollama_url}/api/tags", timeout=5)
        if resp.ok:
            api_ok = True
            api_detail = "reachable"
            names = [m.get("name", "") for m in resp.json().get("models", [])]
            model_ok = any(name.startswith(config.model) for name in names)
    except Exception as exc:  # noqa: BLE001
        api_detail = str(exc)

    _print_check("Ollama API", api_ok, api_detail)
    _print_check("Model pulled", model_ok, config.model)

    voice = check_voice_stack(config)
    _print_check("Whisper dependency", voice.stt_ready, "faster-whisper")
    _print_check("Microphone", voice.microphone_ready, "input device check")
    _print_check("TTS output", voice.tts_ready, "piper or macOS say")

    overall = py_ok and bool(ollama_bin) and api_ok
    print("-" * 40)
    print("Ready" if overall else "Needs setup")
    return 0 if overall else 1
