import unittest
import numpy as np
from stt import SpeechToText

class TestSpeechToText(unittest.TestCase):
    def setUp(self):
        self.stt = SpeechToText()

    def test_vad_is_speech_silence(self):
        audio_chunk = np.zeros(512, dtype=np.float32)
        self.assertFalse(self.stt.is_speech(audio_chunk))

    def test_vad_rejects_background_noise(self):
        rng = np.random.default_rng(42)
        audio_chunk = rng.uniform(-0.05, 0.05, 512).astype(np.float32)
        self.assertFalse(self.stt.is_speech(audio_chunk))

    def test_detect_and_transcribe_spoken_command(self):
        from scipy.signal import resample_poly
        from tts import TextToSpeech

        voice = TextToSpeech()
        raw = voice.synthesize("Jarvis, what time is it?")
        self.assertTrue(raw, "Piper must produce speech for this integration test")
        samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768
        speech = resample_poly(samples, self.stt.sample_rate, voice.sample_rate)
        frames = speech[:len(speech) // 512 * 512].reshape(-1, 512)
        self.assertTrue(any(self.stt.is_speech(frame) for frame in frames))
        self.assertIn("time", self.stt.transcribe(speech).lower())

    def test_transcribe_buffer(self):
        # Create a dummy audio buffer (1 second of silence at 16kHz)
        audio_buffer = np.zeros(16000, dtype=np.float32)
        # This should return a string (possibly empty)
        result = self.stt.transcribe(audio_buffer)
        self.assertIsInstance(result, str)

if __name__ == "__main__":
    unittest.main()
