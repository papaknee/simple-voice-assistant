# Development Specification: Modular Edge Python Voice Assistant

## A simple, extensible, fully customizable voice assistant framework for small physical edge hardware.

# 1\. Purpose and Product Vision

This project will deliver a lightweight Python voice assistant that runs locally on small edge hardware, listens for a configurable wake word, captures spoken commands, routes intent to modular skills, and responds through configurable audio feedback and text-to-speech. The system should feel streamlined like a consumer voice assistant while remaining developer-friendly, privacy-conscious, offline-first where practical, and easy to customize without modifying core code.

Design inspiration comes from current edge voice assistant patterns: a small wake-word model can run continuously while heavier speech recognition or response generation runs only after activation; on-device processing improves privacy, latency, and resilience when connectivity is poor; and modular pipelines make it possible to swap wake-word, speech-to-text, intent, and text-to-speech implementations independently.

# 2\. Goals and Non-Goals

## 2.1 Goals

* Run on constrained physical hardware such as Raspberry Pi-class devices, mini PCs, or embedded Linux systems.  
* Keep the core simple, readable, and modular so contributors and coding agents can work independently.  
* Support pluggable wake-word engines, speech-to-text engines, intent routers, skills, text-to-speech engines, and sound packs.  
* Make customization possible through configuration files, user assets, and plugin discovery rather than core code edits.  
* Prefer local and offline-capable components, with optional cloud integrations behind clear interfaces.  
* Provide explicit task instructions for multiple coding agents and common guidelines that all agents must follow.  
* Include unit, integration, hardware, performance, and end-to-end testing plans.

## 2.2 Non-Goals

* Do not build a monolithic assistant where wake word, transcription, intent handling, and speech output are tightly coupled.  
* Do not require an always-on cloud service for core operation.  
* Do not hard-code wake words, sounds, voices, skill names, or hardware-specific paths.  
* Do not optimize for advanced conversational AI before the basic event loop, customization model, and testing foundation are stable.  
* Do not prioritize a complex graphical interface in the first implementation.

# 3\. Target Hardware and Runtime Assumptions

* **Primary target:** Linux-based edge hardware with Python 3.11+, microphone input, speaker output, and enough CPU/RAM for lightweight wake-word detection and command processing.  
* **Reference device:** Raspberry Pi 4 or newer, though the architecture must not depend on Raspberry Pi-specific APIs.  
* **Audio input:** USB microphone, I2S microphone, or ALSA/PulseAudio/PipeWire-compatible capture device.  
* **Audio output:** 3.5 mm, HDMI, USB speaker, Bluetooth speaker, DAC, or any system-recognized output device.  
* **Network:** Optional. The assistant must boot and handle local skills without internet after dependencies and models are installed.  
* **Operating mode:** Long-running daemon or CLI process suitable for systemd startup.

# 4\. High-Level Architecture

The assistant should be implemented as an event-driven loop with independently replaceable stages. Each stage exposes a small interface, emits structured events, and avoids direct dependencies on unrelated stages.

| Stage | Responsibility | Examples |
| :---- | :---- | :---- |
| **Audio Input** | Open microphone stream, normalize frames, expose audio chunks. | sounddevice, PyAudio, ALSA wrapper |
| **Wake Word** | Continuously detect configurable activation phrase with low CPU use. | openWakeWord, local-wake, Picovoice Porcupine adapter |
| **Voice Activity Detection** | Detect speech boundaries and stop recording after configurable silence. | webrtcvad, Silero VAD, simple RMS threshold adapter |
| **Speech-to-Text** | Convert captured speech to text using local or optional cloud engines. | Vosk, Whisper.cpp binding, faster-whisper, cloud adapter |
| **Intent Router** | Map text to skill invocation, command, clarification, or fallback. | Rule router, semantic router, local LLM router |
| **Skill Runtime** | Execute modular skills with typed inputs and safe outputs. | Time, timers, home automation, shell-safe local utilities |
| **Response Generator** | Turn skill results into concise spoken responses. | Template responses, local model, deterministic formatter |
| **Text-to-Speech** | Synthesize response audio using configurable voice engines. | Piper, eSpeak NG, Coqui TTS adapter |
| **Sound Manager** | Play activation, listening, success, error, and thinking sounds. | WAV/OGG sound packs |

# 5\. Proposed Repository Structure

The repository should separate core interfaces, runtime orchestration, adapters, skills, configuration, assets, documentation, and tests.

