import os
import json

def scan_apps():
    print("Scanning system for installed applications...")
    paths_to_scan = [
        os.path.expandvars(r"%ProgramData%\Microsoft\Windows\Start Menu\Programs"),
        os.path.expandvars(r"%AppData%\Microsoft\Windows\Start Menu\Programs")
    ]
    
    apps_dict = {}
    
    for base_path in paths_to_scan:
        if not os.path.exists(base_path):
            continue
            
        for root, _, files in os.walk(base_path):
            for file in files:
                if file.lower().endswith('.lnk') or file.lower().endswith('.exe'):
                    # The display name is the filename without extension
                    app_name = os.path.splitext(file)[0].lower()
                    
                    # Clean up some common garbage from shortcut names
                    app_name = app_name.replace(" (x86)", "").replace(" (x64)", "")
                    
                    full_path = os.path.join(root, file)
                    apps_dict[app_name] = full_path

    # Hardcode some common utilities that don't always have simple start menu shortcuts
    common_apps = {
        "chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        "notepad": "notepad.exe",
        "calculator": "calc.exe",
        "command prompt": "cmd.exe",
        "cmd": "cmd.exe",
        "settings": "ms-settings:",
        "file explorer": "explorer.exe",
        "task manager": "taskmgr.exe"
    }
    
    for k, v in common_apps.items():
        if k not in apps_dict:
            apps_dict[k] = v
            
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "apps.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(apps_dict, f, indent=4)
        
    print(f"Successfully scanned {len(apps_dict)} applications and saved to {output_path}")

if __name__ == "__main__":
    scan_apps()
