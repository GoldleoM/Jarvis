---
phase: 01-core-voice-engine
plan: 06
subsystem: STT
tags: [VAD, noise-reduction, anti-hallucination]
dependency_graph:
  requires: [01-05]
  provides: [VAD-stability]
  affects: [stt.py]
tech_stack:
  added: []
  patterns: [Conditional Normalization]
key_files:
  - stt.py
decisions:
  - "Increased RMS VAD fallback to 0.03 to reduce noise triggers"
  - "Increased REQUIRED_SPEECH_FRAMES to 5 for more stable recording start"
  - "Implemented conditional normalization (threshold 0.5) to prevent boosting low-level noise into ghost words"
metrics:
  duration: "15 minutes"
  completed_date: "2026-04-20"
---

# Phase 01 Plan 06: VAD Stability Summary

Eliminated "ghost words" and false-positive transcriptions by tuning VAD sensitivity and implementing conditional audio normalization.

## Changes

### 1. VAD Threshold Tuning
- **RMS Fallback**: Increased from `0.01` to `0.03` in `is_speech()`. This prevents low-level ambient noise from being flagged as speech.
- **Trigger Stability**: Increased `REQUIRED_SPEECH_FRAMES` from `2` to `5` in the consumer loop. This requires a longer continuous block of speech (~150ms) before the recording actually starts, filtering out transient pops and clicks.

### 2. Conditional Normalization
- **Logic**: Replaced mandatory normalization in `transcribe()` with a check: `if peak < 0.5: normalize()`.
- **Effect**: When the user speaks clearly, the original gain is preserved. When the user speaks quietly, it is boosted to a usable level. Most importantly, low-level noise that manages to trigger the VAD is no longer boosted to full scale, which was the primary cause of Whisper hallucinations ("ghost words").

## Deviations from Plan

None - plan executed exactly as written.

## Self-Check: PASSED
- [x] RMS threshold updated to 0.03
- [x] REQUIRED_SPEECH_FRAMES updated to 5
- [x] Normalization made conditional in transcribe()
- [x] stt.py modified and verified
