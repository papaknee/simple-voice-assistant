"""Voice activity detector adapters and deterministic test doubles."""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt

from assistant_core.interfaces import VoiceActivityDetector


@dataclass(slots=True)
class RmsVoiceActivityDetector(VoiceActivityDetector):
    """Simple PCM energy detector based on an RMS speech threshold."""

    speech_threshold: float = 0.02
    stop_after_silence_frames: int = 2
    _seen_speech: bool = False
    _silence_frames: int = 0
    _speech: bool = False

    def __post_init__(self) -> None:
        if not 0.0 <= self.speech_threshold <= 1.0:
            raise ValueError("speech_threshold must be between 0.0 and 1.0.")
        if self.stop_after_silence_frames < 0:
            raise ValueError("stop_after_silence_frames must be >= 0.")

    def process_frame(self, frame: bytes) -> None:
        self._speech = self._is_speech_frame(frame)
        if self._speech:
            self._seen_speech = True
            self._silence_frames = 0
            return
        self._silence_frames += 1

    def is_speech(self) -> bool:
        return self._speech

    def should_stop_recording(self) -> bool:
        return self._seen_speech and self._silence_frames >= self.stop_after_silence_frames

    def _is_speech_frame(self, frame: bytes) -> bool:
        if len(frame) < 2:
            return False

        sample_count = len(frame) // 2
        if sample_count == 0:
            return False

        total_energy = 0.0
        for offset in range(0, sample_count * 2, 2):
            sample = int.from_bytes(frame[offset : offset + 2], byteorder="little", signed=True)
            total_energy += float(sample * sample)

        rms = sqrt(total_energy / sample_count) / 32768.0
        return rms >= self.speech_threshold


@dataclass(slots=True)
class FakeVoiceActivityDetector(VoiceActivityDetector):
    """Deterministic fake VAD with configurable speech/silence stop threshold."""

    stop_after_silence_frames: int = 2
    _seen_speech: bool = False
    _silence_frames: int = 0
    _speech: bool = False

    def process_frame(self, frame: bytes) -> None:
        self._speech = bool(frame.strip())
        if self._speech:
            self._seen_speech = True
            self._silence_frames = 0
            return
        self._silence_frames += 1

    def is_speech(self) -> bool:
        return self._speech

    def should_stop_recording(self) -> bool:
        return self._seen_speech and self._silence_frames >= self.stop_after_silence_frames