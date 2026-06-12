---
status: testing
phase: 01-core-voice-engine
source: [01-01-SUMMARY.md, 01-02-SUMMARY.md, 01-03-SUMMARY.md, 01-04-SUMMARY.md, 01-05-SUMMARY.md]
started: 2026-04-20T16:00:00Z
updated: 2026-04-20T19:15:00Z
---

## Current Test

number: 3
name: VAD Stability
expected: |
  Test in an environment with background noise. No false-positive transcriptions or "ghost" words.
awaiting: user response

## Tests

### 1. Cold Start Smoke Test
expected: System boots without errors and reaches listening state from a fresh start.
result: pass

### 2. End-to-End Voice Loop
expected: Say "Jarvis, hello". System activates, transcribes "hello", and responds via speakers.
result: pass

### 3. VAD Stability
expected: Test in an environment with background noise. No false-positive transcriptions or "ghost" words.
result: issue
reported: "many ghost words and wrong transcription even with nvidia broadcast noise removal when spoken in low voice or mumbling kind of. Also, after wake-word detection, volume seems to drop and transcription becomes inaccurate."
severity: major

### 4. TTS Quality & Brevity
expected: Responses are audible, clear, and limited to 1-2 sentences (no rambling).
result: issue
reported: "responses are audible clear and limited but a cut sound before starting and in the end cuts the word in last"
severity: minor

### 5. Exit Command
expected: Say "Jarvis, exit". System prints "Shutting down Jarvis...", speaks the goodbye message, and terminates the process.
result: pass

## Summary

total: 5
passed: 3
issues: 2
pending: 0
skipped: 0

## Gaps

- truth: "Test in an environment with background noise. No false-positive transcriptions or 'ghost' words."
  status: failed
  reason: "User reported: many ghost words and wrong transcription even with nvidia broadcast noise removal when spoken in low voice or mumbling kind of. Also, after wake-word detection, volume seems to drop and transcription becomes inaccurate."
  severity: major
  test: 3
  root_cause: "Overly sensitive VAD trigger combined with mandatory audio normalization boosts low-level noise to full scale, causing Whisper to hallucinate 'ghost words'."
  artifacts:
    - path: "stt.py"
      issue: "RMS fallback threshold (0.01) too low; mandatory normalization in transcribe()"
  missing:
    - "Increase RMS threshold in is_speech"
    - "Increase REQUIRED_SPEECH_FRAMES"
    - "Make normalization conditional on peak volume"
  debug_session: .planning/debug/vad-stability.md

- truth: "Responses are audible, clear, and limited to 1-2 sentences (no rambling)."
  status: failed
  reason: "User reported: responses are audible clear and limited but a cut sound before starting and in the end cuts the word in last"
  severity: minor
  test: 4
  root_cause: "Raw PCM audio played without boundary padding or amplitude envelopes, causing DC offset pops at start and driver-level truncation at end."
  artifacts:
    - path: "tts.py"
      issue: "sd.play() called on raw array without silence padding or fade-in/out"
  missing:
    - "Prepend/append 100ms silence to audio buffer"
    - "Apply short linear fade-in/out to eliminate pops"
  debug_session: .planning/debug/tts-clipping.md
