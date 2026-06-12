import re

# 1. Update generate_massive_routes.py
with open('generate_massive_routes.py', 'r') as f:
    gen_content = f.read()

new_writer = '''    "writer": {
        "prefixes": ["", "please ", "can you ", "i want you to "],
        "core": ["write a story about", "draft an email for", "write a message saying", "type out a paragraph about", "generate a prompt for", "write something about", "create a story on", "draft a text about", "compose an email regarding", "write out a response for"]
    },
    "coding": {'''

if '"writer": {' not in gen_content:
    gen_content = gen_content.replace('    "coding": {', new_writer)

with open('generate_massive_routes.py', 'w') as f:
    f.write(gen_content)

# 2. Update router.py
with open('router.py', 'r') as f:
    router_content = f.read()

new_writer_route = '''        self.writer_route = Route(name="writer", utterances=[])
        self.coding_route'''

if 'self.writer_route =' not in router_content:
    router_content = router_content.replace('        self.coding_route', new_writer_route)
    router_content = router_content.replace('self.call_route, self.coding_route', 'self.call_route, self.writer_route, self.coding_route')

with open('router.py', 'w') as f:
    f.write(router_content)

# 3. Update app_skills.py
with open('skills/app_skills.py', 'r') as f:
    skills_content = f.read()

new_writer_skill = '''    elif intent_name == "writer":
        match = re.search(r'(?:write|draft|type|generate|compose|create)\s+(.+)', text.lower())
        if match:
            return f"__WRITER__{match.group(1).strip()}"
        return f"__WRITER__{text}"
        
    elif intent_name == "open_website":'''

if 'elif intent_name == "writer":' not in skills_content:
    skills_content = skills_content.replace('    elif intent_name == "open_website":', new_writer_skill)

with open('skills/app_skills.py', 'w') as f:
    f.write(skills_content)

print("Patched router, skills, and generation scripts.")
