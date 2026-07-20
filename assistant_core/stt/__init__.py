"""Speech-to-text interfaces and adapters."""

from assistant_core.stt.engine import FakeSpeechToTextEngine, VoskSpeechToTextEngine, create_stt_engine

__all__ = [
	"FakeSpeechToTextEngine",
	"VoskSpeechToTextEngine",
	"create_stt_engine",
]
