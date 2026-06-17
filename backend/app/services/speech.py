from __future__ import annotations

import importlib.util
import shutil
import subprocess
from functools import lru_cache
from pathlib import Path
from tempfile import NamedTemporaryFile
from uuid import uuid4

from backend.app.services.domain import DomainCatalog


class SpeechService:
    def __init__(self, catalog: DomainCatalog) -> None:
        self.catalog = catalog

    def status(self) -> dict[str, object]:
        faster_whisper_available = importlib.util.find_spec("faster_whisper") is not None
        macos_say_available = shutil.which("say") is not None
        return {
            "stt": {
                "backend": "faster-whisper" if faster_whisper_available else "browser-fallback",
                "available": faster_whisper_available,
                "fallback": "Web Speech API",
                "domain_prompt": self.catalog.vocabulary_prompt,
            },
            "tts": {
                "backend": "macOS say" if macos_say_available else "browser-fallback",
                "available": macos_say_available,
                "fallback": "SpeechSynthesis API",
            },
        }

    def transcribe(self, audio_path: Path) -> dict[str, object]:
        if importlib.util.find_spec("faster_whisper") is None:
            return {
                "available": False,
                "transcript": "",
                "engine": "browser-fallback",
                "message": "faster-whisper is not installed; use browser speech recognition fallback.",
            }

        try:
            return transcribe_with_faster_whisper(audio_path, self.catalog.vocabulary_prompt)
        except Exception as exc:
            return {
                "available": False,
                "transcript": "",
                "engine": "faster-whisper",
                "message": f"Whisper could not decode this audio: {exc}",
            }

    def synthesize(self, text: str) -> Path | None:
        if shutil.which("say") is None:
            return None
        output = Path(NamedTemporaryFile(prefix=f"fieldvoice-{uuid4()}-", suffix=".m4a", delete=False).name)
        try:
            subprocess.run(
                ["say", "-o", str(output), text],
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError:
            output.unlink(missing_ok=True)
            return None
        return output


@lru_cache
def load_whisper_model():
    from faster_whisper import WhisperModel

    return WhisperModel("small", device="cpu", compute_type="int8")


def transcribe_with_faster_whisper(audio_path: Path, domain_prompt: str) -> dict[str, object]:
    model = load_whisper_model()
    segments, info = model.transcribe(
        str(audio_path),
        beam_size=5,
        vad_filter=True,
        initial_prompt=(
            "Indian industrial field inspection vocabulary. "
            f"Prefer exact equipment and procedure terms: {domain_prompt}"
        ),
    )
    transcript = " ".join(segment.text.strip() for segment in segments).strip()
    return {
        "available": True,
        "transcript": transcript,
        "engine": "faster-whisper",
        "language": getattr(info, "language", None),
        "duration": getattr(info, "duration", None),
    }
