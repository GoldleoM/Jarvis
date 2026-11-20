"""Use the signed-in Codex app server for Jarvis conversations over local stdio."""
import asyncio
from collections import deque
from contextlib import asynccontextmanager
import json
import os
from pathlib import Path
import shutil
import subprocess

SECTION = "Jarvis Chats"
CHAT_FOLDER = Path.home() / SECTION
CONFIG = Path(__file__).with_name("config.json")
VOICE_INSTRUCTIONS = (
    "You are Jarvis, a voice assistant. Answer ordinary questions directly in concise, "
    "natural sentences that sound good aloud. Use tools for coding or file work when requested."
)


class CodexError(Exception):
    """A short error that Jarvis can show or speak."""


def codex_binary():
    if os.name != "nt":
        binary = shutil.which("codex")
    else:
        binary = shutil.which("codex.exe")
        if not binary:
            # Explorer may lack npm on PATH. Launch its native binary without cmd.exe.
            shim = shutil.which("codex.cmd")
            roots = [Path(shim).parent] if shim else []
            if os.environ.get("APPDATA"):
                roots.append(Path(os.environ["APPDATA"]) / "npm")
            for root in roots:
                package = root / "node_modules/@openai/codex"
                for pattern in ("node_modules/@openai/codex-win32-*/vendor/*", "vendor/*"):
                    for target in package.glob(pattern):
                        for relative in ("bin/codex.exe", "codex/codex.exe"):
                            if (target / relative).is_file():
                                return str(target / relative)
    if not binary:
        raise CodexError("Install the Codex CLI and run codex login to connect Jarvis.")
    return binary


class AppServer:
    def __init__(self, process):
        self.process = process
        self.request_id = 0

    async def send(self, message):
        self.process.stdin.write(json.dumps(message).encode() + b"\n")
        await self.process.stdin.drain()

    async def receive(self):
        while line := await self.process.stdout.readline():
            event = json.loads(line)
            if "id" in event and "method" in event:
                # A voice turn has no interactive tool-approval dialog.
                await self.send({"id": event["id"], "error": {"code": -32601,
                                 "message": "This interaction requires the Codex app."}})
                continue
            return event
        raise CodexError("The Codex connection closed. Please try again.")

    async def request(self, method, params, *, early_events=None):
        self.request_id += 1
        await self.send({"method": method, "id": self.request_id, "params": params})
        while True:
            event = await self.receive()
            if event.get("id") == self.request_id:
                if "error" in event:
                    raise CodexError("Codex reported: " + event["error"]["message"][:240])
                return event["result"]
            if early_events is not None and event.get("method") in {"item/completed", "turn/completed"}:
                early_events.append(event)

    async def section_id(self):
        cursor = None
        while True:
            page = await self.request("threadSection/list", {"cursor": cursor})
            for section in page["data"]:
                if section["name"] == SECTION:
                    return section["id"]
            cursor = page.get("nextCursor")
            if not cursor:
                created = await self.request("threadSection/create", {"name": SECTION})
                return created["section"]["id"]

    async def answer(self, thread_id, prompt):
        pending = deque()
        result = await self.request("turn/start", {"threadId": thread_id,
                                    "input": [{"type": "text", "text": prompt}]}, early_events=pending)
        turn_id = result["turn"]["id"]
        try:
            return await self.final_text(thread_id, turn_id, pending)
        except asyncio.CancelledError:
            try:
                await asyncio.wait_for(self.request("turn/interrupt", {"threadId": thread_id, "turnId": turn_id}), 2)
            except (asyncio.TimeoutError, OSError, CodexError):
                pass
            raise

    async def final_text(self, thread_id, turn_id, pending):
        text = ""
        while True:
            event = pending.popleft() if pending else await self.receive()
            params = event.get("params", {})
            if params.get("threadId") != thread_id:
                continue
            if event.get("method") == "item/completed" and params.get("turnId") == turn_id:
                item = params["item"]
                if item["type"] == "agentMessage" and item.get("phase") != "commentary":
                    text = item["text"].strip()
            if event.get("method") != "turn/completed" or params["turn"]["id"] != turn_id:
                continue
            turn = params["turn"]
            if turn["status"] != "completed":
                reason = (turn.get("error") or {}).get("message") or turn["status"]
                raise CodexError("Codex could not finish the reply: " + reason[:240])
            if not text:
                raise CodexError("Codex finished without a text reply. Please try again.")
            return text


@asynccontextmanager
async def connect(folder):
    folder.mkdir(parents=True, exist_ok=True)
    process = await asyncio.create_subprocess_exec(
        codex_binary(), "app-server", cwd=folder,
        stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL, limit=16 * 1024 * 1024,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    try:
        server = AppServer(process)
        await server.request("initialize", {"clientInfo": {"name": "jarvis", "title": "Jarvis", "version": "1"},
                                             "capabilities": {"experimentalApi": True}})
        await server.send({"method": "initialized"})
        yield server
    finally:
        if process.returncode is None:
            process.stdin.close()
            try:
                await asyncio.wait_for(process.communicate(), timeout=3)
            except asyncio.TimeoutError:
                if process.returncode is None:
                    process.kill()
                await process.communicate()


class CodexChat:
    """A Jarvis launch owns one conversation. Only its returned ID can be resumed."""
    def __init__(self, folder=CHAT_FOLDER):
        self.folder = folder
        self.thread_id = None
        self.lock = asyncio.Lock()

    async def ask(self, prompt, *, title=None, temporary=False):
        try:
            async with self.lock:
                return await asyncio.wait_for(self._ask(prompt, title, temporary), timeout=180)
        except asyncio.TimeoutError as exc:
            raise CodexError("Codex took too long to reply. You can try again.") from exc
        except (OSError, ValueError) as exc:
            raise CodexError("Jarvis could not connect to Codex. Check that codex login status shows you are signed in.") from exc

    async def _ask(self, prompt, title, temporary):
        async with connect(self.folder) as server:
            params = {"cwd": str(self.folder), "sandbox": "read-only" if temporary else "workspace-write",
                      "approvalPolicy": "never", "developerInstructions": VOICE_INSTRUCTIONS}
            try:
                model = json.loads(CONFIG.read_text(encoding="utf-8")).get("codex", {}).get("model")
            except (OSError, ValueError):
                model = None
            if model:
                params["model"] = model
            if self.thread_id and not temporary:
                await server.request("thread/resume", dict(params, threadId=self.thread_id, excludeTurns=True))
                thread_id = self.thread_id
            else:
                result = await server.request("thread/start", dict(params, ephemeral=temporary))
                thread_id = result["thread"]["id"]
                if not temporary:
                    section_id = await server.section_id()
                    await server.request("thread/section/move", {"threadId": thread_id, "sectionId": section_id})
                    await server.request("thread/name/set", {"threadId": thread_id,
                                         "name": " ".join((title or prompt).split())[:80]})
                    self.thread_id = thread_id
            return await server.answer(thread_id, prompt)
