import unittest
import os
from tts import TextToSpeech

class TestTextToSpeech(unittest.TestCase):
    def setUp(self):
        self.tts = TextToSpeech()

    def test_synthesize_returns_bytes(self):
        text = "Hello Jarvis"
        audio = self.tts.synthesize(text)
        self.assertIsInstance(audio, bytes)
        self.assertGreater(len(audio), 0)

if __name__ == "__main__":
    unittest.main()
