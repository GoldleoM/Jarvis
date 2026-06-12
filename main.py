import asyncio
import concurrent.futures
import time
import re
import sounddevice as sd
import numpy as np
from stt import SpeechToText
from tts import TextToSpeech
from router import Gatekeeper


# ---------- AUDIO UTILS ----------

def get_working_input_devices():
    """Return only devices that actually work."""
    devices = sd.query_devices()
    working = []

    for i, d in enumerate(devices):
        if d['max_input_channels'] > 0:
            try:
                sd.check_input_settings(device=i, samplerate=16000)
                working.append((i, d['name']))
            except:
                continue

    return working


def select_input_device():
    devices = get_working_input_devices()

    if not devices:
        print("[ERROR] No usable microphones found.")
        return None

    print("\n[MIC] Available Working Input Devices:\n")
    for idx, name in devices:
        print(f"[{idx}] {name}")

    try:
        choice = input("\nSelect mic index (Enter for default): ").strip()

        if choice == "":
            print("Using system default mic.")
            return None

        choice = int(choice)

        if any(idx == choice for idx, _ in devices):
            sd.default.device = (choice, None)
            print(f"[SUCCESS] Selected mic: {sd.query_devices(choice)['name']}")
            return choice

    except:
        pass

    print("Invalid choice. Using default mic.")
    return None


def detect_audio_input(duration=2, threshold=0.001):
    try:
        samplerate = 16000

        recording = sd.rec(
            int(duration * samplerate),
            samplerate=samplerate,
            channels=1,
            dtype='float32',
            device=sd.default.device[0]  # 🔥 force correct device
        )
        sd.wait()

        volume = float(np.linalg.norm(recording))
        return volume > threshold, volume

    except Exception as e:
        print("Mic test failed:", e)
        return False, 0


def get_current_mic():
    try:
        idx = sd.default.device[0]
        return sd.query_devices(idx)
    except:
        return None


# ---------- VOICE ENGINE ----------

