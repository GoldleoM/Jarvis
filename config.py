"""
Configuration for the Jarvis Voice Assistant
"""

# ---------- AUDIO ----------
MIC_INDEX = 1
SAMPLE_RATE = 16000
CHUNK_SIZE = 512


# ---------- VAD ----------
VAD_ENGINE = "silero"
VAD_SAMPLING_RATE = 16000
VAD_THRESHOLD = 0.5


# ---------- WAKE WORD ----------
WAKE_WORD = "jarvis"
WAKE_WORD_CONFIDENCE_THRESHOLD = 0.85


# ---------- WHISPER ----------
WHISPER_MODEL = "medium.en"
WHISPER_DEVICE = "cuda"
WHISPER_COMPUTE_TYPE = "float16" # Using full float16 precision for maximum accuracy


# ---------- TTS ----------
TTS_ENGINE = "piper"

# 🔥 ADD THIS (you were missing it)
PIPER_PATH = r"C:\Users\GoldleoM\AppData\Roaming\Python\Python310\Scripts\piper.exe"

# 🔥 FIX NAME (match your TTS code)
PIPER_MODEL = r"models\en_GB-alba-medium.onnx"

# Optional (future)
AUDIO_OUTPUT_DEVICE = 2


# ---------- OPTIONAL CLOUD ----------
ELEVENLABS_API_KEY = "your_api_key_here"


# ---------- SYSTEM ----------
LOG_LEVEL = "INFO"
SHUTDOWN_COMMANDS = ["exit", "stop", "quit", "goodbye"]