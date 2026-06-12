import sounddevice as sd
import numpy as np
import torch
import time
import warnings
from speechbrain.inference.speaker import EncoderClassifier
from main import get_working_input_devices
import config

# Suppress internal SpeechBrain and PyTorch FutureWarnings
warnings.filterwarnings("ignore")

def enroll_voice():
    print("Initializing Voice Enrollment...")
    
    devices = get_working_input_devices()
    if not devices:
        print("[ERROR] No working microphones found.")
        return
        
    print("\nAvailable Input Devices:")
    for idx, name in devices:
        print(f"[{idx}] {name}")
        
    try:
        choice = input(f"\nSelect mic index (Enter for default {devices[0][0]}): ")
        device_idx = int(choice) if choice.strip() else devices[0][0]
    except ValueError:
        print("Invalid choice, using default.")
        device_idx = devices[0][0]

    sample_rate = 16000
    duration = 30 # 30 seconds of speech for a much stronger voice print
    
    print("\n--- VOICE ENROLLMENT ---")
    print("Please read the following text out loud in your normal speaking voice.")
    print("Take your time and speak naturally until the timer finishes:")
    print("\n'The quick brown fox jumps over the lazy dog. I am authenticating my voice print for Jarvis. This allows the system to recognize my unique vocal characteristics. A longer sample provides the AI with more data about my pitch, resonance, and cadence, making the system much more secure against background noises.'\n")
    
    input("Press Enter to start recording...")
    
    print(f"\n[RECORDING] Speak now for {duration} seconds...")
    
    # Start recording
    audio_data = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype='float32', device=device_idx)
    
    for i in range(duration, 0, -1):
        print(f"{i} seconds remaining...   ", end="\r")
        time.sleep(1)
        
    sd.wait()
    print("\n[DONE] Recording complete. Analyzing voice print...")
    
    # Strip silence (RMS gate) so the Voice Print isn't polluted by background noise
    frame_size = 480 # 30ms at 16000Hz
    audio_flat = audio_data.flatten()
    voiced_audio = []
    for i in range(0, len(audio_flat), frame_size):
        frame = audio_flat[i:i+frame_size]
        if np.sqrt(np.mean(frame**2)) >= 0.02: # Same threshold as STT
            voiced_audio.append(frame)
            
    if not voiced_audio:
        print("\n[ERROR] No speech detected! Please speak louder or check your mic.")
        return
        
    audio_flat = np.concatenate(voiced_audio)
    
    print("\n[VERIFICATION] Transcribing your enrollment audio to ensure it was captured perfectly...")
    import faster_whisper
    whisper_device = "cuda" if getattr(config, "WHISPER_DEVICE", "cpu") == "cuda" and torch.cuda.is_available() else "cpu"
    whisper_compute = getattr(config, "WHISPER_COMPUTE_TYPE", "int8_float16" if whisper_device == "cuda" else "int8")
    
    whisper_model = faster_whisper.WhisperModel(getattr(config, "WHISPER_MODEL", "small.en"), device=whisper_device, compute_type=whisper_compute)
    segments, _ = whisper_model.transcribe(audio_flat, language="en")
    transcription = " ".join([segment.text for segment in segments]).strip()
    
    print(f"\n[WHAT JARVIS HEARD]: {transcription}\n")
    
    # Flatten and Peak-Normalize the audio for the voice print
    audio_tensor = torch.tensor(audio_flat, dtype=torch.float32)
    audio_tensor = audio_tensor / (torch.max(torch.abs(audio_tensor)) + 1e-6)
    
    print("Loading SpeechBrain Voice Print model (this may download weights on first run)...")
    
    # Try cuda if available, otherwise cpu
    device = "cuda" if getattr(config, "WHISPER_DEVICE", "cpu") == "cuda" and torch.cuda.is_available() else "cpu"
    
    classifier = EncoderClassifier.from_hparams(
        source="speechbrain/spkrec-ecapa-voxceleb", 
        savedir="models/spkrec-ecapa-voxceleb",
        run_opts={"device": device}
    )
    
    print("Extracting embedding...")
    # encode_batch expects [batch, time]
    embedding = classifier.encode_batch(audio_tensor.unsqueeze(0))
    
    save_path = "voice_print.pt"
    torch.save(embedding, save_path)
    
    print(f"\n[SUCCESS] Your unique voice print has been saved to {save_path}!")
    print("Jarvis will now use this to verify your identity and ignore background voices.")

if __name__ == "__main__":
    enroll_voice()
