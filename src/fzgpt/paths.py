from __future__ import annotations

from pathlib import Path

APP_NAME = "fzgpt"


def config_dir() -> Path:
    return Path.home() / ".config" / APP_NAME


def config_path() -> Path:
    return config_dir() / "config.toml"


def data_dir() -> Path:
    return Path.home() / ".local" / "share" / APP_NAME


def log_dir() -> Path:
    return data_dir() / "logs"


def undo_dir() -> Path:
    return data_dir() / "undo"


def ensure_dirs() -> None:
    config_dir().mkdir(parents=True, exist_ok=True)
    data_dir().mkdir(parents=True, exist_ok=True)
    log_dir().mkdir(parents=True, exist_ok=True)
    undo_dir().mkdir(parents=True, exist_ok=True)
