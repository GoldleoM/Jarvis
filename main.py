import asyncio
import concurrent.futures
import time
import re
import os
import logging
import warnings

# --- Suppress Verbose Library Logs ---
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["HF_HUB_DISABLE_EXPERIMENTAL_WARNING"] = "1"
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
warnings.filterwarnings("ignore", category=UserWarning, module="huggingface_hub")
logging.getLogger("semantic_router").setLevel(logging.ERROR)
logging.getLogger("faster_whisper").setLevel(logging.ERROR)
logging.getLogger("huggingface_hub").setLevel(logging.ERROR)

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


def select_input_device(auto_default=False):
    devices = get_working_input_devices()

    if not devices:
        print("[ERROR] No usable microphones found.")
        return None

    if auto_default:
        import sounddevice as sd
        try:
            sd.default.device = (3, None)
            return 3
        except:
            return None

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
    def __init__(self, debug=False, ui_mode=False):
        self.debug = debug
        self.ui_mode = ui_mode
        self.stt = None
        self.tts = None
        self.gatekeeper = None
        
        # Boot persistent OpenCode Console in background (hidden)
        import subprocess
        import sys
        creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
        self.opencode_process = subprocess.Popen(
            'opencode --agent Jarvis --model google/gemma-4-31b-it --port 4096',
            shell=True,
            creationflags=creationflags
        )
        self.queue = asyncio.Queue(maxsize=20)
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=3)
        self.current_task = None
        self.loop = None

        import config
        self.wake_word = getattr(config, "WAKE_WORD", "jarvis")
        self.is_active = False
        self.last_active_time = 0
        self.activity_timeout = 10
        self.pending_confirmation = None
        self.pending_context = None
        self.pending_contact = None
        self.notes_mode = False
        self.non_llm_events = []
        
        self.ui_state = "idle"
        self.ui_text = "ONLINE"
        
        # Launch the Typebox UI (only if not in UI mode)
        if not self.ui_mode:
            import threading
            threading.Thread(target=self._run_typebox, daemon=True).start()


    def _set_ui_state(self, state, text=None):
        self.ui_state = state
        if text:
            self.ui_text = text

    # ---------- CALLBACK ----------

    def stt_partial_callback(self, text):
        if self.ui_state in ["idle", "listening"]:
            if self.is_active or self.detect_wake_word(text) or self.notes_mode:
                self._set_ui_state("listening", f'"{text}"')

    def stt_callback(self, text):
        if not self.loop:
            return

        # Acoustic Echo Prevention: If Jarvis is speaking or just finished speaking recently (to allow STT to catch up), ignore transcribed audio
        # UNLESS the user is explicitly trying to interrupt with the wake word or a stop command
        recent_speech = hasattr(self, 'last_speech_time') and (time.time() - self.last_speech_time < 2.0)
        
        if self.ui_state == "speaking" or recent_speech:
            if not (self.detect_wake_word(text) or self.is_interruption(text)):
                return

        try:
            self.loop.call_soon_threadsafe(self.queue.put_nowait, text)
        except asyncio.QueueFull:
            pass

    async def hot_reload(self, settings_dict):
        print(f"\n[System] Hot Reloading Settings...")
        self._set_ui_state("thinking", "RELOADING...")
        
        # 1. Update wake word
        if settings_dict.get("WAKE_WORD"):
            self.wake_word = settings_dict["WAKE_WORD"]
            
        # 2. Check if we need to reload STT
        import config
        current_mic = getattr(config, "MIC_INDEX", None)
        current_whisper = getattr(config, "WHISPER_MODEL", "medium.en")
        current_compute = getattr(config, "WHISPER_COMPUTE_TYPE", "float16")
        
        needs_stt_reload = False
        new_mic = settings_dict.get("MIC_INDEX", current_mic)
        new_whisper = settings_dict.get("WHISPER_MODEL", current_whisper)
        new_compute = settings_dict.get("WHISPER_COMPUTE_TYPE", current_compute)
        
        if new_mic != current_mic or new_whisper != current_whisper or new_compute != current_compute:
            needs_stt_reload = True
            
        if needs_stt_reload:
            print("[System] Audio streams/models changed. Restarting STT engine safely...")
            if self.stt:
                # Need to use an executor to stop the threads to prevent blocking the event loop
                await self.loop.run_in_executor(self.executor, self.stt.stop_listening)
            
            # Reinitialize STT model
            def _reload_stt():
                import importlib
                import sys
                if 'config' in sys.modules:
                    importlib.reload(sys.modules['config'])
                from stt import SpeechToText
                self.stt = SpeechToText(model_size=new_whisper, compute_type=new_compute, debug_volume=self.debug)
                self.stt.on_partial = self.stt_partial_callback
                
            await self.loop.run_in_executor(self.executor, _reload_stt)
            
            # Restart listening
            if hasattr(self.stt, "set_device"):
                self.stt.set_device(new_mic)
            self.stt.start_listening(self.stt_callback, device_index=new_mic)
            print("[System] STT Hot Reload Complete.")
            
        self._set_ui_state("idle", "ONLINE")

    # ---------- LOGIC ----------

    def check_timeout(self):
        if self.is_active and (time.time() - self.last_active_time > self.activity_timeout):
            print("System going back to sleep...")
            self.is_active = False

    def detect_wake_word(self, text):
        return re.search(rf"\b{self.wake_word}\b", text.lower())

    def is_interruption(self, text):
        text_lower = text.lower()
        
        # If the user is specifically targeting media or tasks, don't treat it as a generic TTS interruption
        if any(keyword in text_lower for keyword in ["music", "spotify", "song", "video", "youtube", "media", "timer", "alarm"]):
            return False
            
        interruption_words = ["stop", "quiet", "shut up", "pause", "enough", "cancel", "halt", "silence", "shh", "shutup", "stop talking"]
        for word in interruption_words:
            if re.search(rf"\b{word}\b", text_lower):
                # Ensure it's a short command, so we don't accidentally interrupt on complex sentences
                if len(text_lower.split()) <= 4:
                    return True
        return False

    # ---------- COMMAND ----------    async def handle_command(self, text):
        self._set_ui_state("thinking", "PROCESSING...")
        print(f"Command: {text}")

        try:
            clean_text = text.lower().strip(" ,!?.-")
            if clean_text in ["exit", "quit", "stop", "close", "shut down", "goodbye", "close this", "stop there"]:
                print("\nShutting down Jarvis...")
                self._set_ui_state("speaking", "Goodbye, sir.")
                try:
                    await asyncio.wait_for(
                        self.loop.run_in_executor(self.executor, self.tts.speak, "Goodbye, sir."),
                        timeout=10
                    )
                except:
                    pass
                self._set_ui_state("idle", "OFFLINE")
                if getattr(self, 'ui_mode', False):
                    from PySide6.QtWidgets import QApplication
                    app = QApplication.instance()
                    if app:
                        app.quit()
                    return
                else:
                    import os
                    os._exit(0)

            # --- CONTEXTUAL STATE MACHINE ---
            if self.pending_context:
                
                # Allow user to abort contextual flows
                if clean_text in ["cancel", "nevermind", "never mind", "stop", "abort", "forget it", "ignore that"]:
                    self.pending_context = None
                    self.pending_contact = None
                    self.pending_confirmation = None
                    try:
                        await asyncio.wait_for(
                            self.loop.run_in_executor(self.executor, self.tts.speak, "Cancelled."),
                            timeout=5
                        )
                    except:
                        pass
                    return

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
            local_response = await self.loop.run_in_executor(self.executor, self.gatekeeper.route_command, clean_text)
            
            if local_response == "__IGNORE__":
                self._set_ui_state("idle", "ONLINE")
                return
                
            if local_response == "__SLEEP__":
                self.is_active = False
                self._set_ui_state("idle", "ONLINE")
                print("System going back to sleep...")
                return
                
            if local_response == "__RESTART__":
                print("\nRestarting Jarvis...")
                self._set_ui_state("speaking", "Restarting the engine, sir.")
                try:
                    await asyncio.wait_for(
                        self.loop.run_in_executor(self.executor, self.tts.speak, "Restarting the engine, sir."),
                        timeout=5
                    )
                except:
                    pass
                self._set_ui_state("idle", "RESTARTING")
                
                import sys, subprocess, os
                subprocess.Popen([sys.executable] + sys.argv)
                
                if getattr(self, 'ui_mode', False):
                    from PySide6.QtWidgets import QApplication
                    app = QApplication.instance()
                    if app:
                        app.quit()
                    return
                else:
                    os._exit(0)

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
                self.last_spoken_text = local_response
                self._set_ui_state("speaking", local_response)
                print(f"Jarvis: {local_response}")
                try:
                    await asyncio.wait_for(
                        self.loop.run_in_executor(self.executor, self.tts.speak, local_response),
                        timeout=20
                    )
                except asyncio.TimeoutError:
                    pass
                finally:
                    self.last_speech_time = time.time()
                    if self.ui_state in ["thinking", "speaking"]:
                        self._set_ui_state("idle", "ONLINE")
                
                if hasattr(self, 'non_llm_events'):
                    self.non_llm_events.append({"user": text, "jarvis": local_response})
                    
                return # Skip the LLM
        except asyncio.CancelledError:
            print("[System] Task cancelled.")
            return
        except Exception as e:
            print(f"[ERROR] Exception in handle_command: {e}")
            return
        finally:
            if self.ui_state in ["thinking", "speaking"]:
                self._set_ui_state("idle", "ONLINE")
            
        # Speak the AI's response
        self.last_spoken_text = response
        self._set_ui_state("speaking", response)
        print(f"Jarvis: {response}")

        try:
            await asyncio.wait_for(
                self.loop.run_in_executor(self.executor, self.tts.speak, response),
                timeout=60 # Extended timeout for longer responses
            )
        except asyncio.TimeoutError:
            pass
        finally:
            self.last_speech_time = time.time()
            self._set_ui_state("idle", "ONLINE")

    # ---------- MAIN ----------

    async def run(self):
        print("Initializing Jarvis Voice Interface...")
        self.loop = asyncio.get_running_loop()
        
        # Move heavy loading to a background thread so UI can appear immediately
        def _load_models():
            print("[System] Loading Voice Engine Models in background...")
            self.gatekeeper = Gatekeeper()
            self.tts = TextToSpeech()
            self.stt = SpeechToText(debug_volume=self.debug)
            self.stt.on_partial = self.stt_partial_callback
            
            # Wrap TTS speak to mute STT to prevent feedback loop and background music loops
            original_speak = self.tts.speak
            def _speak_wrapper(text):
                if hasattr(self, 'stt') and self.stt:
                    self.stt.is_muted = True
                    if hasattr(self.stt, 'audio_queue'):
                        with self.stt.audio_queue.mutex:
                            self.stt.audio_queue.queue.clear()
                try:
                    original_speak(text)
                finally:
                    if hasattr(self, 'stt') and self.stt:
                        if hasattr(self.stt, 'audio_queue'):
                            with self.stt.audio_queue.mutex:
                                self.stt.audio_queue.queue.clear()
                        self.stt.flush_requested = True
                        self.stt.is_muted = False
            self.tts.speak = _speak_wrapper
            
        print("\n--- Background Model Loading ---")
        await self.loop.run_in_executor(self.executor, _load_models)

        print("\n--- Audio Setup ---")

        # 🔥 Select only valid devices (skip blocking input if in UI mode)
        select_input_device(auto_default=getattr(self, 'ui_mode', False))

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
        import config
        mic_index = getattr(config, "MIC_INDEX", None)
        
        if hasattr(self.stt, "set_device"):
            self.stt.set_device(sd.default.device[0])

        self.stt.start_listening(self.stt_callback, device_index=mic_index)

        print("Listening for 'Jarvis'...\n")

        # LLM Warmup and Welcome Message
        async def _warmup_and_greet():
            print("[System] Warming up LLM and fetching welcome message...")
            try:
                from agent_runner import run_opencode_task
                response = await run_opencode_task("System startup complete. Please give a very short, 1-sentence greeting indicating you are online and ready, sir.")
                print(f"Jarvis: {response}")
                self._set_ui_state("speaking", response)
                await self.loop.run_in_executor(self.executor, self.tts.speak, response)
                self._set_ui_state("idle", "ONLINE")
            except Exception as e:
                print(f"[System] LLM Warmup failed: {e}")
                self._set_ui_state("idle", "ONLINE")

        asyncio.create_task(_warmup_and_greet())

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
                    text_lower_clean = text.lower().strip(" ,.!?")
                    has_wake = self.detect_wake_word(text)
                    command_text = re.sub(r'jarvis\s*', '', text_lower_clean, flags=re.IGNORECASE).strip()
                    
                    if command_text in ["hit enter", "press enter", "new line"]:
                        import pyautogui
                        pyautogui.press("enter")
                        if not hasattr(self, 'current_note_buffer'): self.current_note_buffer = ""
                        self.current_note_buffer += "\n"
                        self.queue.task_done()
                        continue
                    elif command_text in ["hit backspace", "press backspace", "delete that"]:
                        import pyautogui
                        pyautogui.press("backspace")
                        if not hasattr(self, 'current_note_buffer'): self.current_note_buffer = ""
                        self.current_note_buffer = self.current_note_buffer[:-1] if self.current_note_buffer else ""
                        self.queue.task_done()
                        continue
                    elif command_text in ["hit tab", "press tab"]:
                        import pyautogui
                        pyautogui.press("tab")
                        if not hasattr(self, 'current_note_buffer'): self.current_note_buffer = ""
                        self.current_note_buffer += "\t"
                        self.queue.task_done()
                        continue

                    if has_wake:
                        self.notes_mode = False

                        print("\n[!] Exiting notes mode")
                        
                        if getattr(self, 'current_note_buffer', '').strip():
                            notes_content = self.current_note_buffer.strip()
                            self._set_ui_state("thinking", "SAVING NOTE...")
                            try:
                                from agent_runner import run_opencode_task
                                prompt = f"Generate a short 1 to 4 word file name for the following notes. Output ONLY the file name without any extension or punctuation. Notes: {notes_content[:500]}"
                                filename_res = await run_opencode_task(prompt)
                                
                                filename = re.sub(r'[^a-zA-Z0-9_\- ]', '', filename_res.strip())
                                if not filename:
                                    filename = "Untitled Note"
                                filename = filename.replace(' ', '_') + ".txt"
                                
                                notes_dir = r"C:\users\goldleom\jarvis-voice-engine\jarvis_notes"
                                os.makedirs(notes_dir, exist_ok=True)
                                filepath = os.path.join(notes_dir, filename)
                                
                                with open(filepath, "w", encoding="utf-8") as f:
                                    f.write(notes_content)
                                    
                                exit_msg = f"I have saved your notes as {filename.replace('_', ' ').replace('.txt', '')}."
                            except Exception as e:
                                print(f"Error saving note: {e}")
                                exit_msg = "Exiting notes mode, sir. I encountered an error saving the file."
                        else:
                            exit_msg = "Exiting notes mode, sir. No notes were recorded."

                        try:
                            await asyncio.wait_for(
                                self.loop.run_in_executor(self.executor, self.tts.speak, exit_msg),
                                timeout=15
                            )
                        except:
                            pass
                        
                        self._set_ui_state("idle", "ONLINE")
                        self.current_note_buffer = ""
                        self.queue.task_done()
                        continue
                    else:
                        import pyautogui
                        pyautogui.write(text + " ", interval=0.01)
                        if not hasattr(self, 'current_note_buffer'):
                            self.current_note_buffer = ""
                        self.current_note_buffer += text + " "
                        self.queue.task_done()
                        continue

                text_lower_clean = text.lower().strip(" ,.!?")
                if hasattr(self, 'last_spoken_text') and self.last_spoken_text:
                    import difflib
                    similarity = difflib.SequenceMatcher(None, text_lower_clean, self.last_spoken_text.lower().strip(" ,.!?")).ratio()
                    if similarity > 0.8 or (text_lower_clean and text_lower_clean in self.last_spoken_text.lower()):
                        print(f"[System] Ignoring echo of own speech: {text}")
                        self.queue.task_done()
                        continue

                if self.detect_wake_word(text):
                    print("\n[!] Wake word detected")
                    self.tts.stop() # Interrupt audio on wake word
                    self.is_active = True
                    self._set_ui_state("listening", "LISTENING...")
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

                elif self.is_interruption(text):
                    print("\n[!] Interruption detected")
                    self.tts.stop() # Interrupt audio
                    self._set_ui_state("idle", "ONLINE")
                    if self.current_task and not self.current_task.done():
                        print("\n[!] Interrupting current task...")
                        self.current_task.cancel()
                    self.is_active = False

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
                    if not self.detect_wake_word(text.lower()):
                        if not getattr(self, 'is_active', False) and not getattr(self, 'notes_mode', False):
                            text = f"{self.wake_word} {text}"
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

async def main(debug=False, ui_mode=False):
    engine = VoiceEngine(debug=debug, ui_mode=ui_mode)
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