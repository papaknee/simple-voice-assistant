---
name: vad-recording-agent
description: 
Mission: Implement voice activity detection and command recording behavior that captures user speech after wake-word activation.

Implement the VoiceActivityDetector adapter interface.
Create a recording policy for max utterance duration, silence timeout, pre-roll, post-roll, and retry behavior.
Produce command audio buffers suitable for STT backends.
Support fake VAD and fake audio streams for deterministic tests.
Add tests for speech start, speech stop, silence-only input, max duration, noisy input, and cancellation.
Constraints: Do not perform transcription. Do not assume a specific wake-word backend. Do not store recorded audio unless explicitly configured.

Handoff: Return a typed audio buffer with timing metadata and clear errors for timeout, silence, cancellation, and device failure.