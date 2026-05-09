from pathlib import Path

import pytest

from fzgpt.tools import ApprovalRejected, ToolExecutor, format_tool_result
from fzgpt.types import ToolCall


def test_write_file_requires_approval(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    executor = ToolExecutor()
    target = tmp_path / "a.txt"
    call = ToolCall(
        tool_name="write_file",
        arguments={"path": str(target), "content": "hello"},
        requires_approval=True,
    )

    monkeypatch.setattr("builtins.input", lambda _: "n")
    with pytest.raises(ApprovalRejected):
        executor.execute(call)


def test_write_file_and_read(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    executor = ToolExecutor()
    target = tmp_path / "a.txt"

    monkeypatch.setattr("builtins.input", lambda _: "y")
    write_call = ToolCall(
        tool_name="write_file",
        arguments={"path": str(target), "content": "hello"},
        requires_approval=True,
    )
    write_result = executor.execute(write_call)
    assert write_result["ok"] is True

    read_call = ToolCall(
        tool_name="read_file",
        arguments={"path": str(target)},
        requires_approval=False,
    )
    read_result = executor.execute(read_call)
    assert read_result["content"] == "hello"


def test_run_shell_non_mutating(monkeypatch: pytest.MonkeyPatch):
    executor = ToolExecutor()
    monkeypatch.setattr("builtins.input", lambda _: "y")
    call = ToolCall(
        tool_name="run_shell",
        arguments={"command": "echo hi"},
        requires_approval=True,
    )
    result = executor.execute(call)
    assert result["ok"] is True
    assert "hi" in result["stdout"]


def test_read_file_on_directory_returns_listing(tmp_path: Path):
    executor = ToolExecutor()
    folder = tmp_path / "repo"
    folder.mkdir()
    (folder / "a.py").write_text("print('x')", encoding="utf-8")

    call = ToolCall(
        tool_name="read_file",
        arguments={"path": str(folder)},
        requires_approval=False,
    )
    result = executor.execute(call)
    assert result["ok"] is True
    assert result["tool"] == "list_dir"
    assert any(entry["name"] == "a.py" for entry in result["entries"])


def test_fuzzy_path_resolution_handles_trailing_spaces(tmp_path: Path):
    executor = ToolExecutor()
    base = tmp_path / "Own Ai "
    base.mkdir()
    project = base / "fzgpt"
    project.mkdir()
    target = project / "file.txt"
    target.write_text("ok", encoding="utf-8")

    wrong = str(tmp_path / "Own Ai" / "fzgpt" / "file.txt")
    call = ToolCall(
        tool_name="read_file",
        arguments={"path": wrong},
        requires_approval=False,
    )
    result = executor.execute(call)
    assert result["ok"] is True
    assert result["content"] == "ok"


def test_placeholder_username_path_maps_to_home_downloads(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    executor = ToolExecutor()
    fake_home = tmp_path / "homeuser"
    downloads = fake_home / "Downloads"
    downloads.mkdir(parents=True)
    (downloads / "a.txt").write_text("hello", encoding="utf-8")

    monkeypatch.setattr("fzgpt.tools.Path.home", lambda: fake_home)

    call = ToolCall(
        tool_name="list_dir",
        arguments={"path": "/Users/your_username/Downloads"},
        requires_approval=False,
    )
    result = executor.execute(call)
    assert result["ok"] is True
    assert any(entry["name"] == "a.txt" for entry in result["entries"])


def test_format_web_search_result():
    payload = {
        "ok": True,
        "tool": "web_search",
        "query": "today weather karachi",
        "results": [
            {
                "title": "Karachi Weather",
                "url": "https://example.com/weather",
                "snippet": "Sunny and warm.",
            }
        ],
    }
    text = format_tool_result(payload)
    assert "Web results for: today weather karachi" in text
    assert "Karachi Weather" in text


def test_format_weather_result():
    payload = {
        "ok": True,
        "tool": "get_weather",
        "location": "Karachi",
        "current": {"condition": "Sunny", "temp_c": "34", "feels_like_c": "36"},
        "today": {"min_c": "28", "max_c": "38"},
    }
    text = format_tool_result(payload)
    assert "Weather for Karachi" in text
    assert "Sunny" in text
