# Voice Assistant Work Plan

This file is the working tracker for the modular edge voice assistant. It turns the development specification into assignable, dependency-aware work items. Update the status, assignee, pull request, and handoff notes whenever work changes state.

Source of truth for scope and acceptance criteria: [simple assistant spec.md](simple%20assistant%20spec.md).

## Status Key

| Status | Meaning |
| --- | --- |
| `Backlog` | Approved work that is not yet dependency-ready. |
| `Ready` | Dependencies are complete; an agent may claim it. |
| `In progress` | An agent has claimed the work. |
| `Blocked` | Cannot proceed; record the missing decision, asset, or dependency. |
| `Review` | Implementation, tests, documentation, and handoff notes are ready for review. |
| `Validation` | Integration, hardware, performance, or acceptance checks are running. |
| `Done` | Merged, verified, documented, and accepted. |

## Operating Rules

- Assign only one primary agent per work item. Supporting agents should be named in the handoff notes.
- Before moving an item to `Ready`, verify that every listed dependency is `Done`.
- Any shared interface change belongs in an architecture issue before subsystem code is changed.
- Configuration additions must update the schema, sample configuration, tests, and documentation in the same change set.
- Backend-specific dependencies must remain optional unless required by the core runtime.
- Hardware blockers must leave a fake adapter or fixture-based path whenever practical.
- The integration agent should file targeted contract bugs rather than rewriting ownership boundaries across subsystems.

## Start Here: Wave 0

These items have no dependencies and can be assigned now.

| ID | Status | Owner Agent | Work Item | Handoff / Exit Gate |
| --- | --- | --- | --- | --- |
| META-001 | Done | Architecture | Confirm MVP decisions and unresolved project assumptions | Decisions recorded in "META-001 Decision Record" below; `ARCH-001` is now unblocked. |
| DOC-001 | Done | Documentation | Create initial README outline and contribution conventions | Added `README.md` and `CONTRIBUTING.md`; contributor workflow and tracker links are now documented. |
| TEST-001 | Done | Testing | Define testing strategy, pytest layout, and CI assumptions | Added `TESTING.md` with offline defaults, required test categories, pytest layout, markers, and CI assumptions. |

## Wave 1: Foundation

**Gate:** Complete the core contracts, fake runtime path, test foundation, and validated configuration before subsystem implementations begin.

| ID | Status | Owner Agent | Work Item | Dependencies |
| --- | --- | --- | --- | --- |
| ARCH-001 | Done | Architecture | Create repository package structure and baseline project files | Added baseline scaffold (`assistant_core/` packages, top-level project directories, `.gitignore`, typed package marker, README layout section); unblocks `ARCH-002`, `TEST-002`, `ARCH-003`, and `DOC-002`. |
| ARCH-002 | Done | Architecture | Create `pyproject.toml` with package metadata and dependency groups | Added `pyproject.toml` with PEP 621 metadata, setuptools build config, and optional dependency groups (`dev`, `audio`, `wake`, `vad`, `stt`, `tts`, `hardware`). |
| TEST-002 | Done | Testing | Configure pytest, ruff, mypy, formatting, and pre-commit hooks | Added tool configuration in `pyproject.toml` (`pytest`, `ruff`, `mypy`) plus `.pre-commit-config.yaml`; documented default validation commands. |
| ARCH-003 | Done | Architecture | Define core dataclasses and runtime event types | Added `assistant_core/models.py` core dataclasses and `assistant_core/runtime/events.py` runtime state/event types, with unit tests for validation/defaults. |
| ARCH-004 | Backlog | Architecture | Define abstract interfaces for replaceable components | ARCH-003 |
| ARCH-005 | Backlog | Architecture | Implement event bus and fake component adapters | ARCH-003, ARCH-004 |
| ARCH-006 | Backlog | Architecture | Implement skeleton runtime state machine with fake adapters | ARCH-005 |
| TEST-003 | Backlog | Testing | Create reusable fake components and core test fixtures | ARCH-004 |
| CONF-001 | Backlog | Configuration | Design typed configuration schema and defaults | ARCH-003 |
| CONF-002 | Backlog | Configuration | Implement config loader, validation, and environment overrides | CONF-001, TEST-002 |
| CONF-003 | Backlog | Configuration | Add sample configurations for development and reference devices | CONF-002 |
| DOC-002 | Backlog | Documentation | Document architecture boundaries and agent contribution workflow | ARCH-001 |

