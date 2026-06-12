with open('main.py', 'r') as f:
    content = f.read()

new_intercept = '''
            elif local_response.startswith("__WRITER__"):
                parts = local_response.split("__")
                prompt = parts[2] if len(parts) > 2 and parts[2] else text
                
                try:
                    import asyncio
                    await asyncio.wait_for(
                        self.loop.run_in_executor(self.executor, self.tts.speak, "Writing that for you now, sir."),
                        timeout=5
                    )
                except:
                    pass
                
                from agent_runner import run_writer_task
                import asyncio
                asyncio.create_task(run_writer_task(prompt))
                return
'''

if 'elif local_response.startswith("__WRITER__"):' not in content:
    insert_idx = content.find('            elif local_response.startswith("__CONTEXT__"):')
    content = content[:insert_idx] + new_intercept + content[insert_idx:]

with open('main.py', 'w') as f:
    f.write(content)

print("Patched main.py")