class VoiceEngine:
    def __init__(self, debug=False):
        self.debug = debug
        if self.debug:
            print("[DEBUG] Initializing STT Engine with volume debugging...")
        self.stt = SpeechToText(debug_volume=self.debug)
        
        # Start the persistent OpenCode console in a new window with Gemma-4-31B-it
        print("Booting persistent OpenCode Console on Port 4096...")
        import subprocess
        subprocess.Popen('start cmd /k "title Jarvis Console && opencode --agent Jarvis --model google/gemma-4-31b-it --port 4096"', shell=True)
        
        self.tts = TextToSpeech()
        self.gatekeeper = Gatekeeper()
        self.queue = asyncio.Queue(maxsize=20)
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=3)
        self.current_task = None
        self.loop = None

        self.wake_word = "jarvis"
        self.is_active = False
        self.last_active_time = 0
        self.activity_timeout = 10
        self.pending_confirmation = None
        self.pending_context = None
        self.pending_contact = None
        self.notes_mode = False
        self.non_llm_events = []
        
        # Launch the Typebox UI
        import threading
        threading.Thread(target=self._run_typebox, daemon=True).start()


    # ---------- CALLBACK ----------

    def stt_callback(self, text):
        if not self.loop:
            return

        try:
            self.loop.call_soon_threadsafe(self.queue.put_nowait, text)
        except asyncio.QueueFull:
            pass

    # ---------- LOGIC ----------

    def check_timeout(self):
        if self.is_active and (time.time() - self.last_active_time > self.activity_timeout):
            print("System going back to sleep...")
            self.is_active = False

    def detect_wake_word(self, text):
        return re.search(rf"\b{self.wake_word}\b", text.lower())

    # ---------- COMMAND ----------

    async def handle_command(self, text):
        print(f"Command: {text}")

        clean_text = text.lower().strip(" ,!?.-")
        if clean_text in ["exit", "quit", "stop", "close", "shut down", "goodbye", "close this", "stop there"]:
            print("\nShutting down Jarvis...")
            try:
                # Run TTS synchronously so it finishes before killing the process
                self.tts.speak("Goodbye, sir.")
            except:
                pass
            import os
            os._exit(0) # Immediately exits and suppresses asyncio event loop closure errors on Windows


        # --- CONTEXTUAL STATE MACHINE ---
        if self.pending_context:
            action = self.pending_context
            self.pending_context = None
            
            if action == "timer":
                text = f"set a timer for {text}"
                clean_text = text.lower().strip(" ,!?.-")
            elif action == "youtube_search":
                text = f"search youtube for {text}"
                clean_text = text.lower().strip(" ,!?.-")
            elif action == "whatsapp_who":
                text = f"send a whatsapp to {text}"
                clean_text = text.lower().strip(" ,!?.-")
            elif action == "whatsapp_confirm":
                if any(word in clean_text for word in ["yes", "do it", "confirm", "proceed", "sure", "yeah", "yep"]):
                    self.pending_context = f"whatsapp_msg_{self.pending_contact}"
                    try:
                        await asyncio.wait_for(
                            self.loop.run_in_executor(self.executor, self.tts.speak, f"What would you like to say to {self.pending_contact}?"),
                            timeout=5
                        )
                    except:
                        pass
                    self.is_active = True
                    self.last_active_time = __import__('time').time()
                    return
                else:
                    try:
                        await asyncio.wait_for(
                            self.loop.run_in_executor(self.executor, self.tts.speak, "Okay, cancelling message."),
                            timeout=5
                        )
                    except:
                        pass
                    return
            elif action.startswith("whatsapp_msg_"):
                contact = action.split("whatsapp_msg_")[1]
                text = f"send a whatsapp to {contact} saying {text}"
                clean_text = text.lower().strip(" ,!?.-")
        # --- STATEFUL CONFIRMATION LOGIC ---
        if self.pending_confirmation:
            if any(word in clean_text for word in ["yes", "do it", "confirm", "proceed", "sure"]):
                action = self.pending_confirmation
                self.pending_confirmation = None
                self.pending_context = None
                self.pending_contact = None
                
                try:
                    await asyncio.wait_for(
                        self.loop.run_in_executor(self.executor, self.tts.speak, "Executing, sir."),
                        timeout=5
                    )
                except:
                    pass
                
                import os
                if action == "sleep_pc":
                    os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
                elif action == "restart_pc":
                    os.system("shutdown /r /t 0")
                elif action == "shutdown_pc":
                    os.system("shutdown /s /t 0")
                    
                return
            else:
                self.pending_confirmation = None
                self.pending_context = None
                self.pending_contact = None
                try:
                    await asyncio.wait_for(
                        self.loop.run_in_executor(self.executor, self.tts.speak, "Action cancelled."),
                        timeout=5
                    )
                except:
                    pass
                return

        self.last_active_time = time.time()

        # Check local intent via Semantic Router
        local_response = self.gatekeeper.route_command(clean_text)
        if local_response is None or local_response == "__CODING__":
            # Delegate to Heavy Coding AI (OpenCode)
            from agent_runner import run_opencode_task
            try:
                await asyncio.wait_for(
                    self.loop.run_in_executor(self.executor, self.tts.speak, "Right away, sir."),
                    timeout=10
                )
            except asyncio.TimeoutError:
                pass
            
            if hasattr(self, 'non_llm_events') and self.non_llm_events:
                context_str = "For context, since our last interaction, the following local commands were executed on the user's system:\n"
                for event in self.non_llm_events:
                    context_str += f"- User requested: '{event['user']}' -> System output: '{event['jarvis']}'\n"
                context_str += f"\nNow, please respond to the user's latest request: {text}"
                
                response = await run_opencode_task(context_str)
                self.non_llm_events = []
            else:
                response = await run_opencode_task(text)
            
        else:
            # It's a local script execution (e.g. Open Spotify)
            if local_response == "__NOTES_MODE__":
                self.notes_mode = True
                local_response = "I am ready to take notes, sir. Just speak, and say my name when you are done."
            elif local_response.startswith("__CONFIRM__"):
                parts = local_response.split("__")
                self.pending_confirmation = parts[2]
                local_response = parts[3]


            elif local_response.startswith("__WRITER__"):
                parts = local_response.split("__")
                prompt = parts[2] if len(parts) > 2 and parts[2] else text
                
                try:
                    await asyncio.wait_for(
                        self.loop.run_in_executor(self.executor, self.tts.speak, "Writing that for you now, sir."),
                        timeout=5
                    )
                except:
                    pass
                
                from agent_runner import run_writer_task
                asyncio.create_task(run_writer_task(prompt))
                return
            elif local_response.startswith("__CONTEXT__"):
                parts = local_response.split("__")
                self.pending_context = parts[2]
                if len(parts) > 4:
                    self.pending_contact = parts[4]
                local_response = parts[3]
                
                # VERY IMPORTANT: keep active state true so she listens immediately!
                self.is_active = True
                self.last_active_time = __import__('time').time()
            elif local_response.startswith("__TIMER__"):
                parts = local_response.split("__")
                seconds = int(parts[2])
                local_response = parts[3]
                
                async def timer_task(sec):
                    await asyncio.sleep(sec)
                    try:
                        await asyncio.wait_for(
                            self.loop.run_in_executor(self.executor, self.tts.speak, "Sir, your timer is up!"),
                            timeout=20
                        )
                    except:
                        pass
                        
                asyncio.create_task(timer_task(seconds))

            print(f"Jarvis: {local_response}")
            try:
                await asyncio.wait_for(
                    self.loop.run_in_executor(self.executor, self.tts.speak, local_response),
                    timeout=20
                )
            except asyncio.TimeoutError:
                pass
            
            if hasattr(self, 'non_llm_events'):
                self.non_llm_events.append({"user": text, "jarvis": local_response})
                
            return # Skip the LLM
            
        # Speak the AI's response
        print(f"Jarvis: {response}")

        try:
            await asyncio.wait_for(
                self.loop.run_in_executor(self.executor, self.tts.speak, response),
                timeout=60 # Extended timeout for longer responses
            )
        except asyncio.TimeoutError:
            pass    # ---------- MAIN ----------

    async def run(self):
        print("Initializing Jarvis Voice Interface...")
        self.loop = asyncio.get_running_loop()

        print("\n--- Audio Setup ---")

        # 🔥 Select only valid devices
        select_input_device()

        mic = get_current_mic()
        if mic:
            print(f"\n[MIC] Using mic: {mic['name']}")

        # 🔥 test input safely
        has_audio, level = detect_audio_input()

        print(f"[LEVEL] Mic level: {level:.6f}")

        if has_audio:
            print("[AUDIO] Audio detected")
        else:
            print("[WARNING] Very low input detected")

        print("-------------------\n")

        # 🔥 IMPORTANT: pass selected device to STT if supported
        if hasattr(self.stt, "set_device"):
            self.stt.set_device(sd.default.device[0])

        self.stt.start_listening(self.stt_callback)

        print("Listening for 'Jarvis'...\n")

        try:
            while True:
                self.check_timeout()

                try:
                    text = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue

                text_lower = text.lower()

                # --- NOTES MODE LOGIC ---
                if self.notes_mode:
                    if self.detect_wake_word(text):
                        self.notes_mode = False

                        print("\n[!] Exiting notes mode")
                        try:
                            await asyncio.wait_for(
                                self.loop.run_in_executor(self.executor, self.tts.speak, "Exiting notes mode, sir."),
                                timeout=10
                            )
                        except:
                            pass
                        self.queue.task_done()
                        continue
                    else:
                        import pyautogui
                        pyautogui.write(text + " ", interval=0.01)
                        self.queue.task_done()
                        continue

                if self.detect_wake_word(text):
                    print("\n[!] Wake word detected")
                    self.is_active = True
                    self.last_active_time = time.time()

                    command = re.split(
                        rf"\b{self.wake_word}\b",
                        text_lower,
                        maxsplit=1
                    )[1].strip(" ,!?.")

                    if command:
                        if self.current_task and not self.current_task.done():
                            print("\n[!] Interrupting current task...")
                            self.current_task.cancel()
                        
                        self.current_task = asyncio.create_task(self.handle_command(command))
                    else:
                        print("Listening...")

                elif self.is_active:
                    if self.current_task and not self.current_task.done():
                        print("\n[!] Interrupting current task...")
                        self.current_task.cancel()
                        
                    self.current_task = asyncio.create_task(self.handle_command(text))
                    self.is_active = False # Require wake word again for next command

                self.queue.task_done()

        finally:
            self.stt.stop_listening()
            self.executor.shutdown(wait=False)

    def _run_typebox(self):
        import tkinter as tk
        
        root = tk.Tk()
        root.title("Jarvis Typebox")
        root.geometry("400x80")
        root.attributes('-topmost', True)
        
        def on_submit(event=None):
            text = entry.get().strip()
            if text and self.loop and not self.loop.is_closed():
                try:
                    self.loop.call_soon_threadsafe(self.queue.put_nowait, text)
                except Exception:
                    pass
                entry.delete(0, tk.END)
                
        entry = tk.Entry(root, font=("Segoe UI", 14))
        entry.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        entry.bind("<Return>", on_submit)
        entry.focus()
        
        root.mainloop()


# ---------- ENTRY ----------

async def main(debug=False):
    engine = VoiceEngine(debug=debug)
    await engine.run()


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Jarvis Voice Engine")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    args = parser.parse_args()

    try:
        asyncio.run(main(debug=args.debug))
    except KeyboardInterrupt:
        print("\nStopped.")