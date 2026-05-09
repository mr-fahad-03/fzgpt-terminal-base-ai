from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
import re
from typing import Literal

from .config import AppConfig
from .model import OllamaClient
from .paths import ensure_dirs, log_dir
from .tools import (
    ApprovalRejected,
    ToolExecutor,
    format_tool_result,
    serialize_tool_result_for_model,
)
from .types import ToolCall
from .ui import TerminalUI
from .voice import VoiceEngine

InputMode = Literal["typed", "voice", "mixed"]


class InteractiveSession:
    def __init__(self, config: AppConfig, mode: InputMode) -> None:
        self.config = config
        self.mode = mode
        self.client = OllamaClient(config)
        self.tools = ToolExecutor(confirmation_verbosity=config.confirmation_verbosity)
        self.voice = VoiceEngine(config)
        self.ui = TerminalUI()
        self.history: list[dict[str, str]] = []

    def _is_repo_access_request(self, text: str) -> bool:
        lowered = text.lower()
        patterns = [
            r"\bread\b.*\b(code|project|repo|repository|folder|files?)\b",
            r"\bscan\b.*\b(code|project|repo|folder|files?)\b",
            r"\bwhole\b.*\b(code|project|repo)\b",
            r"\bcodebase\b",
            r"\brepository\b",
            r"\bthis folder\b",
        ]
        return any(re.search(pattern, lowered) for pattern in patterns)

    def _workspace_snapshot(self) -> str:
        root = Path.cwd()
        skip_dirs = {
            ".git",
            "__pycache__",
            ".pytest_cache",
            ".venv",
            "venv",
            "node_modules",
            "dist",
            "build",
        }
        preferred = [
            "pyproject.toml",
            "package.json",
            "README.md",
            "setup.py",
            "requirements.txt",
        ]

        files: list[Path] = []
        for path in root.rglob("*"):
            if path.is_dir():
                continue
            rel_parts = path.relative_to(root).parts
            if any(part in skip_dirs for part in rel_parts):
                continue
            files.append(path)
            if len(files) >= 240:
                break

        rel_paths = sorted(str(p.relative_to(root)) for p in files)
        summary_lines = [
            f"Workspace root: {root}",
            f"Visible files (sampled, {len(rel_paths)}):",
        ]
        for rel in rel_paths[:180]:
            summary_lines.append(f"- {rel}")

        preview_chunks: list[str] = []
        for name in preferred:
            target = root / name
            if not target.exists() or not target.is_file():
                continue
            try:
                content = target.read_text(encoding="utf-8")
            except Exception:  # noqa: BLE001
                continue
            excerpt = "\n".join(content.splitlines()[:80])
            preview_chunks.append(f"\n[{name}]\n{excerpt}")

        snapshot = "\n".join(summary_lines)
        if preview_chunks:
            snapshot += "\n\nKey file previews:" + "".join(preview_chunks)
        return snapshot[:14000]

    def _log_path(self) -> Path:
        ensure_dirs()
        stamp = dt.datetime.now().strftime("session-%Y%m%d-%H%M%S.jsonl")
        return log_dir() / stamp

    def _record(self, path: Path, role: str, content: str) -> None:
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"role": role, "content": content}) + "\n")

    def _get_user_input(self) -> str:
        if self.mode == "voice":
            return self.voice.capture_and_transcribe()
        typed = input(self.ui.prompt()).strip()
        if typed == "/voice":
            return self.voice.capture_and_transcribe()
        return typed

    def run(self) -> None:
        self.ui.print_banner()
        self.ui.startup_help()
        session_log = self._log_path()

        while True:
            try:
                user_text = self._get_user_input()
            except KeyboardInterrupt:
                print()
                self.ui.warn("Exiting.")
                break

            if not user_text:
                continue
            if user_text.lower() in {"/quit", "/exit"}:
                self.ui.success("Goodbye.")
                break
            if user_text.startswith("/sh "):
                command = user_text[4:].strip()
                if not command:
                    self.ui.warn("Usage: /sh <command>")
                    continue
                call = ToolCall(
                    tool_name="run_shell",
                    arguments={"command": command},
                    requires_approval=True,
                    risk_level="medium",
                    dry_run_preview=command,
                )
                try:
                    result = self.tools.execute(call)
                    display_payload = format_tool_result(result)
                    model_payload = serialize_tool_result_for_model(result)
                    self.ui.tool("run_shell", display_payload)
                    print()
                    self._record(session_log, "tool", model_payload)
                except ApprovalRejected as exc:
                    msg = f"Skipped run_shell: {exc}"
                    self.ui.warn(msg)
                    self._record(session_log, "tool", msg)
                except Exception as exc:  # noqa: BLE001
                    msg = f"Shell tool error: {exc}"
                    self.ui.error(msg)
                    self._record(session_log, "tool", msg)
                continue

            stripped = user_text.strip()
            shell_like_prefixes = (
                "ollama ",
                "brew ",
                "pip ",
                "python ",
                "git ",
                "ls",
                "cd ",
                "cat ",
                "rm ",
                "mv ",
                "cp ",
            )
            if stripped.startswith(shell_like_prefixes):
                self.ui.warn(
                    "This looks like a shell command. "
                    "Run it in terminal, or use: /sh " + stripped
                )
                continue

            effective_user_text = user_text
            repo_context_loaded = False
            if self._is_repo_access_request(user_text):
                snapshot = self._workspace_snapshot()
                effective_user_text = (
                    f"{user_text}\n\n"
                    "LOCAL_CONTEXT: You are inside the user's workspace and have direct "
                    "filesystem access via tools. Never say you cannot access files.\n"
                    "The user is explicitly asking you to inspect now. "
                    "Do not ask 'would you like me to read'; do the read/scan immediately.\n"
                    "If deeper inspection is needed, emit tool_calls.\n\n"
                    f"{snapshot}"
                )
                repo_context_loaded = True
                self.ui.info("Workspace context loaded from current folder.")

            self.history.append({"role": "user", "content": effective_user_text})
            self._record(session_log, "user", user_text)

            try:
                response = self.client.ask(self.history)
            except Exception as exc:  # noqa: BLE001
                self.ui.error(f"Model error: {exc}")
                continue

            if response.assistant_message:
                if (
                    repo_context_loaded
                    and (
                        "can't read" in response.assistant_message.lower()
                        or "cannot access" in response.assistant_message.lower()
                    )
                ):
                    response.assistant_message = (
                        "Yes, I can access this folder. "
                        "Ask me what to inspect (for example: 'scan this codebase and summarize')."
                    )
                print()
                self.ui.ai(response.assistant_message)
                print()
                self._record(session_log, "assistant", response.assistant_message)
                if self.config.voice_enabled:
                    self.voice.speak(response.assistant_message)

            tool_outputs: list[str] = []
            for call in response.tool_calls:
                try:
                    result = self.tools.execute(call)
                    display_payload = format_tool_result(result)
                    model_payload = serialize_tool_result_for_model(result)
                    tool_outputs.append(model_payload)
                    self.ui.tool(call.tool_name, display_payload)
                    print()
                    self._record(session_log, "tool", model_payload)
                except ApprovalRejected as exc:
                    msg = f"Skipped {call.tool_name}: {exc}"
                    self.ui.warn(msg)
                    tool_outputs.append(msg)
                    self._record(session_log, "tool", msg)
                except Exception as exc:  # noqa: BLE001
                    msg = f"Tool error for {call.tool_name}: {exc}"
                    self.ui.error(msg)
                    tool_outputs.append(msg)
                    self._record(session_log, "tool", msg)

            if tool_outputs:
                self.history.append(
                    {
                        "role": "assistant",
                        "content": response.assistant_message
                        + "\nTOOL_OUTPUTS:\n"
                        + "\n".join(tool_outputs),
                    }
                )
                try:
                    final = self.client.ask(self.history)
                    if final.assistant_message:
                        self.ui.ai(final.assistant_message)
                        print()
                        self._record(session_log, "assistant", final.assistant_message)
                        if self.config.voice_enabled:
                            self.voice.speak(final.assistant_message)
                    self.history.append(
                        {"role": "assistant", "content": final.assistant_message}
                    )
                except Exception as exc:  # noqa: BLE001
                    self.ui.error(f"Follow-up model error: {exc}")
            else:
                self.history.append(
                    {"role": "assistant", "content": response.assistant_message}
                )