| Path | Purpose |
| :---- | :---- |
| **assistant\_core/** | Core domain types, events, interfaces, lifecycle, dependency injection, and configuration loader. |
| **assistant\_core/audio/** | Audio capture, playback, device selection, buffers, and sound pack management. |
| **assistant\_core/wake/** | Wake-word interface and engine adapters. |
| **assistant\_core/stt/** | Speech-to-text interface and adapters. |
| **assistant\_core/tts/** | Text-to-speech interface and adapters. |
| **assistant\_core/intent/** | Intent router, command parser, semantic matching, fallback behavior. |
| **assistant\_core/skills/** | Skill protocol, built-in skills, skill registry, and sandboxing helpers. |
| **assistant\_core/runtime/** | Main event loop, state machine, startup/shutdown, health checks, and telemetry hooks. |
| **plugins/** | Optional user or third-party skills discovered at runtime. |
| **config/** | Default, sample, and environment-specific YAML or TOML configuration. |
| **assets/sounds/** | Sound packs for wake, listening, confirmation, error, and processing cues. |
| **models/** | Local wake-word, STT, TTS, or intent models, excluded from source control when large. |
| **tests/** | Unit, integration, hardware, fixture, and end-to-end tests. |
| **docs/** | Developer guides, plugin authoring, hardware setup, troubleshooting, and architecture decisions. |
| **scripts/** | Setup, model download, calibration, benchmark, and device diagnostic scripts. |

# 6\. Configuration and Customization

Customization is a first-class requirement. Users must be able to change behavior by editing configuration and assets rather than modifying Python source files.

* **Wake words:** Configurable engine, model path, sensitivity, threshold, activation cooldown, and alternate phrases.  
* **Sounds:** Configurable sound pack with named cues such as wake\_detected, listening\_start, listening\_stop, thinking, success, and error.  
* **Voice:** Configurable TTS engine, voice model, speaking rate, volume, and language.  
* **Speech recognition:** Configurable STT engine, model path, language, timeout, maximum utterance duration, and silence duration.  
* **Skills:** Enable or disable built-in and external skills through configuration.  
* **Privacy:** Toggle cloud adapters explicitly and default to local-only behavior where feasible.  
* **Logging:** Configure log level, log destination, redaction rules, and whether transcripts are stored.  
* **Hardware:** Select input and output devices by name or index, with diagnostic commands to list devices.

# 7\. Core Interfaces

Every interchangeable component should implement a small protocol-style interface. Interfaces should prefer typed dataclasses, clear exceptions, and dependency injection over global state.

* **AudioInput:** start(), stop(), read\_frames(), device\_info().  
* **WakeWordDetector:** load(), reset(), process\_frame(), detection\_metadata().  
* **VoiceActivityDetector:** process\_frame(), is\_speech(), should\_stop\_recording().  
* **SpeechToTextEngine:** transcribe(audio\_buffer, language, options).  
* **IntentRouter:** route(transcript, context) returning intent name, confidence, parameters, and fallback reason.  
* **Skill:** metadata(), can\_handle(intent), run(request, context), permissions().  
* **TextToSpeechEngine:** synthesize(text, voice, options) returning playable audio.  
* **SoundManager:** play(cue\_name), list\_available\_cues(), validate\_pack().  
* **RuntimeEventBus:** publish(event), subscribe(event\_type, handler), record(event).

# 8\. Runtime State Machine

The assistant should run as a simple state machine that is easy to test and reason about.

1. **Boot:** Load configuration, validate assets, initialize devices, load models, and register skills.  
2. **IdleListening:** Stream audio through the wake-word detector using minimal CPU.  
3. **Activated:** Play wake sound, publish activation event, and transition to command capture.  
4. **CapturingCommand:** Record speech until VAD detects enough silence or a maximum duration is reached.  
5. **Transcribing:** Convert captured audio to text; handle low-confidence or empty transcript cases gracefully.  
6. **RoutingIntent:** Match transcript to a skill or fallback response.  
7. **ExecutingSkill:** Run the selected skill with permissions and timeout controls.  
8. **Responding:** Generate speech, play success or error sounds, and speak response.  
9. **Recovering:** Handle exceptions, reset audio buffers, and return to IdleListening.  
10. **Shutdown:** Close devices, flush logs, and release model resources.

# 9\. Skill and Plugin System

Skills should be small, independently testable modules that declare metadata, example utterances, required permissions, configuration schema, and expected response types. The runtime should discover built-in skills and external plugins without editing the core registry.

* Each skill must expose a stable entry point and a metadata object.  
* Each skill must declare permissions such as network, filesystem\_read, filesystem\_write, shell, gpio, or home\_automation.  
* Dangerous permissions must be disabled by default and require explicit configuration.  
* Skills must return structured results instead of directly speaking, playing audio, or exiting the process.  
* Skill execution must support timeouts, cancellation, and clear error reporting.  
* Plugin discovery should support local folders and Python package entry points in a later milestone.

# 10\. Coding Agent Work Plan

Multiple coding agents may work in parallel if each agent owns a clearly bounded task, produces tests, updates documentation, and avoids cross-cutting rewrites without approval.

| Agent | Primary Mission | Deliverables |
| :---- | :---- | :---- |
| **Architecture Agent** | Define core interfaces, domain events, runtime state machine, and dependency injection pattern. | Interface modules, architecture decision records, skeleton runtime, type definitions. |
| **Audio Agent** | Implement audio capture, playback, device discovery, buffering, and sound cue playback. | AudioInput adapter, AudioOutput adapter, SoundManager, audio fixtures, diagnostics CLI. |
| **Wake Word Agent** | Implement wake-word adapter abstraction and at least one local wake-word backend. | WakeWordDetector interface implementation, model configuration, sensitivity tests. |
| **VAD and Recording Agent** | Implement speech boundary detection and command capture behavior. | VAD adapter, recording policy, timeout behavior, silence handling tests. |
| **STT Agent** | Implement transcription abstraction and first local STT backend. | SpeechToTextEngine adapter, language config, transcription fixtures, confidence handling. |
| **TTS Agent** | Implement speech synthesis abstraction and first local TTS backend. | TextToSpeechEngine adapter, voice config, response audio tests. |
| **Intent Agent** | Implement rule-based routing first, then prepare interface for semantic or model-based routing. | IntentRouter, utterance examples, confidence model, fallback handling. |
| **Skill Agent** | Build plugin protocol, registry, and initial built-in skills. | Skill interface, registry, time/date skill, echo/debug skill, plugin docs. |
| **Configuration Agent** | Design validated configuration files and customization workflow. | Config schema, defaults, sample configs, validation errors, migration notes. |
| **Testing Agent** | Build testing framework, fixtures, mocks, hardware test tags, and CI plan. | pytest setup, test matrix, fake audio streams, integration harness. |
| **Integration Agent** | Assemble the full assistant loop and verify cross-module behavior. | Main CLI, systemd sample, end-to-end smoke test, release checklist. |
| **Documentation Agent** | Create setup, customization, plugin authoring, and troubleshooting documentation. | README, docs folder, hardware guide, contributor guide, examples. |

# 11\. Shared Guidelines for All Coding Agents

* Keep modules small, typed, and independently testable.  
* Use dependency injection instead of global singletons.  
* Prefer explicit configuration over hidden defaults.  
* Never hard-code user-specific paths, wake words, devices, model names, voices, or sound files.  
* Do not introduce cloud dependencies into the default path.  
* When adding a backend, implement it behind an existing interface instead of changing the runtime loop.  
* All new features must include unit tests and at least one integration or fixture-based test when applicable.  
* Log useful lifecycle events, but avoid storing raw transcripts or audio unless explicitly configured.  
* Return structured errors with actionable messages.  
* Update relevant documentation in the same change set as code.  
* Preserve backwards-compatible configuration whenever possible.  
* Keep startup fast and memory usage modest; avoid loading heavy models until needed.

# 12\. Testing Strategy

## 12.1 Unit Testing

* Test configuration parsing, schema validation, and error messages.  
* Test each interface adapter with fake dependencies.  
* Test intent routing with example utterances and expected confidence ranges.  
* Test skills with mocked context, permissions, and timeout behavior.  
* Test state-machine transitions without real audio hardware.

## 12.2 Integration Testing

* Use recorded WAV fixtures for wake-word, speech, silence, noise, and invalid audio cases.  
* Run the assistant loop with fake audio streams and fake TTS playback.  
* Verify event ordering: wake detected, command captured, transcript produced, intent routed, skill executed, response generated.  
* Verify error recovery when STT returns empty text, a skill times out, or audio output fails.  
* Include tests for disabled skills, missing sound files, invalid model paths, and unsupported devices.

## 12.3 Hardware Testing

* Provide hardware tests marked so they do not run in standard CI by default.  
* Test microphone discovery, recording, playback, wake-word latency, and command capture on reference hardware.  
* Measure CPU, memory, startup time, wake detection latency, transcription latency, and total response latency.  
* Run noise and distance tests with a small matrix of environments: quiet room, fan noise, music background, and far-field speech.  
* Document minimum acceptable performance thresholds before release.

# 13\. Integration Plan

1. **Milestone 1: Skeleton Runtime** — repository structure, interfaces, configuration loader, event bus, fake adapters, and passing unit tests.  
2. **Milestone 2: Audio Loop** — real audio input/output, sound manager, wake-word adapter, and command capture with VAD.  
3. **Milestone 3: Local Assistant MVP** — local STT, rule-based intent router, built-in skills, local TTS, and end-to-end CLI demo.  
4. **Milestone 4: Customization Layer** — user sound packs, wake-word model configuration, voice selection, plugin discovery, and setup docs.  
5. **Milestone 5: Hardware Hardening** — systemd service, diagnostics, performance benchmarks, error recovery, and reference hardware report.  
6. **Milestone 6: Extensibility Release** — plugin authoring guide, stable skill API, semantic routing option, and packaged distribution.

# 14\. Quality, Privacy, and Reliability Requirements

* **Privacy:** Audio and transcripts remain local by default. Cloud adapters must be opt-in and clearly documented.  
* **Reliability:** The runtime must recover from transient audio, model, and skill errors without crashing the daemon.  
* **Performance:** Wake-word detection must be lightweight enough for continuous operation on the target device.  
* **Observability:** Logs must describe state transitions, timings, and errors without leaking sensitive content by default.  
* **Maintainability:** Code must be typed, formatted, linted, and organized around clear interfaces.  
* **Extensibility:** Adding a new backend or skill must not require modifying the main event loop.  
* **Accessibility:** Sound cues and spoken responses should be configurable, concise, and optional.

# 15\. Initial Technology Recommendations

These are starting recommendations, not permanent commitments. Each backend must remain replaceable through the project interfaces.

* **Language:** Python 3.11+ for modern typing and broad library support.  
* **Configuration:** YAML or TOML with schema validation.  
* **Testing:** pytest with fixture audio and hardware-specific markers.  
* **Wake word:** Start with an adapter for openWakeWord or local-wake, both of which support local wake-word workflows.  
* **STT:** Start with a local engine such as Vosk or a Whisper-family local adapter depending on hardware capability.  
* **TTS:** Start with Piper or eSpeak NG for offline-capable response speech.  
* **Packaging:** pyproject.toml with optional dependency groups for wake, stt, tts, hardware, and dev.  
* **Runtime:** CLI first, then optional systemd service configuration.

# 16\. Open Questions

* Which reference hardware should define the minimum performance target?  
* Should the MVP require full offline operation, or allow optional cloud STT/TTS adapters for early testing?  
* Should wake-word customization use trained models, a few-shot local reference approach, or both?  
* What default personality, response style, and voice should the assistant use?  
* Which built-in skills are required for the first usable release?  
* Should user transcripts ever be stored locally for debugging, and if so, how should redaction and retention work?

# 17\. Acceptance Criteria for MVP

* The assistant boots from a documented command using a sample configuration.  
* The assistant detects a configured wake word or wake-word model locally.  
* The assistant plays configurable sound cues for wake, listening, success, and error states.  
* The assistant records a command, transcribes it, routes it to at least one built-in skill, and speaks a response.  
* The assistant can run without internet after setup when local backends are configured.  
* Wake-word, STT, TTS, sounds, and skills can be changed through configuration.  
* Unit and integration tests pass in CI, with hardware tests documented separately.  
* A developer can add a new skill by following the plugin guide without editing the runtime loop.

# 18\. Agent-Specific Prompt Files

Use the following prompt files to assign focused implementation work to specialized coding agents. Each prompt should be saved as an individual Markdown file in an **agents/** or **.github/agents/** directory and paired with the relevant backlog tasks.

## 18.1 shared-guidelines.agent.md

**Role:** You are a coding agent contributing to a modular Python edge voice assistant. Your work must preserve the project goals: simple, extensible, configurable, offline-first where practical, and suitable for small physical hardware.

* Keep changes focused on the assigned task.  
* Use Python 3.11+ typing throughout.  
* Prefer dependency injection over global state.  
* Do not hard-code wake words, sounds, device names, model paths, voices, or user-specific paths.  
* Do not add cloud services to the default runtime path.  
* Place each backend behind an interface.  
* Include unit tests and fixture-based tests where practical.  
* Update documentation in the same change set.  
* Log state and timing information without storing raw audio or transcripts unless explicitly configured.  
* Return structured errors with actionable messages.  
* Preserve backwards-compatible configuration whenever possible.  
* Keep startup time, CPU use, and memory use modest.

**Before coding:** Read the development specification, relevant backlog tasks, existing interfaces, and current tests. Identify dependencies on other agents and avoid cross-cutting rewrites unless explicitly requested.

**Final response format:** Summarize changed files, tests added, tests run, known limitations, and handoff notes for dependent agents.

## 18.2 architecture-agent.md

**Mission:** Define the foundational architecture for the assistant, including core interfaces, domain types, events, dependency injection, and the skeleton runtime state machine.

* Create or refine package boundaries under assistant\_core/.  
* Define typed domain models for assistant context, requests, transcripts, intents, skill results, errors, and runtime events.  
* Define abstract contracts for audio input, audio output, wake-word detection, VAD, STT, intent routing, skills, TTS, sound management, and event publishing.  
* Implement a minimal runtime state machine with fake adapters only.  
* Document architecture decisions and extension points.  
* Add unit tests for interface assumptions, state transitions, and event publishing.

**Constraints:** Do not implement real audio, wake-word, STT, or TTS backends. Do not add heavyweight dependencies. Do not make the runtime depend on any specific hardware.

**Handoff:** Provide clear interfaces and fake implementations that other agents can build against without changing the runtime loop.

## 18.3 configuration-agent.md

**Mission:** Build the validated configuration system that makes the assistant customizable without code changes.

* Design the configuration schema for audio, wake word, VAD, STT, TTS, sounds, skills, logging, privacy, runtime, plugins, and hardware.  
* Implement loading from default files, user files, and environment overrides.  
* Validate required fields and return actionable errors.  
* Create sample configurations for development, Raspberry Pi-class hardware, and mini-PC hardware.  
* Support configuration versioning and a simple migration path.  
* Add tests for valid config, missing fields, invalid types, invalid paths, disabled skills, and override precedence.

**Constraints:** Do not require cloud credentials. Do not hard-code machine-specific paths. Do not load large models while validating configuration.

**Handoff:** Provide typed config objects and validation helpers for all backend agents.

## 18.4 audio-agent.md

**Mission:** Implement audio capture, playback, device discovery, buffering, and configurable sound cue playback for Linux edge hardware.

* Implement audio device discovery with selection by name or index.  
* Implement microphone capture that yields normalized PCM frames.  
* Implement playback for generated TTS audio and configured sound cues.  
* Build a SoundManager for wake\_detected, listening\_start, listening\_stop, thinking, success, and error cues.  
* Add diagnostics commands for listing devices, testing microphone input, and testing speaker output.  
* Add fake audio fixtures and unit tests for buffering, missing devices, missing sound files, and playback errors.

**Constraints:** Keep hardware-specific behavior isolated. Do not assume Raspberry Pi-only APIs. Do not block the runtime indefinitely on audio failures.

**Handoff:** Provide stable audio input, audio output, and sound manager implementations for wake-word, VAD, TTS, and integration agents.

## 18.5 wake-word-agent.md

**Mission:** Implement the wake-word detection layer and the first local wake-word backend behind the WakeWordDetector interface.

* Implement model loading, reset behavior, frame processing, detection metadata, threshold configuration, and cooldown behavior.  
* Support configurable wake-word model paths and sensitivity values.  
* Provide a fake detector for deterministic tests.  
* Add benchmark tooling for detection latency, CPU usage, and false positives using fixture audio.  
* Add tests for detection, non-detection, threshold behavior, cooldown behavior, invalid model paths, and backend failure recovery.

**Constraints:** Do not hard-code wake words. Do not couple directly to microphone hardware. Do not route intents or execute skills.

**Handoff:** Emit structured wake events that the runtime can consume without knowing which backend produced them.

## 18.6 vad-recording-agent.md

**Mission:** Implement voice activity detection and command recording behavior that captures user speech after wake-word activation.

* Implement the VoiceActivityDetector adapter interface.  
* Create a recording policy for max utterance duration, silence timeout, pre-roll, post-roll, and retry behavior.  
* Produce command audio buffers suitable for STT backends.  
* Support fake VAD and fake audio streams for deterministic tests.  
* Add tests for speech start, speech stop, silence-only input, max duration, noisy input, and cancellation.

**Constraints:** Do not perform transcription. Do not assume a specific wake-word backend. Do not store recorded audio unless explicitly configured.

**Handoff:** Return a typed audio buffer with timing metadata and clear errors for timeout, silence, cancellation, and device failure.

## 18.7 stt-agent.md

**Mission:** Implement the speech-to-text abstraction and the first local STT backend for transcribing captured command audio.

* Implement SpeechToTextEngine with model loading, language selection, transcription, confidence handling, and structured errors.  
* Create a fake STT engine for tests.  
* Support configurable model paths and language codes.  
* Handle empty audio, silence, low-confidence transcripts, backend failure, and unsupported language cases.  
* Add fixture-based tests using short recorded audio samples and synthetic buffers.

**Constraints:** Do not route intents. Do not speak responses. Do not store transcripts unless privacy configuration explicitly enables it.

**Handoff:** Return TranscriptResult objects containing text, confidence, language, duration, backend name, and warnings.

## 18.8 intent-agent.md

**Mission:** Implement the MVP intent routing system, starting with deterministic rule-based routing and a future-ready semantic routing interface.

* Implement IntentRouter with command patterns, aliases, parameters, confidence scoring, and fallback behavior.  
* Load intent examples from skill metadata or configuration.  
* Normalize transcripts without destroying meaningful user input.  
* Return clarification, unsupported command, or no-match results when appropriate.  
* Add tests for exact matches, aliases, parameter extraction, low-confidence matches, disabled skills, and ambiguous intents.

**Constraints:** Do not execute skills. Do not add a heavyweight model router in the MVP unless requested. Do not make routing depend on a specific STT backend.

**Handoff:** Return IntentResult objects with intent name, confidence, extracted parameters, matched skill, and fallback reason.

## 18.9 skill-agent.md

**Mission:** Build the skill protocol, registry, permission model, execution wrapper, and first built-in skills.

* Define skill metadata including name, version, description, example utterances, config schema, permissions, and response contract.  
* Implement skill registry with enable/disable support.  
* Implement permission checks for network, filesystem\_read, filesystem\_write, gpio, shell, and home\_automation.  
* Implement timeout and cancellation handling around skill execution.  
* Create initial built-in skills: time/date and echo/debug.  
* Add tests for registration, disabled skills, permission denial, timeout, structured results, and built-in skill behavior.

**Constraints:** Skills must not speak directly, play audio directly, exit the process, or mutate global runtime state. Dangerous permissions must be disabled by default.

**Handoff:** Return SkillResult objects that response generation and TTS layers can consume consistently.

## 18.10 tts-agent.md

**Mission:** Implement the text-to-speech abstraction and first offline-capable TTS backend for spoken assistant responses.

* Implement TextToSpeechEngine with voice selection, language selection, speaking rate, volume metadata, synthesis, and structured errors.  
* Create a fake TTS engine for tests.  
* Implement response audio caching for repeated short responses when enabled.  
* Handle missing voice models, unsupported languages, empty text, long text, and backend failure.  
* Add tests for synthesis calls, cache hits, cache invalidation, voice configuration, and error paths.

**Constraints:** Do not decide what the assistant should say; consume already prepared response text. Do not play audio directly unless implementing a clearly separated audio output adapter.

**Handoff:** Return synthesized audio objects or file references that the audio output layer can play.

## 18.11 testing-agent.md

**Mission:** Build the test infrastructure, fixtures, mocks, integration harness, hardware markers, and CI testing strategy for the project.

* Configure pytest, markers, fixtures, and test discovery.  
* Create fake audio streams, fake wake detector, fake VAD, fake STT, fake intent router, fake skill registry, fake TTS, and fake audio output.  
* Create an end-to-end simulation test that verifies wake, capture, transcription, routing, skill execution, response generation, synthesis, and playback order.  
* Add hardware test markers that are excluded from standard CI.  
* Create performance benchmark helpers for startup time, memory use, CPU use, wake latency, transcription latency, and total response latency.  
* Document how agents should add tests for new modules.

**Constraints:** Do not require physical hardware for default tests. Do not require internet access for default tests. Keep fixture audio small and deterministic.

**Handoff:** Provide reusable fixtures and test utilities that all other agents can import.

## 18.12 integration-agent.md

**Mission:** Assemble the full assistant loop, wire real and fake components through configuration, expose the CLI, and verify end-to-end behavior.

* Implement the main CLI entry point for running the assistant, validating configuration, listing devices, running diagnostics, and executing smoke tests.  
* Wire configuration to component factories without hard-coded backend choices.  
* Implement startup, shutdown, health checks, graceful recovery, and signal handling.  
* Verify event ordering across wake, record, transcribe, route, execute, respond, synthesize, and playback stages.  
* Add end-to-end smoke tests using fake components and optional hardware smoke tests with markers.  
* Create a sample systemd service file and release checklist.

**Constraints:** Do not bypass interfaces to call concrete backends directly. Do not let one backend failure crash the daemon without recovery. Do not make cloud services required for the default path.

**Handoff:** Provide a working MVP path that demonstrates the assistant loop and documents remaining integration gaps.

## 18.13 documentation-agent.md

**Mission:** Create clear, practical documentation for installing, configuring, customizing, extending, testing, and troubleshooting the assistant.

* Create README sections for project purpose, quick start, architecture overview, configuration, running locally, testing, and contributing.  
* Create setup guides for development machines and Raspberry Pi-class hardware.  
* Create customization guides for wake words, sounds, voices, STT, TTS, skills, logging, and privacy.  
* Create plugin authoring documentation with a minimal example skill.  
* Create troubleshooting guidance for microphone detection, speaker playback, model paths, permissions, and poor wake-word performance.  
* Keep examples consistent with current configuration schema and CLI commands.

**Constraints:** Do not document features that are not implemented unless clearly marked as planned. Avoid vendor lock-in. Keep setup paths configurable.

**Handoff:** Provide docs that help new agents and developers complete setup and contribute safely without relying on tribal knowledge.

# 19\. GitHub Issues Backlog with Agent Assignments

This backlog is designed for GitHub Issues and project boards. Each issue includes a designated owner agent, completion order, dependencies, and concurrency notes so multiple coding agents can work safely in parallel without destabilizing the core runtime.

## 19.1 Recommended Labels

* **type:architecture**, **type:config**, **type:audio**, **type:wake**, **type:vad**, **type:stt**, **type:intent**, **type:skill**, **type:tts**, **type:runtime**, **type:test**, **type:docs**, **type:release**  
* **priority:p0**, **priority:p1**, **priority:p2**  
* **status:blocked**, **status:ready**, **status:in-progress**, **status:review**  
* **needs:hardware**, **needs:model**, **needs:fixtures**, **needs:decision**  
* **agent:architecture**, **agent:configuration**, **agent:audio**, **agent:wake**, **agent:vad**, **agent:stt**, **agent:intent**, **agent:skill**, **agent:tts**, **agent:testing**, **agent:integration**, **agent:documentation**

## 19.2 Completion Waves and Concurrency Plan

| Wave | Goal | Must Finish Before | Concurrency Notes |
| :---- | :---- | :---- | :---- |
| **Wave 0** | Project decisions and issue scaffolding. | Wave 1 | Documentation and architecture agents can prepare decisions while testing agent prepares CI assumptions. |
| **Wave 1** | Repository skeleton, core types, interfaces, fake adapters, test framework, and configuration draft. | Wave 2 | Architecture, configuration, testing, and documentation agents can work concurrently once boundaries are agreed. |
| **Wave 2** | Independent subsystem implementations behind stable interfaces. | Wave 3 | Audio, wake, VAD, STT, TTS, skill, and intent agents can work in parallel using fake components and typed contracts. |
| **Wave 3** | Runtime assembly, CLI, end-to-end simulation, and customization hooks. | Wave 4 | Integration agent leads; subsystem agents fix integration gaps concurrently. |
| **Wave 4** | Hardware hardening, benchmarks, documentation completion, packaging, and release candidate. | MVP Release | Testing, documentation, audio, wake, integration, and release tasks can run in parallel after the fake end-to-end loop passes. |

## 19.3 GitHub Issue Template

**Title:** \[AREA-\#\#\#\] Short imperative title  
**Assigned Agent:** Agent name  
**Wave:** Completion wave  
**Dependencies:** Blocking issue IDs or “None”  
**Can Run Concurrently With:** Issue IDs or agent groups  
**Description:** What must be implemented and why it matters  
**Acceptance Criteria:** Checklist of observable completion requirements  
**Testing Requirements:** Unit, fixture, integration, hardware, or benchmark expectations  
**Documentation Requirements:** README, docs, comments, examples, or ADR updates  
**Definition of Done:** Typed code, tests passing, lint passing, docs updated, no hard-coded local paths, and handoff notes included

## 19.4 Ordered GitHub Issues Backlog

| Order | Issue ID | Issue Title | Assigned Agent | Dependencies | Concurrency Opportunity |
| :---- | :---- | :---- | :---- | :---- | :---- |
| **0.1** | META-001 | Confirm MVP decisions and unresolved project assumptions | Architecture Agent | None | Can run with DOC-001 and TEST-001. |
| **0.2** | DOC-001 | Create initial README outline and contribution conventions | Documentation Agent | None | Can run with META-001 and TEST-001. |
| **0.3** | TEST-001 | Define testing strategy, pytest layout, and CI assumptions | Testing Agent | None | Can run with META-001 and DOC-001. |
| **1.1** | ARCH-001 | Create repository package structure and baseline project files | Architecture Agent | META-001 | Blocks most Wave 1 tasks; keep small and merge early. |
| **1.2** | ARCH-002 | Create pyproject.toml with package metadata and dependency groups | Architecture Agent | ARCH-001 | Can run with TEST-002 after skeleton exists. |
| **1.3** | TEST-002 | Configure pytest, ruff, mypy, formatting, and pre-commit hooks | Testing Agent | ARCH-001 | Can run with ARCH-002 and DOC-002. |
| **1.4** | ARCH-003 | Define core dataclasses and runtime event types | Architecture Agent | ARCH-001 | Can run with CONF-001 if names are coordinated. |
| **1.5** | ARCH-004 | Define abstract interfaces for all replaceable components | Architecture Agent | ARCH-003 | Blocks subsystem work; merge before Wave 2\. |
| **1.6** | ARCH-005 | Implement event bus and fake component adapters | Architecture Agent | ARCH-003, ARCH-004 | Can run with TEST-003. |
| **1.7** | ARCH-006 | Implement skeleton runtime state machine with fake adapters | Architecture Agent | ARCH-005 | Can run with TEST-003 and CONF-002. |
| **1.8** | TEST-003 | Create reusable fake components and core test fixtures | Testing Agent | ARCH-004 | Can run with ARCH-005 and ARCH-006. |
| **1.9** | CONF-001 | Design typed configuration schema and defaults | Configuration Agent | ARCH-003 | Can run with ARCH-004 if config object names are coordinated. |
| **1.10** | CONF-002 | Implement config loader, validation, and environment overrides | Configuration Agent | CONF-001, TEST-002 | Can run with DOC-002 and ARCH-006. |
| **1.11** | CONF-003 | Add sample configurations for development and reference devices | Configuration Agent | CONF-002 | Can run with DOC-003. |
| **1.12** | DOC-002 | Document architecture boundaries and agent contribution workflow | Documentation Agent | ARCH-001 | Can run with TEST-002 and CONF-002. |

| Order | Issue ID | Issue Title | Assigned Agent | Dependencies | Concurrency Opportunity |
| :---- | :---- | :---- | :---- | :---- | :---- |
| **2.1** | AUDIO-001 | Implement audio device discovery and selection | Audio Agent | ARCH-004, CONF-002, TEST-003 | Can run with WAKE-001, VAD-001, STT-001, TTS-001, SKILL-001, INTENT-001. |
| **2.2** | AUDIO-002 | Implement microphone capture and PCM frame buffering | Audio Agent | AUDIO-001 | Can run with AUDIO-003 and VAD-001. |
| **2.3** | AUDIO-003 | Implement audio output playback and sound manager | Audio Agent | AUDIO-001, CONF-002 | Can run with TTS-001 and DOC-004. |
| **2.4** | WAKE-001 | Implement wake-word detector adapter shell and fake detector | Wake Word Agent | ARCH-004, CONF-002, TEST-003 | Can run with AUDIO-001 and VAD-001. |
| **2.5** | WAKE-002 | Implement first local wake-word backend adapter | Wake Word Agent | WAKE-001 | Can run with STT-002 and TTS-002 if optional dependencies remain isolated. |
| **2.6** | VAD-001 | Implement VAD interface adapter and fake VAD | VAD and Recording Agent | ARCH-004, TEST-003 | Can run with AUDIO-002 and WAKE-001. |
| **2.7** | VAD-002 | Implement command recording policy and audio buffer output | VAD and Recording Agent | VAD-001, AUDIO-002 | Can run with STT-001 using fake buffers. |
| **2.8** | STT-001 | Implement STT abstraction shell and fake STT engine | STT Agent | ARCH-004, CONF-002, TEST-003 | Can run with VAD-002 and INTENT-001. |
| **2.9** | STT-002 | Implement first local STT backend adapter | STT Agent | STT-001 | Can run with WAKE-002 and TTS-002 if dependency groups stay optional. |
| **2.10** | INTENT-001 | Implement rule-based intent router with aliases and parameters | Intent Agent | ARCH-004, SKILL-001 | Can start with fake skill metadata while Skill Agent finalizes registry. |
| **2.11** | INTENT-002 | Add confidence scoring, ambiguity handling, and fallback behavior | Intent Agent | INTENT-001 | Can run with SKILL-003. |
| **2.12** | SKILL-001 | Implement skill protocol, metadata model, and registry | Skill Agent | ARCH-004, CONF-002 | Can run with INTENT-001 after metadata shape is agreed. |
| **2.13** | SKILL-002 | Implement permission model and timeout wrapper | Skill Agent | SKILL-001 | Can run with INTENT-002. |
| **2.14** | SKILL-003 | Add initial built-in time/date and echo/debug skills | Skill Agent | SKILL-001, SKILL-002 | Can run with DOC-005. |
| **2.15** | TTS-001 | Implement TTS abstraction shell and fake TTS engine | TTS Agent | ARCH-004, CONF-002, TEST-003 | Can run with AUDIO-003. |
| **2.16** | TTS-002 | Implement first offline-capable TTS backend adapter | TTS Agent | TTS-001 | Can run with STT-002 and WAKE-002 if dependencies remain optional. |
| **2.17** | TTS-003 | Implement optional response audio caching | TTS Agent | TTS-001 | Can run with AUDIO-003 and OBS-001. |

| Order | Issue ID | Issue Title | Assigned Agent | Dependencies | Concurrency Opportunity |
| :---- | :---- | :---- | :---- | :---- | :---- |
| **3.1** | OBS-001 | Implement structured logging and redaction policy | Integration Agent | CONF-002, ARCH-005 | Can run with subsystem finishing work. |
| **3.2** | RUNTIME-001 | Wire fake end-to-end assistant loop through configuration | Integration Agent | ARCH-006, CONF-002, TEST-003, STT-001, TTS-001, WAKE-001, VAD-001, SKILL-001, INTENT-001 | Can begin before real backends are ready by using fake components. |
| **3.3** | TEST-004 | Create end-to-end fake pipeline simulation test | Testing Agent | RUNTIME-001 | Can run while real backend adapters continue. |
| **3.4** | RUNTIME-002 | Add CLI commands for run, config validation, device listing, and diagnostics | Integration Agent | RUNTIME-001, AUDIO-001, CONF-002 | Can run with DOC-006. |
| **3.5** | RUNTIME-003 | Wire real audio, wake, VAD, STT, intent, skill, TTS, and playback path | Integration Agent | RUNTIME-001, AUDIO-003, WAKE-002, VAD-002, STT-002, INTENT-002, SKILL-003, TTS-002 | Subsystem agents should remain available for integration fixes. |
| **3.6** | RUNTIME-004 | Implement graceful shutdown, recovery states, and health checks | Integration Agent | RUNTIME-001, OBS-001 | Can run with TEST-005. |
| **3.7** | TEST-005 | Add failure recovery tests for STT empty output, skill timeout, and audio failure | Testing Agent | RUNTIME-001, SKILL-002, STT-001, AUDIO-003 | Can run with RUNTIME-004. |
| **3.8** | CUSTOM-001 | Support user sound packs and validate required sound cues | Audio Agent | AUDIO-003, CONF-002 | Can run with CUSTOM-002 and CUSTOM-003. |
| **3.9** | CUSTOM-002 | Support configurable wake-word model paths and sensitivity profiles | Wake Word Agent | WAKE-002, CONF-002 | Can run with CUSTOM-001 and CUSTOM-003. |
| **3.10** | CUSTOM-003 | Support configurable TTS voices, speaking rate, and volume metadata | TTS Agent | TTS-002, CONF-002 | Can run with CUSTOM-001 and CUSTOM-002. |
| **3.11** | CUSTOM-004 | Support plugin loading from external folders | Skill Agent | SKILL-001, CONF-002 | Can run after runtime fake loop is stable. |
| **3.12** | DOC-003 | Document configuration and sample config usage | Documentation Agent | CONF-003 | Can run with runtime integration tasks. |
| **3.13** | DOC-004 | Document sound pack, wake-word, and voice customization | Documentation Agent | CUSTOM-001, CUSTOM-002, CUSTOM-003 | Can be drafted earlier and finalized after customization tests pass. |
| **3.14** | DOC-005 | Document plugin authoring with a minimal example skill | Documentation Agent | SKILL-003, CUSTOM-004 | Can run with CUSTOM-004 once plugin API is stable. |

| Order | Issue ID | Issue Title | Assigned Agent | Dependencies | Concurrency Opportunity |
| :---- | :---- | :---- | :---- | :---- | :---- |
| **4.1** | TEST-006 | Add hardware test markers and reference hardware checklist | Testing Agent | TEST-004, AUDIO-001 | Can run with DOC-006 and BENCH-001. |
| **4.2** | BENCH-001 | Add performance benchmark helpers and reporting format | Testing Agent | OBS-001, RUNTIME-001 | Can run with WAKE-003 and DOC-006. |
| **4.3** | WAKE-003 | Add wake-word benchmark script for latency and false positives | Wake Word Agent | WAKE-002, BENCH-001 | Can run with hardware validation docs. |
| **4.4** | AUDIO-004 | Add microphone and speaker diagnostic CLI tests | Audio Agent | AUDIO-003, RUNTIME-002 | Can run with TEST-006. |
| **4.5** | OBS-002 | Add runtime timing metrics for wake, transcription, skill, TTS, and total response | Integration Agent | OBS-001, RUNTIME-003 | Can run with BENCH-001. |
| **4.6** | REL-001 | Create install script and local development setup command | Integration Agent | RUNTIME-002, CONF-003 | Can run with DOC-006. |
| **4.7** | REL-002 | Create sample systemd service and daemon run instructions | Integration Agent | RUNTIME-004, REL-001 | Can run with DOC-006. |
| **4.8** | DOC-006 | Write hardware setup, diagnostics, and troubleshooting guide | Documentation Agent | AUDIO-004, TEST-006 | Can draft earlier; finalize after diagnostics commands stabilize. |
| **4.9** | DOC-007 | Write release checklist and MVP validation guide | Documentation Agent | RUNTIME-003, TEST-004, REL-001 | Can run with REL-002. |
| **4.10** | TEST-007 | Run full MVP acceptance test pass and file integration bugs | Testing Agent | RUNTIME-003, TEST-004, DOC-007 | Final validation; subsystem agents fix bugs concurrently. |
| **4.11** | REL-003 | Prepare MVP release candidate and tag checklist | Integration Agent | TEST-007, REL-002, DOC-007 | Final issue before MVP release. |

## 19.5 Suggested GitHub Project Board Columns

* **Backlog:** Approved issues not ready for implementation.  
* **Ready:** Dependencies are complete and acceptance criteria are clear.  
* **In Progress:** Assigned agent is actively implementing.  
* **Blocked:** Waiting on dependency, decision, hardware, or model asset.  
* **Review:** Implementation complete and awaiting review.  
* **Validation:** Tests, integration, documentation, or hardware checks are being verified.  
* **Done:** Merged, tested, documented, and accepted.

## 19.6 High-Value Concurrency Windows

* **After ARCH-004:** Subsystem agents can begin adapter shells using stable interfaces while the architecture agent finishes fake runtime work.  
* **After TEST-003:** Audio, wake, VAD, STT, TTS, intent, and skill agents can share common fixtures and avoid duplicating fake components.  
* **After CONF-002:** Configuration-driven customization work can proceed in parallel across audio, wake, STT, TTS, and skills.  
* **After RUNTIME-001:** Integration and testing agents can validate the full fake pipeline while real backend adapters continue independently.  
* **After RUNTIME-003:** Hardware hardening, benchmarks, release docs, diagnostics, and acceptance testing can proceed together.

## 19.7 Blocking Rules for Agents

* If an agent needs to change a shared interface, they must open or update an architecture issue before changing subsystem code.  
* If an agent adds a configuration field, they must update schema validation, sample config, tests, and documentation.  
* If an agent adds a dependency, it must be optional unless it is required by the core runtime.  
* If an agent introduces hardware-specific behavior, it must be isolated behind an adapter and covered by non-hardware tests.  
* If a task cannot be completed because of missing hardware or model assets, the agent should mark the issue blocked and provide a fake implementation or fixture path where possible.  
* If an integration task reveals a mismatch between two subsystem contracts, the integration agent should create a targeted bug issue assigned to the responsible subsystem agent instead of rewriting both components.

