#welcome window integration
#added user input of VAOV and HAOV


import os
import math
import tkinter as tk
from tkinter import filedialog, simpledialog
from PIL import Image, ImageTk, ImageEnhance
import pandas as pd
import numpy as np
from fractions import Fraction
from bisect import bisect_left
import PRFunctionsTS
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
from matplotlib.ticker import ScalarFormatter
from rasterio.transform import Affine
import matplotlib.image as mpimg
import rasterio
from rasterio.plot import show


def load_world_file(tif_path):
    """Reads a .tfw file associated with a .tif and returns a rasterio Affine transform."""
    base, _ = os.path.splitext(tif_path)
    tfw_path = base + '.tfw'

    if not os.path.exists(tfw_path):
        print(f"No world file found at {tfw_path}")
        return None

    with open(tfw_path, 'r') as f:
        lines = f.readlines()
        if len(lines) != 6:
            print("Invalid .tfw format")
            return None

        A = float(lines[0])  # pixel size in x-direction
        D = float(lines[1])  # rotation term
        B = float(lines[2])  # rotation term
        E = float(lines[3])  # pixel size in y-direction (often negative)
        C = float(lines[4])  # x-coordinate of center of upper-left pixel
        F = float(lines[5])  # y-coordinate of center of upper-left pixel

        return Affine(A, B, C, D, E, F)


def plot_tif_with_tfw(ax, tif_path):
    """Plots a TIFF image with georeferencing from a TFW file onto a matplotlib axis."""
    transform = load_world_file(tif_path)
    if transform is None:
        print("[ERROR] No transform found")
        return

    try:
        with rasterio.open(tif_path) as src:
            #img = src.read(1)  # Read first band for now
            extent = [
                transform.c,
                transform.c + transform.a * src.width,
                transform.f + transform.e * src.height,
                transform.f
            ]
            
            if src.count >= 3:
                img = src.read([1, 2, 3])  # RGB bands
                img = np.transpose(img, (1, 2, 0))  # Reorder for imshow
                ax.imshow(img, extent=extent, origin='upper', zorder=0)
            else:
                img = src.read(1)
                ax.imshow(img, extent=extent, origin='upper', cmap='gray', zorder=0)
            
            # ax.imshow(img, extent=extent, origin='upper', cmap='gray', zorder=0)
    except Exception as e:
        print(f"[ERROR] Failed to load TIFF in plot_tif_with_tfw: {e}")


