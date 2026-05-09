from __future__ import annotations

from dataclasses import dataclass
import shutil
import subprocess
import tempfile
import wave

from .config import AppConfig


@dataclass
class VoiceStatus:
    stt_ready: bool
    tts_ready: bool
    microphone_ready: bool


class VoiceEngine:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self._whisper = None

    def _lazy_load_whisper(self) -> None:
        if self._whisper is not None:
            return
        from faster_whisper import WhisperModel  # type: ignore

        self._whisper = WhisperModel(self.config.whisper_model)

    def capture_and_transcribe(self) -> str:
        import numpy as np  # type: ignore
        import sounddevice as sd  # type: ignore

        print(
            f"Press Enter to start {self.config.voice_record_seconds}s recording, then stay silent to finish."
        )
        input("")
        sr = 16000
        frames = int(self.config.voice_record_seconds * sr)
        audio = sd.rec(frames, samplerate=sr, channels=1, dtype="float32")
        sd.wait()

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            with wave.open(tmp.name, "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(sr)
                pcm = (audio.flatten() * 32767).astype(np.int16)
                wav.writeframes(pcm.tobytes())
            wav_path = tmp.name

        self._lazy_load_whisper()
        segments, _ = self._whisper.transcribe(wav_path)
        text = " ".join(seg.text.strip() for seg in segments).strip()
        return text

    def speak(self, text: str) -> None:
        if not text.strip():
            return
        piper = shutil.which("piper")
        if piper:
            cmd = [piper]
            if self.config.piper_voice:
                cmd += ["--model", self.config.piper_voice]
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            proc.communicate(text)
            return

        # macOS fallback so voice output works without Piper.
        say_bin = shutil.which("say")
        if say_bin:
            subprocess.run([say_bin, text], check=False)


def check_voice_stack(config: AppConfig) -> VoiceStatus:
    _ = config
    stt_ready = False
    tts_ready = bool(shutil.which("piper") or shutil.which("say"))
    microphone_ready = False

    try:
        import faster_whisper  # noqa: F401

        stt_ready = True
    except Exception:
        stt_ready = False

    try:
        import sounddevice as sd  # type: ignore

        devices = sd.query_devices()
        microphone_ready = any((d.get("max_input_channels", 0) or 0) > 0 for d in devices)
    except Exception:
        microphone_ready = False

    return VoiceStatus(
        stt_ready=stt_ready, tts_ready=tts_ready, microphone_ready=microphone_ready
    )
