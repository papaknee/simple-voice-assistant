"""Command recording helpers that turn frame streams into STT-ready audio buffers."""

from __future__ import annotations

from collections import deque
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from math import ceil

from assistant_core.interfaces import VoiceActivityDetector
from assistant_core.models import AssistantError, CapturedAudio


class RecordingError(RuntimeError):
    """Raised when command recording cannot complete successfully."""

    def __init__(self, error: AssistantError) -> None:
        super().__init__(error.message)
        self.error = error


@dataclass(frozen=True, slots=True)
class RecordingPolicy:
    """Policy values that control command recording behavior."""

    sample_rate_hz: int = 16000
    channels: int = 1
    sample_width_bytes: int = 2
    frame_duration_seconds: float = 0.1
    max_utterance_seconds: float = 12.0
    silence_timeout_seconds: float = 1.0
    pre_roll_seconds: float = 0.0
    post_roll_seconds: float = 0.0
    max_retries: int = 0

    def __post_init__(self) -> None:
        if self.sample_rate_hz <= 0:
            raise ValueError("sample_rate_hz must be > 0.")
        if self.channels <= 0:
            raise ValueError("channels must be > 0.")
        if self.sample_width_bytes <= 0:
            raise ValueError("sample_width_bytes must be > 0.")
        if self.frame_duration_seconds <= 0:
            raise ValueError("frame_duration_seconds must be > 0.")
        if self.max_utterance_seconds <= 0:
            raise ValueError("max_utterance_seconds must be > 0.")
        if self.silence_timeout_seconds < 0:
            raise ValueError("silence_timeout_seconds must be >= 0.")
        if self.pre_roll_seconds < 0:
            raise ValueError("pre_roll_seconds must be >= 0.")
        if self.post_roll_seconds < 0:
            raise ValueError("post_roll_seconds must be >= 0.")
        if self.max_retries < 0:
            raise ValueError("max_retries must be >= 0.")

    @property
    def pre_roll_frames(self) -> int:
        return ceil(self.pre_roll_seconds / self.frame_duration_seconds)

    @property
    def post_roll_frames(self) -> int:
        return ceil(self.post_roll_seconds / self.frame_duration_seconds)


@dataclass(frozen=True, slots=True)
class RecordedCommandAudio:
    """STT-ready command audio plus timing metadata."""

    audio_bytes: bytes
    captured_audio: CapturedAudio
    source: str | None = None
    attempt: int = 1
    speech_started_at_seconds: float = 0.0
    speech_ended_at_seconds: float = 0.0
    pre_roll_seconds: float = 0.0
    post_roll_seconds: float = 0.0
    speech_frame_count: int = 0
    total_frame_count: int = 0


def record_command(
    frame_source_factory: Callable[[], Iterator[bytes]],
    vad_factory: Callable[[], VoiceActivityDetector],
    policy: RecordingPolicy,
    *,
    cancellation_check: Callable[[], bool] | None = None,
    source: str | None = None,
) -> RecordedCommandAudio:
    """Record a command from a frame source until silence or a duration limit.

    The recorder uses a factory for frames and a factory for VAD instances so retry
    behavior can restart cleanly without requiring a reset method on the detector
    interface.
    """

    last_error: RecordingError | None = None
    for attempt in range(1, policy.max_retries + 2):
        vad = vad_factory()
        try:
            return _record_once(
                frame_source_factory(),
                vad,
                policy,
                attempt=attempt,
                cancellation_check=cancellation_check,
                source=source,
            )
        except RecordingError as error:
            last_error = error
            if error.error.code not in {
                "vad_recording.silence_only",
                "vad_recording.timeout",
            }:
                raise
    assert last_error is not None
    raise last_error


