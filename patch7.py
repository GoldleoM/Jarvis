with open('main.py', 'r') as f:
    content = f.read()

# Add to init
if 'self.pending_context = None' not in content:
    content = content.replace('self.pending_confirmation = None', 'self.pending_confirmation = None\n        self.pending_context = None\n        self.pending_contact = None')

# Add to handle_command top
new_handle_top = '''
        # --- CONTEXTUAL STATE MACHINE ---
        if self.pending_context:
            action = self.pending_context
            self.pending_context = None
            
            if action == "youtube_search":
                text = f"search youtube for {text}"
                clean_text = text.lower().strip(" ,!?.-")
            elif action == "whatsapp_who":
                text = f"send a whatsapp to {text}"
                clean_text = text.lower().strip(" ,!?.-")
            elif action == "whatsapp_confirm":
                if any(word in clean_text for word in ["yes", "do it", "confirm", "proceed", "sure", "yeah", "yep"]):
                    self.pending_context = f"whatsapp_msg_{self.pending_contact}"
                    try:
                        import asyncio
                        await asyncio.wait_for(
                            self.loop.run_in_executor(self.executor, self.tts.speak, f"What would you like to say to {self.pending_contact}?"),
                            timeout=5
                        )
                    except:
                        pass
                    self.is_active = True
                    self.last_active_time = __import__('time').time()
                    return
                else:
                    try:
                        import asyncio
                        await asyncio.wait_for(
                            self.loop.run_in_executor(self.executor, self.tts.speak, "Okay, cancelling message."),
                            timeout=5
                        )
                    except:
                        pass
                    return
            elif action.startswith("whatsapp_msg_"):
                contact = action.split("whatsapp_msg_")[1]
                text = f"send a whatsapp to {contact} saying {text}"
                clean_text = text.lower().strip(" ,!?.-")
'''
insert_idx = content.find('        # --- STATEFUL CONFIRMATION LOGIC ---')
if insert_idx != -1 and 'self.pending_context:' not in content:
    content = content[:insert_idx] + new_handle_top + content[insert_idx:]

# Handle parsing the return value from app_skills.py
new_context_parser = '''
            elif local_response.startswith("__CONTEXT__"):
                parts = local_response.split("__")
                self.pending_context = parts[2]
                if len(parts) > 4:
                    self.pending_contact = parts[4]
                local_response = parts[3]
                
                # VERY IMPORTANT: keep active state true so she listens immediately!
                self.is_active = True
                self.last_active_time = __import__('time').time()
'''
insert_idx2 = content.find('            elif local_response.startswith("__TIMER__"):')
if insert_idx2 != -1 and '__CONTEXT__' not in content:
    content = content[:insert_idx2] + new_context_parser + content[insert_idx2:]

with open('main.py', 'w') as f:
    f.write(content)

print('Patched main.py state machine successfully')
