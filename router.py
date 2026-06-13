import os
import sys

# Optional: suppress transformers logging spam
os.environ["TRANSFORMERS_VERBOSITY"] = "error"

from semantic_router import Route
from semantic_router.encoders import HuggingFaceEncoder
from semantic_router.routers import SemanticRouter
from skills import system_skills, app_skills

class Gatekeeper:
    def __init__(self):
        print("Initializing Gatekeeper (Semantic Router)...")
        # Ensure we use a small, fast model
        self.encoder = HuggingFaceEncoder(name="sentence-transformers/all-MiniLM-L6-v2")
        
        # System & Butler Intents
        self.get_time_route = Route(name="get_time", utterances=['tell me the time', 'i want to know say the time', 'i want to know give me the time', 'can you do you have the time', 'can you what time is it', 'i want to know what time is it', 'read the clock', 'hey jarvis tell me the time', 'hey jarvis what time is it', 'what is the current time', 'i want to know what time do we have', "i want to know what's the time", 'i want to know what is the current time', 'what time do we have', 'hey jarvis do you have the time', 'can you what time do we have', 'can you give me the time', 'can you what is the current time', 'say the time', "can you what's the time", 'please what time is it', 'hey jarvis what time do we have', 'check the time', 'do you have the time', 'can you check the time', 'please read the clock', "what's the time", 'please what time do we have', 'please do you have the time', 'hey jarvis read the clock', "please what's the time", 'please tell me the time', 'what time is it', 'please say the time', 'can you read the clock', 'hey jarvis check the time', 'can you tell me the time', 'hey jarvis what is the current time', 'please give me the time', 'please what is the current time', 'hey jarvis say the time', 'i want to know do you have the time', 'i want to know tell me the time', 'give me the time', 'can you say the time', 'hey jarvis give me the time', "hey jarvis what's the time", 'please check the time', 'i want to know read the clock', 'i want to know check the time'])
        self.lock_pc_route = Route(name="lock_pc", utterances=['jarvis lock windows', 'jarvis secure the desktop', 'i need you to lock the screen', 'can you secure the desktop', 'lock my session', 'can you lock my computer', 'please lock windows', 'jarvis lock my computer', 'jarvis put the computer in lock mode', 'lock the machine', 'i need you to lock my session', 'please lock the pc', 'please lock my computer', 'lock windows', 'jarvis secure my pc', 'i need you to lock windows', 'i need you to put the computer in lock mode', 'please lock the machine', 'jarvis lock the pc', 'secure my pc', 'can you lock the pc', 'jarvis secure the workstation', 'can you lock my session', 'i need you to lock the machine', 'please secure the desktop', 'jarvis lock the screen', 'can you lock windows', 'i need you to secure my pc', 'can you put the computer in lock mode', 'i need you to lock my computer', 'jarvis lock the machine', 'please put the computer in lock mode', 'can you secure the workstation', 'jarvis lock my session', 'i need you to secure the workstation', 'secure the desktop', 'lock the screen', 'please secure my pc', 'please lock the screen', 'i need you to secure the desktop', 'secure the workstation', 'lock the pc', 'please lock my session', 'i need you to lock the pc', 'please secure the workstation', 'put the computer in lock mode', 'can you lock the screen', 'lock my computer', 'can you secure my pc', 'can you lock the machine'])
        self.battery_route = Route(name="battery_status", utterances=["what is the battery percentage", "check the battery", "how much battery is left", "battery status"])
        
        # Window Management
        self.focus_window_route = Route(name="focus_window", utterances=['focus', 'bring to front', 'switch to', 'show me', 'go to the', 'bring up', 'can you focus', 'i want to switch to'])
        
        # Trash/Ignore
        self.ignore_route = Route(name="ignore_action", utterances=[
            'nevermind', 'ignore that', 'cancel that', 'forget it', 'never mind', 'nothing', "doesn't matter"
        ])
        
        # Sleep
        self.sleep_route = Route(name="sleep_action", utterances=[
            'jarvis', 'stop', 'quiet', 'shut up', 'uhh', 'umm', 'stop speaking', 'shh', 'be quiet', 
            'enough', 'stop talking', 'wait', 'hold on', 'abort', "don't worry about it", 
            'nevermind jarvis', 'stop it', 'stop jarvis', 'skip', 'mute', 'unmute', 'volume zero', 
            'silence', 'shut your mouth', 'zip it', 'button it', 'put a sock in it', 'give it a rest', 
            'take a break', 'stop right there', 'halt', 'cease', 'desist', 'drop it', 'let it go', 
            'clear', 'reset', 'say again', 'pardon', 'huh', 'eh', 'come again', 'speak up', 'hmm', 
            'ah', 'uh huh', 'um hmm'
        ])
        self.minimize_windows_route = Route(name="minimize_windows", utterances=['can you go to desktop', 'can you clear the screen', 'show the desktop', 'quickly minimize windows', 'clear the screen', 'can you get rid of these windows', 'quickly hide everything', 'please show the desktop', 'quickly show the desktop', 'can you minimize all windows', 'please get rid of these windows', 'quickly clear the screen', 'quickly minimize all windows', 'please show my wallpaper', 'minimize windows', 'can you minimize windows', 'can you show my wallpaper', 'minimize my apps', 'can you hide everything', 'hide all windows', 'minimize all windows', 'go to desktop', 'quickly minimize my apps', 'quickly get rid of these windows', 'quickly go to desktop', 'please clear the screen', 'please hide all windows', 'can you minimize my apps', 'can you show the desktop', 'hide everything', 'show my wallpaper', 'please go to desktop', 'please minimize all windows', 'quickly show my wallpaper', 'please hide everything', 'can you hide all windows', 'quickly hide all windows', 'get rid of these windows', 'please minimize windows', 'please minimize my apps'])
        self.close_window_route = Route(name="close_window", utterances=['quit this program', 'please quit the active program', 'please exit this screen', 'jarvis terminate this app', 'can you close this window', 'terminate this app', 'close the active window', 'please exit the app', 'can you exit the app', 'quit the active program', 'exit the app', 'jarvis close the active window', 'close what i am looking at', 'can you quit this program', 'please quit this program', 'jarvis close the current app', 'can you exit this screen', 'can you quit the active program', 'can you close what i am looking at', 'jarvis close what i am looking at', 'jarvis quit the active program', 'please shut this window', 'jarvis quit this program', 'please terminate this app', 'please close the current app', 'jarvis close this window', 'jarvis exit the app', 'jarvis exit this screen', 'can you shut this window', 'jarvis shut this window', 'please close what i am looking at', 'close this window', 'please close this window', 'exit this screen', 'can you close the current app', 'close the current app', 'can you close the active window', 'can you terminate this app', 'shut this window', 'please close the active window'])
        self.focus_app_route = Route(name="focus_app", utterances=['focus on spotify', 'focus google chrome', 'switch to obs studio', 'bring discord to front', 'go to visual studio', 'can you switch to chrome', 'please focus on the browser', 'focus the browser', 'bring the browser to front', 'switch to the browser', 'switch over to spotify', 'focus anti-gravity', 'can you focus on my ide', 'bring up the terminal', 'switch back to chrome', 'make spotify the active window', 'can you pull up visual studio', 'i need to see discord', 'show me obs studio', 'jump to the web browser', 'put focus on discord', 'can you bring spotify up', 'switch my screen to chrome', 'activate the terminal window', 'please pull up brave', 'switch me over to discord', 'i want to switch to visual studio', 'show me spotify please', 'make chrome the active window', 'focus on that app', 'switch to the active window', 'bring that window up', 'focus the terminal', 'jump over to the terminal'])
        self.screenshot_route = Route(name="take_screenshot", utterances=["take a screenshot", "screenshot the screen", "capture the screen"])
        self.restart_engine_route = Route(name="restart_engine", utterances=["restart yourself", "jarvis restart the engine", "reboot yourself", "jarvis restart yourself", "restart the application", "restart the app", "restart the system", "reboot the engine"])

        # Media & Volume
        self.media_play_pause_route = Route(name="media_play_pause", utterances=['play', 'pause', 'stop', 'resume', 'please toggle playback', 'please stop playing', 'stop the audio', 'can you play this', 'can you toggle playback', 'please play the media', 'can you play the media', 'can you pause the music', 'toggle playback', 'please pause the music', 'please play the music', 'please resume playback', 'can you stop the audio', 'can you resume playback', 'resume playback', 'please stop the audio', 'please pause this', 'can you play the music', 'play the media', 'pause the music', 'pause the video', 'can you pause the video', 'can you stop playing', 'please play this', 'play this', 'can you pause this', 'pause this', 'play the music', 'please pause the video', 'stop playing'])
        self.media_next_route = Route(name="media_next", utterances=['next', 'skip', 'please go to the next song', 'play the next one', 'can you play the next one', 'can you skip forward', 'skip music', 'next song', 'can you skip this track', 'skip forward', 'can you skip music', 'next media', 'can you skip song', 'please forward track', 'can you forward track', 'please next media', 'please skip song', 'please skip this track', 'please skip forward', 'go to the next song', 'skip this track', 'please skip music', 'please play the next one', 'skip song', 'please next song', 'forward track', 'please next track', 'can you next song', 'can you go to the next song', 'can you next media', 'next track', 'can you next track'])
        self.media_prev_route = Route(name="media_prev", utterances=['previous', 'back', 'go back', 'previous media', 'play the last song', 'please back track', 'please play the last song', 'can you previous track', 'please play that again', 'can you previous song', 'can you rewind track', 'rewind track', 'can you go to the previous music', 'please last song', 'please previous song', 'previous song', 'please previous media', 'can you last song', 'can you back track', 'can you previous media', 'please previous track', 'can you go back a track', 'last song', 'previous track', 'please go back a track', 'can you play the last song', 'can you play that again', 'go back a track', 'please go to the previous music', 'back track', 'play that again', 'go to the previous music', 'please rewind track'])
        self.volume_up_route = Route(name="volume_up", utterances=['please turn it up', 'turn the volume up', 'turn it up', 'can you turn the sound up', 'please turn the volume up', 'increase sound', 'can you make it louder', 'can you turn it up', 'can you sound up', 'can you louder please', 'louder please', 'please increase the volume', 'can you volume up', 'please pump up the volume', 'can you increase the volume', 'please increase sound', 'please turn the sound up', 'please louder please', 'make it louder', 'sound up', 'please make it louder', 'volume up', 'pump up the volume', 'can you pump up the volume', 'can you increase sound', 'turn the sound up', 'increase the volume', 'can you turn the volume up', 'please volume up', 'please sound up'])
        self.volume_down_route = Route(name="volume_down", utterances=['volume down', 'can you sound down', 'can you turn the volume down', 'turn it down', 'please lower the volume', 'turn the volume down', 'please turn the audio down', 'can you reduce the sound', 'please volume down', 'turn the audio down', 'decrease the volume', 'lower the volume', 'can you turn it down', 'can you lower the volume', 'please turn the volume down', 'please turn it down', 'please sound down', 'can you make it quieter', 'can you volume down', 'quieter please', 'reduce the sound', 'can you quieter please', 'can you turn the audio down', 'please reduce the sound', 'please make it quieter', 'please decrease the volume', 'please quieter please', 'can you decrease the volume', 'make it quieter', 'sound down'])
        self.volume_mute_route = Route(name="volume_mute", utterances=['please stop the sound', 'can you turn off the sound', 'mute my pc', 'please mute my pc', 'please mute the sound', 'mute computer', 'please mute the volume', 'can you cut the audio', 'can you mute computer', 'please silence it', 'cut the audio', 'can you mute the sound', 'please silence the audio', 'can you mute the volume', 'can you mute it', 'can you silence it', 'please turn off the sound', 'please mute computer', 'mute the volume', 'silence the audio', 'can you mute my pc', 'turn off the sound', 'please mute it', 'please cut the audio', 'can you stop the sound', 'stop the sound', 'mute the sound', 'can you silence the audio', 'mute it', 'silence it'])

        self.power_route = Route(name="power_action", utterances=['immediately turn this computer off', 'can you sleep mode', 'immediately restart the pc', 'shut down the computer', 'please restart windows', 'jarvis put the computer to sleep', 'power off the machine', 'please restart the pc', 'jarvis restart windows', 'can you shut down the computer', 'please power off the machine', 'jarvis power off the machine', 'jarvis hibernate the pc', 'can you restart the pc', 'immediately restart windows', 'put the computer to sleep', 'can you turn off the pc', 'can you reboot the system', 'restart windows', 'can you restart windows', 'please put the computer to sleep', 'immediately shut down the computer', 'turn this computer off', 'jarvis shut down the computer', 'can you power off the machine', 'please sleep mode', 'jarvis reboot the system', 'please turn off the pc', 'jarvis restart the pc', 'hibernate the pc', 'restart the pc', 'reboot the system', 'please turn this computer off', 'jarvis turn this computer off', 'can you hibernate the pc', 'turn off the pc', 'immediately turn off the pc', 'immediately power off the machine', 'please reboot the system', 'can you turn this computer off', 'immediately hibernate the pc', 'jarvis sleep mode', 'jarvis turn off the pc', 'immediately sleep mode', 'sleep mode', 'immediately reboot the system', 'please hibernate the pc', 'can you put the computer to sleep', 'please shut down the computer', 'immediately put the computer to sleep'])
        self.notes_mode_route = Route(name="notes_mode", utterances=['start typing what i say', 'please record my notes', "let's enter notes mode", "let's write this down", 'i want to start typing what i say', "let's take a memo", 'please start typing what i say', 'please take some notes', 'open notepad and listen', "let's open notepad and listen", "let's take some notes", 'please start dictation', 'take a memo', 'jot this down', "let's jot this down", 'take some notes', 'enter notes mode', 'i want to jot this down', 'begin dictation', 'i want to open notepad and listen', 'i want to record my notes', "let's start typing what i say", "let's record my notes", "let's start dictation", 'please open notepad and listen', 'please write this down', 'i want to begin dictation', 'please enter notes mode', 'please take a memo', "let's begin dictation", 'record my notes', 'i want to start dictation', 'please jot this down', 'start dictation', 'i want to enter notes mode', 'i want to take a memo', 'i want to take some notes', 'write this down', 'please begin dictation', 'i want to write this down'])

        self.system_stats_route = Route(name="system_stats", utterances=['check memory usage', 'please system health check', 'can you system monitor', 'please what is the ram usage', 'please system monitor', 'can you check memory usage', 'what is the ram usage', 'diagnose the system', 'check system stats', 'please how is the computer doing', 'please check system stats', 'please diagnose the system', 'how is the computer doing', 'please how is the cpu', 'can you check system stats', 'can you read out pc performance', "what's my cpu at", 'can you what is the ram usage', 'how is the cpu', 'can you system health check', "can you what's my cpu at", 'please read out pc performance', 'system health check', 'can you diagnose the system', 'can you how is the cpu', 'read out pc performance', 'system monitor', 'please check memory usage', "please what's my cpu at", 'can you how is the computer doing'])
        self.empty_trash_route = Route(name="empty_trash", utterances=['empty recycling', 'jarvis empty out the bin', 'please empty out the bin', 'jarvis clear the recycle bin', 'can you clear my garbage', 'jarvis wipe the recycle bin', 'can you clear the recycle bin', 'jarvis empty the recycle bin', 'empty the trash', 'clear my garbage', 'can you purge the trash', 'jarvis empty recycling', 'can you empty recycling', 'jarvis clean the trash', 'clear the recycle bin', 'please purge the trash', 'please delete the trash', 'please wipe the recycle bin', 'jarvis delete the trash', 'empty the recycle bin', 'please clear my garbage', 'can you empty the recycle bin', 'jarvis purge the trash', 'wipe the recycle bin', 'jarvis clear my garbage', 'please empty recycling', 'can you wipe the recycle bin', 'purge the trash', 'clean the trash', 'please clean the trash', 'can you empty out the bin', 'can you clean the trash', 'jarvis empty the trash', 'empty out the bin', 'can you empty the trash', 'please clear the recycle bin', 'can you delete the trash', 'delete the trash', 'please empty the recycle bin', 'please empty the trash'])
        self.open_folder_route = Route(name="open_folder", utterances=['please navigate to downloads', 'please go to my desktop folder', 'i want to open my stuff', 'i want to open my downloads', 'open my downloads', 'show documents', 'i want to open my music', 'please open pictures folder', 'can you show documents', 'can you open pictures folder', 'can you open my music', 'i want to show documents', 'can you open my downloads', 'navigate to downloads', 'can you show my files', 'please show my files', 'please open my music', 'i want to show my files', 'go to my desktop folder', 'i want to go to my desktop folder', 'please show documents', 'open the videos', 'please open the videos', 'please open file explorer', 'open pictures folder', 'i want to open file explorer', 'open file explorer', 'can you open file explorer', 'please open my downloads', 'can you go to my desktop folder', 'can you open the videos', 'can you navigate to downloads', 'show my files', 'open my music', 'open my stuff', 'please open my stuff', 'i want to open the videos', 'i want to navigate to downloads', 'can you open my stuff', 'i want to open pictures folder'])
        self.type_text_route = Route(name="type_text", utterances=['type this down', 'i want you to type this down', 'insert this text', 'input this text', 'type exactly this', 'write this on the screen', 'can you type the following', 'can you type this down', 'i want you to type the following', 'i want you to type what i say', 'please insert this text', 'i want you to type exactly this', 'please type what i say', 'please type exactly this', 'write this text', 'i want you to write this text', 'can you input this text', 'can you type what i say', 'please type the following', 'can you write this on the screen', 'please type this out', 'type the following', 'please type this down', 'can you type this out', 'type this out', 'i want you to input this text', 'can you insert this text', 'can you write this text', 'i want you to dictate this for me', 'dictate this for me', 'i want you to write this on the screen', 'can you type exactly this', 'please write this text', 'please write this on the screen', 'i want you to type this out', 'please dictate this for me', 'can you dictate this for me', 'type what i say', 'i want you to insert this text', 'please input this text'])
        self.wifi_action_route = Route(name="wifi_action", utterances=["turn off wifi", "disable wifi", "disconnect from wifi", "turn off the internet", "turn on wifi", "enable wifi", "connect to wifi", "turn on the internet"])
        
        # Windows OS Controls
        self.open_settings_route = Route(name="open_settings", utterances=["open settings", "open windows settings", "show me settings", "go to settings"])
        self.open_task_manager_route = Route(name="open_task_manager", utterances=["open task manager", "show running processes", "task manager", "check task manager", "show processes", "bring up task manager"])
        self.open_control_panel_route = Route(name="open_control_panel", utterances=["open control panel", "control panel", "show control panel"])
        self.clear_clipboard_route = Route(name="clear_clipboard", utterances=["clear my clipboard", "empty clipboard", "clear the clipboard", "wipe clipboard", "erase my clipboard"])
        
        # Deep Windows Controls
        self.flush_dns_route = Route(name="flush_dns", utterances=["flush dns", "reset the dns cache", "clear the dns cache", "flush my network dns", "reset my network connection"])
        self.clear_temp_route = Route(name="clear_temp_files", utterances=["clear temporary files", "clean my system cache", "delete temp files", "empty my temp folder", "clean up my temporary files", "clear windows cache"])
        self.kill_task_route = Route(name="kill_task", utterances=['close this app', 'can you close spotify', 'please close whatsapp', 'i want to close discord', 'shut down chrome', 'exit this program', 'jarvis close the calculator', 'please shut down the application', 'can you close this program', 'stop spotify', 'force close it', 'close the app', 'please close the program', 'kill the process', 'terminate the application', 'i need you to close this app', 'can you shut down discord', 'please exit chrome', 'close whatsapp please', 'shut down the app', 'close it', 'please close it'])
        self.theme_toggle_route = Route(name="theme_toggle", utterances=["turn on dark mode", "enable dark mode", "switch to light mode", "turn on light theme", "enable dark theme", "change windows to dark mode"])
        self.set_brightness_route = Route(name="set_brightness", utterances=["set brightness to 50", "change screen brightness to 100", "turn down the brightness to 20", "make the screen brightness 70 percent"])


        # Generalized Apps & Search
        self.spotify_route = Route(name="spotify", utterances=['play starboy on spotify', 'play music on spotify', 'listen to drake on spotify', 'play the weeknd on spotify', 'spotify play blinding lights', 'play on spotify'])
        self.open_website_route = Route(name="open_website", utterances=[
            "open amazon.com", "go to youtube.com", "open a website", "launch google.com", "go to facebook.com",
            "open the website", "open the url", "go to the link", "browse to", "navigate to", "open web page",
            "open amazon", "open netflix", "open github.com"
        ])
        self.weather_route = Route(name="weather", utterances=["what's the weather", 'please local weather', 'can you local weather', 'please is it raining outside', "can you what's the weather", 'i want to weather in tokyo', 'please how cold is it', 'is it sunny', 'is it raining outside', 'how is the weather', 'please weather update', 'i want to is it sunny', 'i want to local weather', 'how cold is it', 'please weather in tokyo', 'i want to weather forecast', 'please weather forecast', 'please current temperature', 'weather forecast', 'can you how cold is it', 'can you current temperature', 'can you weather update', 'can you weather in tokyo', 'i want to how is the weather', 'please is it sunny', 'can you weather forecast', 'please how is the weather', 'can you how is the weather', 'can you is it sunny', 'weather in tokyo', 'i want to current temperature', 'i want to how cold is it', 'current temperature', 'weather update', 'local weather', "i want to what's the weather", 'can you is it raining outside', 'i want to is it raining outside', "please what's the weather", 'i want to weather update'])
        self.open_app_route = Route(name="open_app", utterances=['i want to open discord', 'start notepad', 'please launch chrome', 'can you launch visual studio', 'can you start notepad', 'launch chrome', 'open discord', 'can you open discord', 'can you start the calculator', 'launch visual studio', 'please open the camera', 'can you launch chrome', 'open brave', 'open the camera', 'i want to open the camera', 'can you open brave', 'i want to open brave', 'launch steam', 'can you launch steam', 'open valorant', 'i want to launch chrome', 'start the calculator', 'please start the calculator', 'please open discord', 'can you open spotify', 'please open brave', 'i want to open valorant', 'i want to launch visual studio', 'can you open valorant', 'i want to launch steam', 'please open spotify', 'please start notepad', 'i want to open spotify', 'open spotify', 'i want to start notepad', 'please launch visual studio', 'can you open the camera', 'i want to start the calculator', 'please open valorant', 'please launch steam'])
        self.search_web_route = Route(name="search_web", utterances=['i want to google this', 'look up on the internet', 'can you look up on the internet', 'i want to search online for', 'search bing for', 'look it up online', 'can you query google for', 'can you google this', 'do a web search', 'search the web for', 'can you find information about', 'i want to look up on the internet', 'search online for', 'please look up on the internet', 'i want to look it up online', 'please do a web search', 'can you look it up online', 'find on the internet', 'please find information about', 'i want to find information about', 'i want to find on the internet', 'please look it up online', 'i want to search bing for', 'can you search online for', 'please google this', 'please search online for', 'please search the web for', 'can you find on the internet', 'can you search bing for', 'google this', 'i want to query google for', 'find information about', 'please query google for', 'can you do a web search', 'i want to search the web for', 'please find on the internet', 'please search bing for', 'can you search the web for', 'i want to do a web search', 'query google for'])
        
        self.youtube_route = Route(name="youtube", utterances=['please find on youtube', 'can you search for this video', 'can you find on youtube', 'find a youtube video', 'youtube search', 'play this on youtube', 'please look up on youtube', 'please play the youtube video', 'can you watch a video about', 'can you youtube search', 'i want to search youtube for', 'look up on youtube', 'i want to play this on youtube', 'watch a video about', 'i want to watch a video about', 'please find a youtube video', 'can you play a video on youtube', 'i want to search for this video', 'i want to find a youtube video', 'search for this video', 'play the youtube video', 'i want to look up on youtube', 'i want to play a video on youtube', 'find on youtube', 'can you find a youtube video', 'play a video on youtube', 'can you play this on youtube', 'please search for this video', 'i want to play the youtube video', 'i want to find on youtube', 'please search youtube for', 'can you look up on youtube', 'please youtube search', 'please play this on youtube', 'can you search youtube for', 'i want to youtube search', 'can you play the youtube video', 'search youtube for', 'please play a video on youtube', 'please watch a video about'])
        self.wikipedia_route = Route(name="wikipedia", utterances=['who is', 'what is', 'define', 'tell me about', 'look up on wikipedia', 'give me the definition of', 'who was', 'what are', 'search wikipedia for', 'can you tell me about', 'give me some information on', 'i want to know about', 'find out who is', 'explain what is', 'what does it mean', 'meaning of'])
        self.timer_route = Route(name="timer", utterances=['set a timer for', 'set timer', 'set a timer', 'wake me up in', 'remind me in', 'start a timer for', 'give me a timer for', 'countdown from', 'set an alarm for', 'can you set a timer', 'i need a timer', 'timer for', 'start the clock for', 'put a timer on for', 'alert me in', 'let me know in', 'remind me to'])
        self.math_route = Route(name="math", utterances=['calculate', 'what is plus', 'what is divided by', 'what is times', 'what is minus', 'math problem', 'can you calculate', 'do some math', 'multiply', 'divide', 'add', 'subtract', "what's the sum of", 'what does it equal', 'equals', 'give me the answer to', 'solve this math'])
        self.joke_route = Route(name="joke", utterances=['can you fun fact please', 'please interesting fact', 'please say something funny', 'interesting fact', 'i want to make me smile', 'i want to tell me a joke', 'i want to fun fact please', 'give me a fun fact', 'i need a joke', 'i want to say a joke', 'i want to i need a joke', 'i want to tell me a trivia', 'tell me a trivia', 'i want to interesting fact', 'please make me smile', 'can you say a joke', 'please fun fact please', 'please say a joke', 'please i need a joke', 'can you tell me a joke', 'can you give me a fun fact', 'can you make me laugh', 'say a joke', 'say something funny', 'i want to give me a fun fact', 'please tell me a trivia', 'please make me laugh', 'can you interesting fact', 'can you make me smile', 'tell me a joke', 'i want to make me laugh', 'fun fact please', 'can you say something funny', 'can you tell me a trivia', 'please tell me a joke', 'can you i need a joke', 'i want to say something funny', 'make me laugh', 'please give me a fun fact', 'make me smile'])
        self.date_route = Route(name="date", utterances=['current date', 'please current date', 'i want to what is the date', 'i want to date today', 'please what day is it', 'what is the date', 'please what month is it', 'i want to what day of the week is it', 'please date today', 'can you what month is it', 'i want to read the calendar', 'can you what day of the week is it', 'i want to current date', 'can you what day is it', 'please what is the date', 'can you read the calendar', 'can you what is the date', 'i want to what year is it', 'please what day of the week is it', 'please read the calendar', "give me today's date", 'i want to tell me the date today', 'what day is it', 'read the calendar', "can you give me today's date", 'i want to what month is it', 'can you what year is it', 'what month is it', 'can you date today', "please give me today's date", 'i want to what day is it', 'please what year is it', 'what year is it', 'can you tell me the date today', "i want to give me today's date", 'what day of the week is it', 'please tell me the date today', 'can you current date', 'date today', 'tell me the date today'])
        self.whatsapp_route = Route(name="whatsapp", utterances=['send a text', 'i want to send a whatsapp to', 'please message a friend', 'i want to text a contact', 'send a whatsapp message', 'shoot a text to', 'send a whatsapp to', 'can you text a contact', 'i want to whatsapp message', 'please send a whatsapp to', 'i want to send a text', 'can you shoot a text to', 'can you message a friend', 'whatsapp message', 'can you send a text', 'please whatsapp message', 'please shoot a text to', 'message someone on whatsapp', 'please text someone', 'i want to message someone on whatsapp', 'message a friend', 'can you send a message', 'text a contact', 'i want to send a whatsapp message', 'send a message', 'can you send a whatsapp message', 'please send a message', 'can you whatsapp message', 'i want to send a message', 'i want to shoot a text to', 'please send a text', 'please message someone on whatsapp', 'i want to message a friend', 'please send a whatsapp message', 'text someone', 'please text a contact', 'i want to text someone', 'can you text someone', 'can you send a whatsapp to', 'can you message someone on whatsapp'])
        self.call_route = Route(name="call", utterances=['can you phone someone', 'please phone someone', 'i want to start a call', 'make a phone call', 'please dial a number', 'can you make a voice call', 'dial a number', 'i want to make a phone call', 'can you voice call', 'please voice call', 'phone someone', 'i want to i need to call', 'i want to make a voice call', 'i want to call my friend', 'i need to call', 'voice call', 'please call my friend', 'make a voice call', 'i want to voice call', 'can you make a phone call', 'call my friend', 'can you start a call', 'start a call', 'call a contact', 'can you i need to call', 'can you call my friend', 'i want to phone someone', 'please make a voice call', 'call someone', 'please call someone', 'i want to dial a number', 'please i need to call', 'i want to call a contact', 'i want to call someone', 'can you dial a number', 'please start a call', 'please make a phone call', 'please call a contact', 'can you call someone', 'can you call a contact'])
        self.writer_route = Route(name="writer", utterances=[])
        self.coding_route = Route(name="coding", utterances=['please write some code', 'fix the bug', 'write some code', 'can you debug this program', 'i want to run opencode', 'please build an app', 'code a website', 'i want to build an app', 'i want to analyze this code', 'build an app', 'program a script', 'i want to write a python script', 'can you run opencode', 'analyze this code', 'please code a website', 'please analyze this code', 'can you code a website', 'can you write some code', 'please run opencode', 'i want to debug this program', 'can you analyze this code', 'debug this program', 'i want to program a script', 'can you write a python script', 'please fix the bug', 'i want to write some code', 'write a python script', 'i want to code a website', 'can you program a script', 'can you fix the bug', 'please create a new file', 'can you create a new file', 'please program a script', 'please write a python script', 'run opencode', 'i want to fix the bug', 'create a new file', 'can you build an app', 'please debug this program', 'i want to create a new file'])
        self.ghostwriter_route = Route(name="ghostwriter", utterances=['draft an email', 'write a message saying', 'draft a prompt to', 'compose an email about', 'draft a letter to', 'can you draft a reply', 'write an essay about', 'type an email asking', 'type a message to', 'generate a response', 'draft a message'])
        self.press_key_route = Route(name="press_key", utterances=['hit enter', 'press enter', 'hit the enter key', 'press space', 'hit backspace', 'press escape', 'hit tab', 'press the spacebar', 'hit escape', 'press return'])

        self.routes = [
            self.get_time_route, self.lock_pc_route, self.battery_route,
            self.power_route, self.notes_mode_route,
            self.minimize_windows_route, self.close_window_route, self.screenshot_route,
            self.media_play_pause_route, self.media_next_route, self.media_prev_route,
            self.volume_up_route, self.volume_down_route, self.volume_mute_route,
            self.system_stats_route, self.empty_trash_route, self.open_folder_route, self.type_text_route, self.weather_route, self.open_website_route,
            self.open_app_route, self.search_web_route, self.youtube_route, self.coding_route,
            self.wikipedia_route, self.timer_route, self.math_route, self.joke_route, 
            self.date_route, self.whatsapp_route, self.call_route, self.writer_route,
            self.ignore_route, self.sleep_route, self.wifi_action_route,
            self.ghostwriter_route, self.press_key_route, self.spotify_route,
            self.open_settings_route, self.open_task_manager_route, self.open_control_panel_route,
            self.clear_clipboard_route, self.flush_dns_route, self.clear_temp_route,
            self.kill_task_route, self.theme_toggle_route, self.set_brightness_route,
            self.restart_engine_route, self.focus_app_route
        ]
        
        self.router = SemanticRouter(encoder=self.encoder, routes=self.routes, auto_sync="local")

    def route_command(self, text):
        text_lower = text.lower()
        
        # Hard intercept for volume controls (Semantic Router confuses antonyms)
        import re
        if re.search(r'(?:set\s+)?volume(?:\s+(?:to|at|level))?\s+\d+', text_lower):
            return app_skills.execute_skill("set_volume", text) or system_skills.execute_skill("set_volume", text)
        if "volume down" in text_lower or "turn down" in text_lower or "quieter" in text_lower:
            return app_skills.execute_skill("volume_down", text) or system_skills.execute_skill("volume_down", text)
        if "volume up" in text_lower or "turn up" in text_lower or "louder" in text_lower:
            return app_skills.execute_skill("volume_up", text) or system_skills.execute_skill("volume_up", text)

        # Hard intercept for app launching
        import re
        if re.match(r'^(?:please\s+)?(?:open|launch|start)\s+([a-zA-Z0-9\s]+)', text_lower):
            print(f"[Gatekeeper] Intercepted app launch command: {text}")
            res = app_skills.execute_skill("open_app", text)
            if res:
                return res
                
        # Hard intercept for closing apps
        if re.match(r'^(?:please\s+)?(?:close|shut down|quit|exit)\s+([a-zA-Z0-9\s]+)', text_lower):
            print(f"[Gatekeeper] Intercepted app close command: {text}")
            res = app_skills.execute_skill("kill_task", text)
            if res:
                return res

        decision = self.router(text)
        
        if decision.name:
            print(f"[Gatekeeper] Matched intent: {decision.name}")
            
            # --- INTELLIGENCE LAYER: Context & Conversational Override ---
            action_intents = {
                "power_action", "clear_clipboard", "empty_trash", "kill_task", 
                "lock_pc", "restart_engine", "wifi_action", "theme_toggle", 
                "set_brightness", "open_task_manager"
            }
            
            if decision.name in action_intents:
                # 1. Check for conversational questions
                question_patterns = [
                    r'^(should i|why|how|am i|can i|do i|is it|what if|would it|could i|whats|what is)\b',
                    r'\b(instead|then|anyway|even|explain|look into)\b',
                    r'\?'
                ]
                is_question = any(re.search(pattern, text_lower) for pattern in question_patterns)
                
                # Exceptions where 'can i' or 'do i' actually mean the command
                if is_question and not re.search(r'^(can you|please|i want to|i need you to)', text_lower):
                    print(f"[Gatekeeper] Override: Detected conversational inquiry for action '{decision.name}'. Routing to LLM...")
                    return None
                    
            # 2. Specific intent overrides
            if decision.name == "clear_clipboard":
                if any(word in text_lower for word in ["copy", "save", "write", "logs", "read"]):
                    print(f"[Gatekeeper] Override: Detected 'copy' intent rather than 'clear'. Routing to LLM...")
                    return None
            # -----------------------------------------------------------
            
            if decision.name == "coding":
                return "__CODING__"
            
            if decision.name == "ignore_action":
                return "__IGNORE__"
            
            if decision.name == "sleep_action":
                return "__SLEEP__"
                
            if decision.name == "restart_engine":
                return "__RESTART__"
                
            # Pass text to execute_skill for regex extraction
            res = system_skills.execute_skill(decision.name, text)
            if res:
                return res
            
            res = app_skills.execute_skill(decision.name, text)
            if res:
                return res
        
        print("[Gatekeeper] No local match found. Routing to LLM...")
        return None
