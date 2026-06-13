import os
import numpy as np
import sounddevice as sd
import threading
import config
import re
import io
import wave

# Point to espeak-ng for Kokoro's phonemizer
os.environ['PHONEMIZER_ESPEAK_LIBRARY'] = os.path.join(
    os.environ.get('APPDATA', ''),
    'eSpeak NG',
    'libespeak-ng.dll'
)

import warnings
from kokoro import KPipeline


class TextToSpeech:
    def __init__(self):
        lang_code = getattr(config, 'KOKORO_LANG_CODE', 'b')
        self.voice = getattr(config, 'KOKORO_VOICE', 'bm_lewis')
        self.sample_rate = 24000
        self.lock = threading.Lock()
        self._pipeline = None

    @property
    def pipeline(self):
        if self._pipeline is None:
            lang_code = getattr(config, 'KOKORO_LANG_CODE', 'b')
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                self._pipeline = KPipeline(lang_code=lang_code, repo_id='hexgrad/Kokoro-82M')
        return self._pipeline

    def _sanitize_text(self, text):
        text = text.replace('\u2013', ' to ').replace('\u2014', ', ')
        text = re.sub(r'\|?\s*(:?-+:?\s*\|)+\s*', ' ', text)
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
        text = re.sub(r'[*#_]', '', text)
        text = text.replace('|', ', ')
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r',\s*(?=,)', '', text)
        text = re.sub(r'\s+,\s+', ', ', text)
        return text.strip()[:2000].strip(', ')

    def synthesize(self, text):
        if not text:
            return b""
        text = self._sanitize_text(text)
        try:
            audio_chunks = []
            gen = self.pipeline(text, voice=self.voice, speed=1.0)
            for _, _, audio in gen:
                audio_chunks.append(audio)
            if not audio_chunks:
                return b""
            full_audio = np.concatenate(audio_chunks)
            int16_audio = (full_audio * 32767).astype(np.int16)
            buf = io.BytesIO()
            with wave.open(buf, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(self.sample_rate)
                wf.writeframes(int16_audio.tobytes())
            return buf.getvalue()
        except Exception as e:
            print(f"Kokoro synthesis failed: {e}")
            return b""

    def speak(self, text):
        with self.lock:
            audio_bytes = self.synthesize(text)
            if not audio_bytes:
                return
            try:
                with wave.open(io.BytesIO(audio_bytes), 'rb') as wf:
                    audio = np.frombuffer(wf.readframes(-1), dtype=np.int16).astype(np.float32) / 32768.0
                silence = np.zeros(int(self.sample_rate * 0.1), dtype=np.float32)
                audio = np.concatenate([silence, audio, silence])
                sd.stop()
                sd.play(audio, self.sample_rate)
                sd.wait()
            except Exception as e:
                print(f"Kokoro playback failed: {e}")

    def stop(self):
        try:
            sd.stop()
        except:
            pass
