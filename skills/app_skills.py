import os
import re

def execute_skill(intent_name, text=""):
    if intent_name == "open_app":
        # Extract the app name using a regex
        match = re.search(r'(?:open|launch|start)\s+(.+)', text.lower())
        if match:
            app_name = match.group(1).strip()
            import pyautogui
            import time
            pyautogui.press('win')
            time.sleep(0.5)
            pyautogui.write(app_name, interval=0.05)
            time.sleep(0.5)
            pyautogui.press('enter')
            return f"Opening {app_name}, sir."
        return "I didn't catch the app name, sir."

    elif intent_name == "type_text":
        match = re.search(r'(?:type for me|dictate this|type out)(?:\s+(?:that|this))*\s+(.+)', text.lower(), re.IGNORECASE)
        if match:
            content = match.group(1).strip()
            import pyautogui
            pyautogui.write(content, interval=0.02)
            return "Typed it out for you, sir."
        return "What would you like me to type?"

    elif intent_name == "notes_mode":
        import os
        os.system("start notepad")
        return "__NOTES_MODE__"
        
    elif intent_name == "search_web":
        # Extract the search query
        match = re.search(r'(?:search|google|look up)(?:\s+(?:youtube|the web|the internet|for|on))*\s+(.+)', text.lower())
        query = ""
        if match:
            query = match.group(1).strip()
            # Strip extra prepositions at the start
            query = re.sub(r'^(for|on|about)\s+', '', query).strip()
        
        if query:
            # Check if it specifically wants youtube
            if 'youtube' in text.lower():
                import urllib.parse
                safe_query = urllib.parse.quote_plus(query)
                os.system(f"start https://www.youtube.com/results?search_query={safe_query}")
                return f"Searching YouTube for {query}."
            else:
                import urllib.parse
                safe_query = urllib.parse.quote_plus(query)
                os.system(f"start https://www.google.com/search?q={safe_query}")
                return f"Searching the web for {query}."
        else:
            return "What would you like me to search for, sir?"

    elif intent_name == "youtube":
        match = re.search(r'(?:search youtube for|play on youtube|find on youtube|look up on youtube|play a video about|can you search youtube for|play the video|play the song on youtube|youtube search|look on youtube for|search for this on youtube|find a video about|play something on youtube|i want to watch a video about|pull up a youtube video of|show me a video of|play)\s+(.+)', text.lower())
        if match:
            query = match.group(1).strip()
            # remove trailing phrases if any
            query = re.sub(r'\s+(?:on youtube|video)$', '', query).strip()
            try:
                import pywhatkit
                # Play instantly opens the browser to the first matching video and starts playing it
                pywhatkit.playonyt(query)
                return f"Playing {query} on YouTube, sir."
            except Exception as e:
                import urllib.parse
                import os
                url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"
                os.system(f"start {url}")
                return f"Searching YouTube for {query}, sir."
        return "__CONTEXT__youtube_search__What would you like me to find on YouTube?"


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
        return "__CONTEXT__timer__How long should I set the timer for, sir?"


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

    return None
