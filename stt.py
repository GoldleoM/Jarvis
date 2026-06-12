import faster_whisper
import numpy as np
import sounddevice as sd
import queue
import threading
import webrtcvad
import torch
import os
import warnings
import collections

# Suppress internal PyTorch FutureWarnings
warnings.filterwarnings("ignore")

class SpeechToText:
    def __init__(self, model_size=None, device=None, compute_type=None, debug_volume=False):
        import config
        self.debug_volume = debug_volume
        device = device or getattr(config, "WHISPER_DEVICE", "cpu")
        model_size = model_size or getattr(config, "WHISPER_MODEL", "small.en")
        
        # Use config if available, otherwise default to int8_float16 for CUDA to save massive VRAM, or int8 for CPU
        default_compute = "int8_float16" if device == "cuda" else "int8"
        compute_type = compute_type or getattr(config, "WHISPER_COMPUTE_TYPE", default_compute)
        
        print(f"Loading Whisper model '{model_size}' on {device} with {compute_type}...")
        try:
            self.model = faster_whisper.WhisperModel(model_size, device=device, compute_type=compute_type)
        except Exception as e:
            print(f"[WARNING] Failed to load with {compute_type}: {e}. Falling back to float32...")
            self.model = faster_whisper.WhisperModel(model_size, device=device, compute_type="float32")
        
        # VAD Settings (Silero VAD)
        self.vad_model, _ = torch.hub.load(repo_or_dir='snakers4/silero-vad', model='silero_vad')
        self.vad_model.eval()
        self.sample_rate = 16000
        # Silero VAD strongly prefers exactly 512 samples per chunk (32ms at 16000Hz)
        self.frame_duration_ms = 32 
        self.frame_size = int(self.sample_rate * self.frame_duration_ms / 1000)
        self.debug_volume = debug_volume

        # --- ANTI-HALLUCINATION GUARDS ---
        self.min_recording_duration = 0.6  # Ignore anything shorter than 0.6s
        self.ghost_phrases = [
            "thank you", "thanks", "bye guys", "thank you for watching", 
            "subscribe", "yardım et", "please subscribe", "hmm", "uh",
            "thank you very much", "see you in the next video"
        ]

        # Speaker Verification
        self.device_str = device
        self.speaker_embedding = None
        self.speaker_classifier = None
        
        print("Speaker Verification disabled.")

    def is_speech(self, audio_chunk):
        try:
            # RMS gate to ignore pure silence before running the model
            rms = np.sqrt(np.mean(audio_chunk**2))
            if rms < 0.01: 
                return False
                
            audio_tensor = torch.tensor(audio_chunk, dtype=torch.float32)
            confidence = self.vad_model(audio_tensor, self.sample_rate).item()
            return confidence > 0.5
        except Exception as e:
            print(f"[ERROR] VAD Error: {e}")
            return False

    def transcribe(self, audio_data):
        duration = len(audio_data) / self.sample_rate
        
        if self.debug_volume:
            print(f"\n[DEBUG] Captured Audio Clip: {duration:.2f} seconds")
            
        # 1. Normalize Audio Volume (Crucial for quiet microphones)
        max_amp = np.max(np.abs(audio_data))
        if max_amp > 0:
            audio_data = audio_data / max_amp
            
        # 2. Duration Gate: Stop "pops" and "clicks" from being transcribed
        if duration < self.min_recording_duration:
            if self.debug_volume:
                print(f"[DEBUG] -> Ignored: Clip too short (< {self.min_recording_duration}s)")
            return ""

        # 3. Strict Transcription Parameters
        segments, info = self.model.transcribe(
            audio_data, 
            language="en",          # Force English to stop foreign language hallucinations on static
            beam_size=5,
            vad_filter=True,        # Use faster-whisper's built in VAD to strip silent edges
            no_speech_threshold=0.6, 
            log_prob_threshold=-1.0,
            condition_on_previous_text=False, # Stops the "looping" hallucination
            initial_prompt="Jarvis, listen to my commands. Wake up, exit, stop, please. What time is it? Open Spotify. Open Chrome." # Bias model to English commands
        )
        
        text = " ".join([segment.text for segment in segments]).strip()
        
        if self.debug_volume:
            print(f"\n[DEBUG] Audio Clip Duration: {duration:.2f}s | Raw Transcription: '{text}'")
        
        # 3. Ghost Phrase Filter
        if not text:
            return ""
            
        if any(phrase in text.lower() for phrase in self.ghost_phrases):
            if self.debug_volume:
                print(f"[DEBUG] -> Blocked by ghost phrase filter!")
            return ""
            
        return text

    def start_listening(self, callback, device_index=None):
        self.audio_queue = queue.Queue()
        self.stop_event = threading.Event()

        def producer():
            def audio_callback(indata, frames, time, status):
                if status:
                    print(f"Error: {status}")
                self.audio_queue.put(indata.copy())

            with sd.InputStream(samplerate=self.sample_rate, 
                                channels=1, 
                                device=device_index,
                                callback=audio_callback, 
                                blocksize=self.frame_size):
                while not self.stop_event.is_set():
                    sd.sleep(100)

        def consumer():
            audio_buffer = []
            pre_record_buffer = collections.deque(maxlen=10) # ~320ms rolling memory
            is_recording = False
            speech_frames_count = 0
            silence_frames_count = 0
            
            REQUIRED_SPEECH_FRAMES = 3 # Require ~96ms of speech to start
            # 1.5 seconds of silence before we consider the user "done" speaking (32ms per frame -> 50 frames)
            MAX_SILENCE_FRAMES = 50 

            while not self.stop_event.is_set():
                try:
                    chunk = self.audio_queue.get(timeout=1)
                    chunk_flat = chunk.flatten()
                    
                    if self.debug_volume:
                        rms = np.sqrt(np.mean(chunk_flat**2))
                        bar_len = int(min(rms * 100, 20))
                        bar = "#" * bar_len + "-" * (20 - bar_len)
                        print(f"\rVolume: [{bar}] {rms:.4f}", end="")

                    if not is_recording:
                        pre_record_buffer.append(chunk_flat)

                    if self.is_speech(chunk_flat):
                        speech_frames_count += 1
                        silence_frames_count = 0 # Reset silence counter when user speaks again
                        
                        if speech_frames_count >= REQUIRED_SPEECH_FRAMES:
                            if not is_recording:
                                print("\n[VAD] Speech detected... recording")
                                is_recording = True
                                audio_buffer.extend(pre_record_buffer)
                                pre_record_buffer.clear()
                            else:
                                audio_buffer.append(chunk_flat)
                    else:
                        speech_frames_count = 0
                        if is_recording:
                            silence_frames_count += 1
                            audio_buffer.append(chunk_flat) # Keep recording the pause so audio isn't jumpy
                            
                            if silence_frames_count >= MAX_SILENCE_FRAMES:
                                print("\n[VAD] Silence timeout reached... processing")
                                is_recording = False
                                silence_frames_count = 0
                                full_audio = np.concatenate(audio_buffer)
                                
                                text = ""
                                text = self.transcribe(full_audio)
                                    
                                if text:
                                    callback(text)
                                audio_buffer = []
                except queue.Empty:
                    continue

        self.producer_thread = threading.Thread(target=producer, daemon=True)
        self.consumer_thread = threading.Thread(target=consumer, daemon=True)
        
        self.producer_thread.start()
        self.consumer_thread.start()

    def stop_listening(self):
        self.stop_event.set()
        self.producer_thread.join()
        self.consumer_thread.join()
