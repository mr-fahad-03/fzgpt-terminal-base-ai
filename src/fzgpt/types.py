from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolCall:
    tool_name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    requires_approval: bool = True
    risk_level: str = "medium"
    dry_run_preview: str = ""


@dataclass
class AgentResponse:
    assistant_message: str
    tool_calls: list[ToolCall] = field(default_factory=list)
