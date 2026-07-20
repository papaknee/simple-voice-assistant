---
name: tts-agent
description: 
Mission: Implement the text-to-speech abstraction and first offline-capable TTS backend for spoken assistant responses.

Implement TextToSpeechEngine with voice selection, language selection, speaking rate, volume metadata, synthesis, and structured errors.
Create a fake TTS engine for tests.
Implement response audio caching for repeated short responses when enabled.
Handle missing voice models, unsupported languages, empty text, long text, and backend failure.
Add tests for synthesis calls, cache hits, cache invalidation, voice configuration, and error paths.
Constraints: Do not decide what the assistant should say; consume already prepared response text. Do not play audio directly unless implementing a clearly separated audio output adapter.

Handoff: Return synthesized audio objects or file references that the audio output layer can play.