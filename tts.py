import subprocess
import numpy as np
import sounddevice as sd
import threading
import config
import re


class TextToSpeech:
    def __init__(self):
        self.piper_exe = config.PIPER_PATH
        self.model_path = config.PIPER_MODEL
        self.sample_rate = 22050
        self.lock = threading.Lock()

    def _sanitize_text(self, text):
        text = text.replace('\u2013', ' to ').replace('\u2014', ', ')
        text = re.sub(r'\|?\s*(:?-+:?\s*\|)+\s*', ' ', text)
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
        text = re.sub(r'[*#_]', '', text)
        text = text.replace('|', ', ')
        sanitized = text.encode('ascii', 'ignore').decode()
        sanitized = re.sub(r'\s+', ' ', sanitized)
        sanitized = re.sub(r',\s*(?=,)', '', sanitized)
        sanitized = re.sub(r'\s+,\s+', ', ', sanitized)
        return sanitized[:2000].strip(', ')

    def synthesize(self, text):
        if not text:
            return b""
        text = self._sanitize_text(text)
        try:
            process = subprocess.Popen(
                [self.piper_exe, "--model", self.model_path, "--output_raw"],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=False, creationflags=subprocess.CREATE_NO_WINDOW
            )
            stdout, stderr = process.communicate(input=text.encode("utf-8"), timeout=10)
            if process.returncode != 0:
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
                audio = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
                silence = np.zeros(int(self.sample_rate * 0.1), dtype=np.float32)
                audio = np.concatenate([silence, audio, silence])
                sd.stop()
                sd.play(audio, self.sample_rate)
                sd.wait()
            except Exception as e:
                print(f"Playback failed: {e}")

    def stop(self):
        try:
            sd.stop()
        except:
            pass
