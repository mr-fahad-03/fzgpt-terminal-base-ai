from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import requests

from .config import AppConfig
from .types import AgentResponse, ToolCall

SYSTEM_POLICY = """You are fzgpt, a local coding assistant.
Return valid JSON only with this schema:
{
  \"assistant_message\": string,
  \"tool_calls\": [
    {
      \"tool_name\": string,
      \"arguments\": object,
      \"requires_approval\": boolean,
      \"risk_level\": \"low\"|\"medium\"|\"high\",
      \"dry_run_preview\": string
    }
  ]
}
Rules:
- You are running on the user's local machine and you DO have filesystem access via tools.
- Never claim you cannot access files, code, or folders.
- You also have internet access via tools (`web_search` and `get_weather`).
- For weather/news/web lookups, use tools instead of refusing.
- If user asks about project/repo/codebase contents, inspect with tools before answering.
- Never use placeholder paths like /Users/your_username.
- Ask-before-action for mutations and shell commands.
- Never hide tool usage.
- Keep assistant_message concise and clear.
Available tools:
- read_file(path)
- write_file(path, content)
- append_file(path, content)
- search_text(path, pattern)
- list_dir(path)
- run_shell(command, cwd?)
- web_search(query, max_results?)
- get_weather(location)
"""


class OllamaClient:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def _extract_json(self, text: str) -> dict[str, Any]:
        text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1 and end > start:
                return json.loads(text[start : end + 1])
            raise

    def ask(self, messages: list[dict[str, str]]) -> AgentResponse:
        runtime_context = (
            "Runtime facts:\n"
            f"- Current working directory: {Path.cwd()}\n"
            f"- Home directory: {Path.home()}\n"
            "- Use real absolute paths from these facts, not placeholders.\n"
        )
        payload = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": SYSTEM_POLICY},
                {"role": "system", "content": runtime_context},
            ]
            + messages,
            "stream": False,
            "format": "json",
            "options": {"temperature": self.config.temperature},
        }
        try:
            response = requests.post(
                f"{self.config.ollama_url}/api/chat", json=payload, timeout=120
            )
        except requests.exceptions.ConnectionError as exc:
            raise RuntimeError(
                "Cannot connect to Ollama at http://127.0.0.1:11434. "
                "Start it with `ollama serve` (or run `fzgpt doctor`). "
                f"Then pull model: `ollama pull {self.config.model}`"
            ) from exc
        if response.status_code == 404:
            detail = ""
            try:
                detail = str(response.json().get("error", "")).strip()
            except Exception:  # noqa: BLE001
                detail = response.text.strip()

            if detail:
                raise RuntimeError(
                    "Ollama returned 404. "
                    f"{detail} "
                    f"Run in terminal (outside fzgpt): `ollama pull {self.config.model}`"
                )
            raise RuntimeError(
                "Ollama returned 404. Run in terminal (outside fzgpt): "
                f"`ollama pull {self.config.model}`"
            )

        response.raise_for_status()
        data = response.json()

        content = data.get("message", {}).get("content", "")
        parsed = self._extract_json(content)

        tool_calls: list[ToolCall] = []
        for raw in parsed.get("tool_calls", []):
            if not isinstance(raw, dict):
                continue
            tool_calls.append(
                ToolCall(
                    tool_name=str(raw.get("tool_name", "")),
                    arguments=dict(raw.get("arguments", {})),
                    requires_approval=bool(raw.get("requires_approval", True)),
                    risk_level=str(raw.get("risk_level", "medium")),
                    dry_run_preview=str(raw.get("dry_run_preview", "")),
                )
            )

        return AgentResponse(
            assistant_message=str(parsed.get("assistant_message", "")),
            tool_calls=tool_calls,
        )
