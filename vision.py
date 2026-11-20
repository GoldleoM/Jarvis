"""Answer explicit screen questions from a single, current, local screenshot."""
import asyncio
import base64
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

import aiohttp
from PIL import ImageGrab

VISION_MODEL = "moondream:latest"
OLLAMA_URL = "http://127.0.0.1:11434/api/generate"


def _grab_screen():
    # The primary display is also the display used by the Jarvis HUD.
    return ImageGrab.grab().convert("RGB")


def capture_screenshot():
    """Compatibility helper for callers that need a PNG path. Caller owns the file."""
    try:
        image = _grab_screen()
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as output:
            image.save(output, format="PNG")
            return output.name
    except OSError:
        return None


def encode_image(image_path):
    with open(image_path, "rb") as source:
        return base64.b64encode(source.read()).decode("ascii")


async def _ocr(image):
    from winrt.windows.graphics.imaging import BitmapAlphaMode, BitmapPixelFormat, SoftwareBitmap
    from winrt.windows.media.ocr import OcrEngine
    from winrt.windows.storage.streams import DataWriter

    engine = OcrEngine.try_create_from_user_profile_languages()
    if engine is None:
        raise RuntimeError("Windows has no OCR language installed")
    image = image.convert("RGBA")
    image.thumbnail((OcrEngine.max_image_dimension,) * 2)
    with DataWriter() as writer:
        writer.write_bytes(image.tobytes("raw", "BGRA"))
        with SoftwareBitmap.create_copy_from_buffer(
            writer.detach_buffer(), BitmapPixelFormat.BGRA8, *image.size, BitmapAlphaMode.IGNORE
        ) as bitmap:
            result = await engine.recognize_async(bitmap)
    return result.lines, image.size


def _target_label(prompt):
    cmd = re.sub(r"^(?:(?:please|can you|could you|would you)\s+)+", "", prompt.strip(), flags=re.I)
    match = re.match(r"(?:find|locate|look for|search for|where (?:is|are)|do you see|see|is there)\s+(.+)", cmd, re.I)
    if not match:
        return None
    target = re.sub(r"\s+on (?:the |my |this )?(?:screen|display|monitor)\b.*", "", match[1], flags=re.I)
    quoted = re.search(r'["“](.+?)["”]', target)
    if quoted:
        return quoted[1]
    target = re.sub(r"^(?:the |a |an )?(?:(?:button|text|label) (?:called |saying |labeled )?)?", "", target, flags=re.I)
    return re.sub(r"\s+(?:button|label)$", "", target.strip(" '.?!"), flags=re.I).strip()


def _find_label(lines, size, target):
    needle = re.findall(r"\w+", target.casefold())
    if not needle:
        return None
    for line in lines:
        words = [(token, word.bounding_rect) for word in line.words
                 for token in re.findall(r"\w+", word.text.casefold())]
        tokens = [token for token, _ in words]
        for index in range(len(words) - len(needle) + 1):
            if tokens[index:index + len(needle)] == needle:
                first, last = words[index][1], words[index + len(needle) - 1][1]
                x = (first.x + last.x + last.width) / (2 * size[0])
                y = (first.y + first.height / 2) / size[1]
                horizontal = ("left", "center", "right")[min(2, int(x * 3))]
                vertical = ("upper", "middle", "lower")[min(2, int(y * 3))]
                return f'I found "{target}" in the {vertical} {horizontal} of the screen.'
    return None


def _excerpt(lines):
    text = " ".join(line.text for line in lines).strip()
    if len(text) <= 650:
        return text
    return text[:650].rsplit(" ", 1)[0] + "…"


def _png(image):
    with io.BytesIO() as data:
        image.save(data, format="PNG")
        return data.getvalue()


