with open('agent_runner.py', 'r') as f:
    content = f.read()

new_task = '''
async def run_writer_task(prompt: str):
    print(f"\\n[AgentRunner] Forwarding Writer Task to OpenCode: {prompt}")
    session_id = await get_active_session()
    if not session_id:
        print("[AgentRunner] No active session found for Writer Task.")
        return
        
    url = f"http://127.0.0.1:4096/session/{session_id}/message"
    
    constrained_prompt = f"You are a ghostwriter tool. Write exactly what is requested below and NOTHING ELSE. Do NOT include any introductory sentences, conversational filler, markdown formatting, or concluding sentences. Only output the pure requested text.\\n\\nRequest: {prompt}"

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
'''

if 'async def run_writer_task' not in content:
    content = content.replace('if __name__ == "__main__":', new_task)
    
with open('agent_runner.py', 'w') as f:
    f.write(content)

print("Patched agent_runner.py")
