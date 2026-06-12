with open('main.py', 'r') as f:
    content = f.read()

new_typebox = '''
    def _run_typebox(self):
        import tkinter as tk
        root = tk.Tk()
        root.title("Jarvis Typebox")
        root.geometry("450x60")
        root.attributes("-topmost", True)
        root.configure(bg="#1E1E1E")
        
        entry = tk.Entry(root, font=("Segoe UI", 14), width=45, bg="#333333", fg="white", insertbackground="white", relief="flat")
        entry.pack(padx=10, pady=10)
        entry.focus_set()
        
        def on_enter(event):
            text = entry.get()
            entry.delete(0, tk.END)
            if text.strip() and self.loop:
                # Inject text identically to voice
                self.loop.call_soon_threadsafe(self.queue.put_nowait, text)
                
        entry.bind('<Return>', on_enter)
        root.mainloop()
'''

if 'def _run_typebox(self):' not in content:
    insert_idx = content.find('    def on_speech_detected(self, text):')
    if insert_idx != -1:
        content = content[:insert_idx] + new_typebox + '\n' + content[insert_idx:]

init_injection = '''        self.notes_mode = False
        
        # Launch the Typebox UI
        import threading
        threading.Thread(target=self._run_typebox, daemon=True).start()
'''

content = content.replace('        self.notes_mode = False', init_injection)

with open('main.py', 'w') as f:
    f.write(content)

print("Patched main.py with Typebox GUI")
