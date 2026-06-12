import re

with open('expand_routes.py', 'r') as f:
    content = f.read()

new_routes = '''    "whatsapp": [
        "send a text", "text someone", "send a message", "message someone on whatsapp", "send a whatsapp",
        "i need to send a message", "text a contact", "shoot a text to", "can you send a text", "whatsapp message"
    ],
    "call": [
        "make a phone call", "call someone", "i need to call", "dial a number", "can you call",
        "start a call", "voice call", "call a contact", "phone someone"
    ],
'''
insert_idx = content.find('    "coding": [')
if insert_idx != -1 and '"whatsapp": [' not in content:
    content = content[:insert_idx] + new_routes + content[insert_idx:]

with open('expand_routes.py', 'w') as f:
    f.write(content)

with open('router.py', 'r') as f:
    content = f.read()

new_placeholders = '''        self.whatsapp_route = Route(name="whatsapp", utterances=[])
        self.call_route = Route(name="call", utterances=[])
'''
insert_idx = content.find('        self.coding_route')
if insert_idx != -1 and 'self.whatsapp_route' not in content:
    content = content[:insert_idx] + new_placeholders + content[insert_idx:]
    content = content.replace('self.date_route, self.youtube_route, self.coding_route', 'self.date_route, self.youtube_route, self.whatsapp_route, self.call_route, self.coding_route')

with open('router.py', 'w') as f:
    f.write(content)

print("Patch applied for routes.")
