---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: Executing Phase 01
last_updated: "2026-04-20T19:15:00.000Z"
progress:
  total_phases: 1
  completed_phases: 0
  total_plans: 7
  completed_plans: 6
  percent: 86
---

# Project State: Jarvis Voice Interface

## Project Reference

**Core Value**: A seamless, low-latency local voice loop that allows Aaron to interact with Jarvis hands-free.
**Current Focus**: Roadmapping and Phase 1 Implementation.

## Current Position

Phase: 01 (core-voice-engine) — EXECUTING
Plan: 6 of 7
**Phase**: 1 (Core Voice Engine)
**Plan**: 06
**Status**: Completed
**Progress**: [------------------] 86%

## Performance Metrics

- **Round-trip Latency**: Target < 2s | Current: N/A
- **Transcription Accuracy**: Target High | Current: N/A

## Accumulated Context

### Decisions

- Local-first architecture using `faster-whisper` and `Piper TTS` for privacy and speed.
- Headless/CLI implementation to prioritize latency over UI.
- [Phase 01]: Implemented energy-based VAD as fallback due to Silero VAD loading timeouts
- [Phase 01-core-voice-engine]: Use piper-tts python package for binary installation on Windows
- [Phase 01-core-voice-engine]: Use en_US-lessac-medium model for balance of quality and speed
- [Phase 01-core-voice-engine]: Use asyncio.Queue to bridge the threaded STT callback with the async main loop.
- [Phase 01-core-voice-engine]: Use run_in_executor for tts.speak to prevent blocking the voice engine during audio playback.
- [Phase 01-core-voice-engine]: Implement wake-word detection by scanning for 'jarvis' and optionally extracting the command from the same utterance.
- [Phase 01-core-voice-engine]: Increased RMS VAD fallback to 0.03 to reduce noise triggers.
- [Phase 01-core-voice-engine]: Increased REQUIRED_SPEECH_FRAMES to 5 for more stable recording start.
- [Phase 01-core-voice-engine]: Implemented conditional normalization (threshold 0.5) to prevent boosting low-level noise into ghost words.

### Todos

- [x] Initialize Python environment and install dependencies.
- [x] Implement `stt.py` with `faster-whisper`.
- [x] Implement `tts.py` with `Piper`.

### Blockers

- None.

## Session Continuity

**Last Session**: Completed 01-core-voice-engine-06-PLAN.md
**Next Step**: Execute plan 01-07 to fix TTS quality (clipping/pops).
