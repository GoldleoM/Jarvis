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
    def __init__(self, bridge):
        super().__init__()
        self.bridge = bridge
        
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
        
        menu = QMenu()
        show_action = QAction("Show UI", self)
        show_action.triggered.connect(self.show_ui)
        hide_action = QAction("Hide UI", self)
        hide_action.triggered.connect(self.hide_ui)
        quit_action = QAction("Quit Jarvis", self)
        quit_action.triggered.connect(self.quit_app)
        
        menu.addAction(show_action)
        menu.addAction(hide_action)
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
        
    def quit_app(self):
        QApplication.quit()


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
