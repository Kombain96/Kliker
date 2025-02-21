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

# Uwaga: Aby użyć SURF, potrzebujesz OpenCV z modułem xfeatures2d
# np. z instalacji opencv-contrib-python

class AutoClicker:
    def __init__(self, root):
        # Ustawienia stylu i kolorów – niebieska kolorystyka
        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.style.configure("TFrame", background="#ADD8E6")
        self.style.configure("TLabel", background="#ADD8E6", foreground="#333333", font=("Arial", 10))
        self.style.configure("TButton", background="#87CEFA", foreground="#000000", font=("Arial", 10))
        root.config(bg="#ADD8E6")
        
        self.root = root
        self.root.title("Kobra 7.0 - SURF")
        self.running = False
        self.tracking_enabled = False
        self.selected_region = None  # (x, y, width, height)
        # Lista wzorców – przechowywanie wielu wzorców
        self.templates = []
        self.clicked_on_template = False  # zapobiega wielokrotnemu klikaniu przy jednym wykryciu

        # Domyślne ustawienia zaawansowane – SURF, FLANN, RANSAC, wieloskalowość, normalizacja, kontrast
        self.advanced_params = {
            "normalization": True,          # Włącza equalizeHist, co wyrównuje histogram i poprawia kontrast obrazu
            "contrast": 1.0,                # Współczynnik kontrastu (alpha) – wartości >1 zwiększają kontrast
            # Parametry SURF:
            "surf_hessianThreshold": 400.0, # Im niższy próg, tym więcej cech; domyślnie ~400
            "surf_nOctaves": 4,             # Liczba oktaw – więcej oktaw pozwala wykryć cechy w różnych skalach
            "surf_nOctaveLayers": 3,        # Liczba warstw w każdej oktawie (domyślnie 3)
            "surf_extended": False,         # True: 128-wymiarowy descriptor, False: 64-wymiarowy
            "surf_upright": False,          # Jeśli True – pomijamy orientację (szybsze, ale mniej odpornie na obrót)
            # Parametry FLANN (dla SIFT/SURF – KD-Tree)
            "flann_trees": 5,               # Liczba drzew w KD-Tree; więcej drzew = dokładniejsze, ale wolniejsze dopasowanie
            "flann_checks": 50,             # Liczba sprawdzanych drzew – im więcej, tym dokładniejsze dopasowanie
            "ransac_reproj_threshold": 5.0, # Próg reprojekcji w RANSAC; niższa wartość = bardziej rygorystyczne dopasowanie
            # Parametry wieloskalowego przeszukiwania:
            "multi_scale_min": 0.8,         # Minimalna skala szukania
            "multi_scale_max": 1.2,         # Maksymalna skala szukania
            "multi_scale_step": 0.1         # Krok zmiany skali
        }
        
        # (Pozostała część inicjalizacji GUI, dynamiczne klawisze, wybór regionu, ustawienia hotkeyów itd.)
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

        # -------------------- Konfiguracja kliknięcia prawego przycisku myszy --------------------
        frame_mouse = ttk.Frame(root)
        frame_mouse.grid(row=10, column=0, padx=5, pady=2, sticky='w')
        ttk.Label(frame_mouse, text="Czas przytrzymania prawego przycisku (s):").pack(side=tk.LEFT)
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
        ttk.Label(frame_keys, text="Ustal wzorzec:").pack(side=tk.LEFT)
        self.test_key_entry = ttk.Entry(frame_keys, width=5)
        self.test_key_entry.pack(side=tk.LEFT, padx=2)
        self.test_key_entry.insert(0, "F9")
        ttk.Label(frame_keys, text="Nowy Screenshot:").pack(side=tk.LEFT)
        self.new_screenshot_key_entry = ttk.Entry(frame_keys, width=5)
        self.new_screenshot_key_entry.pack(side=tk.LEFT, padx=2)
        self.new_screenshot_key_entry.insert(0, "F10")
        self.rebind_button = ttk.Button(frame_keys, text="Zmień klawisze", command=self.rebind_hotkeys)
        self.rebind_button.pack(side=tk.LEFT, padx=5)

        # -------------------- Zapis/Wczytanie konfiguracji --------------------
        frame_config = ttk.Frame(root)
        frame_config.grid(row=14, column=0, padx=5, pady=2, sticky='w')
        self.save_config_button = ttk.Button(frame_config, text="Zapisz konfigurację", command=self.save_config)
        self.save_config_button.pack(side=tk.LEFT, padx=2)
        self.load_config_button = ttk.Button(frame_config, text="Wczytaj konfigurację", command=self.load_config)
        self.load_config_button.pack(side=tk.LEFT, padx=2)

        # -------------------- Panel logów --------------------
        self.log_text = ScrolledText(root, height=10, width=50, bg="white")
        self.log_text.grid(row=15, column=0, columnspan=2, padx=5, pady=5, sticky='we')

        # -------------------- Sekcja stałych klawiszy F1-F12 --------------------
        self.fixed_frame = ttk.Frame(root)
        self.fixed_frame.grid(row=0, column=1, rowspan=15, padx=5, pady=5, sticky='n')
        ttk.Label(self.fixed_frame, text="Stałe klawisze F1 - F12:", style="TLabel").grid(row=0, column=0, columnspan=4, sticky="w", padx=5, pady=2)
        self.fixed_key_entries = {}
        for i in range(1, 13):
            r = ((i - 1) % 6) + 1
            c = 0 if i <= 6 else 2
            label = ttk.Label(self.fixed_frame, text=f"F{i}:", style="TLabel")
            label.grid(row=r, column=c, padx=(5,0), pady=2, sticky="w")
            time_entry = ttk.Entry(self.fixed_frame, width=5)
            time_entry.grid(row=r, column=c+1, padx=(0,5), pady=2, sticky="w")
            self.fixed_key_entries[f"F{i}"] = time_entry

        # -------------------- Przyciski dodatkowe --------------------
        frame_extra = ttk.Frame(root)
        frame_extra.grid(row=16, column=0, padx=5, pady=5, sticky='w')
        self.preview_button = ttk.Button(frame_extra, text="Podgląd w czasie rzeczywistym", command=self.show_preview_window)
        self.preview_button.pack(side=tk.LEFT)
        self.template_button = ttk.Button(frame_extra, text="Pokaż wzorzec", command=self.show_template_window)
        self.template_button.pack(side=tk.LEFT, padx=5)
        self.advanced_button = ttk.Button(frame_extra, text="Zaawansowane", command=self.open_advanced_window)
        self.advanced_button.pack(side=tk.LEFT, padx=5)

        # -------------------- Przypisanie hotkeyów --------------------
        self.rebind_hotkeys()

        # -------------------- Uruchomienie wątku śledzenia obiektu --------------------
        self.tracking_thread = threading.Thread(target=self.track_object, daemon=True)
        self.tracking_thread.start()

    # ---------- OKNO ZAAWANSOWANE (SURF, FLANN, RANSAC, Multi-scale) ----------
    def open_advanced_window(self):
        self.adv_window = tk.Toplevel(self.root)
        self.adv_window.title("Zaawansowane - SURF, FLANN, RANSAC i Multi-scale")
        row = 0
        # Normalizacja obrazu
        tk.Label(self.adv_window, text="Normalizacja obrazu (equalizeHist):").grid(row=row, column=0, sticky="w")
        self.norm_var = tk.BooleanVar(value=self.advanced_params["normalization"])
        tk.Checkbutton(self.adv_window, variable=self.norm_var,
                       text="Włącz normalizację - wyrównuje histogram, poprawia kontrast").grid(row=row, column=1, sticky="w")
        row += 1
        # Poprawa kontrastu
        tk.Label(self.adv_window, text="Współczynnik kontrastu (alpha):").grid(row=row, column=0, sticky="w")
        self.contrast_entry = ttk.Entry(self.adv_window, width=10)
        self.contrast_entry.insert(0, str(self.advanced_params["contrast"]))
        tk.Label(self.adv_window, text="Wartość >1 zwiększa kontrast").grid(row=row, column=2, sticky="w")
        self.contrast_entry.grid(row=row, column=1)
        row += 1
        # Parametry SURF
        tk.Label(self.adv_window, text="SURF - hessianThreshold:").grid(row=row, column=0, sticky="w")
        self.surf_hessian_entry = ttk.Entry(self.adv_window, width=10)
        self.surf_hessian_entry.insert(0, str(self.advanced_params["surf_hessianThreshold"]))
        tk.Label(self.adv_window, text="Niższa wartość = więcej wykrytych cech (np. 400)").grid(row=row, column=2, sticky="w")
        self.surf_hessian_entry.grid(row=row, column=1)
        row += 1
        tk.Label(self.adv_window, text="SURF - nOctaves:").grid(row=row, column=0, sticky="w")
        self.surf_octaves_entry = ttk.Entry(self.adv_window, width=10)
        self.surf_octaves_entry.insert(0, str(self.advanced_params["surf_nOctaves"]))
        tk.Label(self.adv_window, text="Liczba oktaw (skal) – domyślnie 4").grid(row=row, column=2, sticky="w")
        self.surf_octaves_entry.grid(row=row, column=1)
        row += 1
        tk.Label(self.adv_window, text="SURF - nOctaveLayers:").grid(row=row, column=0, sticky="w")
        self.surf_octaveLayers_entry = ttk.Entry(self.adv_window, width=10)
        self.surf_octaveLayers_entry.insert(0, str(self.advanced_params["surf_nOctaveLayers"]))
        tk.Label(self.adv_window, text="Liczba warstw w każdej oktawie – domyślnie 3").grid(row=row, column=2, sticky="w")
        self.surf_octaveLayers_entry.grid(row=row, column=1)
        row += 1
        tk.Label(self.adv_window, text="SURF - extended:").grid(row=row, column=0, sticky="w")
        self.surf_extended_entry = ttk.Entry(self.adv_window, width=10)
        self.surf_extended_entry.insert(0, str(self.advanced_params["surf_extended"]))
        tk.Label(self.adv_window, text="True = 128-wymiarowy descriptor, False = 64-wymiarowy").grid(row=row, column=2, sticky="w")
        self.surf_extended_entry.grid(row=row, column=1)
        row += 1
        tk.Label(self.adv_window, text="SURF - upright:").grid(row=row, column=0, sticky="w")
        self.surf_upright_entry = ttk.Entry(self.adv_window, width=10)
        self.surf_upright_entry.insert(0, str(self.advanced_params["surf_upright"]))
        tk.Label(self.adv_window, text="True = pomijanie orientacji (szybsze)").grid(row=row, column=2, sticky="w")
        self.surf_upright_entry.grid(row=row, column=1)
        row += 1
        # Parametry FLANN (dla SURF – KD-Tree)
        tk.Label(self.adv_window, text="FLANN - liczba drzew (trees):").grid(row=row, column=0, sticky="w")
        self.flann_trees_entry = ttk.Entry(self.adv_window, width=10)
        self.flann_trees_entry.insert(0, str(self.advanced_params["flann_trees"]))
        tk.Label(self.adv_window, text="Większa liczba drzew = dokładniejsze, ale wolniejsze dopasowanie").grid(row=row, column=2, sticky="w")
        self.flann_trees_entry.grid(row=row, column=1)
        row += 1
        tk.Label(self.adv_window, text="FLANN - checks:").grid(row=row, column=0, sticky="w")
        self.flann_checks_entry = ttk.Entry(self.adv_window, width=10)
        self.flann_checks_entry.insert(0, str(self.advanced_params["flann_checks"]))
        tk.Label(self.adv_window, text="Liczba sprawdzanych drzew – im więcej, tym dokładniejsze").grid(row=row, column=2, sticky="w")
        self.flann_checks_entry.grid(row=row, column=1)
        row += 1
        # Parametr RANSAC
        tk.Label(self.adv_window, text="RANSAC - reprojection threshold:").grid(row=row, column=0, sticky="w")
        self.ransac_thresh_entry = ttk.Entry(self.adv_window, width=10)
        self.ransac_thresh_entry.insert(0, str(self.advanced_params["ransac_reproj_threshold"]))
        tk.Label(self.adv_window, text="Niższa wartość = bardziej rygorystyczne dopasowanie").grid(row=row, column=2, sticky="w")
        self.ransac_thresh_entry.grid(row=row, column=1)
        row += 1
        # Parametry wieloskalowego przeszukiwania
        tk.Label(self.adv_window, text="Multi-scale - min skala:").grid(row=row, column=0, sticky="w")
        self.ms_min_entry = ttk.Entry(self.adv_window, width=10)
        self.ms_min_entry.insert(0, str(self.advanced_params["multi_scale_min"]))
        tk.Label(self.adv_window, text="Minimalna skala szukania").grid(row=row, column=2, sticky="w")
        self.ms_min_entry.grid(row=row, column=1)
        row += 1
        tk.Label(self.adv_window, text="Multi-scale - max skala:").grid(row=row, column=0, sticky="w")
        self.ms_max_entry = ttk.Entry(self.adv_window, width=10)
        self.ms_max_entry.insert(0, str(self.advanced_params["multi_scale_max"]))
        tk.Label(self.adv_window, text="Maksymalna skala szukania").grid(row=row, column=2, sticky="w")
        self.ms_max_entry.grid(row=row, column=1)
        row += 1
        tk.Label(self.adv_window, text="Multi-scale - krok:").grid(row=row, column=0, sticky="w")
        self.ms_step_entry = ttk.Entry(self.adv_window, width=10)
        self.ms_step_entry.insert(0, str(self.advanced_params["multi_scale_step"]))
        tk.Label(self.adv_window, text="Krok zmiany skali").grid(row=row, column=2, sticky="w")
        self.ms_step_entry.grid(row=row, column=1)
        row += 1
        save_btn = ttk.Button(self.adv_window, text="Zapisz ustawienia", command=self.save_advanced_params)
        save_btn.grid(row=row, column=0, columnspan=3, pady=10)
        
    def save_advanced_params(self):
        try:
            self.advanced_params["normalization"] = self.norm_var.get()
            self.advanced_params["contrast"] = float(self.contrast_entry.get())
            self.advanced_params["surf_hessianThreshold"] = float(self.surf_hessian_entry.get())
            self.advanced_params["surf_nOctaves"] = int(self.surf_octaves_entry.get())
            self.advanced_params["surf_nOctaveLayers"] = int(self.surf_octaveLayers_entry.get())
            self.advanced_params["surf_extended"] = self.surf_extended_entry.get().lower() in ['true', '1', 'yes']
            self.advanced_params["surf_upright"] = self.surf_upright_entry.get().lower() in ['true', '1', 'yes']
            self.advanced_params["flann_trees"] = int(self.flann_trees_entry.get())
            self.advanced_params["flann_checks"] = int(self.flann_checks_entry.get())
            self.advanced_params["ransac_reproj_threshold"] = float(self.ransac_thresh_entry.get())
            self.advanced_params["multi_scale_min"] = float(self.ms_min_entry.get())
            self.advanced_params["multi_scale_max"] = float(self.ms_max_entry.get())
            self.advanced_params["multi_scale_step"] = float(self.ms_step_entry.get())
            self.log_message("Ustawienia zaawansowane zapisane.")
        except Exception as e:
            self.log_message("Błąd zapisu ustawień zaawansowanych: " + str(e))
    
    # ---------- OKNO PODGLĄDU ----------
    def create_preview_window(self):
        self.preview_window = tk.Toplevel(self.root)
        self.preview_window.title("Podgląd w czasie rzeczywistym")
        self.real_time_preview_label = tk.Label(self.preview_window, text="Ustal wzorce i uruchom program", fg="red", bg="black", font=("Arial", 14))
        self.real_time_preview_label.pack()

    def show_preview_window(self):
        if hasattr(self, "preview_window") and self.preview_window.winfo_exists():
            self.preview_window.lift()
        else:
            self.create_preview_window()

    # ---------- OKNO Z WZORCAMI ----------
    def show_template_window(self):
        if not self.templates:
            self.log_message("Brak wzorców. Najpierw ustal wzorce za pomocą testowego zrzutu.")
            return
        if hasattr(self, "template_window") and self.template_window.winfo_exists():
            self.template_window.lift()
            self.refresh_template_window()
        else:
            self.template_window = tk.Toplevel(self.root)
            self.template_window.title("Wzorce")
            self.refresh_template_window()

    def refresh_template_window(self):
        for widget in self.template_window.winfo_children():
            widget.destroy()
        if not self.templates:
            ttk.Label(self.template_window, text="Brak wzorców").pack()
            return
        for idx, template in enumerate(self.templates):
            frame = ttk.Frame(self.template_window, relief=tk.RAISED, borderwidth=1)
            frame.pack(side=tk.LEFT, padx=5, pady=5)
            im_pil = Image.fromarray(template)
            photo = ImageTk.PhotoImage(im_pil)
            label = tk.Label(frame, image=photo)
            label.image = photo
            label.pack()
            btn_delete = ttk.Button(frame, text="Usuń", command=lambda i=idx: self.delete_template(i))
            btn_delete.pack(pady=2)
        btn_delete_all = ttk.Button(self.template_window, text="Usuń wszystkie", command=self.delete_all_templates)
        btn_delete_all.pack(pady=5)

    def delete_template(self, idx):
        try:
            del self.templates[idx]
            self.log_message("Wzorzec usunięty.")
            self.refresh_template_window()
        except Exception as e:
            self.log_message("Błąd przy usuwaniu wzorca: " + str(e))

    def delete_all_templates(self):
        self.templates.clear()
        self.log_message("Wszystkie wzorce usunięte.")
        self.refresh_template_window()

    # ---------- Blokada/odblokowanie interfejsu ----------
    def lock_interface(self):
        widgets = (self.key_entries + self.interval_entries +
                   [self.mouse_interval_entry, self.toggle_key_entry, self.panic_key_entry,
                    self.test_key_entry, self.new_screenshot_key_entry, self.rebind_button, self.select_region_button,
                    self.save_config_button, self.load_config_button])
        for widget in widgets:
            widget.config(state="disabled")
        for widget in self.fixed_key_entries.values():
            widget.config(state="disabled")

    def unlock_interface(self):
        widgets = (self.key_entries + self.interval_entries +
                   [self.mouse_interval_entry, self.toggle_key_entry, self.panic_key_entry,
                    self.test_key_entry, self.new_screenshot_key_entry, self.rebind_button, self.select_region_button,
                    self.save_config_button, self.load_config_button])
        for widget in widgets:
            widget.config(state="normal")
        for widget in self.fixed_key_entries.values():
            widget.config(state="normal")

    # ---------- Interaktywne wybieranie regionu ----------
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

    # ---------- Testowy zrzut ekranu i ustalanie wzorca ----------
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

    def new_screenshot(self):
        if not (hasattr(self, "test_window") and self.test_window.winfo_exists()):
            self.test_screenshot()  # Otwieramy okno, jeśli nie istnieje
        else:
            if self.selected_region:
                x, y, w, h = self.selected_region
                screenshot = pyautogui.screenshot(region=(x, y, w, h))
            else:
                screenshot = pyautogui.screenshot()
            self.test_original_img = np.array(screenshot)
            im_pil = Image.fromarray(self.test_original_img)
            self.test_img = ImageTk.PhotoImage(im_pil)
            self.test_canvas.itemconfig(self.test_canvas_image_id, image=self.test_img)
            self.log_message("Nowy screenshot wykonany.")

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
        y2 = max(self.test_start_y, end_y)
        self.test_selected_region = (x1, y1, x2 - x1, y2 - y1)
        self.log_message(f"Testowy obszar zaznaczony: {self.test_selected_region}")
        region = self.test_original_img[y1:y2, x1:x2]
        if region.size > 0:
            self.templates.append(region)
            self.log_message("Nowy wzorzec został dodany.")
            if hasattr(self, "template_window") and self.template_window.winfo_exists():
                self.refresh_template_window()

    # ---------- Rebinding klawiszy ----------
    def rebind_hotkeys(self):
        try:
            keyboard.unhook_all_hotkeys()
        except Exception as e:
            self.log_message("Błąd przy odpinaniu hotkeys: " + str(e))
        toggle_key = self.toggle_key_entry.get()
        panic_key = self.panic_key_entry.get()
        test_key = self.test_key_entry.get()
        new_shot_key = self.new_screenshot_key_entry.get()
        keyboard.add_hotkey(toggle_key, self.toggle_clicking)
        keyboard.add_hotkey(panic_key, self.panic_stop)
        keyboard.add_hotkey(test_key, self.test_screenshot)
        keyboard.add_hotkey(new_shot_key, self.new_screenshot)
        self.log_message(f"Hotkeys ustawione: Toggle = {toggle_key}, Panic = {panic_key}, Ustal wzorzec = {test_key}, Nowy Screenshot = {new_shot_key}")

    # ---------- Zapis/Wczytanie konfiguracji ----------
    def save_config(self):
        config = {
            "keys": [entry.get() for entry in self.key_entries],
            "intervals": [entry.get() for entry in self.interval_entries],
            "mouse_interval": self.mouse_interval_entry.get(),
            "region": self.selected_region,
            "toggle_key": self.toggle_key_entry.get(),
            "panic_key": self.panic_key_entry.get(),
            "test_key": self.test_key_entry.get(),
            "new_screenshot_key": self.new_screenshot_key_entry.get(),
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
            self.new_screenshot_key_entry.delete(0, tk.END)
            self.new_screenshot_key_entry.insert(0, config.get("new_screenshot_key", "F10"))
            fixed_keys_config = config.get("fixed_keys", {})
            for key in self.fixed_key_entries:
                self.fixed_key_entries[key].delete(0, tk.END)
                self.fixed_key_entries[key].insert(0, fixed_keys_config.get(key, ""))
            self.rebind_hotkeys()
            self.log_message("Konfiguracja wczytana.")
        except Exception as e:
            self.log_message("Błąd wczytywania konfiguracji: " + str(e))

    # ---------- Auto klikacz (dla dynamicznych klawiszy) ----------
    def click_loop(self, keys_intervals):
        while self.running:
            for key, interval in keys_intervals:
                if not self.running:
                    break
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

    # ---------- Zaawansowane wyszukiwanie obrazu z SURF, FLANN, RANSAC i wieloskalowością ----------
    def advanced_image_search(self, screenshot, template):
        # Konwersja do skali szarości
        img_gray = cv2.cvtColor(screenshot, cv2.COLOR_RGB2GRAY)
        template_gray = cv2.cvtColor(template, cv2.COLOR_RGB2GRAY)
        # Normalizacja i poprawa kontrastu
        if self.advanced_params["normalization"]:
            img_gray = cv2.equalizeHist(img_gray)
            template_gray = cv2.equalizeHist(template_gray)
        img_gray = cv2.convertScaleAbs(img_gray, alpha=self.advanced_params["contrast"], beta=0)
        template_gray = cv2.convertScaleAbs(template_gray, alpha=self.advanced_params["contrast"], beta=0)
        
        best_dst = None
        # Wieloskalowe przeszukiwanie
        scales = np.arange(self.advanced_params["multi_scale_min"],
                           self.advanced_params["multi_scale_max"] + self.advanced_params["multi_scale_step"],
                           self.advanced_params["multi_scale_step"])
        for scale in scales:
            try:
                resized_template = cv2.resize(template_gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_LINEAR)
            except Exception:
                continue
            # Utwórz detektor SURF (z modułu xfeatures2d)
            try:
                surf = cv2.xfeatures2d.SURF_create(
                    hessianThreshold=float(self.advanced_params["surf_hessianThreshold"]),
                    nOctaves=int(self.advanced_params["surf_nOctaves"]),
                    nOctaveLayers=int(self.advanced_params["surf_nOctaveLayers"]),
                    extended=bool(self.advanced_params["surf_extended"]),
                    upright=bool(self.advanced_params["surf_upright"])
                )
            except Exception as e:
                self.log_message("Błąd tworzenia SURF: " + str(e))
                return None
            kp1, des1 = surf.detectAndCompute(resized_template, None)
            kp2, des2 = surf.detectAndCompute(img_gray, None)
            if des1 is None or des2 is None:
                continue
            # Używamy FLANN-Based Matcher dla SURF (KD-Tree)
            FLANN_INDEX_KDTREE = 1
            index_params = dict(algorithm=FLANN_INDEX_KDTREE, trees=int(self.advanced_params["flann_trees"]))
            search_params = dict(checks=int(self.advanced_params["flann_checks"]))
            flann = cv2.FlannBasedMatcher(index_params, search_params)
            try:
                matches = flann.knnMatch(des1, des2, k=2)
            except Exception:
                continue
            good_matches = []
            for m, n in matches:
                if m.distance < 0.85 * n.distance:
                    good_matches.append(m)
            if len(good_matches) > 8:
                pts_template = np.float32([kp1[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
                pts_img = np.float32([kp2[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)
                M, mask = cv2.findHomography(pts_template, pts_img, cv2.RANSAC, float(self.advanced_params["ransac_reproj_threshold"]))
                if M is not None:
                    h, w = resized_template.shape
                    pts = np.float32([[0, 0], [0, h - 1], [w - 1, h - 1], [w - 1, 0]]).reshape(-1, 1, 2)
                    dst = cv2.perspectiveTransform(pts, M)
                    best_dst = dst
                    break
        return best_dst

    # ---------- Śledzenie obiektu ----------
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
                    if self.templates:
                        found = False
                        for template in self.templates:
                            dst = self.advanced_image_search(img_rgb, template)
                            if dst is not None:
                                pts = np.int32(dst)
                                center_x = int(np.mean(pts[:, 0, 0])) + offset_x
                                center_y = int(np.mean(pts[:, 0, 1])) + offset_y
                                pyautogui.moveTo(center_x, center_y, duration=0.5)
                                cv2.polylines(annotated_img, [pts], True, (0, 255, 0), 2)
                                cv2.putText(annotated_img, "Wzorzec znaleziony", (pts[0][0][0], pts[0][0][1] - 10),
                                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
                                if not self.clicked_on_template:
                                    try:
                                        hold_time = float(self.mouse_interval_entry.get())
                                    except:
                                        hold_time = 0.5
                                    pyautogui.mouseDown(button='right')
                                    time.sleep(hold_time)
                                    pyautogui.mouseUp(button='right')
                                    self.log_message(f"Kliknięto prawym przyciskiem na wzorcu, przytrzymanie: {hold_time}s")
                                    self.clicked_on_template = True
                                found = True
                                break
                        if not found:
                            self.log_message("Żaden wzorzec nie został znaleziony")
                            self.clicked_on_template = False
                    else:
                        self.log_message("Brak wzorców do wyszukiwania. Użyj 'Ustal wzorzec' (F9) i zaznacz obszar wzorca.")

                    if hasattr(self, "real_time_preview_label"):
                        annotated_img = cv2.cvtColor(annotated_img, cv2.COLOR_RGB2BGR)
                        im_pil = Image.fromarray(cv2.cvtColor(annotated_img, cv2.COLOR_BGR2RGB))
                        imgtk = ImageTk.PhotoImage(im_pil)
                        self.real_time_preview_label.imgtk = imgtk
                        self.real_time_preview_label.config(image=imgtk, text="")
                except Exception as e:
                    self.log_message("Błąd w śledzeniu: " + str(e))
            time.sleep(0.1)

if __name__ == "__main__":
    os.system("title Kobra 7.0")
    root = tk.Tk()
    app = AutoClicker(root)
    root.mainloop()
