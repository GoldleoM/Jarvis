import re

with open('skills/app_skills.py', 'r') as f:
    content = f.read()

# Fix youtube return
content = content.replace('return "What would you like me to find on YouTube?"', 'return "__CONTEXT__youtube_search__What would you like me to find on YouTube?"')

new_whatsapp_logic = '''
    elif intent_name == "whatsapp":
        match = re.search(r'(?:send a whatsapp to|text|message|send a text to)\s+([a-zA-Z\s]+?)\s+saying\s+(.+)', text.lower())
        if match:
            contact = match.group(1).strip()
            msg = match.group(2).strip()
            import pyautogui
            import time
            pyautogui.press('win')
            time.sleep(0.5)
            pyautogui.write('whatsapp', interval=0.05)
            time.sleep(0.5)
            pyautogui.press('enter')
            time.sleep(2)
            pyautogui.hotkey('ctrl', 'f')
            time.sleep(0.5)
            pyautogui.write(contact, interval=0.05)
            time.sleep(1)
            pyautogui.press('enter')
            time.sleep(1)
            pyautogui.write(msg, interval=0.05)
            time.sleep(0.5)
            pyautogui.press('enter')
            return f"Message sent to {contact}, sir."
            
        match_who = re.search(r'(?:send a whatsapp to|text|message|send a text to)\s+([a-zA-Z\s]+)', text.lower())
        if match_who:
            raw_contact = match_who.group(1).strip()
            raw_contact = re.sub(r'\s+(?:please|now)$', '', raw_contact).strip()
            
            import json
            import difflib
            import os
            contacts_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'contacts.json')
            if os.path.exists(contacts_file):
                try:
                    with open(contacts_file, 'r') as f:
                        data = json.load(f)
                        contacts = data.get('contacts', [])
                        
                        matches = difflib.get_close_matches(raw_contact, contacts, n=1, cutoff=0.4)
                        if matches:
                            matched = matches[0]
                            if matched.lower() == raw_contact.lower():
                                return f"__CONTEXT__whatsapp_msg_{matched}__What would you like to say to {matched}?__{matched}"
                            else:
                                return f"__CONTEXT__whatsapp_confirm__Did you mean {matched}?__{matched}"
                except:
                    pass
            return f"__CONTEXT__whatsapp_msg_{raw_contact}__What would you like to say to {raw_contact}?__{raw_contact}"

        return "__CONTEXT__whatsapp_who__Who would you like to text?"
'''

if 'elif intent_name == "whatsapp":' not in content:
    insert_idx = content.find('    elif intent_name == "open_website":')
    if insert_idx == -1:
        insert_idx = content.find('    return None')
    
    if insert_idx != -1:
        content = content[:insert_idx] + new_whatsapp_logic + '\n' + content[insert_idx:]

with open('skills/app_skills.py', 'w') as f:
    f.write(content)

print('Patched app_skills.py successfully')
