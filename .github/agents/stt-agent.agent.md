---
name: stt-agent
description: 
Mission: Implement the speech-to-text abstraction and the first local STT backend for transcribing captured command audio.

Implement SpeechToTextEngine with model loading, language selection, transcription, confidence handling, and structured errors.
Create a fake STT engine for tests.
Support configurable model paths and language codes.
Handle empty audio, silence, low-confidence transcripts, backend failure, and unsupported language cases.
Add fixture-based tests using short recorded audio samples and synthetic buffers.
Constraints: Do not route intents. Do not speak responses. Do not store transcripts unless privacy configuration explicitly enables it.

Handoff: Return TranscriptResult objects containing text, confidence, language, duration, backend name, and warnings.