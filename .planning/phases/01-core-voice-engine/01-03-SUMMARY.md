---
phase: 01-core-voice-engine
plan: 03
subsystem: TTS
tags: [piper-tts, sounddevice, local-voice]
dependency_graph:
  requires: [01-01-PLAN]
  provides: [Local TTS Capability]
  affects: [Main Voice Loop]
tech-stack:
  added: [piper-tts, sounddevice, numpy]
  patterns: [Subprocess Synthesis, NumPy PCM Buffer]
key-files:
  created:
    - C:\Users\GoldleoM\jarvis-voice-engine\models\en_US-lessac-medium.onnx
    - C:\Users\GoldleoM\jarvis-voice-engine\models\en_US-lessac-medium.onnx.json
    - C:\Users\GoldleoM\jarvis-voice-engine\tests\test_tts.py
  modified:
    - C:\Users\GoldleoM\jarvis-voice-engine\tts.py
decisions:
  - Use `piper-tts` python package for easy binary installation on Windows.
  - Use `en_US-lessac-medium` model for a balance of quality and speed.
  - Normalize PCM 16-bit audio to float32 for `sounddevice` compatibility.
metrics:
  duration: "approx 20 mins"
  completed_date: "2026-04-20"
---

# Phase 01 Plan 03: Local TTS Implementation Summary

Implemented a local text-to-speech system using Piper TTS and sounddevice for low-latency audio playback.

## Key Implementation Details
- **Synthesis**: Implemented via `subprocess` calls to the `piper.exe` binary, passing text via stdin and capturing raw PCM audio.
- **Playback**: Used `sounddevice` to play the raw PCM buffer after converting it to a normalized float32 numpy array.
- **Brevity**: Added a trimming utility to limit output to 1-2 sentences, satisfying requirement TTS-03.
- **Security**: Implemented input length limits and subprocess timeouts to prevent DoS (T-01-02).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking Issue] Missing Piper Binary and Models**
- **Found during**: Task 1
- **Issue**: `piper` executable and voice models were not present in the environment.
- **Fix**: Installed `piper-tts` via pip and downloaded the `en_US-lessac-medium` model and config from Hugging Face.
- **Files created**: `models/en_US-lessac-medium.onnx`, `models/en_US-lessac-medium.onnx.json`
- **Commit**: N/A (No git repo)

## Known Stubs
None.

## Threat Flags
None.

## Self-Check: PASSED
- [x] `tts.py` implemented and verified
- [x] `test_tts.py` passes
- [x] Piper binary and models installed
- [x] Audio playback functional
