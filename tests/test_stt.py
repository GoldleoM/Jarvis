import unittest
import numpy as np
from stt import SpeechToText

class TestSpeechToText(unittest.TestCase):
    def setUp(self):
        self.stt = SpeechToText()

    def test_vad_is_speech_silence(self):
        audio_chunk = np.zeros(512, dtype=np.float32)
        self.assertFalse(self.stt.is_speech(audio_chunk))

    def test_vad_is_speech_noise(self):
        audio_chunk = np.random.uniform(-1, 1, 512).astype(np.float32)
        self.assertTrue(self.stt.is_speech(audio_chunk))

    def test_transcribe_buffer(self):
        # Create a dummy audio buffer (1 second of silence at 16kHz)
        audio_buffer = np.zeros(16000, dtype=np.float32)
        # This should return a string (possibly empty)
        result = self.stt.transcribe(audio_buffer)
        self.assertIsInstance(result, str)

if __name__ == "__main__":
    unittest.main()
