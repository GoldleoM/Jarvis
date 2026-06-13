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
WHISPER_MODEL = "small.en"
WHISPER_DEVICE = "cuda"
WHISPER_COMPUTE_TYPE = "int8_float16" # Low power mode: reduced precision, much less GPU usage


# ---------- TTS ----------
TTS_ENGINE = "kokoro"  # "piper" or "kokoro"

# -- Piper (fallback) --
PIPER_PATH = r"C:\Users\GoldleoM\AppData\Roaming\Python\Python310\Scripts\piper.exe"
PIPER_MODEL = r"models\en_GB-alan-low.onnx"

# -- Kokoro (lightning fast) --
KOKORO_LANG_CODE = "b"      # 'b' = British English, 'a' = American English
KOKORO_VOICE = "bm_lewis"    # bm_lewis (British male) | bf_emma (British female)
                              # bf_isabella | bm_george

AUDIO_OUTPUT_DEVICE = 2


# ---------- OPTIONAL CLOUD ----------
ELEVENLABS_API_KEY = "your_api_key_here"


# ---------- SYSTEM ----------
LOG_LEVEL = "INFO"
SHUTDOWN_COMMANDS = ["exit", "stop", "quit", "goodbye"]
