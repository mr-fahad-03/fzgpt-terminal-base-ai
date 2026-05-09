from pathlib import Path

from fzgpt.config import AppConfig
from fzgpt.session import InteractiveSession
from fzgpt.types import AgentResponse, ToolCall


class DummyClient:
    def __init__(self):
        self.calls = 0

    def ask(self, _messages):
        self.calls += 1
        if self.calls == 1:
            return AgentResponse(
                assistant_message="I will create file",
                tool_calls=[
                    ToolCall(
                        tool_name="write_file",
                        arguments={"path": "tmp_out.txt", "content": "ok"},
                        requires_approval=True,
                    )
                ],
            )
        return AgentResponse(assistant_message="Done", tool_calls=[])


class DummyVoice:
    def capture_and_transcribe(self):
        return "voice input"

    def speak(self, _text):
        return None


def test_session_one_turn(monkeypatch):
    session = InteractiveSession(AppConfig(voice_enabled=False), mode="typed")
    session.client = DummyClient()
    session.voice = DummyVoice()

    prompts = iter(["make a file", "/quit"])
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(prompts))
    monkeypatch.setattr(session.tools, "_approve", lambda *args, **kwargs: None)

    session.run()
    assert Path("tmp_out.txt").exists()
    Path("tmp_out.txt").unlink()
