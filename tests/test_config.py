from pathlib import Path

from fzgpt.config import AppConfig, load_config, save_config, set_config_value


def test_save_and_load_config(tmp_path: Path):
    path = tmp_path / "config.toml"
    cfg = AppConfig(model="abc", temperature=0.5, voice_enabled=False)
    save_config(cfg, path)

    loaded = load_config(path)
    assert loaded.model == "abc"
    assert loaded.temperature == 0.5
    assert loaded.voice_enabled is False


def test_set_config_value(tmp_path: Path):
    path = tmp_path / "config.toml"
    save_config(AppConfig(), path)
    updated = set_config_value("temperature", "0.7", path)
    assert updated.temperature == 0.7
