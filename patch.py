import re

with open('router.py', 'r') as f:
    content = f.read()

# Fix the duplicated open_folder_route
content = re.sub(r'self\.open_folder_route = Route\(name=\"open_folder\", utterances=\[.*?\]\)\n\s*self\.open_folder_route = Route\(name=\"open_folder\", utterances=\[.*?\]\)',
                 r'self.open_folder_route = Route(name="open_folder", utterances=[])', content)

# Remove old occurrences of youtube_route
content = re.sub(r'\s*self\.youtube_route = Route\(name=\"youtube\", utterances=\[.*?\]\)', '', content)
content = content.replace('self.search_web_route, self.youtube_route, self.coding_route', 'self.search_web_route, self.coding_route')

# Insert it fresh
new_route = '''        self.youtube_route = Route(name="youtube", utterances=[])
'''
insert_idx = content.find('        self.coding_route')
if insert_idx != -1:
    content = content[:insert_idx] + new_route + content[insert_idx:]
    content = content.replace('self.search_web_route, self.coding_route', 'self.search_web_route, self.youtube_route, self.coding_route')

with open('router.py', 'w') as f:
    f.write(content)

print('Fixed router.py structure')
