import sys

with open('main.py', 'r') as f:
    content = f.read()

# 1. Add self.non_llm_events = [] to init
init_target = """        self.notes_mode = False
        
        # Launch the Typebox UI"""
        
init_replacement = """        self.notes_mode = False
        self.non_llm_events = []
        
        # Launch the Typebox UI"""

content = content.replace(init_target, init_replacement)

# 2. Modify LLM Fallback
llm_target = """            from agent_runner import run_opencode_task
            try:
                await asyncio.wait_for(
                    self.loop.run_in_executor(self.executor, self.tts.speak, "Right away, sir."),
                    timeout=10
                )
            except asyncio.TimeoutError:
                pass
            
            response = await run_opencode_task(text)"""

llm_replacement = """            from agent_runner import run_opencode_task
            try:
                await asyncio.wait_for(
                    self.loop.run_in_executor(self.executor, self.tts.speak, "Right away, sir."),
                    timeout=10
                )
            except asyncio.TimeoutError:
                pass
            
            if hasattr(self, 'non_llm_events') and self.non_llm_events:
                context_str = "For context, since our last interaction, the following local commands were executed on the user's system:\\n"
                for event in self.non_llm_events:
                    context_str += f"- User requested: '{event['user']}' -> System output: '{event['jarvis']}'\\n"
                context_str += f"\\nNow, please respond to the user's latest request: {text}"
                
                response = await run_opencode_task(context_str)
                self.non_llm_events = []
            else:
                response = await run_opencode_task(text)"""

content = content.replace(llm_target, llm_replacement)


# 3. Add to non_llm_events before return
local_target = """            print(f"Jarvis: {local_response}")
            try:
                await asyncio.wait_for(
                    self.loop.run_in_executor(self.executor, self.tts.speak, local_response),
                    timeout=20
                )
            except asyncio.TimeoutError:
                pass
            return # Skip the LLM"""

local_replacement = """            print(f"Jarvis: {local_response}")
            try:
                await asyncio.wait_for(
                    self.loop.run_in_executor(self.executor, self.tts.speak, local_response),
                    timeout=20
                )
            except asyncio.TimeoutError:
                pass
            
            if hasattr(self, 'non_llm_events'):
                self.non_llm_events.append({"user": text, "jarvis": local_response})
                
            return # Skip the LLM"""

content = content.replace(local_target, local_replacement)

with open('main.py', 'w') as f:
    f.write(content)

print("Patch applied.")
