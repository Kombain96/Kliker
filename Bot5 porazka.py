import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText
import threading
import time
import pyautogui
import keyboard
import os
import numpy as np
import cv2
from PIL import Image, ImageTk
import json

class AutoClicker:
    def __init__(self, root):
        self.root = root
        self.root.title("Auto Key Clicker")
        self.running = False
        self.tracking_enabled = False
        self.selected_region = None  # (x, y, width, height)

        # Konfiguracja klawiszy i interwałów (10 par)
        self.key_entries = []
        self.interval_entries = []
        for i in range(10):
            frame = ttk.Frame(root)
            frame.grid(row=i, column=0, padx=5, pady=2, sticky='w')
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
        frame_mouse.grid(row=10, column=0, padx=5, pady=2, sticky='w')
        ttk.Label(frame_mouse, text="Prawy przycisk myszy").pack(side=tk.LEFT)
        ttk.Label(frame_mouse, text="Czas (s):").pack(side=tk.LEFT)
        self.mouse_interval_entry = ttk.Entry(frame_mouse, width=5)
        self.mouse_interval_entry.pack(side=tk.LEFT, padx=5)

        # Etykieta statusu
        self.status_label = ttk.Label(root, text="Stan: OFF", font=("Arial", 12))
        self.status_label.grid(row=11, column=0, padx=5, pady=5)

        # Ramka wyboru regionu (interaktywnie)
        frame_region = ttk.Frame(root)
        frame_region.grid(row=12, column=0, padx=5, pady=2, sticky='w')
        self.select_region_button = ttk.Button(frame_region, text="Wybierz region", command=self.select_region)
        self.select_region_button.pack(side=tk.LEFT)
        self.region_label = ttk.Label(frame_region, text="Region: Cały ekran")
        self.region_label.pack(side=tk.LEFT, padx=5)

        # Ustawienia tolerancji koloru
        frame_tolerance = ttk.Frame(root)
        frame_tolerance.grid(row=13, column=0, padx=5, pady=2, sticky='w')
        ttk.Label(frame_tolerance, text="Tolerancja koloru (Min Red, Max Green, Max Blue):").pack(side=tk.LEFT)
        self.red_min_entry = ttk.Entry(frame_tolerance, width=5)
        self.red_min_entry.pack(side=tk.LEFT, padx=2)
        self.green_max_entry = ttk.Entry(frame_tolerance, width=5)
        self.green_max_entry.pack(side=tk.LEFT, padx=2)
        self.blue_max_entry = ttk.Entry(frame_tolerance, width=5)
        self.blue_max_entry.pack(side=tk.LEFT, padx=2)
        self.red_min_entry.insert(0, "250")
        self.green_max_entry.insert(0, "10")
        self.blue_max_entry.insert(0, "10")

        # Ustawienia klawiszy sterujących
        frame_keys = ttk.Frame(root)
        frame_keys.grid(row=14, column=0, padx=5, pady=2, sticky='w')
        ttk.Label(frame_keys, text="Klawisz włączania/wyłączania:").pack(side=tk.LEFT)
        self.toggle_key_entry = ttk.Entry(frame_keys, width=5)
        self.toggle_key_entry.pack(side=tk.LEFT, padx=2)
        self.toggle_key_entry.insert(0, "`")
        ttk.Label(frame_keys, text="Klawisz panic:").pack(side=tk.LEFT)
        self.panic_key_entry = ttk.Entry(frame_keys, width=5)
        self.panic_key_entry.pack(side=tk.LEFT, padx=2)
        self.panic_key_entry.insert(0, "esc")
        self.rebind_button = ttk.Button(frame_keys, text="Zmień klawisze", command=self.rebind_hotkeys)
        self.rebind_button.pack(side=tk.LEFT, padx=5)

        # Ustawienia wykrywania konturów
        frame_contour = ttk.Frame(root)
        frame_contour.grid(row=15, column=0, padx=5, pady=2, sticky='w')
        ttk.Label(frame_contour, text="Min Obszar Konturu:").pack(side=tk.LEFT)
        self.min_contour_entry = ttk.Entry(frame_contour, width=5)
        self.min_contour_entry.pack(side=tk.LEFT, padx=2)
        self.min_contour_entry.insert(0, "100")
        ttk.Label(frame_contour, text="Wykrywanie kształtu:").pack(side=tk.LEFT)
        self.shape_var = tk.StringVar(value="Any")
        self.shape_option = ttk.Combobox(frame_contour, textvariable=self.shape_var, values=["Any", "Rectangle", "Circle"], width=10)
        self.shape_option.pack(side=tk.LEFT, padx=2)

        # Ramka zapisu/wczytania konfiguracji
        frame_config = ttk.Frame(root)
        frame_config.grid(row=16, column=0, padx=5, pady=2, sticky='w')
        self.save_config_button = ttk.Button(frame_config, text="Zapisz konfigurację", command=self.save_config)
        self.save_config_button.pack(side=tk.LEFT, padx=2)
        self.load_config_button = ttk.Button(frame_config, text="Wczytaj konfigurację", command=self.load_config)
        self.load_config_button.pack(side=tk.LEFT, padx=2)

        # Podgląd analizowanego obszaru (na panelu bocznym)
        frame_preview = ttk.Frame(root)
        frame_preview.grid(row=0, column=1, rowspan=17, padx=5, pady=5)
        ttk.Label(frame_preview, text="Podgląd analizowanego obszaru:").pack()
        self.preview_label = ttk.Label(frame_preview)
        self.preview_label.pack()

        # Panel logów
        self.log_text = ScrolledText(root, height=10, width=50)
        self.log_text.grid(row=17, column=0, columnspan=2, padx=5, pady=5)

        # Przypisanie hotkeyów (domyślne z pól)
        self.rebind_hotkeys()

        # Uruchomienie wątku śledzenia obiektu
        self.tracking_thread = threading.Thread(target=self.track_object, daemon=True)
        self.tracking_thread.start()

    # ----------------------- Interaktywne wybieranie regionu -----------------------
    def select_region(self):
        # Utwórz pełnoekranowe okno Toplevel jako nakładkę
        self.region_window = tk.Toplevel(self.root)
        self.region_window.attributes('-fullscreen', True)
        self.region_window.attributes('-alpha', 0.3)  # półprzezroczyste
        self.region_window.config(bg='gray')
        self.region_window.bind("<ButtonPress-1>", self.on_region_mouse_down)
        self.region_window.bind("<B1-Motion>", self.on_region_mouse_move)
        self.region_window.bind("<ButtonRelease-1>", self.on_region_mouse_up)
        self.start_x = self.start_y = None
        # Użyj Canvas do rysowania zaznaczenia
        self.canvas = tk.Canvas(self.region_window, bg="white")
        self.canvas.place(x=0, y=0, relwidth=1, relheight=1)

    def on_region_mouse_down(self, event):
        self.start_x, self.start_y = event.x, event.y
        self.canvas.delete("sel")

    def on_region_mouse_move(self, event):
        if self.start_x is not None and self.start_y is not None:
            self.canvas.delete("sel")
            self.canvas.create_rectangle(self.start_x, self.start_y, event.x, event.y, outline='red', width=2, tag="sel")

    def on_region_mouse_up(self, event):
        if self.start_x is None or self.start_y is None:
            return
        end_x, end_y = event.x, event.y
        x1 = min(self.start_x, end_x)
        y1 = min(self.start_y, end_y)
        x2 = max(self.start_x, end_x)
        y2 = max(self.start_y, end_y)
        self.selected_region = (x1, y1, x2 - x1, y2 - y1)
        self.region_label.config(text=f"Region: {self.selected_region}")
        self.region_window.destroy()
        self.log_message(f"Region wybrany: {self.selected_region}")

    # ----------------------- Rebinding klawiszy -----------------------
    def rebind_hotkeys(self):
        keyboard.unhook_all_hotkeys()
        toggle_key = self.toggle_key_entry.get()
        panic_key = self.panic_key_entry.get()
        keyboard.add_hotkey(toggle_key, self.toggle_clicking)
        keyboard.add_hotkey(panic_key, self.panic_stop)
        self.log_message(f"Hotkeys ustawione: Toggle = {toggle_key}, Panic = {panic_key}")

    # ----------------------- Zapis/Wczytanie konfiguracji -----------------------
    def save_config(self):
        config = {
            "keys": [entry.get() for entry in self.key_entries],
            "intervals": [entry.get() for entry in self.interval_entries],
            "mouse_interval": self.mouse_interval_entry.get(),
            "region": self.selected_region,
            "red_min": self.red_min_entry.get(),
            "green_max": self.green_max_entry.get(),
            "blue_max": self.blue_max_entry.get(),
            "toggle_key": self.toggle_key_entry.get(),
            "panic_key": self.panic_key_entry.get(),
            "min_contour_area": self.min_contour_entry.get(),
            "shape_filter": self.shape_var.get()
        }
        with open("config.json", "w") as f:
            json.dump(config, f)
        self.log_message("Konfiguracja zapisana.")

    def load_config(self):
        try:
            with open("config.json", "r") as f:
                config = json.load(f)
            for entry, value in zip(self.key_entries, config.get("keys", [])):
                entry.delete(0, tk.END)
                entry.insert(0, value)
            for entry, value in zip(self.interval_entries, config.get("intervals", [])):
                entry.delete(0, tk.END)
                entry.insert(0, value)
            self.mouse_interval_entry.delete(0, tk.END)
            self.mouse_interval_entry.insert(0, config.get("mouse_interval", ""))
            self.selected_region = config.get("region", None)
            if self.selected_region:
                self.region_label.config(text=f"Region: {self.selected_region}")
            self.red_min_entry.delete(0, tk.END)
            self.red_min_entry.insert(0, config.get("red_min", "250"))
            self.green_max_entry.delete(0, tk.END)
            self.green_max_entry.insert(0, config.get("green_max", "10"))
            self.blue_max_entry.delete(0, tk.END)
            self.blue_max_entry.insert(0, config.get("blue_max", "10"))
            self.toggle_key_entry.delete(0, tk.END)
            self.toggle_key_entry.insert(0, config.get("toggle_key", "`"))
            self.panic_key_entry.delete(0, tk.END)
            self.panic_key_entry.insert(0, config.get("panic_key", "esc"))
            self.min_contour_entry.delete(0, tk.END)
            self.min_contour_entry.insert(0, config.get("min_contour_area", "100"))
            self.shape_var.set(config.get("shape_filter", "Any"))
            self.rebind_hotkeys()
            self.log_message("Konfiguracja wczytana.")
        except Exception as e:
            self.log_message("Błąd wczytywania konfiguracji: " + str(e))

    # ----------------------- Auto klikacz -----------------------
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
            threading.Thread(target=self.click_loop, args=(keys_intervals,), daemon=True).start()
            self.log_message("Klikacz uruchomiony.")

    def stop_clicking(self):
        self.running = False
        self.log_message("Klikacz zatrzymany.")

    def toggle_clicking(self):
        if self.running or self.tracking_enabled:
            self.running = False
            self.tracking_enabled = False
            self.status_label.config(text="Stan: OFF", foreground="red")
            self.log_message("Klikacz i śledzenie zatrzymane.")
        else:
            self.start_clicking()
            self.tracking_enabled = True
            self.status_label.config(text="Stan: ON", foreground="green")
            self.log_message("Klikacz i śledzenie uruchomione.")

    def panic_stop(self):
        self.running = False
        self.tracking_enabled = False
        self.status_label.config(text="Stan: PANIC", foreground="red")
        self.log_message("Panic button activated: Stopped all clicking and tracking.")

    def log_message(self, msg):
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {msg}\n")
        self.log_text.see(tk.END)

    # ----------------------- Śledzenie obiektu z użyciem OpenCV -----------------------
    def track_object(self):
        while True:
            if self.tracking_enabled:
                try:
                    # Pobranie regionu – jeśli został wybrany, inaczej pełny ekran
                    if self.selected_region:
                        x, y, w, h = self.selected_region
                        screenshot = pyautogui.screenshot(region=(x, y, w, h))
                        offset_x, offset_y = x, y
                    else:
                        screenshot = pyautogui.screenshot()
                        offset_x, offset_y = 0, 0

                    # Konwersja zrzutu do tablicy (RGB)
                    img_rgb = np.array(screenshot)

                    # Tworzenie maski na podstawie tolerancji kolorów
                    red_min = int(self.red_min_entry.get())
                    green_max = int(self.green_max_entry.get())
                    blue_max = int(self.blue_max_entry.get())
                    lower = np.array([red_min, 0, 0])
                    upper = np.array([255, green_max, blue_max])
                    mask = cv2.inRange(img_rgb, lower, upper)

                    # Wyszukiwanie konturów
                    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    valid_contour = None
                    max_area = 0
                    try:
                        min_area = float(self.min_contour_entry.get())
                    except:
                        min_area = 100
                    shape_filter = self.shape_var.get()
                    for cnt in contours:
                        area = cv2.contourArea(cnt)
                        if area < min_area:
                            continue
                        if shape_filter == "Rectangle":
                            approx = cv2.approxPolyDP(cnt, 0.02 * cv2.arcLength(cnt, True), True)
                            if len(approx) != 4:
                                continue
                        elif shape_filter == "Circle":
                            perimeter = cv2.arcLength(cnt, True)
                            if perimeter == 0:
                                continue
                            circularity = 4 * np.pi * (area / (perimeter * perimeter))
                            if circularity < 0.7:
                                continue
                        if area > max_area:
                            max_area = area
                            valid_contour = cnt

                    annotated_img = img_rgb.copy()
                    if valid_contour is not None:
                        x_rect, y_rect, w_rect, h_rect = cv2.boundingRect(valid_contour)
                        center_x = x_rect + w_rect // 2 + offset_x
                        center_y = y_rect + h_rect // 2 + offset_y
                        pyautogui.moveTo(center_x, center_y, duration=0.5)
                        cv2.rectangle(annotated_img, (x_rect, y_rect), (x_rect + w_rect, y_rect + h_rect), (0, 255, 0), 2)
                        self.log_message(f"Przesunięto kursor do obiektu: ({center_x}, {center_y})")
                    # Aktualizacja podglądu: przekształcenie obrazu na format kompatybilny z Tkinter
                    annotated_img = cv2.cvtColor(annotated_img, cv2.COLOR_RGB2BGR)
                    im_pil = Image.fromarray(cv2.cvtColor(annotated_img, cv2.COLOR_BGR2RGB))
                    imgtk = ImageTk.PhotoImage(im_pil)
                    self.preview_label.imgtk = imgtk
                    self.preview_label.config(image=imgtk)
                except Exception as e:
                    self.log_message("Błąd w śledzeniu: " + str(e))
            time.sleep(0.1)

if __name__ == "__main__":
    os.system("title Auto Key Clicker")
    root = tk.Tk()
    app = AutoClicker(root)
    root.mainloop()
