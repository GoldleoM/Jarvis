import asyncio
import aiohttp
import re
import os
import json

async def get_active_session():
    print("[AgentRunner] Attempting to connect to OpenCode API at http://127.0.0.1:4096/api/session...")
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get("http://127.0.0.1:4096/api/session") as response:
                print(f"[AgentRunner] GET /api/session returned status: {response.status}")
                if response.status == 200:
                    data = await response.json()
                    print(f"[AgentRunner] Session data received: {data}")
                    # data is a dictionary with an 'items' array
                    if isinstance(data, dict) and 'items' in data and len(data['items']) > 0:
                        # Grab the most recent session ID
                        session_id = data['items'][0].get('id')
                        print(f"[AgentRunner] Found active session ID: {session_id}")
                        return session_id
                    else:
                        print("[AgentRunner] API returned an empty list of sessions.")
                else:
                    print(f"[AgentRunner] API Error response text: {await response.text()}")
        except Exception as e:
            print(f"[AgentRunner] Exception during GET /api/session: {e}")
            pass
    return None

async def run_opencode_task(command: str):
    print(f"\n[AgentRunner] Forwarding command to persistent OpenCode Console: {command}")
    
    # 1. Fetch the ID of the visible terminal session
    session_id = await get_active_session()
    if not session_id:
        print("[AgentRunner] No active session found. Creating a new one...")
        # Create a new session if none exist
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post("http://127.0.0.1:4096/api/session", json={"title": "Jarvis Session"}) as response:
                    print(f"[AgentRunner] POST /api/session returned status: {response.status}")
                    if response.status == 200:
                        data = await response.json()
                        session_id = data.get('id')
                        print(f"[AgentRunner] Created new session ID: {session_id}")
            except Exception as e:
                print(f"[AgentRunner] Exception during POST /api/session: {e}")
                pass
                
    if not session_id:
        print("[AgentRunner] CRITICAL: Failed to locate or create an OpenCode session!")
        return "I could not find the active OpenCode session. Please ensure the terminal is running."
        
    url = f"http://127.0.0.1:4096/session/{session_id}/message"
    # Load model config from config.json or use defaults
    provider_id = "opencode"
    model_id = "big-pickle"
    try:
        if os.path.exists("config.json"):
            with open("config.json", "r") as f:
                config = json.load(f)
                model_config = config.get("model", {})
                provider_id = model_config.get("providerID", provider_id)
                model_id = model_config.get("modelID", model_id)
    except Exception as e:
        print(f"[AgentRunner] Warning: Could not load config.json: {e}")

    system_directive = "\n\n[System Directive: You are a Voice Assistant. Provide your answer in natural, conversational sentences. Do NOT use Markdown tables, bullet points, or complex formatting, as your response will be read aloud.]"
    payload = {
        "model": {
            "providerID": provider_id,
            "modelID": model_id
        },
        "agent": "jarvis",
        "parts": [
            {
                "type": "text",
                "text": command + system_directive
            }
        ]
    }
    
    print(f"[AgentRunner] Sending POST to {url} with payload: {payload}")
    # 2. Send the voice prompt to the terminal
    try:
        # Give the agent a long timeout since coding takes time
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=600) as response:
                print(f"[AgentRunner] POST {url} returned status: {response.status}")
                if response.status == 200:
                    data = await response.json()
                    print(f"[AgentRunner] Received response JSON from OpenCode API.")
                    
                    finish_reason = data.get("info", {}).get("finish")
                    if finish_reason and finish_reason != "stop":
                        print("[AgentRunner] AI is using tools. Polling for final response...")
                        while True:
                            await asyncio.sleep(2)
                            poll_url = f"http://127.0.0.1:4096/session/{session_id}/message?limit=1"
                            async with session.get(poll_url) as poll_res:
                                if poll_res.status == 200:
                                    poll_data = await poll_res.json()
                                    if poll_data and len(poll_data) > 0:
                                        latest_msg = poll_data[0]
                                        info = latest_msg.get("info", {})
                                        if info.get("role") == "assistant" and info.get("finish") == "stop":
                                            data = latest_msg
                                            break
                    
                    # 3. Extract the response text
                    parts = data.get("parts", [])
                    if parts:
                        text_parts = [p.get("text", "") for p in parts if p.get("type") == "text"]
                        full_text = " ".join(text_parts).strip()
                    else:
                        full_text = data.get("text", data.get("message", ""))
                    
                    if not full_text:
                        print("[AgentRunner] API returned 200 but text was empty.")
                        return "Task finished successfully."
                        
                    print(f"[AgentRunner] Raw AI Response Length: {len(full_text)} characters")
                    # 4. Clean up the text for Voice TTS (Remove code blocks, markdown)
                    clean_text = re.sub(r'```.*?```', 'a code block', full_text, flags=re.DOTALL)
                    clean_text = re.sub(r'\*.*?\*', '', clean_text)
                    clean_text = clean_text.replace('\n', ' ')
                    
                    # 5. Prevent Jarvis from reading a massive essay
                    sentences = [s.strip() for s in clean_text.split('.') if s.strip()]
                    if len(sentences) > 6:
                        # Return the first 2 and the last 2 sentences to ensure we don't miss the conclusion
                        return ". ".join(sentences[:2]) + " ... " + ". ".join(sentences[-2:]) + "."
                    return clean_text
                else:
                    error_text = await response.text()
                    print(f"[AgentRunner] ERROR from API: {error_text}")
                    return f"OpenCode returned an error code: {response.status}"
    except asyncio.CancelledError:
        print("[AgentRunner] Task cancelled by user!")
        # Optional: Send an abort request to the session to stop the AI
        try:
            async with aiohttp.ClientSession() as session:
                await session.post(f"http://127.0.0.1:4096/api/session/{session_id}/abort")
        except:
            pass
        raise
    except Exception as e:
        print(f"[AgentRunner] Connection error during POST prompt: {e}")
        return "I encountered a connection error while speaking to OpenCode."


