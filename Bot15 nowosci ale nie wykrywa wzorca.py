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
        # Ustawienia stylu i kolorów – teraz z niebieską kolorystyką
        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.style.configure("TFrame", background="#ADD8E6")
        self.style.configure("TLabel", background="#ADD8E6", foreground="#333333", font=("Arial", 10))
        self.style.configure("TButton", background="#87CEFA", foreground="#000000", font=("Arial", 10))
        root.config(bg="#ADD8E6")
        
        self.root = root
        self.root.title("Kobra 7.0")
        self.running = False
        self.tracking_enabled = False
        self.selected_region = None  # (x, y, width, height)
        self.template_img = None  # Wzorzec obrazu do zaawansowanego wyszukiwania

        # -------------------- Dynamiczne klawisze (do przypisywania) --------------------
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

        # -------------------- Konfiguracja kliknięcia prawym przyciskiem myszy --------------------
        frame_mouse = ttk.Frame(root)
        frame_mouse.grid(row=10, column=0, padx=5, pady=2, sticky='w')
        ttk.Label(frame_mouse, text="Prawy przycisk myszy").pack(side=tk.LEFT)
        ttk.Label(frame_mouse, text="Czas (s):").pack(side=tk.LEFT)
        self.mouse_interval_entry = ttk.Entry(frame_mouse, width=5)
        self.mouse_interval_entry.pack(side=tk.LEFT, padx=5)

        # -------------------- Etykieta statusu --------------------
        self.status_label = ttk.Label(root, text="Stan: OFF", font=("Arial", 12))
        self.status_label.grid(row=11, column=0, padx=5, pady=5, sticky="w")

        # -------------------- Interaktywne wybieranie regionu --------------------
        frame_region = ttk.Frame(root)
        frame_region.grid(row=12, column=0, padx=5, pady=2, sticky='w')
        self.select_region_button = ttk.Button(frame_region, text="Wybierz region", command=self.select_region)
        self.select_region_button.pack(side=tk.LEFT)
        self.region_label = ttk.Label(frame_region, text="Region: Cały ekran")
        self.region_label.pack(side=tk.LEFT, padx=5)

        # -------------------- Ustawienia klawiszy sterujących --------------------
        frame_keys = ttk.Frame(root)
        frame_keys.grid(row=13, column=0, padx=5, pady=2, sticky='w')
        ttk.Label(frame_keys, text="Klawisz włączania/wyłączania:").pack(side=tk.LEFT)
        self.toggle_key_entry = ttk.Entry(frame_keys, width=5)
        self.toggle_key_entry.pack(side=tk.LEFT, padx=2)
        self.toggle_key_entry.insert(0, "`")
        ttk.Label(frame_keys, text="Klawisz panic:").pack(side=tk.LEFT)
        self.panic_key_entry = ttk.Entry(frame_keys, width=5)
        self.panic_key_entry.pack(side=tk.LEFT, padx=2)
        self.panic_key_entry.insert(0, "esc")
        ttk.Label(frame_keys, text="Klawisz testowego zrzutu:").pack(side=tk.LEFT)
        self.test_key_entry = ttk.Entry(frame_keys, width=5)
        self.test_key_entry.pack(side=tk.LEFT, padx=2)
        self.test_key_entry.insert(0, "F9")
        self.rebind_button = ttk.Button(frame_keys, text="Zmień klawisze", command=self.rebind_hotkeys)
        self.rebind_button.pack(side=tk.LEFT, padx=5)

        # -------------------- Ustawienia wykrywania kształtów --------------------
        frame_contour = ttk.Frame(root)
        frame_contour.grid(row=14, column=0, padx=5, pady=2, sticky='w')
        ttk.Label(frame_contour, text="Min Obszar Konturu:").pack(side=tk.LEFT)
        self.min_contour_entry = ttk.Entry(frame_contour, width=5)
        self.min_contour_entry.pack(side=tk.LEFT, padx=2)
        self.min_contour_entry.insert(0, "100")
        ttk.Label(frame_contour, text="Wykrywanie kształtu:").pack(side=tk.LEFT)
        self.shape_var = tk.StringVar(value="Any")
        self.shape_option = ttk.Combobox(frame_contour, textvariable=self.shape_var, values=["Any", "Rectangle", "Circle"], width=10)
        self.shape_option.pack(side=tk.LEFT, padx=2)

        # -------------------- Zapis/Wczytanie konfiguracji --------------------
        frame_config = ttk.Frame(root)
        frame_config.grid(row=15, column=0, padx=5, pady=2, sticky='w')
        self.save_config_button = ttk.Button(frame_config, text="Zapisz konfigurację", command=self.save_config)
        self.save_config_button.pack(side=tk.LEFT, padx=2)
        self.load_config_button = ttk.Button(frame_config, text="Wczytaj konfigurację", command=self.load_config)
        self.load_config_button.pack(side=tk.LEFT, padx=2)

        # -------------------- Panel logów --------------------
        self.log_text = ScrolledText(root, height=10, width=50, bg="white")
        self.log_text.grid(row=16, column=0, columnspan=2, padx=5, pady=5, sticky='we')

        # -------------------- Sekcja stałych klawiszy F1-F12 --------------------
        self.fixed_frame = ttk.Frame(root)
        self.fixed_frame.grid(row=0, column=1, rowspan=16, padx=5, pady=5, sticky='n')
        ttk.Label(self.fixed_frame, text="Stałe klawisze F1 - F12:", style="TLabel").grid(row=0, column=0, columnspan=4, sticky="w", padx=5, pady=2)
        self.fixed_key_entries = {}
        for i in range(1, 13):
            row = ((i - 1) % 6) + 1
            col = 0 if i <= 6 else 2
            label = ttk.Label(self.fixed_frame, text=f"F{i}:", style="TLabel")
            label.grid(row=row, column=col, padx=(5,0), pady=2, sticky="w")
            time_entry = ttk.Entry(self.fixed_frame, width=5)
            time_entry.grid(row=row, column=col+1, padx=(0,5), pady=2, sticky="w")
            self.fixed_key_entries[f"F{i}"] = time_entry

        # -------------------- Przyciski dodatkowe --------------------
        frame_extra = ttk.Frame(root)
        frame_extra.grid(row=17, column=0, padx=5, pady=5, sticky='w')
        self.preview_button = ttk.Button(frame_extra, text="Podgląd w czasie rzeczywistym", command=self.show_preview_window)
        self.preview_button.pack(side=tk.LEFT)

        # -------------------- Przypisanie hotkeyów --------------------
        self.rebind_hotkeys()

        # -------------------- Uruchomienie wątku śledzenia obiektu --------------------
        self.tracking_thread = threading.Thread(target=self.track_object, daemon=True)
        self.tracking_thread.start()

    # -------------------- Tworzenie okna podglądu --------------------
    def create_preview_window(self):
        self.preview_window = tk.Toplevel(self.root)
        self.preview_window.title("Podgląd w czasie rzeczywistym")
        self.real_time_preview_label = tk.Label(self.preview_window, bg="black")
        self.real_time_preview_label.pack()

    def show_preview_window(self):
        if hasattr(self, "preview_window") and self.preview_window.winfo_exists():
            self.preview_window.lift()
        else:
            self.create_preview_window()

    # -------------------- Blokada i odblokowanie interfejsu --------------------
    def lock_interface(self):
        widgets = (self.key_entries + self.interval_entries +
                   [self.mouse_interval_entry, self.toggle_key_entry, self.panic_key_entry,
                    self.test_key_entry, self.rebind_button, self.min_contour_entry, self.shape_option,
                    self.select_region_button, self.save_config_button, self.load_config_button])
        for widget in widgets:
            widget.config(state="disabled")
        for widget in self.fixed_key_entries.values():
            widget.config(state="disabled")

    def unlock_interface(self):
        widgets = (self.key_entries + self.interval_entries +
                   [self.mouse_interval_entry, self.toggle_key_entry, self.panic_key_entry,
                    self.test_key_entry, self.rebind_button, self.min_contour_entry, self.shape_option,
                    self.select_region_button, self.save_config_button, self.load_config_button])
        for widget in widgets:
            widget.config(state="normal")
        for widget in self.fixed_key_entries.values():
            widget.config(state="normal")

    # -------------------- Interaktywne wybieranie regionu --------------------
    def select_region(self):
        self.region_window = tk.Toplevel(self.root)
        self.region_window.attributes('-fullscreen', True)
        self.region_window.attributes('-alpha', 0.3)
        self.region_window.config(bg='gray')
        self.region_window.bind("<ButtonPress-1>", self.on_region_mouse_down)
        self.region_window.bind("<B1-Motion>", self.on_region_mouse_move)
        self.region_window.bind("<ButtonRelease-1>", self.on_region_mouse_up)
        self.start_x = self.start_y = None
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

    # -------------------- Testowy zrzut ekranu i ustawianie wzorca --------------------
    def test_screenshot(self):
        if hasattr(self, "test_window") and self.test_window.winfo_exists():
            self.test_window.destroy()
            return
        if self.selected_region:
            x, y, w, h = self.selected_region
            screenshot = pyautogui.screenshot(region=(x, y, w, h))
        else:
            screenshot = pyautogui.screenshot()
        self.test_original_img = np.array(screenshot)
        self.test_window = tk.Toplevel(self.root)
        self.test_window.title("Testowy zrzut ekranu")
        self.test_canvas = tk.Canvas(self.test_window, width=screenshot.width, height=screenshot.height)
        self.test_canvas.pack()
        im_pil = Image.fromarray(self.test_original_img)
        self.test_img = ImageTk.PhotoImage(im_pil)
        self.test_canvas_image_id = self.test_canvas.create_image(0, 0, image=self.test_img, anchor="nw")
        self.test_canvas.bind("<ButtonPress-1>", self.test_mouse_down)
        self.test_canvas.bind("<B1-Motion>", self.test_mouse_move)
        self.test_canvas.bind("<ButtonRelease-1>", self.test_mouse_up)

    def test_mouse_down(self, event):
        try:
            if self.test_canvas.winfo_exists():
                self.test_canvas.delete("sel")
        except tk.TclError:
            pass
        self.test_start_x = event.x
        self.test_start_y = event.y

    def test_mouse_move(self, event):
        try:
            if self.test_canvas.winfo_exists():
                self.test_canvas.delete("sel")
                self.test_canvas.create_rectangle(self.test_start_x, self.test_start_y, event.x, event.y,
                                                    outline="red", width=2, tag="sel")
        except tk.TclError:
            pass

    def test_mouse_up(self, event):
        end_x, end_y = event.x, event.y
        x1 = min(self.test_start_x, end_x)
        y1 = min(self.test_start_y, end_y)
        x2 = max(self.test_start_x, end_x)
        y2 = max(self.test_start_y, event.y)
        self.test_selected_region = (x1, y1, x2 - x1, y2 - y1)
        self.log_message(f"Testowy obszar zaznaczony: {self.test_selected_region}")
        # Ustawienie wybranego obszaru jako wzorzec do wyszukiwania
        region = self.test_original_img[y1:y2, x1:x2]
        if region.size > 0:
            self.template_img = region
            self.log_message("Wzorzec obrazu został ustawiony do wyszukiwania.")

    # -------------------- Rebinding klawiszy --------------------
    def rebind_hotkeys(self):
        try:
            keyboard.unhook_all_hotkeys()
        except AttributeError as e:
            if hasattr(keyboard, '_listener') and not hasattr(keyboard._listener, 'blocking_hotkeys'):
                keyboard._listener.blocking_hotkeys = []
            else:
                self.log_message("Błąd przy odpinaniu hotkeys: " + str(e))
        toggle_key = self.toggle_key_entry.get()
        panic_key = self.panic_key_entry.get()
        test_key = self.test_key_entry.get()
        keyboard.add_hotkey(toggle_key, self.toggle_clicking)
        keyboard.add_hotkey(panic_key, self.panic_stop)
        keyboard.add_hotkey(test_key, self.test_screenshot)
        self.log_message(f"Hotkeys ustawione: Toggle = {toggle_key}, Panic = {panic_key}, Test = {test_key}")

    # -------------------- Zapis/Wczytanie konfiguracji --------------------
    def save_config(self):
        config = {
            "keys": [entry.get() for entry in self.key_entries],
            "intervals": [entry.get() for entry in self.interval_entries],
            "mouse_interval": self.mouse_interval_entry.get(),
            "region": self.selected_region,
            "toggle_key": self.toggle_key_entry.get(),
            "panic_key": self.panic_key_entry.get(),
            "test_key": self.test_key_entry.get(),
            "min_contour_area": self.min_contour_entry.get(),
            "shape_filter": self.shape_var.get(),
            "fixed_keys": {key: self.fixed_key_entries[key].get() for key in self.fixed_key_entries}
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
            self.toggle_key_entry.delete(0, tk.END)
            self.toggle_key_entry.insert(0, config.get("toggle_key", "`"))
            self.panic_key_entry.delete(0, tk.END)
            self.panic_key_entry.insert(0, config.get("panic_key", "esc"))
            self.test_key_entry.delete(0, tk.END)
            self.test_key_entry.insert(0, config.get("test_key", "F9"))
            self.min_contour_entry.delete(0, tk.END)
            self.min_contour_entry.insert(0, config.get("min_contour_area", "100"))
            self.shape_var.set(config.get("shape_filter", "Any"))
            fixed_keys_config = config.get("fixed_keys", {})
            for key in self.fixed_key_entries:
                self.fixed_key_entries[key].delete(0, tk.END)
                self.fixed_key_entries[key].insert(0, fixed_keys_config.get(key, ""))
            self.rebind_hotkeys()
            self.log_message("Konfiguracja wczytana.")
        except Exception as e:
            self.log_message("Błąd wczytywania konfiguracji: " + str(e))

    # -------------------- Auto klikacz --------------------
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
        for key, entry in self.fixed_key_entries.items():
            val = entry.get()
            if val:
                try:
                    interval = float(val)
                    if interval > 0:
                        keys_intervals.append((key, interval))
                except ValueError:
                    entry.delete(0, tk.END)
                    entry.insert(0, "Błąd")
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
            self.unlock_interface()
        else:
            self.start_clicking()
            self.tracking_enabled = True
            self.status_label.config(text="Stan: ON", foreground="green")
            self.log_message("Klikacz i śledzenie uruchomione.")
            self.lock_interface()

    def panic_stop(self):
        self.running = False
        self.tracking_enabled = False
        self.status_label.config(text="Stan: PANIC", foreground="red")
        self.log_message("Panic button activated: Stopped all clicking and tracking.")
        self.unlock_interface()

    def log_message(self, msg):
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {msg}\n")
        self.log_text.see(tk.END)

    # -------------------- Zaawansowane wyszukiwanie obrazu --------------------
    def advanced_image_search(self, screenshot, template):
        # Konwersja obrazów do skali szarości
        img_gray = cv2.cvtColor(screenshot, cv2.COLOR_RGB2GRAY)
        template_gray = cv2.cvtColor(template, cv2.COLOR_RGB2GRAY)
        orb = cv2.ORB_create(nfeatures=500)
        kp1, des1 = orb.detectAndCompute(template_gray, None)
        kp2, des2 = orb.detectAndCompute(img_gray, None)
        if des1 is None or des2 is None:
            return None
        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        matches = bf.match(des1, des2)
        matches = sorted(matches, key=lambda x: x.distance)
        good_matches = matches[:20]
        if len(good_matches) > 5:
            pts_template = np.float32([kp1[m.queryIdx].pt for m in good_matches]).reshape(-1,1,2)
            pts_img = np.float32([kp2[m.trainIdx].pt for m in good_matches]).reshape(-1,1,2)
            M, mask = cv2.findHomography(pts_template, pts_img, cv2.RANSAC, 5.0)
            if M is not None:
                h, w = template_gray.shape
                pts = np.float32([[0,0], [0, h-1], [w-1, h-1], [w-1, 0]]).reshape(-1,1,2)
                dst = cv2.perspectiveTransform(pts, M)
                return dst
        return None

    # -------------------- Śledzenie obiektu z użyciem zaawansowanego wyszukiwania obrazu --------------------
    def track_object(self):
        while True:
            if self.tracking_enabled:
                try:
                    if self.selected_region:
                        x, y, w, h = self.selected_region
                        screenshot = pyautogui.screenshot(region=(x, y, w, h))
                        offset_x, offset_y = x, y
                    else:
                        screenshot = pyautogui.screenshot()
                        offset_x, offset_y = 0, 0

                    img_rgb = np.array(screenshot)
                    annotated_img = img_rgb.copy()
                    if self.template_img is not None:
                        dst = self.advanced_image_search(img_rgb, self.template_img)
                        if dst is not None:
                            pts = np.int32(dst)
                            center_x = int(np.mean(pts[:,0,0])) + offset_x
                            center_y = int(np.mean(pts[:,0,1])) + offset_y
                            pyautogui.moveTo(center_x, center_y, duration=0.5)
                            cv2.polylines(annotated_img, [pts], True, (0,255,0), 2)
                            text = "Wzorzec znaleziony"
                            cv2.putText(annotated_img, text, (pts[0][0][0], pts[0][0][1]-10),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,0,0), 2)
                            self.log_message(f"Przesunięto kursor do wzorca: ({center_x}, {center_y})")
                        else:
                            self.log_message("Wzorzec nie został znaleziony")
                    else:
                        self.log_message("Brak wzorca do wyszukiwania. Użyj 'Testowy zrzut' i zaznacz obszar wzorca.")

                    # Aktualizacja okna podglądu, jeśli jest otwarte
                    if hasattr(self, "real_time_preview_label"):
                        annotated_img = cv2.cvtColor(annotated_img, cv2.COLOR_RGB2BGR)
                        im_pil = Image.fromarray(cv2.cvtColor(annotated_img, cv2.COLOR_BGR2RGB))
                        imgtk = ImageTk.PhotoImage(im_pil)
                        self.real_time_preview_label.imgtk = imgtk
                        self.real_time_preview_label.config(image=imgtk)
                except Exception as e:
                    self.log_message("Błąd w śledzeniu: " + str(e))
            time.sleep(0.1)

if __name__ == "__main__":
    os.system("title Kobra 7.0")
    root = tk.Tk()
    app = AutoClicker(root)
    root.mainloop()
