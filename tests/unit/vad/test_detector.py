"""Tests for VAD adapters and fake voice activity detection."""

from __future__ import annotations

import struct

import pytest

from assistant_core.interfaces import VoiceActivityDetector
from assistant_core.vad.detector import FakeVoiceActivityDetector, RmsVoiceActivityDetector


def test_rms_detector_marks_loud_pcm_as_speech() -> None:
    detector = RmsVoiceActivityDetector(speech_threshold=0.01, stop_after_silence_frames=2)

    silent_frame = struct.pack("<hhhh", 0, 0, 0, 0)
    speech_frame = struct.pack("<hhhh", 12000, -12000, 14000, -14000)

    detector.process_frame(silent_frame)
    assert detector.is_speech() is False
    assert detector.should_stop_recording() is False

    detector.process_frame(speech_frame)
    assert detector.is_speech() is True
    assert detector.should_stop_recording() is False

    detector.process_frame(silent_frame)
    assert detector.should_stop_recording() is False
    detector.process_frame(silent_frame)
    assert detector.should_stop_recording() is True


def test_rms_detector_rejects_invalid_thresholds() -> None:
    with pytest.raises(ValueError, match="speech_threshold"):
        RmsVoiceActivityDetector(speech_threshold=1.5)

    with pytest.raises(ValueError, match="stop_after_silence_frames"):
        RmsVoiceActivityDetector(stop_after_silence_frames=-1)


def test_fake_vad_is_protocol_compatible_and_stateful() -> None:
    detector = FakeVoiceActivityDetector(stop_after_silence_frames=1)

    assert isinstance(detector, VoiceActivityDetector)

    detector.process_frame(b"speech")
    assert detector.is_speech() is True
    assert detector.should_stop_recording() is False

    detector.process_frame(b"")
    assert detector.should_stop_recording() is True