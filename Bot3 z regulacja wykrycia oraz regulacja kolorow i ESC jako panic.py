import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText
import threading
import time
import pyautogui
import keyboard
import os
import numpy as np

class AutoClicker:
    def __init__(self, root):
        self.root = root
        self.root.title("Auto Key Clicker")
        
        self.running = False
        
        # Pola dla klawiszy i interwałów
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
        
        # Konfiguracja kliknięcia prawym przyciskiem myszy
        frame_mouse = ttk.Frame(root)
        frame_mouse.grid(row=10, column=0, padx=5, pady=5, sticky='w')
        ttk.Label(frame_mouse, text="Prawy przycisk myszy").pack(side=tk.LEFT)
        ttk.Label(frame_mouse, text="Czas (s):").pack(side=tk.LEFT)
        self.mouse_interval_entry = ttk.Entry(frame_mouse, width=5)
        self.mouse_interval_entry.pack(side=tk.LEFT, padx=5)
        
        # Status
        self.status_label = ttk.Label(root, text="Stan: OFF", font=("Arial", 12))
        self.status_label.grid(row=11, column=0, padx=5, pady=5)
        
        # Region wyszukiwania obiektu (opcjonalnie)
        frame_region = ttk.Frame(root)
        frame_region.grid(row=12, column=0, padx=5, pady=5, sticky='w')
        ttk.Label(frame_region, text="Region (X, Y, Width, Height):").pack(side=tk.LEFT)
        self.region_x_entry = ttk.Entry(frame_region, width=5)
        self.region_x_entry.pack(side=tk.LEFT, padx=2)
        self.region_y_entry = ttk.Entry(frame_region, width=5)
        self.region_y_entry.pack(side=tk.LEFT, padx=2)
        self.region_width_entry = ttk.Entry(frame_region, width=5)
        self.region_width_entry.pack(side=tk.LEFT, padx=2)
        self.region_height_entry = ttk.Entry(frame_region, width=5)
        self.region_height_entry.pack(side=tk.LEFT, padx=2)
        # Domyślne wartości (0 oznacza pełny ekran)
        self.region_x_entry.insert(0, "0")
        self.region_y_entry.insert(0, "0")
        self.region_width_entry.insert(0, "0")
        self.region_height_entry.insert(0, "0")
        
        # Ustawienia tolerancji koloru
        frame_tolerance = ttk.Frame(root)
        frame_tolerance.grid(row=13, column=0, padx=5, pady=5, sticky='w')
        ttk.Label(frame_tolerance, text="Tolerancja koloru (Min Red, Max Green, Max Blue):").pack(side=tk.LEFT)
        self.red_min_entry = ttk.Entry(frame_tolerance, width=5)
        self.red_min_entry.pack(side=tk.LEFT, padx=2)
        self.green_max_entry = ttk.Entry(frame_tolerance, width=5)
        self.green_max_entry.pack(side=tk.LEFT, padx=2)
        self.blue_max_entry = ttk.Entry(frame_tolerance, width=5)
        self.blue_max_entry.pack(side=tk.LEFT, padx=2)
        # Domyślne wartości
        self.red_min_entry.insert(0, "250")
        self.green_max_entry.insert(0, "10")
        self.blue_max_entry.insert(0, "10")
        
        # Panel logów
        self.log_text = ScrolledText(root, height=5, width=50)
        self.log_text.grid(row=14, column=0, padx=5, pady=5)
        
        # Hotkey do włączania/wyłączania klikacza oraz panic (ESC)
        keyboard.add_hotkey('`', self.toggle_clicking)
        keyboard.add_hotkey('esc', self.panic_stop)
        
        self.tracking_thread = threading.Thread(target=self.track_object, daemon=True)
        self.tracking_thread.start()
    
    def click_loop(self, keys_intervals):
        while self.running:
            for key, interval in keys_intervals:
                if not self.running:
                    break
                if key == "RightClick":
                    pyautogui.click(button='right')
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
            self.log_message("Klikacz uruchomiony.")
    
    def stop_clicking(self):
        self.running = False
        self.status_label.config(text="Stan: OFF", foreground="red")
        self.log_message("Klikacz zatrzymany.")
    
    def toggle_clicking(self):
        if self.running:
            self.stop_clicking()
        else:
            self.start_clicking()
    
    def panic_stop(self):
        self.running = False
        self.status_label.config(text="Stan: PANIC", foreground="red")
        self.log_message("Panic button activated: Stopped all clicking.")
    
    def log_message(self, msg):
        def append():
            timestamp = time.strftime("%H:%M:%S")
            self.log_text.insert(tk.END, f"[{timestamp}] {msg}\n")
            self.log_text.see(tk.END)
        self.root.after(0, append)
    
    def track_object(self):
        while True:
            try:
                # Pobieranie ustawień regionu
                try:
                    region_x = int(self.region_x_entry.get())
                    region_y = int(self.region_y_entry.get())
                    region_width = int(self.region_width_entry.get())
                    region_height = int(self.region_height_entry.get())
                except ValueError:
                    region_x, region_y, region_width, region_height = 0, 0, 0, 0
                
                if region_width > 0 and region_height > 0:
                    screenshot = pyautogui.screenshot(region=(region_x, region_y, region_width, region_height))
                    offset_x, offset_y = region_x, region_y
                else:
                    screenshot = pyautogui.screenshot()
                    offset_x, offset_y = 0, 0
                
                img = np.array(screenshot)
                
                # Pobieranie ustawień tolerancji koloru
                try:
                    red_min = int(self.red_min_entry.get())
                    green_max = int(self.green_max_entry.get())
                    blue_max = int(self.blue_max_entry.get())
                except ValueError:
                    red_min, green_max, blue_max = 250, 10, 10
                
                # Tworzymy maskę dla pikseli spełniających kryteria koloru
                red_mask = (img[:, :, 0] >= red_min) & (img[:, :, 1] <= green_max) & (img[:, :, 2] <= blue_max)
                indices = np.argwhere(red_mask)
                if indices.size > 0:
                    # Pobieramy współrzędne pierwszego wykrytego czerwonego piksela
                    y, x = indices[0]
                    final_x = x + offset_x
                    final_y = y + offset_y
                    pyautogui.moveTo(final_x, final_y, duration=0.5)
                    self.log_message(f"Przesunięto kursor do czerwonego obiektu na ({final_x}, {final_y}).")
            except Exception as e:
                self.log_message("Błąd w śledzeniu obiektu: " + str(e))
            time.sleep(0.1)

if __name__ == "__main__":
    os.system("title Auto Key Clicker")
    root = tk.Tk()
    app = AutoClicker(root)
    root.mainloop()
