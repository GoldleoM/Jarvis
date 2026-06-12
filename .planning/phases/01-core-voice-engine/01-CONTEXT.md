# Phase 01: Core Voice Engine - Context

**Gathered:** 2026-04-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Establish the fundamental local audio pipeline. This includes capturing audio from the microphone, detecting speech boundaries (VAD), transcribing speech to text using `faster-whisper`, and synthesizing text to speech using `Piper TTS`. This phase focuses on the "engine" components; the high-level interaction loop and safety layers are handled in subsequent phases.
</domain>

<decisions>
## Implementation Decisions

### Voice Activity Detection (VAD)
- **D-01**: Use **Silero VAD** for speech boundary detection. It provides the best balance of accuracy and latency for local Python implementations.

### Concurrency Model
- **D-02**: Use **`asyncio` combined with `ThreadPoolExecutor`**. This allows the audio capture loop to remain non-blocking while offloading the CPU-intensive transcription and synthesis tasks to worker threads.

### Audio Buffering
- **D-03**: Implement a **`queue.Queue` based producer-consumer pattern**. The microphone thread will produce audio chunks, and the transcription thread will consume them, preventing frame loss during processing spikes.

### Wake Word Implementation
- **D-04**: Use **keyword matching on the first transcription chunk**. For v1, we will avoid a separate wake-word engine and instead check for "Jarvis" in the initial `faster-whisper` output to trigger the full interaction.

### Audio Playback
- **D-05**: Use the **`sounddevice` library** for low-latency audio output of Piper TTS streams.

### the agent's Discretion
- Exact buffer sizes for audio chunks.
- Specific `faster-whisper` model size (e.g., `base` vs `small`) based on hardware detection.
- Piper voice selection (defaulting to a clear, professional male voice).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### STT & VAD
- `https://github.com/SYSTRAN/faster-whisper` — Official documentation for the transcription engine.
- `https://github.com/snypr/silero-vad` — Documentation for the VAD model.

### TTS
- `https://github.com/rhasspy/piper` — Official documentation for the Piper TTS engine.

### Project Specs
- `.planning/PROJECT.md` — Core value and constraints.
- `.planning/REQUIREMENTS.md` — Specific STT/TTS requirements.
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- None. This is a greenfield implementation of the voice engine.

### Established Patterns
- Modular Python structure as requested in REQUIREMENTS.md (`stt.py`, `tts.py`, `main.py`).

### Integration Points
- The output of `stt.py` will eventually feed into `send_to_opencode()`.
- The output of `tts.py` will be sent to the system audio device.
</code_context>

<specifics>
## Specific Ideas

- "Keep it simple, fast, and local-first."
- Prioritize latency over absolute transcription perfection.
</specifics>

<deferred>
## Deferred Ideas

- Streaming transcription (partial results) — Deferred to v2.
- Advanced wake-word engines (e.g., Porcupine) — Deferred to v2.

---

*Phase: 01-core-voice-engine*
*Context gathered: 2026-04-19*
