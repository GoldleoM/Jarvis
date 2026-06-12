import sounddevice as sd
import numpy as np
import sys

def test_mics():
    print("--- Available Audio Devices ---")
    devices = sd.query_devices()
    print(devices)
    print("-------------------------------\n")
    
    default_mic = sd.default.device['input']
    print(f"System Default Mic Index: {default_mic}\n")
    
    print("Testing devices for audio input... (Please speak into your mic!)")
    
    # Test all input devices
    for i in range(len(devices)):
        if devices[i].get('max_input_channels', 0) > 0:
            try:
                print(f"Testing Device [{i}] {devices[i]['name']}...", end=" ")
                # Flush stdout so the message appears before the recording starts
                sys.stdout.flush()
                # Record 0.5 seconds of audio
                recording = sd.rec(int(16000 * 0.5), samplerate=16000, channels=1, device=i)
                sd.wait()
                
                # Calculate RMS volume
                rms = np.sqrt(np.mean(recording**2))
                print(f"Volume: {rms:.4f}")
                
                if rms > 0.01:
                    print("[SUCCESS] This device is picking up sound!")
            except Exception as e:
                # Catch errors (e.g. invalid sample rate) and print without emojis to avoid encoding errors
                print(f"[ERROR] {e}")

if __name__ == "__main__":
    test_mics()
