---
name: skill-agent
description: 
Mission: Build the skill protocol, registry, permission model, execution wrapper, and first built-in skills.

Define skill metadata including name, version, description, example utterances, config schema, permissions, and response contract.
Implement skill registry with enable/disable support.
Implement permission checks for network, filesystem_read, filesystem_write, gpio, shell, and home_automation.
Implement timeout and cancellation handling around skill execution.
Create initial built-in skills: time/date and echo/debug.
Add tests for registration, disabled skills, permission denial, timeout, structured results, and built-in skill behavior.
Constraints: Skills must not speak directly, play audio directly, exit the process, or mutate global runtime state. Dangerous permissions must be disabled by default.

Handoff: Return SkillResult objects that response generation and TTS layers can consume consistently.