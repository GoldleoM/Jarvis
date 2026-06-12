import asyncio
import aiohttp
import json

async def run_ollama_task(prompt: str, model: str = "llama3.2:1b"):
    print(f"\n[OllamaRunner] Generating response for: {prompt}")
    url = "http://localhost:11434/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "system": (
            "You are Jarvis, a precise and factual voice assistant.\n"
            "1. Be Direct: Provide the answer immediately. Avoid filler phrases like 'Certainly' or 'I can help'.\n"
            "2. Be Concise: Use under 2 short sentences.\n"
            "3. Be Factual: If you do not know the exact factual answer, you must state 'I do not have enough information to answer that.' Do not guess.\n"
            "4. Format: Use plain text only. Do not use markdown, asterisks, or formatting."
        )
    }
    
    try:
        # Give Ollama up to 60 seconds to process
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=60) as response:
                if response.status == 200:
                    data = await response.json()
                    answer = data.get("response", "I'm sorry, I couldn't formulate a response.").strip()
                    print(f"[OllamaRunner] Response generated.")
                    return answer
                else:
                    print(f"[OllamaRunner] Error {response.status}")
                    return "I encountered a local server error."
    except asyncio.CancelledError:
        print("[OllamaRunner] Task cancelled by user! Stopping generation...")
        raise
    except Exception as e:
        print(f"[OllamaRunner] Connection error: {e}")
        return "I am currently unable to connect to Ollama. Please ensure it is running."

if __name__ == "__main__":
    async def test():
        print(await run_ollama_task("What is the capital of France?"))
    asyncio.run(test())
