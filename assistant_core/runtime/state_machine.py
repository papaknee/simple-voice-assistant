"""Skeleton runtime state machine wired to replaceable interfaces."""

from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter

from assistant_core.interfaces import (
    AudioInput,
    AudioOutput,
    IntentRouter,
    RuntimeEventBus,
    Skill,
    SoundManager,
    SpeechToTextEngine,
    TextToSpeechEngine,
    VoiceActivityDetector,
    WakeWordDetector,
)
from assistant_core.models import (
    AssistantContext,
    AssistantError,
    CapturedAudio,
    IntentResolution,
    JsonValue,
    SkillRequest,
    SkillResult,
    Transcript,
)
from assistant_core.runtime.events import RuntimeEvent, RuntimeEventType, RuntimeState
from assistant_core.skills import SkillExecutor


@dataclass(slots=True)
class AssistantRuntime:
    """State-machine runtime that orchestrates the fake-capable assistant pipeline."""

    audio_input: AudioInput
    audio_output: AudioOutput
    wake_detector: WakeWordDetector
    vad: VoiceActivityDetector
    stt: SpeechToTextEngine
    intent_router: IntentRouter
    skills: list[Skill]
    tts: TextToSpeechEngine
    sound_manager: SoundManager
    event_bus: RuntimeEventBus
    context: AssistantContext
    skill_executor: SkillExecutor = field(default_factory=SkillExecutor)
    fallback_response: str = "I did not understand the command."
    state: RuntimeState = RuntimeState.BOOT
    _capture_buffer: bytearray = field(default_factory=bytearray)

    def start(self) -> None:
        self._transition(RuntimeState.BOOT)
        self.audio_input.start()
        self.wake_detector.load()
        self._transition(RuntimeState.IDLE_LISTENING)

    def shutdown(self) -> None:
        self.audio_input.stop()
        self.audio_output.stop()
        self._transition(RuntimeState.SHUTDOWN)
        self._publish(RuntimeEventType.SHUTDOWN_COMPLETED, RuntimeState.SHUTDOWN)

    def process_audio_frame(self, frame: bytes) -> None:
        if self.state == RuntimeState.IDLE_LISTENING:
            detection = self.wake_detector.process_frame(frame)
            if not detection.detected:
                return
            self._publish(
                RuntimeEventType.WAKE_DETECTED,
                RuntimeState.IDLE_LISTENING,
                payload={"score": detection.score},
            )
            self.sound_manager.play("wake_detected")
            self._transition(RuntimeState.ACTIVATED)
            self._capture_buffer.clear()
            self._transition(RuntimeState.CAPTURING_COMMAND)
            self._publish(RuntimeEventType.COMMAND_CAPTURE_STARTED, RuntimeState.CAPTURING_COMMAND)
            return

        if self.state != RuntimeState.CAPTURING_COMMAND:
            return

        self._capture_buffer.extend(frame)
        self.vad.process_frame(frame)
        if self.vad.should_stop_recording():
            self._publish(
                RuntimeEventType.COMMAND_CAPTURE_COMPLETED, RuntimeState.CAPTURING_COMMAND
            )
            self._run_command_pipeline(bytes(self._capture_buffer))
            self._capture_buffer.clear()

    def _run_command_pipeline(self, audio_bytes: bytes) -> None:
        try:
            self._transition(RuntimeState.TRANSCRIBING)
            transcript = self._transcribe(audio_bytes)

            self._transition(RuntimeState.ROUTING_INTENT)
            intent = self.intent_router.route(transcript, self.context)
            self._publish(
                RuntimeEventType.INTENT_ROUTED,
                RuntimeState.ROUTING_INTENT,
                payload={"intent_name": intent.intent_name, "confidence": intent.confidence},
            )

            self._transition(RuntimeState.EXECUTING_SKILL)
            result = self._execute_skill(
                intent_name=intent.intent_name, transcript=transcript, intent=intent
            )
            self._publish(
                RuntimeEventType.SKILL_EXECUTED,
                RuntimeState.EXECUTING_SKILL,
                payload={"skill_name": result.skill_name, "success": result.success},
            )

            self._transition(RuntimeState.RESPONDING)
            self._speak_result(result)
            self._publish(RuntimeEventType.RESPONSE_RENDERED, RuntimeState.RESPONDING)
            self._transition(RuntimeState.IDLE_LISTENING)
        except (RuntimeError, ValueError) as exc:
            self._transition(RuntimeState.RECOVERING)
            self._publish(
                RuntimeEventType.ERROR_RAISED,
                RuntimeState.RECOVERING,
                error=AssistantError(
                    code="runtime_pipeline_error",
                    message=str(exc),
                    recoverable=True,
                ),
            )
            self.sound_manager.play("error")
            self._publish(RuntimeEventType.RECOVERY_COMPLETED, RuntimeState.RECOVERING)
            self._transition(RuntimeState.IDLE_LISTENING)

    def _transcribe(self, audio_bytes: bytes) -> Transcript:
        started = perf_counter()
        device = self.audio_input.device_info()
        sample_width_bytes = 2
        frame_count = len(audio_bytes) // max(1, device.channels * sample_width_bytes)
        captured = CapturedAudio(
            sample_rate_hz=device.sample_rate_hz,
            channels=device.channels,
            sample_width_bytes=sample_width_bytes,
            frame_count=frame_count,
            duration_seconds=frame_count / max(1, device.sample_rate_hz),
            source=device.name,
        )
        transcript = self.stt.transcribe(audio_bytes, captured, language=self.context.locale)
        self._publish(
            RuntimeEventType.TRANSCRIPTION_COMPLETED,
            RuntimeState.TRANSCRIBING,
            duration_ms=(perf_counter() - started) * 1000.0,
            payload={"has_text": bool(transcript.text)},
        )
        return transcript

    def _execute_skill(
        self,
        *,
        intent_name: str | None,
        transcript: Transcript,
        intent: IntentResolution,
    ) -> SkillResult:
        selected = self._select_skill(intent_name, intent)
        if selected is None:
            return SkillResult(
                skill_name="fallback",
                success=True,
                spoken_response=self.fallback_response,
            )
        request = SkillRequest(
            skill_name=selected.metadata().name,
            transcript=transcript,
            intent=intent,
            context=self.context,
        )
        return self.skill_executor.execute(selected, request, self.context)

    def _select_skill(self, intent_name: str | None, intent: IntentResolution) -> Skill | None:
        if intent_name is None:
            return None
        for skill in self.skills:
            if skill.metadata().name != intent_name:
                continue
            if skill.can_handle(intent):
                return skill
        for skill in self.skills:
            if skill.can_handle(intent):
                return skill
        return None

    def _speak_result(self, result: SkillResult) -> None:
        response = result.spoken_response or self.fallback_response
        audio = self.tts.synthesize(response)
        self.audio_output.play(audio)
        self.sound_manager.play("success" if result.success else "error")

    def _transition(self, state: RuntimeState) -> None:
        from_state = self.state
        self.state = state
        self._publish(
            RuntimeEventType.STATE_TRANSITIONED,
            state,
            payload={"from_state": from_state.value, "to_state": state.value},
        )

    def _publish(
        self,
        event_type: RuntimeEventType,
        state: RuntimeState,
        *,
        duration_ms: float | None = None,
        payload: dict[str, JsonValue] | None = None,
        error: AssistantError | None = None,
    ) -> None:
        self.event_bus.publish(
            RuntimeEvent(
                event_type=event_type,
                state=state,
                turn_id=self.context.turn_id,
                duration_ms=duration_ms,
                payload=payload or {},
                error=error,
            )
        )
