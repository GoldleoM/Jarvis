import sys
import os
import asyncio

# Fix print() crashing in pythonw by redirecting to a log file
log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jarvis.log")
log_file = open(log_path, "a", encoding="utf-8")

class LogStream:
    def write(self, text):
        try:
            log_file.write(text)
            log_file.flush()
        except:
            pass
    def flush(self):
        try:
            log_file.flush()
        except:
            pass
    def isatty(self):
        return False

if sys.stdout is None:
    sys.stdout = LogStream()
if sys.stderr is None:
    sys.stderr = LogStream()

from PySide6.QtWidgets import QApplication, QMainWindow, QSystemTrayIcon, QMenu
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtCore import QObject, Slot, Signal, Qt, QUrl, QTimer
from PySide6.QtGui import QColor, QIcon, QAction, QPixmap

import qasync

# Import the existing backend
from main import VoiceEngine

class BackendBridge(QObject):
    stateChanged = Signal(str, str) # state, text
    micTestCompleted = Signal(str)

    def __init__(self, engine):
        super().__init__()
        self.engine = engine
        self.window = None  # Will be set later

    @Slot(str)
    def receive_input(self, text):
        print(f"[UI] Input received: {text}")
        if self.engine and self.engine.loop:
            # Artificially prepend the wake word so text commands process instantly, UNLESS we are already actively listening/taking notes
            if not self.engine.detect_wake_word(text.lower()):
                if not getattr(self.engine, 'is_active', False) and not getattr(self.engine, 'notes_mode', False):
                    text = f"{self.engine.wake_word} {text}"
            self.engine.loop.call_soon_threadsafe(self.engine.queue.put_nowait, text)

    @Slot()
    def cancel_task(self):
        print("[UI] Cancel requested")
        if self.engine and self.engine.current_task and not self.engine.current_task.done():
            self.engine.current_task.cancel()
            self.stateChanged.emit("idle", "CANCELLED")

    @Slot(result=str)
    def get_settings(self):
        import json
        import os
        import importlib
        import sys
        
        # We need to reload config to get the latest written values if they changed
        try:
            if 'config' in sys.modules:
                importlib.reload(sys.modules['config'])
            import config
        except ImportError:
            config = None
            
        s = {
            "WAKE_WORD": getattr(config, "WAKE_WORD", "jarvis") if config else "jarvis",
            "MIC_INDEX": getattr(config, "MIC_INDEX", None) if config else None,
            "WHISPER_MODEL": getattr(config, "WHISPER_MODEL", "medium.en") if config else "medium.en",
            "WHISPER_COMPUTE_TYPE": getattr(config, "WHISPER_COMPUTE_TYPE", "float16") if config else "float16",
            "VAD_THRESHOLD": getattr(config, "VAD_THRESHOLD", 0.5) if config else 0.5,
            "OPENCODE_PROVIDER": "opencode",
            "OPENCODE_MODEL": "big-pickle",
            "ORB_COLOR": "#00ffff",
            "ORB_GLOW": "#0088ff"
        }
        
        config_json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
        try:
            if os.path.exists(config_json_path):
                with open(config_json_path, "r", encoding="utf-8") as f:
                    config_data = json.load(f)
                    
                model = config_data.get("model", {})
                if "providerID" in model: s["OPENCODE_PROVIDER"] = model["providerID"]
                if "modelID" in model: s["OPENCODE_MODEL"] = model["modelID"]
                
                ui = config_data.get("UI", {})
                if "ORB_COLOR" in ui: s["ORB_COLOR"] = ui["ORB_COLOR"]
                if "ORB_GLOW" in ui: s["ORB_GLOW"] = ui["ORB_GLOW"]
                if "UI_SHORTCUT" in ui: s["UI_SHORTCUT"] = ui["UI_SHORTCUT"]
        except Exception as e:
            print(f"Error loading config.json: {e}")
            
        return json.dumps(s)

    @Slot(result=str)
    def get_microphones(self):
        import sounddevice as sd
        import json
        mics = [{"index": -1, "name": "System Default"}]
        try:
            devices = sd.query_devices()
            for i, dev in enumerate(devices):
                # Only include devices that have input channels (microphones)
                if dev['max_input_channels'] > 0:
                    mics.append({"index": i, "name": dev['name']})
        except Exception as e:
            print(f"Error querying microphones: {e}")
        return json.dumps(mics)

    @Slot(int)
    def test_mic(self, mic_index):
        import sounddevice as sd
        import numpy as np
        import threading

        def run_test():
            try:
                duration = 1.5 # Listen for 1.5 seconds
                fs = 16000
                idx = None if mic_index == -1 else mic_index
                recording = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype='float32', device=idx)
                sd.wait()
                peak = np.max(np.abs(recording))
                peak_pct = int(peak * 100)
                if peak_pct == 0:
                    msg = "Peak: 0% (Mic works, but no sound detected)"
                else:
                    msg = f"Success! Peak volume: {peak_pct}%"
                self.micTestCompleted.emit(msg)
            except Exception as e:
                self.micTestCompleted.emit(f"Error: {e}")

        threading.Thread(target=run_test, daemon=True).start()

    @Slot(str)
    def save_settings(self, settings_json):
        import json
        import os
        import re
        import asyncio
        
        try:
            s = json.loads(settings_json)
            print(f"[UI] Saving new settings: {s}")
            
            # 1. Save to config.json
            config_json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
            config_data = {}
            if os.path.exists(config_json_path):
                with open(config_json_path, "r", encoding="utf-8") as f:
                    try:
                        config_data = json.load(f)
                    except:
                        pass
                
            if "model" not in config_data:
                config_data["model"] = {}
            config_data["model"]["providerID"] = s.get("OPENCODE_PROVIDER", "opencode")
            config_data["model"]["modelID"] = s.get("OPENCODE_MODEL", "big-pickle")
            
            config_data["UI"] = {
                "ORB_COLOR": s.get("ORB_COLOR", "#00ffff"),
                "ORB_GLOW": s.get("ORB_GLOW", "#0088ff"),
                "UI_SHORTCUT": s.get("UI_SHORTCUT", "alt+space")
            }
            with open(config_json_path, "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=4)
                
            # 2. Modify config.py
            config_py_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.py")
            if os.path.exists(config_py_path):
                with open(config_py_path, "r", encoding="utf-8") as f:
                    config_py_content = f.read()
                    
                if s.get("WAKE_WORD"):
                    config_py_content = re.sub(r'WAKE_WORD\s*=\s*".*"', f'WAKE_WORD = "{s["WAKE_WORD"]}"', config_py_content)
                    
                if s.get("MIC_INDEX") is not None and str(s.get("MIC_INDEX")).strip() != "":
                    config_py_content = re.sub(r'MIC_INDEX\s*=\s*.*', f'MIC_INDEX = {s["MIC_INDEX"]}', config_py_content)
                else:
                    config_py_content = re.sub(r'MIC_INDEX\s*=\s*.*', f'MIC_INDEX = None', config_py_content)
                    
                if s.get("WHISPER_MODEL"):
                    config_py_content = re.sub(r'WHISPER_MODEL\s*=\s*".*"', f'WHISPER_MODEL = "{s["WHISPER_MODEL"]}"', config_py_content)
                    
                if s.get("WHISPER_COMPUTE_TYPE"):
                    config_py_content = re.sub(r'WHISPER_COMPUTE_TYPE\s*=\s*".*"', f'WHISPER_COMPUTE_TYPE = "{s["WHISPER_COMPUTE_TYPE"]}"', config_py_content)
                    
                if s.get("VAD_THRESHOLD") is not None:
                    config_py_content = re.sub(r'VAD_THRESHOLD\s*=\s*.*', f'VAD_THRESHOLD = {s["VAD_THRESHOLD"]}', config_py_content)
                    
                with open(config_py_path, "w", encoding="utf-8") as f:
                    f.write(config_py_content)
                    
            # 3. Hot Reload the engine
            if self.engine and hasattr(self.engine, "hot_reload") and self.engine.loop:
                # Fire and forget hot_reload
                asyncio.run_coroutine_threadsafe(self.engine.hot_reload(s), self.engine.loop)
                
            # 4. Update the global UI hotkey live
            if self.window and hasattr(self.window, "update_hotkey"):
                self.window.update_hotkey(s.get("UI_SHORTCUT", "alt+space"))
                
        except Exception as e:
            print(f"[UI] Error saving settings: {e}")
            
    @Slot(int, int)
    def move_window(self, dx, dy):
        if self.window:
            pos = self.window.pos()
            self.window.move(pos.x() + dx, pos.y() + dy)
            
    @Slot(str)
    def update_mask(self, rects_json):
        import json
        from PySide6.QtGui import QRegion
        if self.window:
            try:
                rects = json.loads(rects_json)
                mask = QRegion()
                for r in rects:
                    if r.get('shape') == 'ellipse':
                        mask = mask.united(QRegion(int(r['x']), int(r['y']), int(r['w']), int(r['h']), QRegion.Ellipse))
                    else:
                        mask = mask.united(QRegion(int(r['x']), int(r['y']), int(r['w']), int(r['h']), QRegion.Rectangle))
                
                # If the mask is empty, passing it to setMask actually REMOVES the mask in Qt,
                # which causes the transparent window to block all clicks. 
                # Fix: provide a 1x1 dummy region off-screen.
                if mask.isEmpty():
                    mask = QRegion(-1, -1, 1, 1)
                    
                self.window.setMask(mask)
            except Exception as e:
                print(f"Mask update error: {e}")


from PySide6.QtWebEngineCore import QWebEnginePage

class WebPage(QWebEnginePage):
    def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
        print(f"[JS Console] Line {lineNumber}: {message}")

class TransparentWindow(QMainWindow):
    toggleUISignal = Signal()

    def __init__(self, bridge):
        super().__init__()
        self.bridge = bridge
        self.current_shortcut = None
        
        self.toggleUISignal.connect(self.toggle_ui)
        
        # Frameless, stay on top, tool window (no taskbar)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        
        # Force keep-on-top timer to prevent glitching behind apps
        self.top_timer = QTimer(self)
        self.top_timer.timeout.connect(self.raise_)
        self.top_timer.start(500)
        
        # Resize and position full screen
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(0, 0, screen.width(), screen.height())

        # WebEngine setup
        self.browser = QWebEngineView(self)
        self.page = WebPage(self.browser)
        self.browser.setPage(self.page)
        self.browser.setAttribute(Qt.WA_TranslucentBackground, True)
        self.browser.page().setBackgroundColor(QColor(0, 0, 0, 0)) # transparent background
        
        self.channel = QWebChannel()
        self.channel.registerObject("backend", self.bridge)
        self.browser.page().setWebChannel(self.channel)
        
        # Load local HTML
        html_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "ui", "index.html"))
        self.browser.setUrl(QUrl.fromLocalFile(html_path))
        
        self.setCentralWidget(self.browser)
        
        # System Tray
        self.tray = QSystemTrayIcon(self)
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jarvis.ico")
        if os.path.exists(icon_path):
            self.tray.setIcon(QIcon(icon_path))
            self.setWindowIcon(QIcon(icon_path))
        else:
            pixmap = QPixmap(32, 32)
            pixmap.fill(QColor("cyan")) # Placeholder icon
            self.tray.setIcon(QIcon(pixmap))
            
        self.setup_global_hotkey()
        
        menu = QMenu()
        show_action = QAction("Show UI", self)
        show_action.triggered.connect(self.show_ui)
        hide_action = QAction("Hide UI", self)
        hide_action.triggered.connect(self.hide_ui)
        view_logs_action = QAction("View Logs", self)
        view_logs_action.triggered.connect(self.view_logs)
        copy_logs_action = QAction("Copy Logs", self)
        copy_logs_action.triggered.connect(self.copy_logs)
        clear_logs_action = QAction("Clear Logs", self)
        clear_logs_action.triggered.connect(self.clear_logs)
        restart_action = QAction("Restart Jarvis", self)
        restart_action.triggered.connect(self.restart_app)
        quit_action = QAction("Quit Jarvis", self)
        quit_action.triggered.connect(self.quit_app)
        
        menu.addAction(show_action)
        menu.addAction(hide_action)
        menu.addAction(view_logs_action)
        menu.addAction(copy_logs_action)
        menu.addAction(clear_logs_action)
        menu.addAction(restart_action)
        menu.addAction(quit_action)
        self.tray.setContextMenu(menu)
        self.tray.show()

    @Slot()
    def show_ui(self):
        self.browser.page().runJavaScript("""
            document.getElementById('hud-container').style.display = 'flex';
            if (typeof sendMaskUpdate === 'function') sendMaskUpdate();
        """)

    @Slot()
    def hide_ui(self):
        self.browser.page().runJavaScript("""
            document.getElementById('hud-container').style.display = 'none';
            if (typeof sendMaskUpdate === 'function') sendMaskUpdate();
        """)
        
    @Slot()
    def toggle_ui(self):
        self.browser.page().runJavaScript("""
            var el = document.getElementById('hud-container');
            if (el.style.display === 'none' || el.style.display === '') {
                el.style.display = 'flex';
            } else {
                el.style.display = 'none';
            }
            if (typeof sendMaskUpdate === 'function') sendMaskUpdate();
        """)

    def setup_global_hotkey(self):
        import json
        import os
        config_json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
        shortcut = "alt+space"
        try:
            if os.path.exists(config_json_path):
                with open(config_json_path, "r", encoding="utf-8") as f:
                    config_data = json.load(f)
                    shortcut = config_data.get("UI", {}).get("UI_SHORTCUT", "alt+space")
        except:
            pass
        self.update_hotkey(shortcut)

    def update_hotkey(self, new_shortcut):
        import keyboard
        if self.current_shortcut:
            try:
                keyboard.remove_hotkey(self.current_shortcut)
            except Exception as e:
                print(f"[UI] Could not remove old hotkey: {e}")
        self.current_shortcut = new_shortcut
        try:
            # We emit the signal from the keyboard listener thread which wakes up Qt's event loop
            keyboard.add_hotkey(self.current_shortcut, self.toggleUISignal.emit)
            print(f"[UI] Global hotkey registered: {self.current_shortcut}")
        except Exception as e:
            print(f"[UI] Failed to register global hotkey '{self.current_shortcut}': {e}")
        
    def restart_app(self):
        import sys
        import subprocess
        # Restart the entire Python script/executable
        subprocess.Popen([sys.executable] + sys.argv)
        self.quit_app()

    def quit_app(self):
        QApplication.quit()

    def view_logs(self):
        import os
        log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jarvis.log")
        if os.path.exists(log_path):
            os.startfile(log_path)
            
    def copy_logs(self):
        import os
        log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jarvis.log")
        if os.path.exists(log_path):
            try:
                with open(log_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                clipboard = QApplication.clipboard()
                clipboard.setText(content)
            except Exception as e:
                print(f"Failed to copy logs: {e}")
            
    def clear_logs(self):
        import os
        log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jarvis.log")
        try:
            with open(log_path, 'w', encoding='utf-8') as f:
                f.write('')
        except Exception as e:
            print(f"Failed to clear logs: {e}")


async def state_monitor(engine, bridge):
    last_state = None
    last_text = None
    while True:
        try:
            curr_state = getattr(engine, 'ui_state', 'idle')
            curr_text = getattr(engine, 'ui_text', 'ONLINE')
            
            if curr_state != last_state or curr_text != last_text:
                last_state = curr_state
                last_text = curr_text
                bridge.stateChanged.emit(curr_state, curr_text)
        except Exception as e:
            print(f"Monitor error: {e}")
            
        await asyncio.sleep(0.1)

async def run_app():
    # Setup PySide6 integration with asyncio
    engine = VoiceEngine(debug=False, ui_mode=True)
    bridge = BackendBridge(engine)
    window = TransparentWindow(bridge)
    bridge.window = window
    window.show()
    
    # Start the monitor loop
    asyncio.create_task(state_monitor(engine, bridge))
    
    # Start the voice engine
    asyncio.create_task(engine.run())

if __name__ == "__main__":
    # Fix WebGL on transparent windows
    QApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
    
    # Fix DPI warnings
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "0"
    
    # Allow high refresh rate monitors (144Hz/240Hz) by disabling Chromium's artificial 60fps cap
    os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-frame-rate-limit"
    
    app = QApplication(sys.argv)
    app.setApplicationName("Jarvis")
    app.setApplicationDisplayName("Jarvis")
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    
    with loop:
        loop.create_task(run_app())
        try:
            loop.run_forever()
        except RuntimeError:
            pass
