import tkinter as tk
from tkinter import ttk
import threading
import time
import pyautogui
import keyboard
import mouse
import os

class AutoClicker:
    def __init__(self, root):
        self.root = root
        self.root.title("Auto Key Clicker")
        
        self.running = False
        
        self.key_entries = []
        self.interval_entries = []
        
        for i in range(10):
            frame = ttk.Frame(root)
            frame.grid(row=i, column=0, padx=5, pady=5, sticky='w')
            
            ttk.Label(frame, text=f"Klawisz {i+1}:").pack(side=tk.LEFT)
            key_entry = ttk.Entry(frame, width=5)
            key_entry.pack(side=tk.LEFT, padx=5)
            self.key_entries.append(key_entry)
            
            ttk.Label(frame, text="Czas (s):").pack(side=tk.LEFT)
            interval_entry = ttk.Entry(frame, width=5)
            interval_entry.pack(side=tk.LEFT, padx=5)
            self.interval_entries.append(interval_entry)
        
        frame = ttk.Frame(root)
        frame.grid(row=10, column=0, padx=5, pady=5, sticky='w')
        
        ttk.Label(frame, text="Prawy przycisk myszy").pack(side=tk.LEFT)
        ttk.Label(frame, text="Czas (s):").pack(side=tk.LEFT)
        self.mouse_interval_entry = ttk.Entry(frame, width=5)
        self.mouse_interval_entry.pack(side=tk.LEFT, padx=5)
        
        self.status_label = ttk.Label(root, text="Stan: OFF", font=("Arial", 12))
        self.status_label.grid(row=11, column=0, padx=5, pady=5)
        
        keyboard.add_hotkey('`', self.toggle_clicking)
        
        self.tracking_thread = threading.Thread(target=self.track_object, daemon=True)
        self.tracking_thread.start()
        
    def click_loop(self, keys_intervals):
        while self.running:
            for key, interval in keys_intervals:
                if key == "RightClick":
                    mouse.click(button='right')
                else:
                    keyboard.press_and_release(key)
                time.sleep(interval)
        
    def start_clicking(self):
        keys_intervals = []
        
        for entry, interval_entry in zip(self.key_entries, self.interval_entries):
            key = entry.get()
            interval = interval_entry.get()
            if key and interval:
                try:
                    interval = float(interval)
                    if interval > 0:
                        keys_intervals.append((key, interval))
                except ValueError:
                    interval_entry.delete(0, tk.END)
                    interval_entry.insert(0, "Błąd")
        
        mouse_interval = self.mouse_interval_entry.get()
        if mouse_interval:
            try:
                mouse_interval = float(mouse_interval)
                if mouse_interval > 0:
                    keys_intervals.append(("RightClick", mouse_interval))
            except ValueError:
                self.mouse_interval_entry.delete(0, tk.END)
                self.mouse_interval_entry.insert(0, "Błąd")
        
        if keys_intervals:
            self.running = True
            self.status_label.config(text="Stan: ON", foreground="green")
            thread = threading.Thread(target=self.click_loop, args=(keys_intervals,), daemon=True)
            thread.start()
        
    def stop_clicking(self):
        self.running = False
        self.status_label.config(text="Stan: OFF", foreground="red")
    
    def toggle_clicking(self):
        if self.running:
            self.stop_clicking()
        else:
            self.start_clicking()
    
    def track_object(self):
        while True:
            try:
                x, y = pyautogui.position()
                pixel_color = pyautogui.screenshot().getpixel((x, y))
                if pixel_color == (255, 0, 0):  # Wykrywa obiekt podświetlony na czerwono
                    pyautogui.moveTo(x, y, duration=0.5)
            except Exception as e:
                print("Błąd w śledzeniu obiektu:", e)
            time.sleep(0.1)

if __name__ == "__main__":
    os.system("title Auto Key Clicker")  # Ustawia tytuł konsoli w Windows
    root = tk.Tk()
    app = AutoClicker(root)
    root.mainloop()
