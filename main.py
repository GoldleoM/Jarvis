import asyncio
import concurrent.futures
import time as _time
import re
import os
import threading
import logging
import warnings
from power_monitor import PowerMonitor, get_power_state, get_optimal_device, get_compute_type, find_fallback_model

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
import config
if config.TTS_ENGINE == "kokoro":
    from tts_kokoro import TextToSpeech
else:
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

    import config
    configured_mic = getattr(config, "MIC_INDEX", None)

    if auto_default or not sys.stdin.isatty():
        if configured_mic is not None and any(idx == configured_mic for idx, _ in devices):
            import sounddevice as sd
            sd.default.device = (configured_mic, None)
            print(f"[SUCCESS] Using configured mic [{configured_mic}]: {sd.query_devices(configured_mic)['name']}")
            return configured_mic
        print("Using system default mic.")
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
        import shutil
        import urllib.request
        creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
        
        # Check if OpenCode is already running on port 4096
        self.opencode_process = None
        opencode_already_running = False
        try:
            with urllib.request.urlopen("http://127.0.0.1:4096/session", timeout=1) as resp:
                if resp.status == 200:
                    opencode_already_running = True
                    print("[System] OpenCode server is already running on port 4096.")
        except Exception:
            pass

        if not opencode_already_running:
            opencode_cmd = shutil.which("opencode")
            if opencode_cmd:
                self.opencode_process = subprocess.Popen(
                    [opencode_cmd, 'serve', '--port', '4096'],
                    creationflags=creationflags,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            else:
                self.opencode_process = subprocess.Popen(
                    'opencode serve --port 4096',
                    shell=True,
                    creationflags=creationflags,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            print("[System] Started OpenCode headless server on port 4096.")
        self.queue = asyncio.Queue(maxsize=20)
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=3)
        self.current_task = None
        self.loop = None
        self.power_monitor = None
        self._power_switch_lock = threading.Lock()

        import config
        self.wake_word = getattr(config, "WAKE_WORD", "jarvis")
        
        import atexit
        atexit.register(self._cleanup_opencode)
        
        self._init_state()

    def _cleanup_opencode(self):
        """Terminate the opencode background process and its children."""
        if hasattr(self, 'opencode_process') and self.opencode_process:
            try:
                import psutil
                parent = psutil.Process(self.opencode_process.pid)
                for child in parent.children(recursive=True):
                    child.terminate()
                parent.terminate()
                parent.wait(timeout=3)
            except Exception:
                try:
                    self.opencode_process.terminate()
                    self.opencode_process.wait(timeout=3)
                except Exception:
                    self.opencode_process.kill()
            self.opencode_process = None
            print("[System] OpenCode session terminated.")

    def _init_state(self):
        """Initialize conversation state variables. Called from __init__."""
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
        # Timeout increased to 3.5s to account for NVIDIA Broadcast latency + VAD silence timeout + Whisper execution time.
        recent_speech = hasattr(self, 'last_speech_time') and (_time.time() - self.last_speech_time < 3.5)
        
        # If we are actively expecting a response, bypass the recent_speech block so the user can answer immediately.
        if self.ui_state == "speaking" or (recent_speech and not getattr(self, 'is_active', False)):
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
        current_device = getattr(config, "WHISPER_DEVICE", "cuda")
        
        needs_stt_reload = False
        new_mic = settings_dict.get("MIC_INDEX", current_mic)
        new_whisper = settings_dict.get("WHISPER_MODEL", current_whisper)
        new_compute = settings_dict.get("WHISPER_COMPUTE_TYPE", current_compute)
        new_device = settings_dict.get("WHISPER_DEVICE", current_device)
        
        # Handle "auto" device — resolve based on current power state
        if new_device == "auto":
            plugged, _ = get_power_state()
            new_device = get_optimal_device(plugged)
            new_compute = get_compute_type(new_device)
            print(f"[System] Auto device resolved to: {new_device}/{new_compute}")
        
        if new_mic != current_mic or new_whisper != current_whisper or new_compute != current_compute or new_device != current_device:
            needs_stt_reload = True
            
        if needs_stt_reload:
            print(f"[System] Audio streams/models changed. Restarting STT engine safely... (device={new_device})")
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
                self.stt = SpeechToText(model_size=new_whisper, device=new_device, compute_type=new_compute, debug_volume=self.debug)
                self.stt.on_partial = self.stt_partial_callback
                
            await self.loop.run_in_executor(self.executor, _reload_stt)
            
            # Restart listening
            if hasattr(self.stt, "set_device"):
                self.stt.set_device(new_mic)
            self.stt.start_listening(self.stt_callback, device_index=new_mic)
            print("[System] STT Hot Reload Complete.")
            
        self._set_ui_state("idle", "ONLINE")

    # ---------- POWER-AWARE STT SWITCHING ----------

    def _on_power_change(self, new_device, new_compute):
        """Called by PowerMonitor from its background thread when AC/battery changes."""
        if not self._power_switch_lock.acquire(blocking=False):
            print("[PowerMonitor] Switch already in progress, skipping.")
            return
        try:
            import config
            current_model = getattr(config, "WHISPER_MODEL", "medium.en")

            print(f"\n[PowerMonitor] ⚡ Switching STT: {new_device}/{new_compute} (model: {current_model})")
            self._set_ui_state("thinking", "SWITCHING DEVICE...")

            # Stop current STT
            if self.stt:
                try:
                    self.stt.stop_listening()
                except Exception:
                    pass

            # Try loading with current model first
            from stt import SpeechToText
            target_model = current_model
            target_compute = new_compute
            loaded = False

            try:
                self.stt = SpeechToText(
                    model_size=target_model,
                    device=new_device,
                    compute_type=target_compute,
                    debug_volume=self.debug
                )
                loaded = True
                print(f"[PowerMonitor] ✓ Loaded '{target_model}' on {new_device}/{target_compute}")
            except Exception as e:
                print(f"[PowerMonitor] ✗ Failed to load '{target_model}' on {new_device}/{target_compute}: {e}")

            # Fallback: try smaller models
            if not loaded:
                print(f"[PowerMonitor] Trying fallback models...")
                result = find_fallback_model(target_model, new_device)
                if result:
                    target_model, target_compute = result
                    try:
                        self.stt = SpeechToText(
                            model_size=target_model,
                            device=new_device,
                            compute_type=target_compute,
                            debug_volume=self.debug
                        )
                        loaded = True
                        print(f"[PowerMonitor] ✓ Fallback loaded '{target_model}' on {new_device}/{target_compute}")
                    except Exception as e:
                        print(f"[PowerMonitor] ✗ Fallback also failed: {e}")

            if not loaded:
                print("[PowerMonitor] ⚠ CRITICAL: Could not load any STT model! Attempting emergency CPU/tiny.en...")
                try:
                    self.stt = SpeechToText(model_size="tiny.en", device="cpu", compute_type="float32", debug_volume=self.debug)
                    target_model = "tiny.en"
                    new_device = "cpu"
                    target_compute = "float32"
                    loaded = True
                except Exception:
                    print("[PowerMonitor] ⚠ FATAL: No STT model could be loaded.")
                    self._set_ui_state("idle", "STT ERROR")
                    return

            # Reconnect STT
            self.stt.on_partial = self.stt_partial_callback

            # Re-wrap TTS speak for mute coordination
            if self.tts:
                original_speak = self.tts._original_speak if hasattr(self.tts, '_original_speak') else self.tts.speak
                self.tts._original_speak = original_speak
                def _speak_wrapper(text, _stt_ref=self.stt, _orig=original_speak):
                    if _stt_ref:
                        _stt_ref.is_muted = True
                        if hasattr(_stt_ref, 'audio_queue'):
                            with _stt_ref.audio_queue.mutex:
                                _stt_ref.audio_queue.queue.clear()
                    try:
                        _orig(text)
                    finally:
                        if _stt_ref:
                            if hasattr(_stt_ref, 'audio_queue'):
                                with _stt_ref.audio_queue.mutex:
                                    _stt_ref.audio_queue.queue.clear()
                            _stt_ref.flush_requested = True
                            _stt_ref.is_muted = False
                self.tts.speak = _speak_wrapper

            mic_index = getattr(config, "MIC_INDEX", None)
            self.stt.start_listening(self.stt_callback, device_index=mic_index)

            state_label = "AC Power (CUDA)" if new_device == "cuda" else "Battery (CPU)"
            print(f"[PowerMonitor] ✓ STT fully switched → {state_label} | model={target_model} | compute={target_compute}")
            self._set_ui_state("idle", "ONLINE")

        except Exception as e:
            print(f"[PowerMonitor] ERROR during switch: {e}")
            self._set_ui_state("idle", "ONLINE")
        finally:
            self._power_switch_lock.release()

    # ---------- LOGIC ----------

    def check_timeout(self):
        if self.is_active and (_time.time() - self.last_active_time > self.activity_timeout):
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

    # ---------- COMMAND ----------
    async def handle_command(self, text):
        self._set_ui_state("thinking", "PROCESSING...")
        print(f"Command: {text}")

        try:
            clean_text = text.lower().strip(" ,!?.-")
            
            # --- HALLUCINATION FILTER ---
            hallucinations = [
                "thank you for watching", "thanks for watching", 
                "please return to your meeting and play back", "the media playback",
                "it's troubling me to get playback", "um, what", "i'm sorry",
                "i'm hearing", "i hear you", "i'm here", "i'm hearing you"
            ]
            if clean_text in hallucinations or len(clean_text) < 2:
                print(f"[!] Ignored known Whisper hallucination: {clean_text}")
                self._set_ui_state("idle", "ONLINE")
                return

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
                self._cleanup_opencode()
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
                elif action == "whatsapp_suggest" or action == "whatsapp_suggest_msg":
                    options_str = self.pending_contact
                    saved_message = None
                    if "|||" in options_str:
                        parts_data = options_str.split("|||", 1)
                        options_str = parts_data[0]
                        saved_message = parts_data[1]
                    options = [o.strip() for o in options_str.split("|") if o.strip()]
                    import difflib
                    clean_lower = clean_text.lower().strip()
                    selected = None
                    if clean_lower.isdigit():
                        num = int(clean_lower)
                        if 1 <= num <= len(options):
                            selected = options[num - 1]
                    if not selected:
                        name_matches = difflib.get_close_matches(clean_lower, [o.lower() for o in options], n=1, cutoff=0.5)
                        if name_matches:
                            idx = [o.lower() for o in options].index(name_matches[0])
                            selected = options[idx]
                    if selected:
                        if saved_message:
                            clean_msg = saved_message
                            text = f"send a whatsapp to {selected} saying {clean_msg}"
                            clean_text = text.lower().strip(" ,!?.-")
                            self.last_active_time = __import__('time').time()
                            local_response = await self.loop.run_in_executor(self.executor, self.gatekeeper.route_command, clean_text)
                            if local_response and local_response.startswith("Message sent"):
                                pass
                            else:
                                self.last_active_time = __import__('time').time()
                            self.pending_context = None
                            self.pending_contact = None
                            self.is_active = False
                            if local_response:
                                self.last_spoken_text = local_response
                                self._set_ui_state("speaking", local_response)
                                print(f"Jarvis: {local_response}")
                                try:
                                    await asyncio.wait_for(self.loop.run_in_executor(self.executor, self.tts.speak, local_response), timeout=20)
                                except:
                                    pass
                                finally:
                                    self.last_speech_time = __import__('time').time()
                                    self.stt.flush_requested = True
                                    if self.ui_state in ["thinking", "speaking"]:
                                        self._set_ui_state("idle", "ONLINE")
                                if hasattr(self, 'non_llm_events'):
                                    self.non_llm_events.append({"user": text, "jarvis": local_response})
                            return
                        else:
                            self.pending_context = f"whatsapp_msg_{selected}"
                            try:
                                await asyncio.wait_for(
                                    self.loop.run_in_executor(self.executor, self.tts.speak, f"What would you like to say to {selected}?"),
                                    timeout=5
                                )
                            except:
                                pass
                            self.is_active = True
                            self.last_active_time = __import__('time').time()
                            return
                    else:
                        self.pending_contact = None
                        try:
                            await asyncio.wait_for(
                                self.loop.run_in_executor(self.executor, self.tts.speak, "Sorry, I didn't catch that. Please try again with a valid name or number."),
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

            self.last_active_time = _time.time()

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
                self._cleanup_opencode()
                
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
                finally:
                    self.last_speech_time = _time.time()
                    self.stt.flush_requested = True
                
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
                    self.last_speech_time = _time.time()
                    self.stt.flush_requested = True
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
            self.last_speech_time = _time.time()
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

        # Start Power Monitor (auto-switch CUDA/CPU on AC/battery)
        plugged, batt = get_power_state()
        if batt is not None:
            print(f"[PowerMonitor] Laptop detected — battery={batt}%, plugged={'Yes' if plugged else 'No'}")
            self.power_monitor = PowerMonitor(self._on_power_change, poll_interval=15)
            self.power_monitor.start()
        else:
            print("[PowerMonitor] Desktop detected — CUDA will be used permanently.")

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
                    self.last_active_time = _time.time()

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
        sys.exit(0)