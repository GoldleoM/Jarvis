import asyncio
import aiohttp
import re
import os
import json

async def get_active_session():
    print("[AgentRunner] Attempting to connect to OpenCode API at http://127.0.0.1:4096/api/session...")
    async with aiohttp.ClientSession() as session:
        for endpoint in ["http://127.0.0.1:4096/api/session", "http://127.0.0.1:4096/session"]:
            try:
                async with session.get(endpoint) as response:
                    print(f"[AgentRunner] GET {endpoint} returned status: {response.status}")
                    if response.status == 200:
                        data = await response.json()
                        sessions_list = []
                        if isinstance(data, list):
                            sessions_list = data
                        elif isinstance(data, dict):
                            if isinstance(data.get('data'), list):
                                sessions_list = data['data']
                            elif isinstance(data.get('items'), list):
                                sessions_list = data['items']
                            elif 'id' in data:
                                sessions_list = [data]
                        
                        if len(sessions_list) > 0:
                            session_id = sessions_list[0].get('id')
                            if session_id:
                                print(f"[AgentRunner] Found active session ID: {session_id}")
                                return session_id
                    else:
                        print(f"[AgentRunner] API Error response text: {await response.text()}")
            except Exception as e:
                print(f"[AgentRunner] Exception during GET {endpoint}: {e}")
                pass
        print("[AgentRunner] API returned an empty list of sessions.")
    return None

async def run_opencode_task(command: str):
    print(f"\n[AgentRunner] Forwarding command to persistent OpenCode Console: {command}")
    
    # 1. Fetch the ID of the visible terminal session
    session_id = await get_active_session()
    if not session_id:
        print("[AgentRunner] No active session found. Creating a new one...")
        # Create a new session if none exist
        async with aiohttp.ClientSession() as session:
            for endpoint in ["http://127.0.0.1:4096/api/session", "http://127.0.0.1:4096/session"]:
                try:
                    async with session.post(endpoint, json={"title": "Jarvis Session"}) as response:
                        print(f"[AgentRunner] POST {endpoint} returned status: {response.status}")
                        if response.status == 200:
                            data = await response.json()
                            if isinstance(data, dict):
                                session_id = data.get('id')
                                if not session_id and isinstance(data.get('data'), dict):
                                    session_id = data['data'].get('id')
                            if session_id:
                                print(f"[AgentRunner] Created new session ID: {session_id}")
                                break
                except Exception as e:
                    print(f"[AgentRunner] Exception during POST {endpoint}: {e}")
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
                        seen_msg_ids = set()
                        if data.get("id"):
                            seen_msg_ids.add(data.get("id"))
                        
                        for part in data.get("parts", []):
                            if part.get("type") == "toolCall":
                                name = part.get("toolCall", {}).get("name", "unknown_tool")
                                print(f"[AgentRunner] 🛠️  Jarvis is using tool: {name}")

                        while True:
                            await asyncio.sleep(2)
                            poll_url = f"http://127.0.0.1:4096/session/{session_id}/message?limit=10"
                            async with session.get(poll_url) as poll_res:
                                if poll_res.status == 200:
                                    poll_data = await poll_res.json()
                                    if poll_data and len(poll_data) > 0:
                                        for msg in reversed(poll_data):
                                            msg_id = msg.get("id")
                                            if msg_id and msg_id not in seen_msg_ids:
                                                seen_msg_ids.add(msg_id)
                                                if msg.get("info", {}).get("role") == "assistant":
                                                    for part in msg.get("parts", []):
                                                        if part.get("type") == "toolCall":
                                                            name = part.get("toolCall", {}).get("name", "unknown_tool")
                                                            print(f"[AgentRunner] 🛠️  Jarvis is using tool: {name}")

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
                        seen_msg_ids = set()
                        if data.get("id"):
                            seen_msg_ids.add(data.get("id"))
                            
                        for part in data.get("parts", []):
                            if part.get("type") == "toolCall":
                                name = part.get("toolCall", {}).get("name", "unknown_tool")
                                print(f"[AgentRunner] 🛠️  Jarvis is using tool: {name}")

                        while True:
                            await asyncio.sleep(2)
                            poll_url = f"http://127.0.0.1:4096/session/{session_id}/message?limit=10"
                            async with session.get(poll_url) as poll_res:
                                if poll_res.status == 200:
                                    poll_data = await poll_res.json()
                                    if poll_data and len(poll_data) > 0:
                                        for msg in reversed(poll_data):
                                            msg_id = msg.get("id")
                                            if msg_id and msg_id not in seen_msg_ids:
                                                seen_msg_ids.add(msg_id)
                                                if msg.get("info", {}).get("role") == "assistant":
                                                    for part in msg.get("parts", []):
                                                        if part.get("type") == "toolCall":
                                                            name = part.get("toolCall", {}).get("name", "unknown_tool")
                                                            print(f"[AgentRunner] 🛠️  Jarvis is using tool: {name}")

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
