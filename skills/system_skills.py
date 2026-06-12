import datetime
import os
try:
    import psutil
except ImportError:
    psutil = None

def execute_skill(intent_name, text=""):
    if intent_name == "get_time":
        now = datetime.datetime.now()
        return now.strftime("It is currently %I:%M %p.")
        
    elif intent_name == "lock_pc":
        os.system("rundll32.exe user32.dll,LockWorkStation")
        return "Locking the computer, sir."
        
    elif intent_name == "battery_status":
        if psutil:
            battery = psutil.sensors_battery()
            if battery:
                percent = battery.percent
                plugged = "plugged in" if battery.power_plugged else "on battery power"
                return f"You are at {percent} percent battery, and the system is {plugged}."
            else:
                return "I couldn't read the battery status, sir. You might be on a desktop."
        else:
            return "I need the psutil library installed to check battery status."

    elif intent_name == "system_stats":
        if psutil:
            cpu = psutil.cpu_percent(interval=0.5)
            ram = psutil.virtual_memory()
            free_ram_gb = round(ram.available / (1024**3), 1)
            total_ram_gb = round(ram.total / (1024**3), 1)
            return f"CPU usage is at {cpu} percent. You have {free_ram_gb} gigabytes of RAM free out of {total_ram_gb} gigabytes."
        return "I need the psutil library installed to check system stats."

    elif intent_name == "empty_trash":
        import ctypes
        # 7 = SHERB_NOCONFIRMATION | SHERB_NOPROGRESSUI | SHERB_NOSOUND
        result = ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, 7)
        if result == 0:
            return "I have emptied the recycle bin, sir."
        return "The recycle bin is already empty."

    elif intent_name == "open_folder":
        import re
        match = re.search(r'open\s+(?:my\s+)?(?:the\s+)?(downloads|documents|pictures|desktop|music|videos)(?:\s+folder)?', text.lower())
        if match:
            folder = match.group(1).strip()
            # On Windows, these are standard shell folders
            shell_map = {
                "downloads": "Downloads",
                "documents": "Documents",
                "pictures": "Pictures",
                "desktop": "Desktop",
                "music": "Music",
                "videos": "Videos"
            }
            target = shell_map.get(folder)
            if target:
                os.system(f"start shell:{target}")
                return f"Opening your {folder} folder, sir."
        return "Which folder would you like me to open?"

    elif intent_name == "power_action":
        if "sleep" in text.lower():
            return "__CONFIRM__sleep_pc__Are you sure you want to put the computer to sleep?"
        elif "restart" in text.lower():
            return "__CONFIRM__restart_pc__Are you sure you want to restart the computer?"
        elif "shut down" in text.lower() or "turn off" in text.lower():
            return "__CONFIRM__shutdown_pc__Are you sure you want to shut down the computer?"
        return "Which power action did you want me to perform?"

    elif intent_name == "minimize_windows":
        import pyautogui
        pyautogui.hotkey('win', 'd')
        return "Minimizing all windows."

    elif intent_name == "close_window":
        import pyautogui
        pyautogui.hotkey('alt', 'f4')
        return "Closing the current window."

    elif intent_name == "take_screenshot":
        import pyautogui
        pyautogui.press('printscreen')
        return "Screenshot taken, sir."

    elif intent_name == "media_play_pause":
        import pyautogui
        pyautogui.press("playpause")
        return "Toggling media playback."
        
    elif intent_name == "media_next":
        import pyautogui
        pyautogui.press("nexttrack")
        return "Skipping to the next track."

    elif intent_name == "media_prev":
        import pyautogui
        pyautogui.press("prevtrack")
        return "Going back to the previous track."

    elif intent_name == "volume_up":
        import pyautogui
        for _ in range(5):
            pyautogui.press("volumeup")
        return "Turning the volume up."
        
    elif intent_name == "volume_down":
        import pyautogui
        for _ in range(5):
            pyautogui.press("volumedown")
        return "Turning the volume down."
        
    elif intent_name == "volume_mute":
        import pyautogui
        pyautogui.press("volumemute")
        return "Muting the system volume."

    elif intent_name == "focus_window":
        import re
        import pyautogui
        match = re.search(r'(?:focus|bring to front|switch to|show me|go to the|bring up)\s+(.+)', text.lower())
        if match:
            app_name = match.group(1).strip()
            # remove words like "window" or "app"
            app_name = re.sub(r'\s+(?:window|app|application)$', '', app_name).strip()
            
            windows = [w for w in pyautogui.getAllWindows() if w.title and w.visible]
            target_window = None
            
            for w in windows:
                if app_name.lower() in w.title.lower():
                    target_window = w
                    break
                    
            if target_window:
                try:
                    if target_window.isMinimized:
                        target_window.restore()
                    target_window.activate()
                    return f"Focusing {app_name}, sir."
                except Exception as e:
                    return f"I found {app_name}, but I couldn't focus it."
            else:
                return f"I couldn't find any open window for {app_name}."
        return "Which window should I focus?"

    return None