def center_window(root, width=1200, height=800):
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = (screen_width // 2) - (width // 2)
    y = (screen_height // 2) - (height // 2)
    root.geometry(f"{width}x{height}+{x}+{y}")

class WelcomeWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Welcome to BIVALVE")
        self.geometry("600x300")
        self.resizable(False, False)
        self.result = {}

        # Allow column 1 (entry boxes) to expand
        self.columnconfigure(1, weight=1)

        # Image folder
        tk.Label(self, text="Image Folder:").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        self.image_entry = tk.Entry(self, width=40)
        self.image_entry.grid(row=0, column=1, sticky="ew")
        tk.Button(self, text="Browse", command=self.browse_image_folder).grid(row=0, column=2, padx=5)

        # ADCP CSV
        tk.Label(self, text="ADCP CSV File:").grid(row=1, column=0, sticky="e", padx=5, pady=5)
        self.csv_entry = tk.Entry(self, width=40)
        self.csv_entry.grid(row=1, column=1, sticky="ew")
        tk.Button(self, text="Browse", command=self.browse_csv).grid(row=1, column=2, padx=5)

        # Start time
        tk.Label(self, text="Start Time (YYYY-MM-DD HH:MM:SS.0000):").grid(row=2, column=0, sticky="e", padx=5, pady=5)
        self.time_entry = tk.Entry(self, width=40)
        self.time_entry.grid(row=2, column=1, columnspan=2, sticky="ew")

        # Time step
        tk.Label(self, text="Time Step (seconds):").grid(row=3, column=0, sticky="e", padx=5, pady=5)
        self.step_entry = tk.Entry(self, width=40)
        self.step_entry.grid(row=3, column=1, columnspan=2, sticky="ew")

        # GeoTIFF file (now last)
        tk.Label(self, text="GeoTIFF Background:").grid(row=4, column=0, sticky="e", padx=5, pady=5)
        self.geotiff_entry = tk.Entry(self, width=40)
        self.geotiff_entry.grid(row=4, column=1, sticky="ew")
        tk.Button(self, text="Browse", command=self.browse_geotiff).grid(row=4, column=2, padx=5)

        # AOV input row
        tk.Label(self, text="Horizontal AOV (°):").grid(row=5, column=0, sticky="e", padx=5, pady=5)
        self.hfov_entry = tk.Entry(self, width=8)
        self.hfov_entry.grid(row=5, column=1, sticky="w", padx=(0, 10))
        
        tk.Label(self, text="Vertical AOV (°):").grid(row=5, column=1, sticky="e", padx=(90, 5), pady=5)
        self.vfov_entry = tk.Entry(self, width=8)
        self.vfov_entry.grid(row=5, column=2, sticky="w")

        # Continue button
        tk.Button(self, text="Continue", command=self.submit).grid(row=6, column=1, pady=(20, 10))

        self.grab_set()  # Make the window modal

    def browse_image_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.image_entry.delete(0, tk.END)
            self.image_entry.insert(0, folder)

    def browse_csv(self):
        file = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])
        if file:
            self.csv_entry.delete(0, tk.END)
            self.csv_entry.insert(0, file)

    def browse_geotiff(self):
        file = filedialog.askopenfilename(filetypes=[("GeoTIFF Files", "*.tif *.tiff")])
        if file:
            self.geotiff_entry.delete(0, tk.END)
            self.geotiff_entry.insert(0, file)

    def submit(self):
        self.result = {
            "image_folder": self.image_entry.get(),
            "csv_path": self.csv_entry.get(),
            "start_time": self.time_entry.get(),
            "time_step": float(self.step_entry.get()),
            "geotiff_path": self.geotiff_entry.get(),
            "hfov": float(self.hfov_entry.get()),
            "vfov": float(self.vfov_entry.get())
        }
        self.destroy()

    def browse_image_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.image_entry.insert(0, folder)

    def browse_csv(self):
        file = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])
        if file:
            self.csv_entry.insert(0, file)


    def browse_geotiff(self):
        file = filedialog.askopenfilename(filetypes=[("GeoTIFF Files", "*.tif *.tiff")])
        if file:
            self.geotiff_entry.insert(0, file)