**Wave 1 coordination:** Coordinate names between `ARCH-003` and `CONF-001`. Merge `ARCH-004` early because it releases all subsystem adapter work. `TEST-003` should provide shared fakes rather than each subsystem creating its own.

## META-001 Decision Record

The following decisions resolve the Wave 0 architecture assumptions and set the MVP baseline for downstream agents.

| Decision Area | MVP Decision | Notes for Dependent Work |
| --- | --- | --- |
| Reference hardware | Raspberry Pi 4 Model B (4 GB) on 64-bit Raspberry Pi OS Bookworm or equivalent Linux, with one system-recognized microphone and speaker path. | Keep implementations Linux-portable; do not rely on Raspberry Pi-specific APIs. |
| Offline MVP scope | The default path is fully local after setup: local wake detection, local VAD/recording, local STT, deterministic intent routing, built-in skills, local TTS, and local sound cue playback. | Cloud adapters are optional and must remain opt-in. |
| Wake customization | Wake behavior must be configurable (engine, model path, sensitivity/threshold, cooldown, alternate phrases) via config/assets with no core-code edits. | Do not hard-code wake phrases or model paths. |
| Default voice/style | Default spoken response style is concise, neutral, and task-focused (generally one to two sentences unless detail is requested). | Keep response generation backend-configurable; style defaults belong in config, not code constants. |
| Built-in skills for MVP | Include `time_date` and `echo_debug` as built-ins for first end-to-end validation. | Additional skills are optional and should be plugin-friendly. |
| Transcript retention | Transcript and raw-audio retention are disabled by default. Any retention requires explicit user opt-in configuration and local-only storage controls. | Logging/observability should use metadata, timings, and redacted details by default. |

### META-001 Exit Gate

- [x] Reference hardware decision recorded.
- [x] Offline MVP scope recorded.
- [x] Wake customization policy recorded.
- [x] Default voice/style decision recorded.
- [x] Built-in MVP skills recorded.
- [x] Transcript retention policy recorded.
- [x] `ARCH-001` dependency on `META-001` is now satisfiable.

## Wave 2: Independent Subsystems

**Gate:** Implement each backend behind the stable interfaces. Use fake components and fixture tests so the tracks can proceed concurrently.

| ID | Status | Owner Agent | Work Item | Dependencies |
| --- | --- | --- | --- | --- |
| AUDIO-001 | Backlog | Audio | Implement audio device discovery and selection | ARCH-004, CONF-002, TEST-003 |
| AUDIO-002 | Backlog | Audio | Implement microphone capture and PCM frame buffering | AUDIO-001 |
| AUDIO-003 | Backlog | Audio | Implement audio output playback and sound manager | AUDIO-001, CONF-002 |
| WAKE-001 | Backlog | Wake Word | Implement wake-word adapter shell and fake detector | ARCH-004, CONF-002, TEST-003 |
| WAKE-002 | Backlog | Wake Word | Implement first local wake-word backend adapter | WAKE-001 |
| VAD-001 | Backlog | VAD and Recording | Implement VAD interface adapter and fake VAD | ARCH-004, TEST-003 |
| VAD-002 | Backlog | VAD and Recording | Implement command recording policy and audio buffer output | VAD-001, AUDIO-002 |
| STT-001 | Backlog | STT | Implement STT abstraction shell and fake STT engine | ARCH-004, CONF-002, TEST-003 |
| STT-002 | Backlog | STT | Implement first local STT backend adapter | STT-001 |
| INTENT-001 | Backlog | Intent | Implement rule-based intent router with aliases and parameters | ARCH-004, SKILL-001 |
| INTENT-002 | Backlog | Intent | Add confidence scoring, ambiguity handling, and fallback behavior | INTENT-001 |
| SKILL-001 | Backlog | Skill | Implement skill protocol, metadata model, and registry | ARCH-004, CONF-002 |
| SKILL-002 | Backlog | Skill | Implement permission model and timeout wrapper | SKILL-001 |
| SKILL-003 | Backlog | Skill | Add built-in time/date and echo/debug skills | SKILL-001, SKILL-002 |
| TTS-001 | Backlog | TTS | Implement TTS abstraction shell and fake TTS engine | ARCH-004, CONF-002, TEST-003 |
| TTS-002 | Backlog | TTS | Implement first offline-capable TTS backend adapter | TTS-001 |
| TTS-003 | Backlog | TTS | Implement optional response audio caching | TTS-001 |

