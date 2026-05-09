from __future__ import annotations

import datetime as dt
import difflib
import html
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
from typing import Any
from urllib.parse import parse_qs, quote_plus, unquote, urlparse

import requests

from .paths import ensure_dirs, undo_dir
from .types import ToolCall


class ApprovalRejected(Exception):
    pass


DESTRUCTIVE_PATTERNS = [
    r"\brm\s+-rf\b",
    r"\bmkfs\b",
    r"\bdd\s+if=",
    r"\bshutdown\b",
    r"\breboot\b",
    r"\bchmod\s+-R\s+777\b",
]


class ToolExecutor:
    def __init__(self, confirmation_verbosity: str = "full") -> None:
        self.confirmation_verbosity = confirmation_verbosity

    def _is_destructive(self, command: str) -> bool:
        lowered = command.lower()
        return any(re.search(pattern, lowered) for pattern in DESTRUCTIVE_PATTERNS)

    def _normalized_name(self, value: str) -> str:
        return " ".join(value.strip().split()).lower()

    def _expand_user_placeholders(self, raw_path: str) -> str:
        home = str(Path.home())
        value = str(raw_path).strip()
        replacements = [
            "/Users/your_username",
            "/Users/username",
            "/home/your_username",
            "/home/username",
        ]
        for needle in replacements:
            if value.startswith(needle):
                return value.replace(needle, home, 1)
        return value

    def _fallback_common_dirs(self, path: Path) -> Path:
        # Common model mistakes: "Download" vs "Downloads", desktop casing, etc.
        name = path.name.lower()
        parent = path.parent
        if not parent.exists():
            return path
        if name == "download":
            alt = parent / "Downloads"
            if alt.exists():
                return alt
        if name == "desktop":
            alt = parent / "Desktop"
            if alt.exists():
                return alt
        if name == "documents":
            alt = parent / "Documents"
            if alt.exists():
                return alt
        return path

    def _clean_html_text(self, value: str) -> str:
        no_tags = re.sub(r"<[^>]+>", "", value or "")
        return html.unescape(" ".join(no_tags.split()))

    def _extract_ddg_redirect(self, href: str) -> str:
        parsed = urlparse(href)
        if parsed.netloc.endswith("duckduckgo.com") and parsed.path.startswith("/l/"):
            qs = parse_qs(parsed.query)
            uddg = qs.get("uddg", [])
            if uddg:
                return unquote(uddg[0])
        return href

    def _web_search(self, query: str, max_results: int = 5) -> dict[str, Any]:
        url = "https://html.duckduckgo.com/html/"
        headers = {"User-Agent": "Mozilla/5.0 fzgpt/0.1"}
        response = requests.get(
            url, params={"q": query}, headers=headers, timeout=20
        )
        response.raise_for_status()
        body = response.text

        link_matches = re.findall(
            r'<a[^>]*class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
            body,
            flags=re.IGNORECASE | re.DOTALL,
        )
        snippet_matches = re.findall(
            r'<a[^>]*class="result__snippet"[^>]*>(.*?)</a>',
            body,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if not snippet_matches:
            snippet_matches = re.findall(
                r'<div[^>]*class="result__snippet"[^>]*>(.*?)</div>',
                body,
                flags=re.IGNORECASE | re.DOTALL,
            )

        results: list[dict[str, str]] = []
        for idx, (href, title_html) in enumerate(link_matches[: max(1, max_results)]):
            title = self._clean_html_text(title_html)
            snippet = ""
            if idx < len(snippet_matches):
                snippet = self._clean_html_text(snippet_matches[idx])
            results.append(
                {
                    "title": title,
                    "url": self._extract_ddg_redirect(href),
                    "snippet": snippet,
                }
            )

        return {"ok": True, "tool": "web_search", "query": query, "results": results}

    def _get_weather(self, location: str) -> dict[str, Any]:
        loc = quote_plus(location.strip() or "auto")
        url = f"https://wttr.in/{loc}?format=j1"
        headers = {"User-Agent": "curl/8.0 fzgpt"}
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        data = response.json()
        current = (data.get("current_condition") or [{}])[0]
        today = (data.get("weather") or [{}])[0]
        desc = ""
        weather_desc = current.get("weatherDesc") or []
        if weather_desc and isinstance(weather_desc, list):
            desc = str(weather_desc[0].get("value", ""))
        return {
            "ok": True,
            "tool": "get_weather",
            "location": location or "auto",
            "current": {
                "temp_c": current.get("temp_C"),
                "feels_like_c": current.get("FeelsLikeC"),
                "humidity": current.get("humidity"),
                "wind_kmph": current.get("windspeedKmph"),
                "condition": desc,
            },
            "today": {
                "max_c": today.get("maxtempC"),
                "min_c": today.get("mintempC"),
            },
        }

    def _resolve_path(self, raw_path: str) -> Path:
        expanded = self._expand_user_placeholders(raw_path)
        path = Path(expanded).expanduser()
        if path.exists():
            return path
        path = self._fallback_common_dirs(path)
        if path.exists():
            return path

        # Fuzzy fallback: match each path segment by normalized name so
        # minor whitespace differences (like trailing spaces) still resolve.
        target = path if path.is_absolute() else (Path.cwd() / path)
        probe = target.resolve(strict=False)
        parts = probe.parts
        if not parts:
            return path

        current = Path(parts[0])
        if not current.exists():
            return path

        for part in parts[1:]:
            try:
                entries = list(current.iterdir())
            except Exception:  # noqa: BLE001
                return path
            matches = [entry for entry in entries if self._normalized_name(entry.name) == self._normalized_name(part)]
            if len(matches) != 1:
                return path
            current = matches[0]
        return current

    def _backup(self, target: Path) -> Path | None:
        if not target.exists() or not target.is_file():
            return None
        ensure_dirs()
        stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        safe = str(target).replace(os.sep, "__")
        backup_path = undo_dir() / f"{stamp}{safe}.bak"
        backup_path.write_bytes(target.read_bytes())
        return backup_path

    def _diff_preview(self, old: str, new: str, path: str) -> str:
        diff = difflib.unified_diff(
            old.splitlines(),
            new.splitlines(),
            fromfile=f"{path} (old)",
            tofile=f"{path} (new)",
            lineterm="",
        )
        return "\n".join(diff)

    def _approve(self, call: ToolCall, intent: str, target: str) -> None:
        print("\n--- Proposed Action ---")
        print(f"Intent: {intent}")
        print(f"Target: {target}")
        print(f"Risk: {call.risk_level}")
        if self.confirmation_verbosity == "full" and call.dry_run_preview:
            print("Preview:")
            print(call.dry_run_preview)
        ans = input("Approve? (y/n) ").strip().lower()
        if ans not in {"y", "yes"}:
            raise ApprovalRejected("Action rejected by user")

    def execute(self, call: ToolCall) -> dict[str, Any]:
        tool_name = call.tool_name
        args = call.arguments

        if tool_name == "read_file":
            path = self._resolve_path(str(args["path"]))
            if path.is_dir():
                entries = []
                for child in sorted(path.iterdir(), key=lambda p: p.name.lower()):
                    entries.append(
                        {
                            "name": child.name,
                            "type": "dir" if child.is_dir() else "file",
                        }
                    )
                return {
                    "ok": True,
                    "tool": "list_dir",
                    "path": str(path),
                    "entries": entries,
                    "note": "Requested read_file on a directory; returned directory listing.",
                }
            content = path.read_text(encoding="utf-8")
            return {"ok": True, "tool": tool_name, "content": content}

        if tool_name == "write_file":
            path = self._resolve_path(str(args["path"]))
            new_content = str(args.get("content", ""))
            old_content = path.read_text(encoding="utf-8") if path.exists() else ""
            call.dry_run_preview = call.dry_run_preview or self._diff_preview(
                old_content, new_content, str(path)
            )
            if call.requires_approval:
                self._approve(call, "Overwrite file contents", str(path))
            path.parent.mkdir(parents=True, exist_ok=True)
            backup_path = self._backup(path)
            path.write_text(new_content, encoding="utf-8")
            return {
                "ok": True,
                "tool": tool_name,
                "path": str(path),
                "backup": str(backup_path) if backup_path else None,
            }

        if tool_name == "append_file":
            path = self._resolve_path(str(args["path"]))
            append_content = str(args.get("content", ""))
            call.dry_run_preview = call.dry_run_preview or append_content
            if call.requires_approval:
                self._approve(call, "Append text to file", str(path))
            path.parent.mkdir(parents=True, exist_ok=True)
            backup_path = self._backup(path)
            with path.open("a", encoding="utf-8") as fh:
                fh.write(append_content)
            return {
                "ok": True,
                "tool": tool_name,
                "path": str(path),
                "backup": str(backup_path) if backup_path else None,
            }

        if tool_name == "search_text":
            path = str(self._resolve_path(str(args["path"])))
            pattern = str(args["pattern"])
            completed = subprocess.run(
                ["rg", "-n", pattern, path], capture_output=True, text=True
            )
            return {
                "ok": completed.returncode in {0, 1},
                "tool": tool_name,
                "matches": completed.stdout,
                "stderr": completed.stderr,
            }

        if tool_name == "list_dir":
            path = self._resolve_path(str(args["path"]))
            entries = []
            for child in sorted(path.iterdir(), key=lambda p: p.name.lower()):
                entries.append(
                    {
                        "name": child.name,
                        "type": "dir" if child.is_dir() else "file",
                    }
                )
            return {"ok": True, "tool": tool_name, "entries": entries}

        if tool_name == "run_shell":
            command = str(args["command"])
            cwd = str(args.get("cwd") or Path.cwd())
            if self._is_destructive(command):
                call.risk_level = "high"
            call.dry_run_preview = call.dry_run_preview or command
            if call.requires_approval:
                self._approve(call, "Run shell command", f"{command} (cwd={cwd})")
            completed = subprocess.run(
                command,
                cwd=cwd,
                shell=True,
                text=True,
                capture_output=True,
            )
            return {
                "ok": completed.returncode == 0,
                "tool": tool_name,
                "returncode": completed.returncode,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
                "argv_hint": shlex.split(command) if command else [],
            }

        if tool_name == "web_search":
            query = str(args.get("query", "")).strip()
            max_results = int(args.get("max_results", 5))
            if not query:
                return {"ok": False, "tool": tool_name, "error": "query is required"}
            return self._web_search(query=query, max_results=max_results)

        if tool_name == "get_weather":
            location = str(args.get("location", "")).strip()
            return self._get_weather(location=location)

        return {"ok": False, "error": f"Unknown tool: {tool_name}"}


def format_tool_result(result: dict[str, Any]) -> str:
    tool = str(result.get("tool", ""))
    ok = bool(result.get("ok", False))
    if not ok:
        return f"Tool failed: {json.dumps(result, ensure_ascii=False)[:1200]}"

    if tool == "list_dir":
        entries = result.get("entries", [])
        lines = ["Directory entries:"]
        for entry in entries[:120]:
            icon = "[D]" if entry.get("type") == "dir" else "[F]"
            lines.append(f"{icon} {entry.get('name', '')}")
        if len(entries) > 120:
            lines.append(f"... and {len(entries) - 120} more")
        return "\n".join(lines)

    if tool == "read_file":
        content = str(result.get("content", ""))
        preview = content[:3000]
        lines = [f"File content preview ({len(content)} chars):", preview]
        if len(content) > 3000:
            lines.append("... output truncated ...")
        return "\n".join(lines)

    if tool == "run_shell":
        rc = result.get("returncode")
        stdout = str(result.get("stdout", ""))[:2000].rstrip()
        stderr = str(result.get("stderr", ""))[:1200].rstrip()
        lines = [f"Shell return code: {rc}"]
        if stdout:
            lines.append("stdout:")
            lines.append(stdout)
        if stderr:
            lines.append("stderr:")
            lines.append(stderr)
        return "\n".join(lines)

    if tool == "web_search":
        query = str(result.get("query", ""))
        items = result.get("results", [])
        lines = [f"Web results for: {query}"]
        for i, item in enumerate(items[:8], start=1):
            lines.append(f"{i}. {item.get('title', '')}")
            lines.append(f"   {item.get('url', '')}")
            snippet = str(item.get("snippet", "")).strip()
            if snippet:
                lines.append(f"   {snippet}")
        if not items:
            lines.append("No results found.")
        return "\n".join(lines)

    if tool == "get_weather":
        current = result.get("current", {})
        today = result.get("today", {})
        lines = [f"Weather for {result.get('location', 'auto')}:"]
        lines.append(
            f"- Condition: {current.get('condition', 'n/a')} | Temp: {current.get('temp_c', 'n/a')}C | Feels like: {current.get('feels_like_c', 'n/a')}C"
        )
        lines.append(
            f"- Humidity: {current.get('humidity', 'n/a')}% | Wind: {current.get('wind_kmph', 'n/a')} km/h"
        )
        lines.append(
            f"- Today: min {today.get('min_c', 'n/a')}C, max {today.get('max_c', 'n/a')}C"
        )
        return "\n".join(lines)

    return json.dumps(result, ensure_ascii=False)[:2500]


def serialize_tool_result_for_model(result: dict[str, Any]) -> str:
    return json.dumps(result, ensure_ascii=False)[:6000]