def _record_once(
    frames: Iterator[bytes],
    vad: VoiceActivityDetector,
    policy: RecordingPolicy,
    *,
    attempt: int,
    cancellation_check: Callable[[], bool] | None,
    source: str | None,
) -> RecordedCommandAudio:
    pre_roll = deque[bytes](maxlen=policy.pre_roll_frames)
    post_roll_frames_remaining = policy.post_roll_frames
    audio_chunks: list[bytes] = []
    speech_started = False
    speech_frame_count = 0
    total_frame_count = 0
    elapsed_seconds = 0.0
    silence_seconds = 0.0
    speech_started_at_seconds = 0.0
    speech_ended_at_seconds = 0.0
    speech_seen = False

    try:
        for frame in frames:
            if cancellation_check is not None and cancellation_check():
                raise RecordingError(
                    AssistantError(
                        code="vad_recording.cancelled",
                        message="Command recording was cancelled.",
                    )
                )

            total_frame_count += 1
            elapsed_seconds += policy.frame_duration_seconds
            vad.process_frame(frame)

            if not speech_started:
                if vad.is_speech():
                    speech_seen = True
                    speech_started = True
                    speech_started_at_seconds = elapsed_seconds - policy.frame_duration_seconds
                    audio_chunks.extend(pre_roll)
                    audio_chunks.append(frame)
                    pre_roll.clear()
                    speech_frame_count += 1
                    speech_ended_at_seconds = elapsed_seconds
                    continue

                pre_roll.append(frame)
                if elapsed_seconds >= policy.max_utterance_seconds:
                    raise RecordingError(
                        AssistantError(
                            code="vad_recording.silence_only",
                            message="No speech was detected before the recording window ended.",
                            details={"attempt": attempt},
                        )
                    )
                continue

            audio_chunks.append(frame)
            speech_frame_count += 1

            if elapsed_seconds >= policy.max_utterance_seconds:
                raise RecordingError(
                    AssistantError(
                        code="vad_recording.timeout",
                        message="Command recording exceeded the maximum utterance duration.",
                        details={"attempt": attempt},
                    )
                )

            if vad.is_speech():
                silence_seconds = 0.0
                post_roll_frames_remaining = policy.post_roll_frames
                speech_ended_at_seconds = elapsed_seconds
                continue

            if post_roll_frames_remaining > 0:
                post_roll_frames_remaining -= 1
                speech_ended_at_seconds = elapsed_seconds
                continue

            silence_seconds += policy.frame_duration_seconds
            speech_ended_at_seconds = elapsed_seconds
            if silence_seconds >= policy.silence_timeout_seconds:
                break
    except StopIteration:
        pass
    except RecordingError:
        raise
    except RuntimeError as exc:
        raise RecordingError(
            AssistantError(
                code="vad_recording.device_failure",
                message=str(exc),
            )
        ) from exc

    if not speech_seen:
        raise RecordingError(
            AssistantError(
                code="vad_recording.silence_only",
                message="No speech was detected before the frame source ended.",
                details={"attempt": attempt},
            )
        )

    audio_bytes = b"".join(audio_chunks)
    frame_count = len(audio_bytes) // max(1, policy.channels * policy.sample_width_bytes)
    captured_audio = CapturedAudio(
        sample_rate_hz=policy.sample_rate_hz,
        channels=policy.channels,
        sample_width_bytes=policy.sample_width_bytes,
        frame_count=frame_count,
        duration_seconds=frame_count / policy.sample_rate_hz,
        source=source,
    )
    return RecordedCommandAudio(
        audio_bytes=audio_bytes,
        captured_audio=captured_audio,
        source=source,
        attempt=attempt,
        speech_started_at_seconds=speech_started_at_seconds,
        speech_ended_at_seconds=speech_ended_at_seconds,
        pre_roll_seconds=policy.pre_roll_frames * policy.frame_duration_seconds,
        post_roll_seconds=policy.post_roll_frames * policy.frame_duration_seconds,
        speech_frame_count=speech_frame_count,
        total_frame_count=total_frame_count,
    )