import re

with open('skills/app_skills.py', 'r') as f:
    content = f.read()

new_logic = '''
    elif intent_name == "wikipedia":
        match = re.search(r'(?:who is|what is|define|tell me about|who was|what are|meaning of|explain what is|search wikipedia for)\s+(.+)', text.lower())
        if match:
            query = match.group(1).strip()
            # remove trailing phrases
            query = re.sub(r'\s+(?:on wikipedia|please)$', '', query).strip()
            try:
                import wikipedia
                summary = wikipedia.summary(query, sentences=2)
                return f"According to Wikipedia: {summary}"
            except wikipedia.exceptions.DisambiguationError as e:
                return f"There are multiple results for {query}. Please be more specific."
            except wikipedia.exceptions.PageError:
                return f"I couldn't find any information on {query}."
            except Exception as e:
                return "I'm having trouble connecting to Wikipedia right now."
        return "What would you like me to look up?"

    elif intent_name == "math":
        match = re.search(r'(?:calculate|what is|what is the sum of|solve this math)\s+(.+)', text.lower())
        if match:
            expression = match.group(1).strip()
            # Sanitize expression: replace words with operators
            expression = expression.replace('plus', '+').replace('minus', '-').replace('times', '*').replace('divided by', '/').replace('multiplied by', '*')
            # Remove anything that isn't a digit or operator
            clean_expr = re.sub(r'[^0-9+\-*/(). ]', '', expression)
            try:
                # safe eval
                import ast
                import operator
                
                # We can just use a restricted eval since we stripped out bad chars
                result = eval(clean_expr, {"__builtins__": None}, {})
                # format result to avoid long decimals if it's an integer
                if isinstance(result, float) and result.is_integer():
                    result = int(result)
                elif isinstance(result, float):
                    result = round(result, 2)
                return f"The answer is {result}."
            except Exception:
                return "I couldn't calculate that, sir. The math expression seems invalid."
        return "What would you like me to calculate?"

    elif intent_name == "joke":
        import requests
        try:
            # 50% chance for joke, 50% for fun fact unless specified
            import random
            if 'fact' in text.lower() or 'trivia' in text.lower():
                resp = requests.get("https://uselessfacts.jsph.pl/random.json?language=en", timeout=5).json()
                return f"Here's a fun fact: {resp['text']}"
            else:
                resp = requests.get("https://official-joke-api.appspot.com/random_joke", timeout=5).json()
                return f"{resp['setup']} ... {resp['punchline']}"
        except Exception:
            return "I seem to have forgotten all my jokes, sir. My connection is down."

    elif intent_name == "date":
        from datetime import datetime
        now = datetime.now()
        day_of_week = now.strftime("%A")
        month = now.strftime("%B")
        day = now.strftime("%d")
        year = now.strftime("%Y")
        
        # Add ordinal suffix to day
        day_num = int(day)
        if 4 <= day_num <= 20 or 24 <= day_num <= 30:
            suffix = "th"
        else:
            suffix = ["st", "nd", "rd"][day_num % 10 - 1]
            
        return f"Today is {day_of_week}, {month} {day_num}{suffix}, {year}."

    elif intent_name == "timer":
        match = re.search(r'(?:for|in)\s+(\d+)\s+(second|minute|hour)', text.lower())
        if match:
            amount = int(match.group(1))
            unit = match.group(2)
            seconds = amount
            if 'minute' in unit:
                seconds *= 60
            elif 'hour' in unit:
                seconds *= 3600
                
            return f"__TIMER__{seconds}__I have set a timer for {amount} {unit}s, sir."
        return "How long should I set the timer for, sir?"
'''

if 'elif intent_name == "wikipedia":' not in content:
    insert_idx = content.find('    return None')
    if insert_idx != -1:
        content = content[:insert_idx] + new_logic + '\n' + content[insert_idx:]

with open('skills/app_skills.py', 'w') as f:
    f.write(content)

print('Added all 5 logical blocks to app_skills.py')
