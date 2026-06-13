import os
import re

def execute_skill(intent_name, text=""):
    if intent_name == "open_app":
        # Extract the app name using a regex, stop at punctuation
        match = re.search(r'(?:open|launch|start|run)\s+([a-zA-Z0-9\s]+)', text.lower())
        app_name = ""
        if match:
            app_name = match.group(1).strip()
            # In case it captured too much, just take the first 3 words
            app_name = " ".join(app_name.split()[:3])
        else:
            # Fallback if Semantic Router routed here without those verbs
            app_name = text.lower().replace("please", "").replace("play", "").strip()
            app_name = re.sub(r'[^a-zA-Z0-9\s]', '', app_name)
            app_name = " ".join(app_name.split()[:3])
            
        if app_name:
            
            import json
            import difflib
            
            apps_json_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "apps.json")
            if not os.path.exists(apps_json_path):
                import sys
                sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                try:
                    from app_scanner import scan_apps
                    scan_apps()
                except Exception as e:
                    print(f"Failed to run app scanner: {e}")
            
            try:
                with open(apps_json_path, 'r', encoding='utf-8') as f:
                    apps_dict = json.load(f)
                    
                matches = difflib.get_close_matches(app_name, apps_dict.keys(), n=1, cutoff=0.75)
                if matches:
                    best_match = matches[0]
                    app_path = apps_dict[best_match]
                    try:
                        os.startfile(app_path)
                        return f"Opening {best_match}, sir."
                    except Exception as e:
                        print(f"Failed to launch {best_match} via path: {e}")
            except Exception as e:
                print(f"Error fuzzy matching apps: {e}")
            
            try:
                import pyautogui
                import time
                pyautogui.press('win')
                time.sleep(0.5)
                pyautogui.write(app_name, interval=0.05)
                time.sleep(0.5)
                pyautogui.press('enter')
                return f"Opening {app_name}, sir."
            except Exception as e:
                print(f"PyAutoGUI fallback failed: {e}")
                return "I ran into an issue launching that app, sir."
        return "I didn't catch the app name, sir."

    elif intent_name == "kill_task":
        match = re.search(r'(?:close|shut down|quit|exit)\s+([a-zA-Z0-9\s]+)', text.lower())
        if match:
            app_name = match.group(1).strip()
            # Just grab first 3 words to avoid eating the sentence
            app_name = " ".join(app_name.split()[:3])
            
            if app_name in ["this window", "the window", "this app", "current window"]:
                import pyautogui
                pyautogui.hotkey('alt', 'f4')
                return "Closing this window, sir."
                
            # Common mappings
            app_map = {"spotify": "spotify.exe", "chrome": "chrome.exe", "discord": "discord.exe", "whatsapp": "whatsapp.exe", "calculator": "calculator.exe"}
            process_name = app_map.get(app_name.lower(), f"{app_name.replace(' ', '')}.exe")
            
            os.system(f"taskkill /F /IM {process_name} /T")
            return f"Closing {app_name}, sir."
        return "Which app would you like me to close?"

    elif intent_name == "focus_app":
        match = re.search(r'(?:focus|switch|bring|go to|activate|jump|pull up|show me|make)\s+(?:on\s+|to\s+|over to\s+|me over to\s+)?(?:the\s+)?([a-zA-Z0-9\s\-]+)', text.lower())
        app_name = ""
        if match:
            app_name = match.group(1).replace("to front", "").replace("the active window", "").replace("up", "").replace("please", "").strip()
        else:
            app_name = text.lower().replace("please", "").replace("focus", "").replace("switch to", "").strip()
            
        if not app_name:
            return "Which app would you like me to focus?"
            
        import pygetwindow as gw
        import difflib
        
        try:
            all_windows = gw.getAllTitles()
            valid_windows = [w for w in all_windows if w.strip()]
            
            if not valid_windows:
                return "No active windows found."
                
            # Try exact/substring match first (case insensitive)
            for w in valid_windows:
                if app_name.lower() in w.lower():
                    try:
                        win = gw.getWindowsWithTitle(w)[0]
                        if win.isMinimized:
                            win.restore()
                        win.activate()
                        return f"Focusing {w}."
                    except Exception as e:
                        pass
                        
            # Fallback to fuzzy match
            matches = difflib.get_close_matches(app_name, valid_windows, n=1, cutoff=0.4)
            if matches:
                best_match = matches[0]
                try:
                    win = gw.getWindowsWithTitle(best_match)[0]
                    if win.isMinimized:
                        win.restore()
                    win.activate()
                    return f"Focusing {best_match}."
                except Exception as e:
                    pass
            
            return f"Could not find a window matching {app_name}."
        except Exception as e:
            print(f"Focus window failed: {e}")
            return "I ran into an issue focusing that window, sir."

    elif intent_name == "type_text":
        match = re.search(r'(?:type|dictate|write)(?:\s+(?:for me|out|down|this|that|exactly))*\s+(.+)', text.lower(), re.IGNORECASE)
        content = match.group(1).strip() if match else text.lower().replace("type", "").strip()
        if content:
            import pyautogui
            pyautogui.write(content, interval=0.02)
            return "Typed it out for you, sir."
        return "What would you like me to type?"

    elif intent_name == "ghostwriter":
        match = re.search(r'(?:draft|write|compose|generate|type out)\s+(?:an?|some)?\s*(?:email|message|prompt|reply|letter|essay|text)(?:\s+(?:saying|about|asking|to|for|that))?\s+(.+)', text.lower(), re.IGNORECASE)
        prompt = match.group(1).strip() if match else text
        return f"__WRITER__{prompt}"

    elif intent_name == "press_key":
        import pyautogui
        if "enter" in text.lower() or "return" in text.lower():
            pyautogui.press("enter")
            return "Pressed Enter."
        elif "space" in text.lower():
            pyautogui.press("space")
            return "Pressed Space."
        elif "backspace" in text.lower() or "delete" in text.lower():
            pyautogui.press("backspace")
            return "Pressed Backspace."
        elif "escape" in text.lower() or "esc" in text.lower():
            pyautogui.press("escape")
            return "Pressed Escape."
        elif "tab" in text.lower():
            pyautogui.press("tab")
            return "Pressed Tab."
        return "I am not sure which key to press."

    elif intent_name == "notes_mode":
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
                url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"
                os.system(f"start {url}")
                return f"Searching YouTube for {query}, sir."
        return "__CONTEXT__youtube_search__What would you like me to find on YouTube?"


    elif intent_name == "spotify":
        match = re.search(r'(?:play|listen to|put on)\s+([a-zA-Z0-9\s\.\,\'\-]+?)(?:\s+on spotify)?$', text.lower())
        if match:
            query = match.group(1).strip().replace('some ', '')
            if query in ['music', 'spotify', 'a song', '']:
                os.system("start spotify:")
                return "Opening Spotify, sir."
            import urllib.parse
            safe_query = urllib.parse.quote(query)
            os.system(f"start spotify:search:{safe_query}")
            return f"Pulling up {query} on Spotify, sir."
        else:
            os.system("start spotify:")
            return "Opening Spotify, sir."

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
        import json
        import difflib

        contacts = []
        contacts_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'contacts.json')
        if os.path.exists(contacts_file):
            try:
                with open(contacts_file, 'r') as f:
                    data = json.load(f)
                    contacts = data.get('contacts', [])
            except:
                pass

        def find_contact(raw_name, cutoff=0.6):
            if not contacts:
                return None
            matches = difflib.get_close_matches(raw_name, contacts, n=1, cutoff=cutoff)
            return matches[0] if matches else None

        def get_suggestions(raw_name, max_count=4):
            if not contacts:
                return []
            return difflib.get_close_matches(raw_name, contacts, n=max_count, cutoff=0.3)

        # Path 1: Both contact and message provided in one utterance
        match = re.search(r'(?:send a whatsapp to|text|message|send a text to)\s+([a-zA-Z\s]+?)\s+saying\s+(.+)', text.lower())
        if match:
            contact_raw = match.group(1).strip()
            msg = match.group(2).strip()
            matched = find_contact(contact_raw)
            if matched:
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
                pyautogui.write(matched, interval=0.05)
                time.sleep(1)
                pyautogui.press('enter')
                time.sleep(1)
                pyautogui.write(msg, interval=0.05)
                time.sleep(0.5)
                pyautogui.press('enter')
                return f"Message sent to {matched}, sir."
            else:
                suggestions = get_suggestions(contact_raw)
                if suggestions:
                    opts = "|".join(suggestions)
                    numbered = ", ".join(f"{i+1}. {s}" for i, s in enumerate(suggestions))
                    encoded_msg = msg.replace("|", " ").replace("__", " ")
                    return f"__CONTEXT__whatsapp_suggest_msg__Did you mean {numbered}? Please say the name or number.__{opts}__{encoded_msg}"
                else:
                    return f"I'm sorry, sir, but {contact_raw} is not in your contacts list."

        # Path 2: Only contact name is provided, need to ask for message
        match_who = re.search(r'(?:send a whatsapp to|text|message|send a text to)\s+([a-zA-Z\s]+)', text.lower())
        if match_who:
            raw_contact = match_who.group(1).strip()
            raw_contact = re.sub(r'\s+(?:please|now)$', '', raw_contact).strip()

            matched = find_contact(raw_contact)
            if matched:
                if matched.lower() == raw_contact.lower():
                    return f"__CONTEXT__whatsapp_msg_{matched}__What would you like to say to {matched}?__{matched}"
                else:
                    return f"__CONTEXT__whatsapp_confirm__Did you mean {matched}?__{matched}"
            else:
                suggestions = get_suggestions(raw_contact)
                if suggestions:
                    opts = "|".join(suggestions)
                    numbered = ", ".join(f"{i+1}. {s}" for i, s in enumerate(suggestions))
                    return f"__CONTEXT__whatsapp_suggest__Did you mean {numbered}? Please say the name or number.__{opts}"
                else:
                    return f"I'm sorry, sir, but {raw_contact} is not in your contacts list."

        return "__CONTEXT__whatsapp_who__Who would you like to text?"
    elif intent_name == "weather":
        import requests
        try:
            resp = requests.get("https://wttr.in/?format=It+is+currently+%C+and+%t.", timeout=5)
            weather_text = resp.text.replace('+', '').replace('°C', ' degrees Celsius').replace('°F', ' degrees Fahrenheit')
            return weather_text
        except Exception:
            return "I am having trouble connecting to the weather service right now, sir."
            
    elif intent_name == "open_website":
        match = re.search(r'(?:open|go to|browse to|navigate to|launch)\s+(.+)', text.lower())
        if match:
            site = match.group(1).strip()
            site = re.sub(r'\s+(?:website|web page|url|link)$', '', site).strip()
            if '.' not in site:
                site = f"{site}.com"
                
            os.system(f"start https://{site}")
            return f"Opening {site}, sir."
        return "Which website would you like me to open?"

    return None
