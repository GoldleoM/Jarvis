import subprocess
import numpy as np
import sounddevice as sd
import threading
import config


class TextToSpeech:
    def __init__(self):
        self.piper_exe = config.PIPER_PATH
        self.model_path = config.PIPER_MODEL
        self.sample_rate = 22050
        self.max_text_length = 500

        self.lock = threading.Lock()

    def _sanitize_text(self, text):
        # Remove emojis and non-ascii characters to prevent Piper/espeak Unicode crashes
        sanitized = text.encode('ascii', 'ignore').decode()
        return sanitized[:2000]

    def synthesize(self, text):
        if not text:
            return b""

        text = self._sanitize_text(text)

        try:
            process = subprocess.Popen(
                [self.piper_exe, "--model", self.model_path, "--output_raw"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=False,
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            stdout, stderr = process.communicate(
                input=text.encode("utf-8"),
                timeout=10
            )

            if process.returncode != 0:
                print(f"Piper Error: {stderr.decode()}")
                return b""

            return stdout

        except subprocess.TimeoutExpired:
            process.kill()
            return b""
        except Exception as e:
            print(f"Synthesis failed: {e}")
            return b""

    def speak(self, text):
        with self.lock:
            audio_bytes = self.synthesize(text)

            if not audio_bytes:
                return

            try:
                audio = np.frombuffer(audio_bytes, dtype=np.int16)
                audio = audio.astype(np.float32) / 32768.0

                # Silence padding
                silence_len = int(self.sample_rate * 0.1)
                silence = np.zeros(silence_len, dtype=np.float32)
                audio = np.concatenate([silence, audio, silence])

                # Fade
                fade_len = int(self.sample_rate * 0.01)
                fade_len = min(fade_len, len(audio)//2)

                fade_in = np.linspace(0, 1, fade_len)
                fade_out = np.linspace(1, 0, fade_len)

                audio[:fade_len] *= fade_in
                audio[-fade_len:] *= fade_out

                sd.stop()  # interrupt previous audio
                sd.play(audio, self.sample_rate)
                sd.wait()

            except Exception as e:
                print(f"Playback failed: {e}")