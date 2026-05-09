from __future__ import annotations

import os
import shutil
import sys
import textwrap


class TerminalUI:
    def __init__(self) -> None:
        self.use_color = self._supports_color()
        self.reset = "\033[0m" if self.use_color else ""
        self.bold = "\033[1m" if self.use_color else ""
        self.dim = "\033[2m" if self.use_color else ""
        self.cyan = "\033[96m" if self.use_color else ""
        self.blue = "\033[94m" if self.use_color else ""
        self.magenta = "\033[95m" if self.use_color else ""
        self.green = "\033[92m" if self.use_color else ""
        self.yellow = "\033[93m" if self.use_color else ""
        self.red = "\033[91m" if self.use_color else ""

    def _supports_color(self) -> bool:
        if os.getenv("NO_COLOR"):
            return False
        if not sys.stdout.isatty():
            return False
        term = os.getenv("TERM", "").lower()
        return term not in {"", "dumb"}

    def _paint(self, text: str, color: str) -> str:
        if not self.use_color:
            return text
        return f"{color}{text}{self.reset}"

    def width(self) -> int:
        return max(60, shutil.get_terminal_size((100, 20)).columns)

    def _center(self, text: str) -> str:
        return text.center(self.width())

    def wrap(self, text: str) -> list[str]:
        wrapped = textwrap.fill(text, width=max(52, self.width() - 4))
        return wrapped.splitlines()

    def print_banner(self) -> None:
        wide_logo = [
            "FFFFFFFF  ZZZZZZZ   CCCCC   OOOOO   DDDDD   EEEEEEE",
            "FF            ZZ   CC      OO   OO  DD  DD  EE     ",
            "FFFF        ZZ     CC      OO   OO  DD   DD EEEEE  ",
            "FF        ZZ       CC      OO   OO  DD  DD  EE     ",
            "FF       ZZZZZZZ    CCCCC   OOOOO   DDDDD   EEEEEEE",
        ]
        compact_logo = [
            "FFFFFF  ZZ  CCC  OOO  DDD  EEEEE",
            "FF      ZZ  CC  OO OO DD D EE   ",
            "FFFF   ZZ   CC  OO OO DDDD EEE  ",
            "FF    ZZ    CC  OO OO DD D EE   ",
            "FF    ZZZZ  CCC  OOO  DDD  EEEEE",
        ]
        logo = wide_logo if self.width() >= 90 else compact_logo
        accents = [self.cyan, self.blue, self.cyan, self.blue, self.cyan]
        for i, line in enumerate(logo):
            color = accents[i % len(accents)]
            print(self._paint(self._center(line), color))

        tagline = "Local AI Agent | Voice + Typed | Safe Approvals"
        print(self._paint(self._center(tagline), self.dim + self.bold if self.use_color else ""))
        print()

    def startup_help(self) -> None:
        lines = [
            "Session started.",
            "Use /voice for microphone, /sh <command> for shell, /quit to exit.",
        ]
        for line in lines:
            for wrapped in self.wrap(line):
                self.info(wrapped)

    def prompt(self) -> str:
        return self._paint("fzgpt> ", self.bold + self.cyan)

    def info(self, text: str) -> None:
        print(self._paint(text, self.cyan))

    def success(self, text: str) -> None:
        print(self._paint(text, self.green))

    def warn(self, text: str) -> None:
        print(self._paint(text, self.yellow))

    def error(self, text: str) -> None:
        print(self._paint(text, self.red))

    def ai(self, text: str) -> None:
        print(self._paint(f"AI: {text}", self.bold + self.magenta))

    def tool(self, name: str, payload: str) -> None:
        print(self._paint(f"[tool:{name}] {payload}", self.blue))