async def run_writer_task(prompt: str):
    print(f"\n[AgentRunner] Forwarding Writer Task to OpenCode: {prompt}")
    session_id = await get_active_session()
    if not session_id:
        print("[AgentRunner] No active session found for Writer Task.")
        return
        
    url = f"http://127.0.0.1:4096/session/{session_id}/message"
    
    constrained_prompt = f"You are a ghostwriter tool. Write exactly what is requested below and NOTHING ELSE. Do NOT include any introductory sentences, conversational filler, markdown formatting, or concluding sentences. Only output the pure requested text.\n\nRequest: {prompt}"

    provider_id = "opencode"
    model_id = "big-pickle"
    try:
        import os, json
        if os.path.exists("config.json"):
            with open("config.json", "r") as f:
                config = json.load(f)
                model_config = config.get("model", {})
                provider_id = model_config.get("providerID", provider_id)
                model_id = model_config.get("modelID", model_id)
    except:
        pass

    payload = {
        "model": {
            "providerID": provider_id,
            "modelID": model_id
        },
        "agent": "jarvis",
        "parts": [
            {
                "type": "text",
                "text": constrained_prompt
            }
        ]
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=600) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    finish_reason = data.get("info", {}).get("finish")
                    if finish_reason and finish_reason != "stop":
                        while True:
                            await asyncio.sleep(2)
                            poll_url = f"http://127.0.0.1:4096/session/{session_id}/message?limit=1"
                            async with session.get(poll_url) as poll_res:
                                if poll_res.status == 200:
                                    poll_data = await poll_res.json()
                                    if poll_data and len(poll_data) > 0:
                                        latest_msg = poll_data[0]
                                        info = latest_msg.get("info", {})
                                        if info.get("role") == "assistant" and info.get("finish") == "stop":
                                            data = latest_msg
                                            break
                    
                    parts = data.get("parts", [])
                    if parts:
                        text_parts = [p.get("text", "") for p in parts if p.get("type") == "text"]
                        full_text = " ".join(text_parts).strip()
                    else:
                        full_text = data.get("text", data.get("message", "")).strip()
                    
                    if full_text:
                        import pyautogui
                        def do_typing():
                            pyautogui.write(full_text, interval=0.1) # approx 120WPM
                        import asyncio
                        await asyncio.get_event_loop().run_in_executor(None, do_typing)
                        print("[AgentRunner] Typing completed.")
                        
    except Exception as e:
        print(f"[AgentRunner] Exception in Writer Task: {e}")

if __name__ == "__main__":

    # Test block
    async def test():
        res = await run_opencode_task("Hello Jarvis, what is 2 plus 2?")
        print(f"Final output: {res}")
    asyncio.run(test())
