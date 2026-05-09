from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

try:  # Python 3.11+
    import tomllib  # type: ignore[attr-defined]
except ModuleNotFoundError:  # Python <3.11
    import tomli as tomllib  # type: ignore[no-redef]

from .paths import config_path, ensure_dirs


@dataclass
class AppConfig:
    model: str = "qwen2.5-coder"
    temperature: float = 0.2
    voice_enabled: bool = True
    default_scope: str = "system"
    confirmation_verbosity: str = "full"
    ollama_url: str = "http://127.0.0.1:11434"
    voice_record_seconds: int = 8
    whisper_model: str = "base"
    piper_voice: str = ""


DEFAULT_CONFIG = AppConfig()


def _to_toml(config: AppConfig) -> str:
    lines = [
        f'model = "{config.model}"',
        f"temperature = {config.temperature}",
        f"voice_enabled = {str(config.voice_enabled).lower()}",
        f'default_scope = "{config.default_scope}"',
        f'confirmation_verbosity = "{config.confirmation_verbosity}"',
        f'ollama_url = "{config.ollama_url}"',
        f"voice_record_seconds = {config.voice_record_seconds}",
        f'whisper_model = "{config.whisper_model}"',
        f'piper_voice = "{config.piper_voice}"',
    ]
    return "\n".join(lines) + "\n"


def load_config(path: Path | None = None) -> AppConfig:
    cfg_path = path or config_path()
    ensure_dirs()
    if not cfg_path.exists():
        save_config(DEFAULT_CONFIG, cfg_path)
        return DEFAULT_CONFIG

    with cfg_path.open("rb") as fh:
        data = tomllib.load(fh)

    merged = AppConfig(
        model=str(data.get("model", DEFAULT_CONFIG.model)),
        temperature=float(data.get("temperature", DEFAULT_CONFIG.temperature)),
        voice_enabled=bool(data.get("voice_enabled", DEFAULT_CONFIG.voice_enabled)),
        default_scope=str(data.get("default_scope", DEFAULT_CONFIG.default_scope)),
        confirmation_verbosity=str(
            data.get("confirmation_verbosity", DEFAULT_CONFIG.confirmation_verbosity)
        ),
        ollama_url=str(data.get("ollama_url", DEFAULT_CONFIG.ollama_url)),
        voice_record_seconds=int(
            data.get("voice_record_seconds", DEFAULT_CONFIG.voice_record_seconds)
        ),
        whisper_model=str(data.get("whisper_model", DEFAULT_CONFIG.whisper_model)),
        piper_voice=str(data.get("piper_voice", DEFAULT_CONFIG.piper_voice)),
    )
    return merged


def save_config(config: AppConfig, path: Path | None = None) -> None:
    cfg_path = path or config_path()
    ensure_dirs()
    cfg_path.write_text(_to_toml(config), encoding="utf-8")


def set_config_value(key: str, value: str, path: Path | None = None) -> AppConfig:
    config = load_config(path)
    if not hasattr(config, key):
        raise KeyError(f"Unknown config key: {key}")

    current = getattr(config, key)
    casted: object
    if isinstance(current, bool):
        casted = value.strip().lower() in {"1", "true", "yes", "on"}
    elif isinstance(current, int):
        casted = int(value)
    elif isinstance(current, float):
        casted = float(value)
    else:
        casted = value

    setattr(config, key, casted)
    save_config(config, path)
    return config
