# Testing Strategy and CI Assumptions

This document defines the baseline testing strategy for the modular edge voice assistant.

It establishes default offline expectations, the planned pytest layout, and CI assumptions for upcoming implementation work.

## Default expectations (offline-first)

- Default test runs must not require internet access.
- Default test runs must not require physical audio hardware.
- Default CI must use fake/fixture-based components for audio, wake, VAD, STT, intent, skill, TTS, and playback.
- Hardware and network-dependent tests are opt-in and excluded from default CI.

## Required test categories

1. Unit tests
   - Configuration parsing and validation errors.
   - Individual adapters and pure logic modules.
   - Runtime state transition behavior with fakes.
2. Fixture-based integration tests
   - Pipeline sequencing and event ordering across multiple components.
   - Failure handling (empty transcripts, timeouts, missing assets/devices, permission denials).
3. End-to-end fake pipeline tests
   - Full assistant loop using fake adapters only.
4. Hardware-marked tests (opt-in)
   - Device discovery, real capture/playback, wake latency, and diagnostics.
5. Performance/benchmark tests (opt-in)
   - Startup time, memory/CPU behavior, and stage timing targets.

## Planned pytest layout

When code scaffolding is introduced, use this layout:

```text
tests/
  conftest.py
  unit/
    config/
    runtime/
    audio/
    wake/
    vad/
    stt/
    intent/
    skills/
    tts/
  integration/
    test_fake_pipeline_flow.py
    test_failure_recovery_paths.py
  e2e/
    test_fake_assistant_loop.py
  hardware/
    test_audio_devices.py
    test_real_capture_playback.py
  performance/
    test_benchmarks.py
  fixtures/
    audio/
```

### Marker plan

- `@pytest.mark.hardware`: requires physical device access; excluded by default.
- `@pytest.mark.performance`: benchmarks/latency checks; excluded by default CI smoke runs.
- `@pytest.mark.integration`: multi-component deterministic tests with fakes/fixtures.
- `@pytest.mark.e2e`: fake end-to-end assistant loop tests.

## CI assumptions (initial)

- CI runs on Linux with Python 3.11+.
- CI uses a deterministic offline default command set:
  - unit tests
  - integration tests with fakes/fixtures
  - fake end-to-end tests
- CI excludes `hardware` and `performance` markers unless explicitly enabled in dedicated workflows.
- No test should pull models or external assets at runtime in default CI.

## Authoring guidance for future agents

- Add tests in the same change set as behavior changes.
- Prefer existing shared fixtures/fakes over ad hoc mocks.
- Keep fixture audio files short and deterministic.
- Assert structured errors and actionable messages.
- Verify recovery behavior for non-fatal failures so runtime can return to listening state.
