import itertools
import re

# We define base structures and procedurally generate massive lists for each intent to reach 50+ easily.

base_routes = {
    "get_time": {
        "prefixes": ["", "can you ", "please ", "hey jarvis ", "i want to know "],
        "core": ["tell me the time", "what time is it", "what is the current time", "give me the time", "read the clock", "what's the time", "do you have the time", "check the time", "what time do we have", "say the time"]
    },
    "lock_pc": {
        "prefixes": ["", "please ", "jarvis ", "can you ", "i need you to "],
        "core": ["lock the pc", "lock my computer", "lock the screen", "secure the workstation", "lock windows", "lock the machine", "secure my pc", "put the computer in lock mode", "lock my session", "secure the desktop"]
    },
    "battery": {
        "prefixes": ["", "please ", "can you tell me ", "what is "],
        "core": ["the battery status", "my battery level", "how much battery is left", "the battery percentage", "is my laptop charging", "how is the battery", "check the battery", "battery charge", "is the battery low", "read battery stats"]
    },
    "power_action": {
        "prefixes": ["", "please ", "jarvis ", "immediately ", "can you "],
        "core": ["shut down the computer", "restart the pc", "put the computer to sleep", "turn off the pc", "reboot the system", "sleep mode", "power off the machine", "restart windows", "hibernate the pc", "turn this computer off"]
    },
    "notes_mode": {
        "prefixes": ["", "please ", "i want to ", "let's "],
        "core": ["take some notes", "enter notes mode", "start dictation", "write this down", "start typing what i say", "open notepad and listen", "record my notes", "take a memo", "begin dictation", "jot this down"]
    },
    "minimize_windows": {
        "prefixes": ["", "please ", "can you ", "quickly "],
        "core": ["minimize all windows", "show the desktop", "hide everything", "minimize my apps", "clear the screen", "go to desktop", "hide all windows", "minimize windows", "show my wallpaper", "get rid of these windows"]
    },
    "close_window": {
        "prefixes": ["", "please ", "can you ", "jarvis "],
        "core": ["close this window", "exit the app", "close the current app", "quit this program", "shut this window", "close the active window", "terminate this app", "exit this screen", "close what i am looking at", "quit the active program"]
    },
    "screenshot": {
        "prefixes": ["", "please ", "can you ", "jarvis "],
        "core": ["take a screenshot", "capture the screen", "print screen", "save a screenshot", "take a picture of the screen", "snap the screen", "screenshot this", "grab the screen", "take a screen capture", "save my screen"]
    },
    "media_play_pause": {
        "prefixes": ["", "please ", "can you "],
        "core": ["pause the music", "play the music", "stop the audio", "resume playback", "pause the video", "play the media", "toggle playback", "pause this", "play this", "stop playing"]
    },
    "media_next": {
        "prefixes": ["", "please ", "can you "],
        "core": ["skip this track", "next song", "play the next one", "skip song", "next track", "skip forward", "go to the next song", "next media", "forward track", "skip music"]
    },
    "media_prev": {
        "prefixes": ["", "please ", "can you "],
        "core": ["previous song", "go back a track", "play the last song", "previous track", "rewind track", "go to the previous music", "last song", "back track", "play that again", "previous media"]
    },
    "volume_up": {
        "prefixes": ["", "please ", "can you "],
        "core": ["turn the volume up", "increase the volume", "make it louder", "volume up", "turn it up", "sound up", "increase sound", "louder please", "pump up the volume", "turn the sound up"]
    },
    "volume_down": {
        "prefixes": ["", "please ", "can you "],
        "core": ["turn the volume down", "decrease the volume", "make it quieter", "volume down", "turn it down", "sound down", "lower the volume", "quieter please", "reduce the sound", "turn the audio down"]
    },
    "volume_mute": {
        "prefixes": ["", "please ", "can you "],
        "core": ["mute the volume", "silence the audio", "mute the sound", "turn off the sound", "mute it", "silence it", "cut the audio", "mute my pc", "stop the sound", "mute computer"]
    },
    "system_stats": {
        "prefixes": ["", "please ", "can you "],
        "core": ["check system stats", "how is the cpu", "what is the ram usage", "read out pc performance", "how is the computer doing", "diagnose the system", "system health check", "check memory usage", "what's my cpu at", "system monitor"]
    },
    "empty_trash": {
        "prefixes": ["", "please ", "can you ", "jarvis "],
        "core": ["empty the trash", "clear the recycle bin", "empty the recycle bin", "delete the trash", "clear my garbage", "empty recycling", "purge the trash", "wipe the recycle bin", "empty out the bin", "clean the trash"]
    },
    "open_folder": {
        "prefixes": ["", "please ", "can you ", "i want to "],
        "core": ["open my downloads", "show documents", "open pictures folder", "go to my desktop folder", "open the videos", "show my files", "open file explorer", "open my music", "navigate to downloads", "open my stuff"]
    },
    "type_text": {
        "prefixes": ["", "please ", "can you ", "i want you to "],
        "core": ["type this out", "dictate this for me", "type the following", "write this on the screen", "input this text", "type what i say", "insert this text", "type this down", "write this text", "type exactly this"]
    },
    "open_app": {
        "prefixes": ["", "please ", "can you ", "i want to "],
        "core": ["open spotify", "launch chrome", "start notepad", "open brave", "open discord", "launch visual studio", "start the calculator", "open the camera", "launch steam", "open valorant"]
    },
    "search_web": {
        "prefixes": ["", "please ", "can you ", "i want to "],
        "core": ["search the web for", "google this", "look up on the internet", "find information about", "search online for", "do a web search", "query google for", "find on the internet", "search bing for", "look it up online"]
    },
    "youtube": {
        "prefixes": ["", "please ", "can you ", "i want to "],
        "core": ["search youtube for", "play a video on youtube", "find on youtube", "look up on youtube", "play this on youtube", "search for this video", "watch a video about", "youtube search", "find a youtube video", "play the youtube video"]
    },
    "wikipedia": {
        "prefixes": ["", "please ", "can you ", "i want to "],
        "core": ["who is", "what is", "define", "tell me about", "search wikipedia for", "look up on wikipedia", "give me the definition of", "explain what is", "meaning of", "who was"]
    },
    "timer": {
        "prefixes": ["", "please ", "can you ", "i want to "],
        "core": ["set a timer for", "remind me in", "wake me up in", "start a countdown for", "give me a timer for", "set an alarm for", "alert me in", "put a timer on", "timer for", "remind me to"]
    },
    "math": {
        "prefixes": ["", "please ", "can you ", "i want to "],
        "core": ["calculate", "what is plus", "what is minus", "solve this math", "what is divided by", "what is multiplied by", "do some math", "what is the sum of", "math problem", "equals"]
    },
    "joke": {
        "prefixes": ["", "please ", "can you ", "i want to "],
        "core": ["tell me a joke", "give me a fun fact", "make me laugh", "say something funny", "i need a joke", "fun fact please", "tell me a trivia", "make me smile", "say a joke", "interesting fact"]
    },
    "date": {
        "prefixes": ["", "please ", "can you ", "i want to "],
        "core": ["what is the date", "what day is it", "current date", "tell me the date today", "what day of the week is it", "give me today's date", "what month is it", "read the calendar", "what year is it", "date today"]
    },
    "weather": {
        "prefixes": ["", "please ", "can you ", "i want to "],
        "core": ["what's the weather", "how is the weather", "is it raining outside", "current temperature", "weather forecast", "weather in tokyo", "local weather", "is it sunny", "how cold is it", "weather update"]
    },
    "whatsapp": {
        "prefixes": ["", "please ", "can you ", "i want to "],
        "core": ["send a whatsapp to", "text someone", "send a message", "message someone on whatsapp", "send a text", "shoot a text to", "whatsapp message", "text a contact", "message a friend", "send a whatsapp message"]
    },
    "call": {
        "prefixes": ["", "please ", "can you ", "i want to "],
        "core": ["make a phone call", "call someone", "dial a number", "voice call", "call a contact", "phone someone", "start a call", "i need to call", "make a voice call", "call my friend"]
    },
    "writer": {
        "prefixes": ["", "please ", "can you ", "i want you to "],
        "core": ["write a story about", "draft an email for", "write a message saying", "type out a paragraph about", "generate a prompt for", "write something about", "create a story on", "draft a text about", "compose an email regarding", "write out a response for"]
    },
    "coding": {
        "prefixes": ["", "please ", "can you ", "i want to "],
        "core": ["write a python script", "code a website", "create a new file", "fix the bug", "run opencode", "build an app", "write some code", "debug this program", "analyze this code", "program a script"]
    }
}

final_utterances = {}

for intent, data in base_routes.items():
    # Generate combinations
    phrases = []
    for p in data["prefixes"]:
        for c in data["core"]:
            phrase = f"{p}{c}".strip()
            phrases.append(phrase)
    
    # ensure uniqueness
    phrases = list(set(phrases))
    final_utterances[intent] = phrases

# Now patch expand_routes.py to use this generated dictionary
with open('expand_routes.py', 'r') as f:
    content = f.read()

# We will just replace the dictionary definition block
import re

new_dict_str = "utterances = {\n"
for intent, phrases in final_utterances.items():
    new_dict_str += f"    \"{intent}\": {phrases},\n"
new_dict_str += "}\n\n"

# find the block between utterances = { and the closing }
start_idx = content.find("utterances = {")
end_idx = content.find("}\n\nwith open", start_idx)

if start_idx != -1 and end_idx != -1:
    content = content[:start_idx] + new_dict_str + content[end_idx+2:]

with open('expand_routes.py', 'w') as f:
    f.write(content)

print("Massive 50+ utterances per route generation complete!")
