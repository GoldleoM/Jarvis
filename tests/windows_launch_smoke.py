"""Exercise the built Windows launcher, local Qt page, microphone and voice engine.

Run with python tests/windows_launch_smoke.py from a configured Jarvis checkout.
Requires websocket-client for the test driver. The test opens the HUD and plays
its replies, then asks Jarvis to quit. Only the test process enables Qt debugging.
"""
import json
import argparse
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import time
from urllib.request import urlopen

import psutil
import keyboard
from PIL import ImageChops, ImageGrab
from websocket import create_connection


def wait_for(description, check, timeout=60):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = check()
        if result:
            print(description, flush=True)
            return result
        time.sleep(0.25)
    raise TimeoutError(description)


def exercise(app, port, test_tools=False, test_codex=False):
    def find_page():
        if app.poll() is not None:
            raise RuntimeError(f"Launcher exited with {app.returncode}")
        try:
            with urlopen(f"http://127.0.0.1:{port}/json/list", timeout=1) as result:
                for page in json.load(result):
                    if page["url"].endswith("/ui/index.html"):
                        return page["webSocketDebuggerUrl"]
        except OSError:
            pass

    url = wait_for("Opened the packaged HUD", find_page)
    client = create_connection(url, timeout=45, suppress_origin=True)

    def js(expression, loading=False):
        client.send(json.dumps({"id": 1, "method": "Runtime.evaluate",
                                "params": {"expression": expression, "returnByValue": True}}))
        while True:
            reply = json.loads(client.recv())
            if reply.get("id") == 1:
                if "error" in reply:
                    if loading and "context" in reply["error"]["message"].lower():
                        return False
                    raise RuntimeError(reply["error"])
                result = reply["result"]
                if "exceptionDetails" in result:
                    raise RuntimeError(result["exceptionDetails"])
                return result["result"].get("value")

    def send(text):
        js(f"chatInput.value = {json.dumps(text)}; "
           "chatInput.dispatchEvent(new KeyboardEvent('keypress', {key:'Enter', bubbles:true}));")

    def check_reply(command, expected):
        start = js("chatHistory.length")
        send(command)
        wait_for(f"Answered {command!r}", lambda: js(
            f"chatHistory.slice({start}).some(e => e.speaker === 'Jarvis' && e.text.includes({json.dumps(expected)}))"))
        wait_for("Ready for the next command", lambda: js("backendState === 'idle'"))

    try:
        wait_for("Connected Qt to the page", lambda: js("typeof backend !== 'undefined' && !!backend", loading=True))
        # A functioning WebChannel and a 200px canvas can both exist off-screen.
        wait_for("Orb and chat input fit inside the visible viewport", lambda: js("""
            ['canvas-container', 'chat-input'].every(id => {
                const r = document.getElementById(id).getBoundingClientRect();
                return r.width > 0 && r.height > 0 && r.left >= 0 && r.top >= 0
                    && r.right <= innerWidth && r.bottom <= innerHeight;
            })
        """))
        js("settingsBtn.click()")
        wait_for("Read settings and enumerated microphones",
                 lambda: js("document.querySelectorAll('#mic-options div').length > 1 && "
                            "document.getElementById('setting-wake-word').value.length > 0"))
        js("closeSettingsBtn.click()")
        if js("document.getElementById('setting-ui-shortcut').value.toLowerCase() === 'alt+space'"):
            # The frameless overlay fills the primary screen. Capture only the orb.
            bounds = js("""(() => {
                const r = document.getElementById('canvas-container').getBoundingClientRect();
                return [screenX + r.left, screenY + r.top, screenX + r.right, screenY + r.bottom]
                    .map(n => Math.round(n * devicePixelRatio));
            })()""")

            def capture_orb():
                return ImageGrab.grab(bbox=tuple(bounds), all_screens=True, include_layered_windows=True)

            def changed_since(reference):
                delta = ImageChops.difference(capture_orb(), reference).convert("L")
                return sum(delta.histogram()[32:]) > 0.01 * delta.width * delta.height

            shown = capture_orb()
            keyboard.send("alt+space")
            wait_for("Hid the overlay with Alt+Space", lambda: js("document.getElementById('container').hidden"))
            wait_for("Orb disappeared from the Windows desktop", lambda: changed_since(shown))
            hidden = capture_orb()
            keyboard.send("alt+space")
            wait_for("Restored the overlay with Alt+Space", lambda: js("!document.getElementById('container').hidden"))
            wait_for("Orb reappeared on the Windows desktop", lambda: changed_since(hidden))
        assert js("chatInput.getBoundingClientRect().width > 0 && "
                  "(webGLSupported || document.querySelector('#canvas-container.fallback-orb') !== null)")
        wait_for("Voice engine ready", lambda: js("!chatInput.disabled"), timeout=180)
        js("settingsBtn.click(); testMicBtn.click()")
        wait_for("Recorded microphone test", lambda: js(
            "!testMicBtn.disabled && /Peak|Success/.test(document.getElementById('test-mic-result').innerText)"))
        js("closeSettingsBtn.click()")
        send("what time is it")
        wait_for("Received the local time reply", lambda: js(
            "chatHistory.some(e => e.speaker === 'Jarvis' && /\\d{1,2}:\\d{2}/.test(e.text))"))
        js("historyBtn.click()")
        assert js("historyModal.style.display === 'flex' && historyContent.innerText.includes('what time is it')")
        js("closeHistoryBtn.click()")
        wait_for("Returned to idle after the reply", lambda: js("backendState === 'idle'"))
        if test_tools:
            check_reply("what's fifteen percent of 80", "The answer is 12.")
            check_reply("set a timer", "How long")
            check_reply("two minutes and thirty seconds", "2 minutes and 30 seconds")
            # Give OCR a known label on the real desktop without changing user documents.
            import tkinter as tk
            fixture = tk.Tk()
            try:
                fixture.overrideredirect(True)
                fixture.geometry("+30+50")
                fixture.attributes("-topmost", True)
                tk.Label(fixture, text="Lunar Orchard", font=("Segoe UI", 36),
                         bg="white", fg="black", padx=20, pady=12).pack()
                fixture.update()
                check_reply("Find the Lunar Orchard label on my screen", 'I found "Lunar Orchard"')
            finally:
                fixture.destroy()
        if test_codex:
            check_reply("What is the capital of Japan?", "Tokyo")
            check_reply("Ask Codex which city you just named. Reply with just the city.", "Tokyo")
        send("goodbye")
    finally:
        client.close()
    assert app.wait(timeout=40) == 0, "The launcher must exit cleanly"
    print("Exited cleanly", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--tools", action="store_true", help="Also exercise arithmetic, timer follow-up and live OCR")
    parser.add_argument("--codex", action="store_true", help="Exercise a real Codex chat and follow-up")
    args = parser.parse_args()
    launcher = Path(__file__).resolve().parents[1] / "Jarvis.exe"
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    env = dict(os.environ, QTWEBENGINE_REMOTE_DEBUGGING=f"127.0.0.1:{port}")
    with tempfile.TemporaryDirectory() as cwd:
        app = subprocess.Popen([str(launcher)], cwd=cwd, env=env)
        try:
            exercise(app, port, args.tools, args.codex)
        finally:
            if app.poll() is None:
                for child in reversed(psutil.Process(app.pid).children(recursive=True)):
                    try:
                        child.kill()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                app.kill()
                app.wait()