**Wave 2 coordination:** After `ARCH-004`, start adapter shells. After `TEST-003` and `CONF-002`, all subsystem agents can work in parallel. The Intent and Skill agents must agree on the metadata contract before claiming `INTENT-001`.

## Wave 3: Runtime Assembly and Customization

**Gate:** Prove the fake pipeline first, then connect real implementations and finish the user-facing customization layer.

| ID | Status | Owner Agent | Work Item | Dependencies |
| --- | --- | --- | --- | --- |
| OBS-001 | Backlog | Integration | Implement structured logging and redaction policy | CONF-002, ARCH-005 |
| RUNTIME-001 | Backlog | Integration | Wire fake end-to-end assistant loop through configuration | ARCH-006, CONF-002, TEST-003, STT-001, TTS-001, WAKE-001, VAD-001, SKILL-001, INTENT-001 |
| TEST-004 | Backlog | Testing | Create end-to-end fake pipeline simulation test | RUNTIME-001 |
| RUNTIME-002 | Backlog | Integration | Add CLI commands for run, config validation, device listing, and diagnostics | RUNTIME-001, AUDIO-001, CONF-002 |
| RUNTIME-003 | Backlog | Integration | Wire real audio, wake, VAD, STT, intent, skill, TTS, and playback path | RUNTIME-001, AUDIO-003, WAKE-002, VAD-002, STT-002, INTENT-002, SKILL-003, TTS-002 |
| RUNTIME-004 | Backlog | Integration | Implement graceful shutdown, recovery states, and health checks | RUNTIME-001, OBS-001 |
| TEST-005 | Backlog | Testing | Add failure recovery tests for STT empty output, skill timeout, and audio failure | RUNTIME-001, SKILL-002, STT-001, AUDIO-003 |
| CUSTOM-001 | Backlog | Audio | Support user sound packs and validate required sound cues | AUDIO-003, CONF-002 |
| CUSTOM-002 | Backlog | Wake Word | Support configurable wake-word model paths and sensitivity profiles | WAKE-002, CONF-002 |
| CUSTOM-003 | Backlog | TTS | Support configurable TTS voices, speaking rate, and volume metadata | TTS-002, CONF-002 |
| CUSTOM-004 | Backlog | Skill | Support plugin loading from external folders | SKILL-001, CONF-002 |
| DOC-003 | Backlog | Documentation | Document configuration and sample configuration usage | CONF-003 |
| DOC-004 | Backlog | Documentation | Document sound pack, wake-word, and voice customization | CUSTOM-001, CUSTOM-002, CUSTOM-003 |
| DOC-005 | Backlog | Documentation | Document plugin authoring with a minimal example skill | SKILL-003, CUSTOM-004 |

**Wave 3 coordination:** `RUNTIME-001` is the critical integration checkpoint and must use fake components initially. Once it passes, real backend tracks continue independently until `RUNTIME-003` can assemble the physical-device path.

## Wave 4: Hardware Hardening and Release

