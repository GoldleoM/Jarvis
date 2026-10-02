import asyncio
import aiohttp
import base64
import io
import subprocess
import time
import json
import os

VISION_MODEL = "moondream:latest"
SCREENSHOT_PATH = os.path.join(os.environ.get('TEMP', os.path.expanduser('~')), '_jarvis_screen.png')

def capture_screenshot():
    """Capture the primary screen to a PNG file. Returns the file path."""
    try:
        result = subprocess.run(['powershell', '-Command', f'''
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$bounds = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$bitmap = New-Object System.Drawing.Bitmap $bounds.Width, $bounds.Height
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.CopyFromScreen($bounds.X, $bounds.Y, 0, 0, $bounds.Size)
$bitmap.Save('{SCREENSHOT_PATH}', [System.Drawing.Imaging.ImageFormat]::Png)
$graphics.Dispose()
$bitmap.Dispose()
Write-Output "OK"
'''], capture_output=True, text=True, timeout=10)
        
        if os.path.exists(SCREENSHOT_PATH):
            return SCREENSHOT_PATH
        return None
    except Exception as e:
        print(f"[Vision] Screenshot capture failed: {e}")
        return None


def encode_image(image_path):
    """Read an image file and return base64 encoded string."""
    with open(image_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')


async def analyze_screen(prompt="What do you see on this screen? Describe it briefly.", model=VISION_MODEL):
    """
    Take a screenshot and analyze it with the vision model.
    Returns a natural language description.
    """
    print(f"\n[Vision] Capturing screenshot for analysis...")
    start_time = time.time()
    
    # Capture screenshot in executor to avoid blocking
    image_path = await asyncio.get_event_loop().run_in_executor(None, capture_screenshot)
    
    if not image_path:
        return "I'm sorry, I couldn't capture the screen."
    
    # Encode image
    b64 = await asyncio.get_event_loop().run_in_executor(None, encode_image, image_path)
    print(f"[Vision] Screenshot captured ({len(b64)} bytes) in {time.time()-start_time:.1f}s")
    
    # System prompt for concise screen descriptions
    system_prompt = (
        "You are Jarvis, a precise voice assistant analyzing the user's screen. "
        "Describe what you see concisely in 1 to 3 short sentences. "
        "Focus on the most important elements: open windows, applications, content, and UI elements. "
        "Do not use markdown or formatting. Speak naturally."
    )
    
    url = "http://localhost:11434/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "images": [b64],
        "stream": False,
        "system": system_prompt,
        "options": {
            "num_predict": 200,
            "temperature": 0.3
        }
    }
    
    print(f"[Vision] Sending to {model}...")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=120) as response:
                if response.status == 200:
                    data = await response.json()
                    answer = data.get("response", "").strip()
                    elapsed = time.time() - start_time
                    print(f"[Vision] Analysis complete ({elapsed:.1f}s): {answer[:100]}...")
                    
                    if not answer:
                        return "I looked at the screen but couldn't make sense of it."
                    return answer
                else:
                    error_text = await response.text()
                    print(f"[Vision] API Error {response.status}: {error_text[:200]}")
                    return "I encountered an error while trying to analyze the screen."
    except asyncio.CancelledError:
        print("[Vision] Analysis cancelled by user.")
        raise
    except Exception as e:
        print(f"[Vision] Connection error: {e}")
        return "I'm unable to connect to the vision model. Please ensure Ollama is running."


async def look_at_screen():
    """
    Convenience function: capture and describe the screen.
    Returns a spoken-ready description.
    """
    description = await analyze_screen(
        "Describe what is currently displayed on the screen. What applications or windows are open? What is the user looking at?"
    )
    return description


async def find_text_on_screen(target_text=None):
    """
    Look at the screen and optionally search for specific text.
    If target_text is provided, look for it. Otherwise, read any visible text.
    """
    if target_text:
        prompt = f"Look at this screen carefully. Can you find the text or element '{target_text}'? Describe where it is and what's around it."
    else:
        prompt = "Read all visible text on this screen. List the key information concisely."
    
    return await analyze_screen(prompt=prompt)


if __name__ == "__main__":
    async def test():
        result = await look_at_screen()
        print(f"\nFinal: {result}")
    asyncio.run(test())