async def _describe_locally(png, question):
    # Keep the vision model's native DLLs and GPU allocation outside the voice engine.
    env = dict(os.environ, MKL_THREADING_LAYER="SEQUENTIAL")
    env.pop("KMP_DUPLICATE_LIB_OK", None)
    worker = await asyncio.create_subprocess_exec(
        sys.executable, "-X", "utf8", str(Path(__file__).with_name("vision_model.py")),
        stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        env=env, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    try:
        request = json.dumps(question).encode("utf-8") + b"\n" + png
        stdout, stderr = await asyncio.wait_for(worker.communicate(request), timeout=120)
        if worker.returncode != 0:
            details = stderr.decode("utf-8", errors="replace").strip().splitlines()
            raise RuntimeError(details[-1][:240] if details else f"worker exit {worker.returncode}")
        return json.loads(stdout)
    finally:
        if worker.returncode is None:
            try:
                worker.kill()
            except ProcessLookupError:
                pass
            await worker.wait()


async def _describe_with_ollama(png, question, model):
    payload = {"model": model, "prompt": question, "images": [base64.b64encode(png).decode("ascii")],
               "stream": False, "system": "Answer the user's question about the image in a few spoken sentences. "
                                         "Report uncertainty when the detail is unreadable.",
               "options": {"num_predict": 160, "temperature": 0.2}}
    timeout = aiohttp.ClientTimeout(total=120, sock_connect=2)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(OLLAMA_URL, json=payload) as response:
            response.raise_for_status()
            return (await response.json()).get("response", "").strip()


async def analyze_image(image, prompt, model=VISION_MODEL, *, target=None):
    target = target or _target_label(prompt)
    read_text = re.search(r"\bread\b|what (?:does|do) .+ say\b", prompt, re.I)
    lines = None
    if target or read_text:
        try:
            lines, size = await _ocr(image)
        except (ImportError, OSError, RuntimeError) as error:
            print(f"[Vision] OCR unavailable: {error}")
        if lines is not None:
            if target:
                found = _find_label(lines, size, target)
                if found:
                    return found
                # Exact label lookups should report what OCR actually recognized.
                if re.search(r'\b(?:text|label|button)\b|["“]', prompt, re.I):
                    return f'I could not read a label matching "{target}" on this screen.'
            elif read_text:
                if re.search(r"\b(?:error|warning)\b", prompt, re.I):
                    indices = {j for i, line in enumerate(lines) if re.search(
                        r"\berror\b|\bwarning\b|failed|exception", line.text, re.I)
                               for j in (i, i + 1)}
                    selected = [line for i, line in enumerate(lines) if i in indices]
                    if selected:
                        return _excerpt(selected)
                elif lines:
                    return _excerpt(lines)
    png = await asyncio.to_thread(_png, image)
    try:
        answer = await _describe_with_ollama(png, prompt, model)
        if answer:
            return answer
    except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as error:
        print(f"[Vision] Local Ollama unavailable: {type(error).__name__}")

    try:
        answer = await _describe_locally(png, prompt)
        if answer:
            return answer
    except (asyncio.TimeoutError, OSError, RuntimeError, ValueError) as error:
        print(f"[Vision] Local image model unavailable: {error}")
    if lines is None:
        try:
            lines, _ = await _ocr(image)
        except (ImportError, OSError, RuntimeError):
            lines = []
    excerpt = _excerpt(lines)
    if excerpt:
        return "Image description is unavailable. The visible text includes: " + excerpt
    return "I couldn't read text or get a visual description. Check the local vision model setup."


async def analyze_screen(prompt="Describe what is visible on this screen.", model=VISION_MODEL, *, target=None):
    try:
        image = await asyncio.to_thread(_grab_screen)
    except OSError as error:
        print(f"[Vision] Capture failed: {error}")
        return "I couldn't capture the current screen."
    return await analyze_image(image, prompt, model, target=target)


async def look_at_screen():
    return await analyze_screen()


async def find_text_on_screen(target_text=None):
    if target_text:
        return await analyze_screen(f'Find the label "{target_text}" on the screen.', target=target_text)
    return await analyze_screen("Read the visible text on the screen.")


if __name__ == "__main__":
    print(asyncio.run(look_at_screen()))