**Gate:** Validate the real MVP under expected hardware conditions, publish operational documentation, and prepare the release candidate.

| ID | Status | Owner Agent | Work Item | Dependencies |
| --- | --- | --- | --- | --- |
| TEST-006 | Backlog | Testing | Add hardware test markers and reference hardware checklist | TEST-004, AUDIO-001 |
| BENCH-001 | Backlog | Testing | Add performance benchmark helpers and reporting format | OBS-001, RUNTIME-001 |
| WAKE-003 | Backlog | Wake Word | Add wake-word benchmark script for latency and false positives | WAKE-002, BENCH-001 |
| AUDIO-004 | Backlog | Audio | Add microphone and speaker diagnostic CLI tests | AUDIO-003, RUNTIME-002 |
| OBS-002 | Backlog | Integration | Add runtime timing metrics for wake, transcription, skill, TTS, and total response | OBS-001, RUNTIME-003 |
| REL-001 | Backlog | Integration | Create install script and local development setup command | RUNTIME-002, CONF-003 |
| REL-002 | Backlog | Integration | Create sample systemd service and daemon run instructions | RUNTIME-004, REL-001 |
| DOC-006 | Backlog | Documentation | Write hardware setup, diagnostics, and troubleshooting guide | AUDIO-004, TEST-006 |
| DOC-007 | Backlog | Documentation | Write release checklist and MVP validation guide | RUNTIME-003, TEST-004, REL-001 |
| TEST-007 | Backlog | Testing | Run full MVP acceptance test pass and file integration bugs | RUNTIME-003, TEST-004, DOC-007 |
| REL-003 | Backlog | Integration | Prepare MVP release candidate and tag checklist | TEST-007, REL-002, DOC-007 |

## Agent Workload Summary

| Agent | Assigned Items | Primary Handoff |
| --- | --- | --- |
| Architecture | META-001, ARCH-001 through ARCH-006 | Stable domain types, interfaces, fake runtime, and extension guidance. |
| Configuration | CONF-001 through CONF-003 | Typed configuration, validation, overrides, and samples. |
| Testing | TEST-001 through TEST-007, BENCH-001 | Shared test harness, offline CI path, hardware markers, and MVP validation. |
| Documentation | DOC-001 through DOC-007 | Accurate setup, customization, plugin, hardware, and release guidance. |
| Audio | AUDIO-001 through AUDIO-004, CUSTOM-001 | Audio adapters, sound manager, diagnostics, and sound-pack support. |
| Wake Word | WAKE-001 through WAKE-003, CUSTOM-002 | Local detector adapter, configuration, and benchmarks. |
| VAD and Recording | VAD-001 through VAD-002 | Typed command audio buffers and recording outcomes. |
| STT | STT-001 through STT-002 | Local transcription results with confidence and warnings. |
| Intent | INTENT-001 through INTENT-002 | Deterministic routed intent results and fallbacks. |
| Skill | SKILL-001 through SKILL-003, CUSTOM-004 | Registry, permissions, timeout execution, built-ins, and plugins. |
| TTS | TTS-001 through TTS-003, CUSTOM-003 | Offline synthesis output, voice settings, and cache behavior. |
| Integration | OBS-001 through OBS-002, RUNTIME-001 through RUNTIME-004, REL-001 through REL-003 | Config-driven CLI, robust assembled pipeline, service support, and release candidate. |

## MVP Completion Checklist

- [ ] A sample configuration boots the assistant through a documented command.
- [ ] A configurable local wake detector activates command capture.
- [ ] Configurable wake, listening, success, and error sound cues play.
- [ ] A command is captured, transcribed, routed to a built-in skill, and spoken aloud.
- [ ] The local-backend path works without internet after setup.
- [ ] Wake, STT, TTS, sounds, and skills are changed through configuration.
- [ ] Unit and integration tests pass in CI; hardware tests are documented and opt-in.
- [ ] A new skill can be added through the plugin guide without changing the runtime loop.
