import re

with open('router.py', 'r') as f:
    content = f.read()

new_route = '''        self.open_website_route = Route(name="open_website", utterances=[
            "open amazon.com", "go to youtube.com", "open a website", "launch google.com", "go to facebook.com",
            "open the website", "open the url", "go to the link", "browse to", "navigate to", "open web page",
            "open amazon", "open netflix", "open github.com"
        ])
'''
insert_idx = content.find('        self.open_app_route')
if insert_idx != -1 and 'self.open_website_route' not in content:
    content = content[:insert_idx] + new_route + content[insert_idx:]
    content = content.replace('self.type_text_route,', 'self.type_text_route, self.open_website_route,')

with open('router.py', 'w') as f:
    f.write(content)

with open('skills/app_skills.py', 'r') as f:
    app_skills = f.read()

new_app_logic = '''
    elif intent_name == "open_website":
        import os
        match = re.search(r'(?:open|go to|launch|navigate to|browse to)\s+([a-zA-Z0-9\-]+(?:\.[a-zA-Z]{2,})?)', text.lower())
        if match:
            website = match.group(1).strip()
            # If no extension provided, default to .com
            if '.' not in website:
                website += '.com'
            os.system(f"start https://{website}")
            return f"Opening {website}, sir."
        return "Which website would you like me to open?"
'''
if 'elif intent_name == "open_website":' not in app_skills:
    insert_idx = app_skills.find('    elif intent_name == "open_app":')
    if insert_idx != -1:
        app_skills = app_skills[:insert_idx] + new_app_logic + '\n' + app_skills[insert_idx:]

with open('skills/app_skills.py', 'w') as f:
    f.write(app_skills)

print('Added open_website successfully')
