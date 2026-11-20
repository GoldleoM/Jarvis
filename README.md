# Jarvis Voice Engine

A low-latency, locally-run voice assistant inspired by Tony Stark's J.A.R.V.I.S. Built with Python, faster-whisper, Piper TTS, and a custom semantic routing engine.

On a configured Windows machine, double-click **Jarvis.exe** in the project folder. The orb and tray appear while the voice models load. When the status reads **ONLINE**, type a command and press Enter, or say “Jarvis, what time is it?”

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
- Automatic app scanning and discovery (app_scanner.py)
- WiFi radio toggle (on/off via Windows Runtime API)
- System tray support (PySide6 UI mode) with chat panel and VU meter
- Notes mode for dictation with automatic file saving
- Confirmation flow for destructive actions (shutdown, restart, sleep)
- Persistent memory for user preferences and context

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
- CUDA-capable GPU (recommended for real-time inference)
- Piper TTS and the configured voice model
- Microphone

## Setup

1. Clone the repo and install dependencies:

```bash
pip install -r requirements.txt
```

2. Download a Piper voice model (.onnx + .json) from Hugging Face (e.g., rhasspy/piper-voices) and place it in the `models/` directory.

3. The Python dependencies install the Piper command. If using a separate Piper installation, set `PIPER_PATH` in `config.py` to its executable. The default voice expects `models/en_GB-alba-medium.onnx` and `models/en_GB-alba-medium.onnx.json`. Allow the speech recognizer and semantic router to download their models on first use.

4. Launch **Jarvis.exe** for the desktop interface. For the console entry point, run

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

`Jarvis.exe` opens the PySide6 interface using your installed Python environment, local models, and settings. Keep the executable alongside `jarvis_ui.py` and `ui/`. Create a Windows shortcut if you want to launch it from the desktop. The launcher looks for dependencies in the project's `.venv` or `venv`, the active Conda environment, Python installations on PATH, and registered Conda environments.

Use **Alt+Space** to hide or show the overlay. The tray menu also offers **Show UI**, **View Logs**, **Restart Jarvis**, and **Quit Jarvis**. Use the gear button to select or test the microphone. For OpenCode-backed replies, install and configure OpenCode locally.

To start the same UI from a terminal, run `python jarvis_ui.py`. To rebuild the checked-in executable, run `.\launcher\build.ps1` in PowerShell on Windows.

Run the speech and synthesis tests with `python -m unittest discover -s tests -v`. For the desktop integration test, install `websocket-client` in the test environment, close other Jarvis instances, and run `python tests/windows_launch_smoke.py`. It opens the real executable, tests the microphone, sends a time request, checks history, and quits.

## Project Structure

```
├── main.py              # Voice engine core loop
├── config.py            # Configuration
├── stt.py               # Speech-to-text (faster-whisper)
├── tts.py               # Text-to-speech (Piper)
├── router.py            # Semantic command router
├── agent_runner.py      # OpenCode LLM integration
├── app_scanner.py       # Automatic app discovery
├── jarvis_ui.py         # PySide6 desktop UI
├── toggle_wifi.ps1      # WiFi radio toggle script
├── skills/
│   ├── app_skills.py    # Application automation
│   └── system_skills.py # System control
├── ui/                  # UI assets (HTML, JS, CSS)
├── models/              # TTS voice models (.onnx)
├── jarvis_notes/        # Saved dictation notes
└── tests/               # Test suite
```
