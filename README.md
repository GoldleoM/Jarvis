# Jarvis Voice Engine

A low-latency, locally-run voice assistant inspired by Tony Stark's J.A.R.V.I.S. Built with Python, faster-whisper, Piper TTS, and a custom semantic routing engine.

## Architecture

```
Microphone → Silero VAD → Wake Word Detection → faster-whisper STT
                                                      │
                                                      ▼
                                             Semantic Router (Gatekeeper)
                                           ┌──────────────┼──────────────┐
                                           ▼              ▼              ▼
                                     Local Skills    OpenCode LLM    Confirmation
                                     (app/system)    (Gemma 4-31B)   (timers, etc.)
                                           │              │
                                           ▼              ▼
                                        Piper TTS ←──────┘
```

## Features

- Wake word detection ("Jarvis") with 0.85 confidence threshold
- Voice Activity Detection via Silero VAD
- Speech-to-text using faster-whisper medium.en on CUDA (float16)
- Text-to-speech using Piper TTS with British English (Alba) voice
- Semantic routing for local commands (apps, system control, timers, WhatsApp)
- Integration with OpenCode LLM agent for complex/coding tasks
- System tray support (PySide6 UI mode)
- Notes mode for dictation
- Confirmation flow for destructive actions (shutdown, restart, sleep)

## Tech Stack

| Layer | Technology |
|---|---|
| Speech-to-Text | faster-whisper (medium.en) |
| Voice Activity Detection | Silero VAD |
| Wake Word | Custom keyword spotting (0.85 threshold) |
| Text-to-Speech | Piper TTS (en_GB-alba-medium) |
| Intent Routing | Custom semantic Gatekeeper |
| LLM Agent | OpenCode / Gemma 4-31B-it |
| Audio | sounddevice, numpy |
| UI (optional) | PySide6 (Qt 6) |
| GPU | CUDA + float16 inference |

## Requirements

- Python 3.10+
- CUDA-capable GPU (recommiouend for real-time inference)
- Piper TTS executable (download from rhasspy/piper releases on GitHub)
- Microphone

## Setup

1. Clone the repo and install dependencies:

```bash
pip install -r requirements.txt
```

2. Download a Piper voice model (.onnx + .json) from Hugging Face (e.g., rhasspy/piper-voices) and place it in the `models/` directory.

3. Download the Piper TTS executable from the releases page and set its path in `config.py` under `PIPER_PATH`.

4. Run:

```bash
python main.py
```

For debug mode:

```bash
python main.py --debug
```

## Configuration

All settings live in `config.py`:

- `WHISPER_MODEL` - Model size (medium.en recommended)
- `WHISPER_DEVICE` - cuda or cpu
- `PIPER_MODEL` - Path to Piper voice model (.onnx)
- `WAKE_WORD` - Activation phrase (default: "jarvis")
- `VAD_THRESHOLD` - Sensitivity (0.5 default)
- `MIC_INDEX` - Microphone device index

## UI Mode

A desktop UI built with PySide6 is available under `jarvis_ui.py` and the `ui/` directory. It features:

- System tray icon for background listening
- Real-time VU meter visualization
- Chat panel with conversation history
- Dark glassmorphism theme
- Always-on-top compact mode

## Project Structure

```
├── main.py              # Voice engine core loop
├── config.py            # Configuration
├── stt.py               # Speech-to-text (faster-whisper)
├── tts.py               # Text-to-speech (Piper)
├── router.py            # Semantic command router
├── agent_runner.py      # OpenCode LLM integration
├── skills/
│   ├── app_skills.py    # Application automation
│   └── system_skills.py # System control
├── jarvis_ui.py         # PySide6 desktop UI
├── ui/                  # UI assets
├── models/              # TTS voice models
└── tests/               # Test suite
```
