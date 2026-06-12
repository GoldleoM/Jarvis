# Jarvis Voice Interface

## What This Is
A real-time, local-first voice interface (STT + TTS) for the OpenCode-based Jarvis system. It allows for hands-free interaction with the AI using low-latency speech-to-text and text-to-speech.

## Core Value
A seamless, low-latency local voice loop that allows Aaron to interact with Jarvis hands-free.

## Requirements

### Validated
(None yet — ship to validate)

### Active
- [ ] **STT-01**: Continuous listening from microphone using `faster-whisper`.
- [ ] **STT-02**: Low-latency transcription with silence detection (VAD).
- [ ] **STT-03**: Optional wake word ("Jarvis") support.
- [ ] **PROC-01**: Integration with `send_to_opencode(text: string)`.
- [ ] **TTS-01**: Local text-to-speech using `Piper TTS`.
- [ ] **TTS-02**: Immediate audio playback of AI responses.
- [ ] **FLOW-01**: Real-time loop: listen -> transcribe -> send -> receive -> speak.
- [ ] **SAFE-01**: "stop" command to interrupt speaking.
- [ ] **SAFE-02**: Confirmation layer for risky system actions.
- [ ] **PERF-01**: Total round-trip latency < 2 seconds.
- [ ] **CODE-01**: Modular Python implementation (stt.py, tts.py, main.py).

### Out of Scope
- UI/Frontend (CLI/Headless only).
- Web frameworks.
- Cloud-based STT/TTS dependencies.

## Context
- Built for the OpenCode-based Jarvis system.
- Local-first requirement to ensure privacy and speed.
- Python-based implementation.

## Constraints
- **Tech Stack**: `faster-whisper` for STT, `Piper` for TTS.
- **Performance**: Must feel real-time (< 2s latency).
- **Dependencies**: Minimal, local-only.

## Key Decisions
| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Local-First | Privacy and latency | ✓ Locked |
| faster-whisper | Best-in-class local STT | ✓ Locked |
| Piper TTS | Fast, high-quality local TTS | ✓ Locked |

---
*Last updated: 2026-04-19 after initialization*
