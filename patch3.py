import re

with open('router.py', 'r') as f:
    content = f.read()

new_route = '''        self.weather_route = Route(name="weather", utterances=[
            "what's the weather", "how is the weather", "is it raining outside", "current temperature", "weather forecast",
            "what is the weather like", "weather update", "is it hot today", "how cold is it outside", "tell me the weather",
            "what is the weather in london", "weather in tokyo", "is it sunny", "local weather", "what's the temperature"
        ])
'''
insert_idx = content.find('        self.open_app_route')
if insert_idx != -1 and 'self.weather_route' not in content:
    content = content[:insert_idx] + new_route + content[insert_idx:]
    content = content.replace('self.type_text_route,', 'self.type_text_route, self.weather_route,')

with open('router.py', 'w') as f:
    f.write(content)

with open('skills/app_skills.py', 'r') as f:
    app_skills = f.read()

new_app_logic = '''
    elif intent_name == "weather":
        import requests
        import re
        import urllib.parse
        
        # Check if they specified a location
        location_match = re.search(r'(?:in|for|at)\s+([a-zA-Z\s]+)', text.lower())
        location = ""
        if location_match:
            # simple extraction of the location name
            potential_loc = location_match.group(1).strip()
            # filter out words like "today", "tomorrow", "now"
            words = [w for w in potential_loc.split() if w not in ["today", "tomorrow", "now", "please"]]
            location = " ".join(words)
        
        url = "https://wttr.in/?format=j1"
        if location:
            url = f"https://wttr.in/{urllib.parse.quote(location)}?format=j1"
            
        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                area = data['nearest_area'][0]['areaName'][0]['value']
                current = data['current_condition'][0]
                temp = current['temp_C']
                desc = current['weatherDesc'][0]['value']
                return f"Currently in {area}, it is {desc} and {temp} degrees Celsius."
            else:
                return "I couldn't fetch the weather right now, sir."
        except Exception as e:
            return "I am having trouble connecting to the weather service, sir."
'''
if 'elif intent_name == "weather":' not in app_skills:
    insert_idx = app_skills.find('    elif intent_name == "open_website":')
    if insert_idx == -1:
        insert_idx = app_skills.find('    elif intent_name == "open_app":')
        
    if insert_idx != -1:
        app_skills = app_skills[:insert_idx] + new_app_logic + '\n' + app_skills[insert_idx:]

with open('skills/app_skills.py', 'w') as f:
    f.write(app_skills)

print('Added weather successfully')
