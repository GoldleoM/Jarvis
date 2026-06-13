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

    elif intent_name == "wifi_action":
        if "off" in text.lower() or "disable" in text.lower() or "disconnect" in text.lower():
            os.system("netsh wlan disconnect")
            return "I have disconnected your active Wi-Fi connection, sir."
        elif "on" in text.lower() or "enable" in text.lower() or "connect" in text.lower():
            return "I cannot dynamically select a Wi-Fi network to connect to, please connect manually."
        return "Did you want me to turn the Wi-Fi on or off?"

    elif intent_name == "open_settings":
        os.system("start ms-settings:")
        return "Opening Windows Settings, sir."
        
    elif intent_name == "open_task_manager":
        os.system("start taskmgr")
        return "Opening Task Manager, sir."
        
    elif intent_name == "open_control_panel":
        os.system("start control")
        return "Opening Control Panel, sir."
        
    elif intent_name == "clear_clipboard":
        os.system("echo off | clip")
        return "Clipboard cleared, sir."

    elif intent_name == "flush_dns":
        os.system("ipconfig /flushdns")
        return "DNS cache has been successfully flushed, sir."

    elif intent_name == "clear_temp_files":
        import tempfile
        temp_dir = tempfile.gettempdir()
        os.system(f"del /q /f /s \"{temp_dir}\\*\" >nul 2>&1")
        return "Temporary files and system cache have been cleared, sir."

    elif intent_name == "kill_task":
        import re
        match = re.search(r'(?:force close|kill|terminate|force quit|end task|kill the process|shut down|exit|stop|close)\s+(.+)', text.lower())
        if match:
            app_name = match.group(1).strip()
            app_name = re.sub(r'\s+(?:task|process|app)$', '', app_name).strip()
            os.system(f"taskkill /F /IM {app_name}.exe /T >nul 2>&1")
            return f"I have forcefully terminated the {app_name} process tree, sir."
        return "Which application would you like me to close?"

    elif intent_name == "theme_toggle":
        if "dark" in text.lower():
            val = 0
            mode = "Dark"
        elif "light" in text.lower():
            val = 1
            mode = "Light"
        else:
            return "Did you want dark mode or light mode?"
            
        ps_cmd = f"New-ItemProperty -Path HKCU:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize -Name AppsUseLightTheme -Value {val} -Type Dword -Force; New-ItemProperty -Path HKCU:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize -Name SystemUsesLightTheme -Value {val} -Type Dword -Force"
        os.system(f'powershell -Command "{ps_cmd}"')
        return f"Switched the Windows system theme to {mode} mode, sir."

    elif intent_name == "set_brightness":
        import re
        match = re.search(r'(\d+)', text.lower())
        if match:
            level = int(match.group(1))
            if level < 0: level = 0
            if level > 100: level = 100
            ps_cmd = f"(Get-WmiObject -Namespace root/wmi -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1,{level})"
            os.system(f'powershell -Command "{ps_cmd}"')
            return f"Screen brightness set to {level} percent. Note that this may only apply to built-in laptop displays."
        return "What percentage should I set the brightness to?"

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
        import ctypes
        # VK_MEDIA_PLAY_PAUSE = 0xB3, KEYEVENTF_EXTENDEDKEY = 1, KEYEVENTF_KEYUP = 2
        ctypes.windll.user32.keybd_event(0xB3, 0, 1, 0)
        ctypes.windll.user32.keybd_event(0xB3, 0, 3, 0)
        return "Toggling media playback."
        
    elif intent_name == "media_next":
        import ctypes
        # VK_MEDIA_NEXT_TRACK = 0xB0
        ctypes.windll.user32.keybd_event(0xB0, 0, 1, 0)
        ctypes.windll.user32.keybd_event(0xB0, 0, 3, 0)
        return "Skipping to the next track."

    elif intent_name == "media_prev":
        import ctypes
        # VK_MEDIA_PREV_TRACK = 0xB1
        ctypes.windll.user32.keybd_event(0xB1, 0, 1, 0)
        ctypes.windll.user32.keybd_event(0xB1, 0, 3, 0)
        return "Going back to the previous track."

    elif intent_name == "volume_up":
        import ctypes
        import re
        
        steps = 5
        match = re.search(r'(\d+)', text)
        if match:
            steps = max(1, min(50, int(match.group(1)) // 2))
        elif "a lot" in text.lower():
            steps = 15
        elif "a little" in text.lower() or "slightly" in text.lower():
            steps = 2
        elif "max" in text.lower() or "full" in text.lower() or "100" in text.lower():
            steps = 50

        # VK_VOLUME_UP = 0xAF
        for _ in range(steps):
            ctypes.windll.user32.keybd_event(0xAF, 0, 1, 0)
            ctypes.windll.user32.keybd_event(0xAF, 0, 3, 0)
        return "Turning the volume up."
        
    elif intent_name == "volume_down":
        import ctypes
        import re
        
        steps = 5
        match = re.search(r'(\d+)', text)
        if match:
            steps = max(1, min(50, int(match.group(1)) // 2))
        elif "a lot" in text.lower():
            steps = 15
        elif "a little" in text.lower() or "slightly" in text.lower():
            steps = 2
        elif "mute" in text.lower() or "zero" in text.lower():
            steps = 50

        # VK_VOLUME_DOWN = 0xAE
        for _ in range(steps):
            ctypes.windll.user32.keybd_event(0xAE, 0, 1, 0)
            ctypes.windll.user32.keybd_event(0xAE, 0, 3, 0)
        return "Turning the volume down."
        
    elif intent_name == "set_volume":
        import re
        match = re.search(r'(\d+)', text)
        if match:
            level = max(0, min(100, int(match.group(1))))
            try:
                import comtypes
                comtypes.CoInitialize()
                from pycaw.pycaw import AudioUtilities
                devices = AudioUtilities.GetSpeakers()
                interface = devices.EndpointVolume
                interface.SetMasterVolumeLevelScalar(level / 100.0, None)
                return f"Setting the volume to {level} percent."
            except ImportError:
                return "I'm sorry, the pycaw library is not installed to set absolute volume."
            except Exception as e:
                print(f"[System Skills] Error setting volume: {e}")
                return "I couldn't set the absolute volume."
        else:
            return "I didn't catch the volume percentage."

    elif intent_name == "volume_mute":
        import ctypes
        # VK_VOLUME_MUTE = 0xAD
        ctypes.windll.user32.keybd_event(0xAD, 0, 1, 0)
        ctypes.windll.user32.keybd_event(0xAD, 0, 3, 0)
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
