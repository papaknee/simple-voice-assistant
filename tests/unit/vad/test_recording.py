"""Tests for VAD command recording and typed audio buffer output."""

from __future__ import annotations

import struct

import pytest

from assistant_core.vad.detector import FakeVoiceActivityDetector, RmsVoiceActivityDetector
from assistant_core.vad.recording import RecordingError, RecordingPolicy, record_command


def _pcm_frame(value: int) -> bytes:
    return struct.pack("<hhhh", value, value, value, value)


def test_record_command_returns_buffer_after_speech_and_silence() -> None:
    policy = RecordingPolicy(
        frame_duration_seconds=0.1,
        pre_roll_seconds=0.1,
        post_roll_seconds=0.1,
        silence_timeout_seconds=0.2,
        max_utterance_seconds=2.0,
    )
    frames = [_pcm_frame(0), _pcm_frame(12000), _pcm_frame(12000), _pcm_frame(0), _pcm_frame(0)]

    result = record_command(
        lambda: iter(frames),
        lambda: RmsVoiceActivityDetector(speech_threshold=0.01, stop_after_silence_frames=2),
        policy,
        source="fake-mic",
    )

    assert result.audio_bytes == b"".join(frames)
    assert result.source == "fake-mic"
    assert result.captured_audio.sample_rate_hz == 16000
    assert result.captured_audio.channels == 1
    assert result.speech_frame_count == 4
    assert result.total_frame_count == 5


def test_record_command_raises_on_silence_only_input() -> None:
    policy = RecordingPolicy(frame_duration_seconds=0.1, max_utterance_seconds=0.3)
    frames = [b"", b"", b""]

    with pytest.raises(RecordingError) as exc_info:
        record_command(
            lambda: iter(frames),
            lambda: FakeVoiceActivityDetector(stop_after_silence_frames=2),
            policy,
        )

    assert exc_info.value.error.code == "vad_recording.silence_only"


def test_record_command_raises_on_timeout_during_continuous_speech() -> None:
    policy = RecordingPolicy(frame_duration_seconds=0.1, max_utterance_seconds=0.3)
    frames = [_pcm_frame(12000), _pcm_frame(12000), _pcm_frame(12000), _pcm_frame(12000)]

    with pytest.raises(RecordingError) as exc_info:
        record_command(
            lambda: iter(frames),
            lambda: FakeVoiceActivityDetector(stop_after_silence_frames=10),
            policy,
        )

    assert exc_info.value.error.code == "vad_recording.timeout"


def test_record_command_treats_noise_as_speech() -> None:
    policy = RecordingPolicy(frame_duration_seconds=0.1, silence_timeout_seconds=0.2)
    noise_frame = _pcm_frame(7000)
    frames = [noise_frame, noise_frame, _pcm_frame(0), _pcm_frame(0)]

    result = record_command(
        lambda: iter(frames),
        lambda: RmsVoiceActivityDetector(speech_threshold=0.01, stop_after_silence_frames=2),
        policy,
    )

    assert result.audio_bytes.startswith(noise_frame)
    assert result.speech_frame_count == 4
    assert result.total_frame_count == 4


def test_record_command_can_be_cancelled() -> None:
    policy = RecordingPolicy(frame_duration_seconds=0.1, max_utterance_seconds=1.0)
    cancelled = {"value": False}

    def frame_source() -> list[bytes]:
        return [_pcm_frame(12000), _pcm_frame(12000)]

    def iterator() -> object:
        for index, frame in enumerate(frame_source()):
            yield frame
            if index == 0:
                cancelled["value"] = True

    with pytest.raises(RecordingError) as exc_info:
        record_command(
            lambda: iter(iterator()),
            lambda: FakeVoiceActivityDetector(stop_after_silence_frames=2),
            policy,
            cancellation_check=lambda: cancelled["value"],
        )

    assert exc_info.value.error.code == "vad_recording.cancelled"


def test_record_command_retries_after_silence_only() -> None:
    policy = RecordingPolicy(frame_duration_seconds=0.1, max_utterance_seconds=1.0, max_retries=1)
    attempts = [
        [b"", b"", b""],
        [_pcm_frame(12000), _pcm_frame(12000), b"", b""],
    ]

    result = record_command(
        lambda: iter(attempts.pop(0)),
        lambda: FakeVoiceActivityDetector(stop_after_silence_frames=2),
        policy,
    )

    assert result.attempt == 2
    assert result.audio_bytes.startswith(_pcm_frame(12000))