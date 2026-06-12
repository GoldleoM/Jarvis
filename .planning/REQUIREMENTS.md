# Requirements: Jarvis Voice Interface

**Defined:** 2026-04-19
**Core Value:** A seamless, low-latency local voice loop that allows Aaron to interact with Jarvis hands-free.

## v1 Requirements

### Speech-to-Text (STT)
- [x] **STT-01**: Use `faster-whisper` for local transcription.
- [x] **STT-02**: Continuously listen from microphone.
- [x] **STT-03**: Implement silence detection (VAD) to trigger processing.
- [ ] **STT-04**: Support wake word ("Jarvis") to start listening.

### Processing
- [ ] **PROC-01**: Send transcribed text to `send_to_opencode(text: string)`.
- [ ] **PROC-02**: Handle AI response string for TTS input.

### Text-to-Speech (TTS)
- [x] **TTS-01**: Use `Piper TTS` for local synthesis.
- [x] **TTS-02**: Play audio immediately after response is received.
- [x] **TTS-03**: Limit responses to 1-2 sentences for voice brevity.

### Control Flow & Performance
- [ ] **FLOW-01**: Implement async loop: listen -> transcribe -> send -> receive -> speak.
- [ ] **PERF-01**: Total round-trip latency < 2 seconds.
- [ ] **PERF-02**: Use threading/async to prevent blocking during I/O.

### Safety & UX
- [ ] **SAFE-01**: Implement "stop" command to cancel current speaking.
- [ ] **SAFE-02**: Add confirmation layer for risky system actions.
- [ ] **SAFE-03**: Implement debounce to avoid repeated triggering.

### Code Quality
- [ ] **CODE-01**: Modular Python structure (`stt.py`, `tts.py`, `main.py`).
- [ ] **CODE-02**: Minimal dependencies, no web frameworks.

## v2 Requirements
- **STT-05**: Streaming transcription (partial results).
- **LOG-01**: Basic logging of all voice commands.

## Out of Scope
| Feature | Reason |
|---------|--------|
| GUI | Not required for a voice interface |
| Cloud APIs | Violates local-first requirement |

## Traceability
| Requirement | Phase | Status |
|-------------|-------|--------|
| STT-01 to 04 | Phase 1 | Pending |
| TTS-01 to 03 | Phase 1 | Pending |
| CODE-01 to 02 | Phase 1 | Pending |
| PROC-01 to 02 | Phase 2 | Pending |
| FLOW-01 | Phase 2 | Pending |
| PERF-01 to 02 | Phase 2 | Pending |
| SAFE-01 to 03 | Phase 3 | Pending |

---
*Requirements defined: 2026-04-19*
*Last updated: 2026-04-19 after initial definition*