class ImageTaggerApp:
    def __init__(self, root,inputs):
        self.root = root
        self.inputs = inputs
        
        self.root.title("BIVALVE - Benthic Imagery VALidation and Visual Enhancement")
    
        self.current_index = 0
        self.active_filter = None
        self.clicks = []
        self.scale_x = 1
        self.scale_y = 1
    
        # === Configure 2x2 Grid Layout ===
        root.grid_rowconfigure(0, weight=3)  # Top row: 75%
        root.grid_rowconfigure(1, weight=1)  # Bottom row: 25%
        root.grid_columnconfigure(0, weight=1)
        root.grid_columnconfigure(1, weight=1)
    
        # === Top-Left: Map ===
        self.map_frame = tk.Frame(root)
        self.map_frame.grid(row=0, column=0, sticky="nsew")
    
        self.fig, self.ax = plt.subplots(figsize=(4, 4), constrained_layout=True)
        self.canvas_map = FigureCanvasTkAgg(self.fig, master=self.map_frame)
        self.canvas_map.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        self.map_initialized = False
        self.current_marker = None
        self.tag_scatters = {}
    
        # === Top-Right: Image ===
        self.image_frame = tk.Frame(root)
        self.image_frame.grid(row=0, column=1, sticky="nsew")
        
        self.image_frame.pack_propagate(False)  # NEW
        self.canvas = tk.Canvas(self.image_frame, bg="gray", width=1)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.canvas.bind("<Configure>", lambda event: self.display_image())
        self.canvas.bind("<Button-1>", self.record_click)
    
        # === Bottom-Right: Navigator + Controls (Side by Side) ===
        self.bottom_right_frame = tk.Frame(root)
        self.bottom_right_frame.grid(row=1, column=1, sticky="nsew")
        self.bottom_right_frame.config(height=200)
        self.bottom_right_frame.grid_propagate(False)
        self.bottom_right_frame.config(width=500)
        self.bottom_right_frame.grid_propagate(False)
        self.bottom_right_frame.grid_columnconfigure(0, weight=1)
        self.bottom_right_frame.grid_columnconfigure(1, weight=2)
        self.bottom_right_frame.grid_rowconfigure(0, weight=1)
    
        # --- Navigator (left side of bottom-right)
        self.navigator_frame = tk.LabelFrame(self.bottom_right_frame, text="File Navigator")
        self.navigator_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
    
        self.scrollbar = tk.Scrollbar(self.navigator_frame)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
        self.image_listbox = tk.Listbox(self.navigator_frame, width=30, yscrollcommand=self.scrollbar.set)
        self.image_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.image_listbox.bind("<<ListboxSelect>>", self.on_image_select)
        self.scrollbar.config(command=self.image_listbox.yview)
    
        # --- Controls (right side of bottom-right)
        self.control_frame = tk.LabelFrame(self.bottom_right_frame, text="Controls", padx=10, pady=10)
        self.control_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
    
        #metadata display
        self.bottom_left_frame = tk.LabelFrame(root, text="Image Metadata", bg="white")
        self.bottom_left_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        self.meta_box = tk.Label(self.bottom_left_frame,text="",justify="left",anchor="nw",font=("Courier", 10),bg="white")
        self.meta_box.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
        self.tag_frame = tk.Frame(self.control_frame)
        self.tag_frame.pack(pady=2)
        self.new_tag_entry = tk.Entry(self.tag_frame)
        self.new_tag_entry.pack(side=tk.LEFT)
        self.add_tag_button = tk.Button(self.tag_frame, text="Add Tag", command=self.add_new_tag_button)
        self.add_tag_button.pack(side=tk.LEFT, padx=5)
    
        tk.Label(self.control_frame, text="Note for current image:").pack()
        self.note_entry = tk.Entry(self.control_frame, width=40)
        self.note_entry.pack()
        self.save_note_button = tk.Button(self.control_frame, text="Save Note", command=self.save_note)
        self.save_note_button.pack(pady=2)
    
        nav_btn_frame = tk.Frame(self.control_frame)
        nav_btn_frame.pack(pady=2)
        self.back_button = tk.Button(nav_btn_frame, text="Back", command=self.back_image)
        self.back_button.pack(side=tk.LEFT, padx=5)
        self.skip_button = tk.Button(nav_btn_frame, text="Skip", command=self.skip_image)
        self.skip_button.pack(side=tk.LEFT, padx=5)
    
        self.export_button = tk.Button(self.control_frame, text="Export Metadata CSV", command=self.export_metadata)
        self.export_button.pack(pady=2)
    
        self.filter_frame = tk.Frame(self.control_frame)
        self.filter_frame.pack(pady=4)
    
        self.filter_buttons = {}
        self.filter_state = None
    
        contrast_btn = tk.Button(self.filter_frame, text="High Contrast", command=lambda: self.set_filter("contrast"))
        contrast_btn.pack(side=tk.LEFT)
        self.filter_buttons["contrast"] = contrast_btn
    
        saturation_btn = tk.Button(self.filter_frame, text="High Saturation", command=lambda: self.set_filter("saturation"))
        saturation_btn.pack(side=tk.LEFT)
        self.filter_buttons["saturation"] = saturation_btn
    
        grayscale_btn = tk.Button(self.filter_frame, text="Grayscale", command=lambda: self.set_filter("grayscale"))
        grayscale_btn.pack(side=tk.LEFT)
        self.filter_buttons["grayscale"] = grayscale_btn
    
        remap_btn = tk.Button(self.filter_frame, text="Remap RGB", command=lambda: self.set_filter("remap"))
        remap_btn.pack(side=tk.LEFT)
        self.filter_buttons["remap"] = remap_btn
    
        reset_btn = tk.Button(self.filter_frame, text="Reset", command=self.reset_image)
        reset_btn.pack(side=tk.LEFT)
        self.filter_buttons["reset"] = reset_btn
    
        # === Load metadata and display ===
        self.load_metadata()
        self.display_image()


    def load_metadata(self):
        self.image_folder = self.inputs['image_folder']
        adcp_csv_path = self.inputs['csv_path']
        start_time = self.inputs['start_time']
        time_step = self.inputs['time_step']
        geotiff_path = self.inputs['geotiff_path']
        self.hfov = self.inputs['hfov']
        self.vfov = self.inputs['vfov']
        
        # self.image_folder = filedialog.askdirectory(title="Select Image Folder")
        # adcp_csv_path = filedialog.askopenfilename(title="Select ADCP CSV File")

        # start_time = simpledialog.askstring("Start Time", "Enter start time (YYYY-MM-DD HH:MM:SS.0000):")
        # time_step = simpledialog.askfloat("Time Step", "Enter time step between images (seconds):")

        #self.tif_path = filedialog.askopenfilename(title="Select GeoTIFF Background",filetypes=[("GeoTIFF files", "*.tif *.tiff")])
        
        self.image_df = PRFunctionsTS.create_image_df2(start_time, time_step, self.image_folder)
        flight_df = pd.read_csv(adcp_csv_path)
        flight_df.columns = flight_df.columns.str.strip()

        dt_start_time = pd.to_datetime(start_time)
        epoch_time = dt_start_time.timestamp()
        flight_df['time_increment'] = None
        flight_df['time'] = None
        flight_df.loc[0, 'time'] = epoch_time

        for i in range(0, len(flight_df) - 1):
            flight_df.iloc[i, flight_df.columns.get_loc('time_increment')] = \
                (flight_df.iloc[i + 1]['mission_msecs'] - flight_df.iloc[i]['mission_msecs']) / 1000

        for i in range(1, len(flight_df)):
            flight_df.iloc[i, flight_df.columns.get_loc('time')] = \
                flight_df.iloc[i - 1]['time'] + flight_df.iloc[i - 1]['time_increment']

        end_time = flight_df['time'].iloc[-1]
        self.image_df = self.image_df[self.image_df['Timestamp'] < end_time]
        PRFunctionsTS.generate_metadata(flight_df, self.image_df)

        self.image_df['Tag'] = None  # Add classification column
        self.image_df['Notes'] = ""  # Add notes column

        self.metadata_df = self.image_df
        self.image_paths = [os.path.join(self.image_folder, f) for f in self.metadata_df['Filename']]

        self.image_listbox.delete(0, tk.END)
        for i, row in self.metadata_df.iterrows():
            fname = row['Filename']
            tag = row['Tag'] if pd.notnull(row['Tag']) else "[unlabeled]"
            note = row['Notes'] if pd.notnull(row['Notes']) else ""
            self.image_listbox.insert(tk.END, f"{fname}  |  {tag}  |  {note}")

        self.image_listbox.select_set(0)
        self.image_listbox.activate(0)

        self.tif_path = geotiff_path


    def refresh_listbox(self):
        yview = self.image_listbox.yview()  # save current scrollbar position
        self.image_listbox.delete(0, tk.END)
        for i, row in self.metadata_df.iterrows():
            fname = row['Filename']
            tag = row['Tag'] if pd.notnull(row['Tag']) else "[unlabeled]"
            note = row['Notes'] if pd.notnull(row['Notes']) else ""
            self.image_listbox.insert(tk.END, f"{fname}  |  {tag}  |  {note}")
        self.image_listbox.yview_moveto(yview[0])  # restore previous scrollbar position
        if not row.empty:
            lat = row['Latitude'].values[0]
            lon = row['Longitude'].values[0]
            alt = row['Altitude'].values[0]
            heading = row['Heading'].values[0]
            self.meta_box.config(
                text=f"Lat:     {lat:.6f}\n"
                     f"Lon:     {lon:.6f}\n"
                     f"Alt:     {alt:.1f} m\n"
                     f"Heading: {heading:.1f}°"
            )
        else:
            self.meta_box.config(text="No metadata available.")


    def display_image(self):
        if not hasattr(self, 'image_paths') or self.current_index >= len(self.image_paths):
            return
        
        if self.current_index >= len(self.image_paths):
            self.canvas.delete("all")
            self.canvas.create_text(400, 300, text="No more images.", font=("Arial", 20))
            return

        image_path = self.image_paths[self.current_index]
        self.current_image = Image.open(image_path).convert("RGB")

        if self.active_filter:
            self.current_image = self.active_filter(self.current_image)

        filename = os.path.basename(image_path)
        row = self.metadata_df[self.metadata_df['Filename'] == filename]

        if not row.empty:
            altitude = float(row['Altitude'].values[0])
            self.scale_x, self.scale_y = self.compute_scale(self.current_image, altitude)
        else:
            print(f"Metadata for {filename} not found.")
            self.scale_x, self.scale_y = 1, 1

        self.canvas.delete("all")
        self.canvas.update_idletasks()
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        # Resize image proportionally to fit canvas
        img_copy = self.current_image.copy()
        img_copy.thumbnail((canvas_width, canvas_height), Image.Resampling.LANCZOS)
        
        # Center the image
        img_width, img_height = img_copy.size
        x_offset = (canvas_width - img_width) // 2
        y_offset = (canvas_height - img_height) // 2
        
        self.tk_image = ImageTk.PhotoImage(img_copy)
        self.canvas.delete("all")
        self.canvas.create_image(x_offset, y_offset, anchor=tk.NW, image=self.tk_image)

        #self.measurement_label.config(text="")
        self.clicks = []

        self.plot_image_locations()

        # Update metadata display box
        if not row.empty:
            lat = row['Latitude'].values[0]
            lon = row['Longitude'].values[0]
            alt = row['Altitude'].values[0]
            heading = row['Heading'].values[0]
            fname = row['Filename'].values[0]
            tag = row['Tag'].values[0] if pd.notnull(row['Tag'].values[0]) else "[unlabeled]"
            note = row['Notes'].values[0] if pd.notnull(row['Notes'].values[0]) else ""
        
            self.meta_box.config(
                text=f"Filename:  {fname}\n"
                     f"Latitude:  {lat:.6f}\n"
                     f"Longitude: {lon:.6f}\n"
                     f"Altitude:  {alt:.1f} m\n"
                     f"Heading:   {heading:.1f}°\n"
                     f"Tag:       {tag}\n"
                     f"Note:      {note}"
            )
        else:
            self.meta_box.config(text="No metadata available.")



    def on_image_select(self, event):
        selected = self.image_listbox.curselection()
        if selected:
            new_index = selected[0]
            if new_index != self.current_index:
                self.current_index = new_index
                self.set_filter(self.filter_state) if self.filter_state else self.reset_image()


    def add_new_tag_button(self):
        tag_text = self.new_tag_entry.get()
        if not tag_text:
            return
        button = tk.Button(self.tag_frame, text=tag_text, command=lambda t=tag_text: self.tag_and_next(t))
        button.pack(side=tk.LEFT)
        self.new_tag_entry.delete(0, tk.END)

    def tag_and_next(self, tag_text):
        filename = os.path.basename(self.image_paths[self.current_index])
        self.metadata_df.loc[self.metadata_df['Filename'] == filename, 'Tag'] = tag_text
    
        # Update corresponding scatter plot data
        if tag_text not in self.tag_scatters:
            # New tag introduced → full redraw
            self.map_initialized = False
            self.plot_image_locations()
        else:
            # Just update the scatter group
            tags = self.metadata_df['Tag'].fillna("[unlabeled]")
            group = self.metadata_df[tags == tag_text]
            lats = group['Latitude'].values
            lons = group['Longitude'].values
            offsets = np.column_stack((lons, lats))
            self.tag_scatters[tag_text].set_offsets(offsets)
            self.canvas_map.draw()
    
        # Move to next image
        self.current_index += 1
        self.set_filter(self.filter_state) if self.filter_state else self.reset_image()
        self.clicks = []
    
        # Update listbox selection
        self.refresh_listbox()
        self.image_listbox.select_clear(0, tk.END)
        self.image_listbox.select_set(self.current_index)
        self.image_listbox.activate(self.current_index)
    
        # Move red star
        self.plot_image_locations()


    def save_note(self):
        note_text = self.note_entry.get()
        filename = os.path.basename(self.image_paths[self.current_index])
        self.metadata_df.loc[self.metadata_df['Filename'] == filename, 'Notes'] = note_text
        self.refresh_listbox()
        self.note_entry.delete(0, tk.END)  # ← clears the entry box
        self.plot_image_locations()
    
    def skip_image(self):
        self.current_index += 1
        self.set_filter(self.filter_state) if self.filter_state else self.reset_image()
        self.clicks = []
        self.image_listbox.select_clear(0, tk.END)
        self.image_listbox.select_set(self.current_index)
        self.image_listbox.activate(self.current_index)

    def back_image(self):
        if self.current_index > 0:
            self.current_index -= 1
            self.set_filter(self.filter_state) if self.filter_state else self.reset_image()
            self.clicks = []
            self.image_listbox.select_clear(0, tk.END)
            self.image_listbox.select_set(self.current_index)
            self.image_listbox.activate(self.current_index)
    
    def apply_high_contrast(self):
        self.active_filter = lambda img: ImageEnhance.Contrast(img).enhance(2.0)
        self.display_image()

    def apply_high_saturation(self):
        self.active_filter = lambda img: ImageEnhance.Color(img).enhance(2.0)
        self.display_image()

    def apply_grayscale(self):
        self.active_filter = lambda img: img.convert("L").convert("RGB")
        self.display_image()

    def apply_remap_rgb(self):
        self.active_filter = self.remap_rgb_histogram
        self.display_image()

    def reset_image(self):
        self.active_filter = None
        self.filter_state = None
        self.update_filter_button_states()
        self.display_image()

    def set_filter(self, filter_name):
        self.filter_state = filter_name
        if filter_name == "contrast":
            self.active_filter = lambda img: ImageEnhance.Contrast(img).enhance(2.0)
        elif filter_name == "saturation":
            self.active_filter = lambda img: ImageEnhance.Color(img).enhance(2.0)
        elif filter_name == "grayscale":
            self.active_filter = lambda img: img.convert("L").convert("RGB")
        elif filter_name == "remap":
            self.active_filter = self.remap_rgb_histogram
        self.update_filter_button_states()
        self.display_image()

    def update_filter_button_states(self):
        for name, btn in self.filter_buttons.items():
            if name == self.filter_state:
                btn.config(relief=tk.SUNKEN, bg="lightblue")
            else:
                btn.config(relief=tk.RAISED, bg="SystemButtonFace")

    def remap_rgb_histogram(self, image):
        image_array = np.array(image)
        red = image_array[:, :, 0]
        green = image_array[:, :, 1]
        blue = image_array[:, :, 2]

        red = ((red - red.min()) / (red.max() - red.min()) * 255).astype(np.uint8)
        green = ((green - green.min()) / (green.max() - green.min()) * 255).astype(np.uint8)
        blue = ((blue - blue.min()) / (blue.max() - blue.min()) * 255).astype(np.uint8)

        return Image.fromarray(np.stack([red, green, blue], axis=2))

    def compute_scale(self, image, altitude):
        HFOV = math.radians(self.hfov)
        VFOV = math.radians(self.vfov)
        img_width, img_height = image.size
        real_width = 2 * altitude * math.tan(HFOV / 2)
        real_height = 2 * altitude * math.tan(VFOV / 2)
        return real_width / img_width, real_height / img_height

    def record_click(self, event):
        self.clicks.append((event.x, event.y))
        if len(self.clicks) == 2:
            x1, y1 = self.clicks[0]
            x2, y2 = self.clicks[1]
            dx = (x2 - x1) * self.scale_x
            dy = (y2 - y1) * self.scale_y
            distance = math.sqrt(dx**2 + dy**2)
            self.canvas.create_line(x1, y1, x2, y2, fill="red", width=2)
            mid_x, mid_y = (x1 + x2) // 2, (y1 + y2) // 2
            self.canvas.create_text(mid_x, mid_y - 10, text=f"{distance:.2f} m", fill="white", font=("Arial", 10), anchor=tk.S)
            #self.measurement_label.config(text=f"Measured distance: {distance:.2f} meters")
            self.clicks = []

    def export_metadata(self):
        output_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if output_path:
            self.metadata_df.to_csv(output_path, index=False)
            print(f"Metadata exported to {output_path}")

    def plot_image_locations(self):
        if not hasattr(self, "map_initialized"):
            self.map_initialized = False
        if not hasattr(self, "tag_scatters"):
            self.tag_scatters = {}
        if not hasattr(self, "current_marker"):
            self.current_marker = None
    
        if not self.map_initialized:
            self.ax.clear()
    
            # GeoTIFF background
            if hasattr(self, 'tif_path') and os.path.exists(self.tif_path):
                plot_tif_with_tfw(self.ax, self.tif_path)
            else:
                print("[WARNING] No GeoTIFF background selected or file not found.")
    
            # Initial tag scatter plots
            tags = self.metadata_df['Tag'].fillna("[unlabeled]")
            unique_tags = sorted(tags.unique())
            self.unique_tags = unique_tags  # store for legend rebuild later
    
            cmap = plt.get_cmap('tab10')
            self.tag_colors = {tag: cmap(i % 10) for i, tag in enumerate(unique_tags)}
            self.tag_colors["[unlabeled]"] = "gray"
    
            self.tag_scatters = {}
            for tag in unique_tags:
                group = self.metadata_df[tags == tag]
                lats = group['Latitude']
                lons = group['Longitude']
                scatter = self.ax.scatter(
                    lons, lats,
                    color=self.tag_colors[tag],
                    label=tag,
                    s=30, edgecolor='none', alpha=0.8, zorder=1
                )
                self.tag_scatters[tag] = scatter
    
            # Legend and map styling
            self.ax.set_xlabel("Longitude")
            self.ax.set_ylabel("Latitude")
            self.ax.set_title("Image Locations")
            self.ax.grid(True)
            self.ax.set_aspect('equal', adjustable='datalim')
    
            formatter = ScalarFormatter(useOffset=False, useMathText=False)
            formatter.set_scientific(False)
            self.ax.yaxis.set_major_formatter(formatter)
    
            self.ax.legend(loc='upper left', fontsize="small", title="Tags",
                           title_fontsize="small", frameon=True, framealpha=1.0)
    
            self.map_initialized = True
    
        # Update red star marker
        if self.current_marker:
            self.current_marker.remove()
    
        if 0 <= self.current_index < len(self.metadata_df):
            current_row = self.metadata_df.iloc[self.current_index]
            lat = current_row['Latitude']
            lon = current_row['Longitude']
    
            self.current_marker, = self.ax.plot(
                lon, lat, marker='*', color='red', markersize=16,
                markeredgecolor='black', markeredgewidth=1.5, zorder=5
            )
    
        self.canvas_map.draw()
        self.canvas_map.flush_events()
        self.canvas_map.get_tk_widget().update_idletasks()


if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()  # Hide the main window initially

    # Show welcome dialog
    welcome = WelcomeWindow(root)
    root.wait_window(welcome)  # Wait for it to close

    if welcome.result:
        # Only show main window if user completed input
        root.deiconify()
        root.title("BIVALVE - Benthic Imagery VALidation and Visual Enhancement")
        center_window(root, 1200, 800)

        icon_path = "bivalve_icon.png"
        icon_image = tk.PhotoImage(file=icon_path)
        root.iconphoto(True, icon_image)

        app = ImageTaggerApp(root, inputs=welcome.result)
        root.mainloop()
    else:
        root.destroy()  # Exit if user closed the welcome window