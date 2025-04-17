import tkinter as tk
from tkinter import filedialog, colorchooser, ttk, messagebox
from PIL import Image, ImageTk, ImageDraw
import os
import pickle
from tkinterdnd2 import TkinterDnD, DND_FILES

# Default paths
INSTALL_DIR = os.path.join(os.getenv("PROGRAMFILES"), "MinecraftTextureEditor")
TEXTURES_DIR = os.path.join(INSTALL_DIR, "Textures")

class MinecraftTextureEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("Minecraft Texture Editor")
        self.root.configure(bg="#1a1a1a")
        self.root.geometry("1200x800")

        # Variables
        self.image = None
        self.tk_image = None
        self.current_tool = "paint"
        self.current_color = (0, 0, 0, 255)  # RGBA
        self.zoom_factor = 16  # Start at 1600%
        self.is_drawing = False
        self.undo_stack = []
        self.redo_stack = []
        self.projects = {}
        self.color_swatch = None
        self.last_action = None
        self.show_grid = True
        self.grid_size_x = 1  # Grid size in pixels (X), integer
        self.grid_size_y = 1  # Grid size in pixels (Y), integer
        self.update_canvas_id = None  # To track the after ID for update_canvas
        self.textures_setup_done = False  # Flag to track if Textures tab is set up

        # Overlay mode variables
        self.overlay_mode = False
        self.first_image_pos = [140, 140]  # Position of the first image (x, y)
        self.first_image_size = [280, 280]  # Size of the first image (width, height)
        self.second_image_pos = [140, 140]  # Position of the second image (x, y)
        self.second_image_size = [100, 100]  # Size of the second image (width, height)
        self.dragging = False
        self.resizing = False
        self.drag_start = [0, 0]  # Starting position of drag
        self.resize_corner = None  # Which corner is being resized
        self.focused_image = "second"  # Which image is focused ("first" or "second")
        self.resize_handles = []  # To store resize handle IDs

        # Textures tab variables
        self.current_image_path = None  # Path of selected image in Textures tab

        # Load projects
        self.load_projects()

        # GUI Setup
        self.setup_ui()

        # Drag-and-Drop Setup for the entire window (for main editor)
        self.root.drop_target_register(DND_FILES)
        self.root.dnd_bind('<<Drop>>', self.on_drop)

    def setup_ui(self):
        # Cancel any pending update_canvas calls
        if self.update_canvas_id is not None:
            self.root.after_cancel(self.update_canvas_id)
            self.update_canvas_id = None

        # Main frame (will hold the notebook)
        self.main_frame = tk.Frame(self.root, bg="#1a1a1a")
        self.main_frame.pack(fill="both", expand=True)

        # Configure dark theme styles for ttk widgets
        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.style.configure("TNotebook", background="#1a1a1a", foreground="white", bordercolor="#1a1a1a")
        self.style.configure("TNotebook.Tab", background="#252525", foreground="white", padding=[10, 5])
        self.style.map("TNotebook.Tab", background=[("selected", "#4CAF50")], foreground=[("selected", "white")])
        self.style.configure("TFrame", background="#1a1a1a")
        self.style.configure("TLabel", background="#1a1a1a", foreground="white")
        self.style.configure("TButton", background="#4CAF50", foreground="white", bordercolor="#1a1a1a")
        self.style.map("TButton", background=[("active", "#45a049")])
        self.style.configure("Treeview", background="#2a2a2a", foreground="white", fieldbackground="#2a2a2a")
        self.style.map("Treeview", background=[("selected", "#4CAF50")])
        self.style.configure("Treeview.Heading", background="#3a3a3a", foreground="white")
        self.style.configure("Horizontal.TScale", background="#1a1a1a", troughcolor="#252525", slidercolor="white")

        # Create a notebook for tabs
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill="both", expand=True, padx=5, pady=5)

        # Editor Tab
        self.editor_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.editor_frame, text="Editor")
        self.setup_editor_tab()

        # Textures Tab
        self.textures_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.textures_frame, text="Textures")
        self.setup_textures_tab()

        # Bind tab change event
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)

    def setup_editor_tab(self):
        # Cancel any pending update_canvas calls
        if self.update_canvas_id is not None:
            self.root.after_cancel(self.update_canvas_id)
            self.update_canvas_id = None

        # Clear the editor frame
        for widget in self.editor_frame.winfo_children():
            widget.destroy()

        # Top Frame for Undo/Redo and Zoom
        self.top_frame = tk.Frame(self.editor_frame, bg="#1a1a1a")
        self.top_frame.pack(side="top", fill="x")
        self.undo_btn = tk.Button(self.top_frame, text="← Undo", command=self.undo, bg="#252525", fg="white", bd=0, state="disabled")
        self.undo_btn.pack(side="right", padx=5, pady=5)
        self.redo_btn = tk.Button(self.top_frame, text="Redo →", command=self.redo, bg="#252525", fg="white", bd=0, state="disabled")
        self.redo_btn.pack(side="right", padx=5, pady=5)
        self.zoom_in_btn = tk.Button(self.top_frame, text="Zoom In", command=self.zoom_in, bg="#252525", fg="white", bd=0)
        self.zoom_in_btn.pack(side="left", padx=5, pady=5)
        self.zoom_out_btn = tk.Button(self.top_frame, text="Zoom Out", command=self.zoom_out, bg="#252525", fg="white", bd=0)
        self.zoom_out_btn.pack(side="left", padx=5, pady=5)

        # Sidebar
        self.sidebar = tk.Frame(self.editor_frame, bg="#252525", width=200)
        self.sidebar.pack(side="left", fill="y", padx=10, pady=10)

        # File Buttons
        tk.Button(self.sidebar, text="New Project", command=self.new_project, bg="#3a3a3a", fg="white").pack(fill="x", pady=5)
        tk.Button(self.sidebar, text="Import", command=self.import_image, bg="#3a3a3a", fg="white").pack(fill="x", pady=5)
        tk.Button(self.sidebar, text="Export", command=self.export_image, bg="#3a3a3a", fg="white").pack(fill="x", pady=5)
        tk.Button(self.sidebar, text="Save Project", command=self.save_project, bg="#3a3a3a", fg="white").pack(fill="x", pady=5)
        tk.Button(self.sidebar, text="Projects", command=self.show_projects, bg="#3a3a3a", fg="white").pack(fill="x", pady=5)

        # Image Combiner Dropdown
        self.combiner_frame = tk.Frame(self.sidebar, bg="#252525")
        self.combiner_frame.pack(fill="x", pady=5)
        tk.Label(self.combiner_frame, text="Image Combiner", bg="#252525", fg="white").pack(fill="x")
        self.combiner_var = tk.StringVar(value="2 Image Combiner")
        combiner_options = [f"{i} Image Combiner" for i in range(2, 11)]
        self.combiner_menu = tk.OptionMenu(self.combiner_frame, self.combiner_var, *combiner_options, command=self.show_image_combiner)
        self.combiner_menu.config(bg="#3a3a3a", fg="white", highlightthickness=0)
        self.combiner_menu.pack(fill="x", padx=5)

        # Tools
        self.tools_frame = tk.LabelFrame(self.sidebar, text="Tools", bg="#252525", fg="white")
        self.tools_frame.pack(fill="x", pady=10)
        self.paint_btn = tk.Button(self.tools_frame, text="Paint", command=lambda: self.set_tool("paint"), bg="#5a5a5a", fg="white")
        self.paint_btn.pack(fill="x")
        tk.Button(self.tools_frame, text="Erase", command=lambda: self.set_tool("erase"), bg="#3a3a3a", fg="white").pack(fill="x")
        tk.Button(self.tools_frame, text="Eyedropper", command=lambda: self.set_tool("eyedropper"), bg="#3a3a3a", fg="white").pack(fill="x")
        tk.Button(self.tools_frame, text="Paint Bucket", command=lambda: self.set_tool("bucket"), bg="#3a3a3a", fg="white").pack(fill="x")
        tk.Button(self.tools_frame, text="Toggle Grid", command=self.toggle_grid, bg="#3a3a3a", fg="white").pack(fill="x", pady=2)

        # Grid Size Controls
        self.grid_size_frame = tk.LabelFrame(self.sidebar, text="Grid Size", bg="#252525", fg="white")
        self.grid_size_frame.pack(fill="x", pady=5)
        tk.Label(self.grid_size_frame, text="X:", bg="#252525", fg="white").pack(side="left", padx=5)
        self.grid_size_x_entry = tk.Entry(self.grid_size_frame, width=5, bg="#3a3a3a", fg="white", insertbackground="white")
        self.grid_size_x_entry.insert(0, "1")
        self.grid_size_x_entry.pack(side="left", padx=5)
        self.grid_size_x_entry.bind("<Return>", self.update_grid_size)
        tk.Label(self.grid_size_frame, text="Y:", bg="#252525", fg="white").pack(side="left", padx=5)
        self.grid_size_y_entry = tk.Entry(self.grid_size_frame, width=5, bg="#3a3a3a", fg="white", insertbackground="white")
        self.grid_size_y_entry.insert(0, "1")
        self.grid_size_y_entry.pack(side="left", padx=5)
        self.grid_size_y_entry.bind("<Return>", self.update_grid_size)

        # Color Picker
        self.color_frame = tk.LabelFrame(self.sidebar, text="Color", bg="#252525", fg="white")
        self.color_frame.pack(fill="x", pady=10)
        tk.Button(self.color_frame, text="Pick Color", command=self.pick_color, bg="#3a3a3a", fg="white").pack(fill="x")
        self.hex_entry = tk.Entry(self.color_frame, bg="#3a3a3a", fg="white", insertbackground="white")
        self.hex_entry.insert(0, "#000000")
        self.hex_entry.pack(fill="x", pady=5)
        self.hex_entry.bind("<Return>", self.update_color_from_hex)
        tk.Label(self.color_frame, text="Alpha", bg="#252525", fg="white").pack()
        self.alpha_slider = ttk.Scale(self.color_frame, from_=0, to=255, orient="horizontal")
        self.alpha_slider.set(255)
        self.alpha_slider.pack(fill="x")
        self.color_swatch = tk.Label(self.color_frame, bg="#000000", width=5, height=2)
        self.color_swatch.pack(pady=5)

        # Bind alpha slider
        self.alpha_slider.config(command=self.update_alpha)

        # Canvas Area
        self.canvas_frame = tk.Frame(self.editor_frame, bg="#1a1a1a")
        self.canvas_frame.pack(side="left", fill="both", expand=True)
        self.canvas = tk.Canvas(self.canvas_frame, bg="#1a1a1a", highlightthickness=0)
        self.canvas.pack(padx=10, pady=10)

        # Zoom Display
        self.zoom_frame = tk.Frame(self.canvas_frame, bg="#1a1a1a")
        self.zoom_frame.pack()
        self.zoom_label = tk.Label(self.zoom_frame, text="1600%", bg="#1a1a1a", fg="white")
        self.zoom_label.pack(side="left", padx=5)

        # Bind Canvas Events
        self.canvas.bind("<Button-1>", self.on_mouse_down)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)
        self.canvas.bind("<Button-1>", self.on_mouse_down if self.current_tool != "bucket" else self.paint_bucket)

        # Bind Arrow Keys for Zoom
        self.root.bind("<Left>", lambda event: self.zoom_out())
        self.root.bind("<Right>", lambda event: self.zoom_in())

        # Update canvas if an image is loaded
        if self.image:
            self.update_canvas()

    def setup_textures_tab(self):
        # Only rebuild the UI if it hasn't been set up yet
        if not hasattr(self, 'textures_setup_done') or not self.textures_setup_done:
            self.textures_top_frame = tk.Frame(self.textures_frame, bg="#1a1a1a")
            self.textures_top_frame.pack(fill="x", padx=5, pady=5)

            self.load_button = ttk.Button(self.textures_top_frame, text="Load into Editor", command=self.load_selected_image, state="disabled")
            self.load_button.pack(side="right", padx=5)

            self.tree = ttk.Treeview(self.textures_frame, show="tree")
            self.tree.pack(fill="both", expand=True, padx=5, pady=5)

            self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)
            self.populate_textures_tree()
            self.textures_setup_done = True  # Mark as set up

    def populate_textures_tree(self):
        if not os.path.exists(TEXTURES_DIR):
            messagebox.showerror("Error", "Textures directory not found.")
            return

        for item in self.tree.get_children():
            self.tree.delete(item)

        for version_dir in os.listdir(TEXTURES_DIR):
            version_path = os.path.join(TEXTURES_DIR, version_dir)
            if os.path.isdir(version_path):
                parent_node = self.tree.insert("", "end", text=version_dir, open=False)
                self.add_files_to_tree(version_path, parent_node)

    def add_files_to_tree(self, directory, parent_node):
        try:
            for item in os.listdir(directory):
                item_path = os.path.join(directory, item)
                if os.path.isdir(item_path):
                    child_node = self.tree.insert(parent_node, "end", text=item, open=False)
                    self.add_files_to_tree(item_path, child_node)
                else:
                    self.tree.insert(parent_node, "end", text=item, values=(item_path,))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load textures: {str(e)}")

    def on_tree_select(self, event):
        selected_items = self.tree.selection()
        if not selected_items:
            self.load_button.config(state="disabled")
            return

        selected_item = selected_items[0]
        values = self.tree.item(selected_item, "values")
        if values and len(values) > 0:
            file_path = values[0]
            if file_path.lower().endswith(".png"):
                self.current_image_path = file_path
                self.load_button.config(state="normal")
            else:
                self.current_image_path = None
                self.load_button.config(state="disabled")
        else:
            self.current_image_path = None
            self.load_button.config(state="disabled")

    def load_selected_image(self):
        if not self.current_image_path:
            messagebox.showerror("Error", "No image selected to load.")
            return

        try:
            self.image = Image.open(self.current_image_path).convert("RGBA")
            self.undo_stack = [self.image.copy()]
            self.redo_stack = []
            self.update_undo_redo_buttons()
            self.update_canvas()
            self.notebook.select(self.editor_frame)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load image: {str(e)}")

    def on_tab_changed(self, event):
        selected_tab = self.notebook.index(self.notebook.select())
        if selected_tab == 0:
            self.setup_editor_tab()
        elif selected_tab == 1:
            # Only populate the tree if it hasn't been set up
            if not hasattr(self, 'textures_setup_done') or not self.textures_setup_done:
                self.setup_textures_tab()
        else:
            self.show_image_combiner(self.combiner_var.get())

    def show_image_combiner(self, num_images_str):
        num_images = int(num_images_str.split()[0])
        self.num_images = num_images

        # Remove existing Image Combiner tabs
        for tab_id in self.notebook.tabs():
            if self.notebook.tab(tab_id, "text").startswith("Image Combiner"):
                self.notebook.forget(tab_id)

        combiner_frame = ttk.Frame(self.notebook)
        self.notebook.add(combiner_frame, text=f"Image Combiner ({num_images})")
        self.notebook.select(combiner_frame)

        if self.update_canvas_id is not None:
            self.root.after_cancel(self.update_canvas_id)
            self.update_canvas_id = None

        self.overlay_mode = False
        self.first_image_pos = [140, 140]
        self.first_image_size = [280, 280]
        self.second_image_pos = [140, 140]
        self.second_image_size = [100, 100]
        self.dragging = False
        self.resizing = False
        self.focused_image = "second"

        top_frame = tk.Frame(combiner_frame, bg="#1a1a1a")
        top_frame.pack(side="top", fill="x")
        tk.Button(top_frame, text="Back to Editor", command=lambda: self.notebook.select(self.editor_frame), bg="#3a3a3a", fg="white").pack(side="left", padx=5, pady=5)
        self.status_label = tk.Label(top_frame, text=f"Welcome to {num_images} Image Combiner", bg="#1a1a1a", fg="white")
        self.status_label.pack(side="left", padx=10)

        content_container = tk.Frame(combiner_frame, bg="#1a1a1a")
        content_container.pack(fill="both", expand=True)

        self.content_canvas = tk.Canvas(content_container, bg="#1a1a1a", highlightthickness=0)
        scrollbar = tk.Scrollbar(content_container, orient="horizontal", command=self.content_canvas.xview)
        scrollbar.pack(side="bottom", fill="x")
        self.content_canvas.configure(xscrollcommand=scrollbar.set)
        self.content_canvas.pack(side="left", fill="both", expand=True)

        content_frame = tk.Frame(self.content_canvas, bg="#1a1a1a")
        self.content_canvas.create_window((0, 0), window=content_frame, anchor="nw")

        content_frame.bind("<Configure>", lambda e: self.content_canvas.configure(scrollregion=self.content_canvas.bbox("all")))

        self.image_paths = [tk.StringVar() for _ in range(num_images)]
        self.image_canvases = []
        self.images = [None] * num_images

        window_width = 1200
        max_canvas_width = 280
        canvas_width = min(max_canvas_width, (window_width - 300) // (num_images + 1))
        canvas_height = canvas_width

        for i in range(num_images):
            image_frame = tk.Frame(content_frame, bg="#252525")
            image_frame.pack(side="left", padx=10, pady=10)
            tk.Label(image_frame, text=f"Image {i+1}", bg="#252525", fg="white", font=("Arial", 10)).pack()
            canvas = tk.Canvas(image_frame, bg="#3a3a3a", highlightthickness=0, width=canvas_width, height=canvas_height)
            canvas.pack(expand=True)
            canvas.create_text(canvas_width//2, canvas_height//2, text="Drag or Click to Upload", fill="gray", font=("Arial", 8))
            tk.Button(image_frame, text="Browse", command=lambda idx=i: self.upload_image(self.image_paths[idx], self.image_canvases[idx]), bg="#3a3a3a", fg="white").pack(pady=5)

            self.image_canvases.append(canvas)

            def register_drop_target(canvas=canvas, idx=i):
                try:
                    if canvas.winfo_exists():  # Ensure canvas still exists
                        canvas.drop_target_register(DND_FILES)
                        canvas.dnd_bind('<<Drop>>', lambda event, idx=idx, c=canvas: self.handle_drop(event, self.image_paths[idx], c))
                    else:
                        print(f"Canvas for Image {idx+1} no longer exists during drop_target_register.")
                except Exception as e:
                    print(f"Error registering drop target for Image {idx+1}: {str(e)}")

            # Increased delay to 300ms for safety
            self.root.after(300, register_drop_target)

            if i < num_images - 1:
                arrow_frame = tk.Frame(content_frame, bg="#1a1a1a")
                arrow_frame.pack(side="left", pady=10)
                arrow_label = tk.Label(arrow_frame, text="→", bg="#1a1a1a", fg="white", font=("Arial", 20))
                arrow_label.pack(pady=canvas_height//2)

        middle_frame = tk.Frame(content_frame, bg="#252525")
        middle_frame.pack(side="left", padx=10, pady=10)
        tk.Label(middle_frame, text="Combined Image", bg="#252525", fg="white", font=("Arial", 10)).pack()
        self.combined_canvas = tk.Canvas(middle_frame, bg="#3a3a3a", highlightthickness=0, width=canvas_width, height=canvas_height)
        self.combined_canvas.pack(padx=5, pady=5, expand=True)

        bottom_frame = tk.Frame(combiner_frame, bg="#252525")
        bottom_frame.pack(side="bottom", fill="x", padx=10, pady=10)

        tk.Label(bottom_frame, text="Output Width:", bg="#252525", fg="white").pack(side="left")
        self.output_width_entry = tk.Entry(bottom_frame, width=5, bg="#3a3a3a", fg="white", insertbackground="white")
        self.output_width_entry.insert(0, "16")
        self.output_width_entry.pack(side="left")

        tk.Label(bottom_frame, text="Output Height:", bg="#252525", fg="white").pack(side="left")
        self.output_height_entry = tk.Entry(bottom_frame, width=5, bg="#3a3a3a", fg="white", insertbackground="white")
        self.output_height_entry.insert(0, "16")
        self.output_height_entry.pack(side="left")

        tk.Button(bottom_frame, text="Combine", command=self.combine_images, bg="#3a3a3a", fg="white").pack(side="left", padx=10)
        tk.Button(bottom_frame, text="Overlay Images", command=self.overlay_images, bg="#3a3a3a", fg="white").pack(side="left", padx=10)
        tk.Button(bottom_frame, text="Export Combined", command=self.export_combined_image, bg="#3a3a3a", fg="white").pack(side="left", padx=10)
        tk.Button(bottom_frame, text="Load into Editor", command=self.load_combined_into_editor, bg="#3a3a3a", fg="white").pack(side="left", padx=10)

        self.sidebar_frame = tk.Frame(combiner_frame, bg="#252525", width=200)
        self.sidebar_visible = False
        tk.Button(bottom_frame, text="Combination Options ▼", command=self.toggle_sidebar, bg="#3a3a3a", fg="white").pack(side="left", padx=5)

        self.pattern_var = tk.StringVar()
        self.update_pattern_options(num_images)

    def update_pattern_options(self, num_images):
        for widget in self.sidebar_frame.winfo_children():
            widget.destroy()

        tk.Label(self.sidebar_frame, text="Select Pattern:", bg="#252525", fg="white", font=("Arial", 10)).pack(pady=5)

        if num_images == 2:
            patterns = [
                "Horizontal Split", "Horizontal Split (Reverse)",
                "Vertical Split", "Vertical Split (Reverse)",
                "Checkerboard", "Checkerboard (Reverse)",
                "Per Bend", "Per Bend (Reverse)",
                "Cross", "Cross (Reverse)",
                "Chevron", "Chevron (Reverse)",
                "Inverted Chevron", "Inverted Chevron (Reverse)",
                "Stripes Horizontal", "Stripes Vertical",
                "Border", "Border (Reverse)",
                "Diamond", "Diamond (Reverse)"
            ]
            self.pattern_var.set("Horizontal Split")
        else:
            patterns = [
                f"Split {num_images} Horizontal",
                f"Split {num_images} Vertical",
                f"Checkerboard {num_images}",
                f"Stripes Horizontal {num_images}",
                f"Stripes Vertical {num_images}",
                f"Gradient {num_images}",
                f"Border Cycle {num_images}",
                f"Diamond Cycle {num_images}"
            ]
            self.pattern_var.set(patterns[0])

        self.pattern_menu = tk.OptionMenu(self.sidebar_frame, self.pattern_var, *patterns)
        self.pattern_menu.config(bg="#3a3a3a", fg="white", highlightthickness=0)
        self.pattern_menu.pack(pady=5, fill="x", padx=10)

    def handle_drop(self, event, path_var, canvas):
        try:
            file_path = event.data
            if file_path.startswith("{") and file_path.endswith("}"):
                file_path = file_path[1:-1]
            if not os.path.exists(file_path):
                self.status_label.config(text=f"Error: File not found: {file_path}")
                print(f"Drop error: File not found: {file_path}")
                return
            if not file_path.lower().endswith(('.png', '.jpg', '.jpeg')):
                self.status_label.config(text="Error: Only PNG/JPG files are supported")
                print(f"Drop error: Unsupported file type: {file_path}")
                return
            path_var.set(file_path)
            image = Image.open(file_path).convert("RGBA")
            canvas_width = canvas.winfo_width()
            canvas_height = canvas.winfo_height()
            img_width, img_height = image.size
            scale = min(canvas_width / img_width, canvas_height / img_height)
            new_width = int(img_width * scale)
            new_height = int(img_height * scale)
            image = image.resize((new_width, new_height), Image.NEAREST)
            tk_image = ImageTk.PhotoImage(image)
            canvas.delete("all")
            canvas.create_image(canvas_width//2, canvas_height//2, anchor="center", image=tk_image)
            canvas.image = tk_image
            self.status_label.config(text="Image uploaded successfully")
        except Exception as e:
            self.status_label.config(text="Error uploading image")
            print(f"Error in handle_drop: {str(e)}")

    def upload_image(self, path_var, canvas):
        file_path = filedialog.askopenfilename(filetypes=[("Image files", "*.png *.jpg *.jpeg")])
        if file_path:
            path_var.set(file_path)
            image = Image.open(file_path).convert("RGBA")
            canvas_width = canvas.winfo_width()
            canvas_height = canvas.winfo_height()
            img_width, img_height = image.size
            scale = min(canvas_width / img_width, canvas_height / img_height)
            new_width = int(img_width * scale)
            new_height = int(img_height * scale)
            image = image.resize((new_width, new_height), Image.NEAREST)
            tk_image = ImageTk.PhotoImage(image)
            canvas.delete("all")
            canvas.create_image(canvas_width//2, canvas_height//2, anchor="center", image=tk_image)
            canvas.image = tk_image
            self.status_label.config(text="Image uploaded successfully")

    def toggle_sidebar(self):
        if self.sidebar_visible:
            self.sidebar_frame.pack_forget()
            self.sidebar_visible = False
        else:
            self.sidebar_frame.pack(side="right", fill="y", padx=5, pady=5)
            self.sidebar_visible = True

    def combine_images(self):
        try:
            for i, path in enumerate(self.image_paths):
                if not path.get():
                    messagebox.showerror("Error", f"Please upload Image {i+1}.")
                    self.status_label.config(text=f"Error: Please upload Image {i+1}")
                    return
                self.images[i] = Image.open(path.get()).convert("RGBA")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load images: {str(e)}")
            self.status_label.config(text="Error: Failed to load images")
            print(f"Error loading images in combine_images: {str(e)}")
            return

        try:
            output_width = int(self.output_width_entry.get())
            output_height = int(self.output_height_entry.get())
            if output_width <= 0 or output_height <= 0:
                raise ValueError("Output dimensions must be positive.")
            if output_width != output_height:
                messagebox.showwarning("Warning", "Output width and height must be equal. Using width as the size.")
                output_height = output_width
                self.output_height_entry.delete(0, tk.END)
                self.output_height_entry.insert(0, str(output_width))
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid output size: {str(e)}")
            self.status_label.config(text="Error: Invalid output size")
            print(f"Error in output size: {str(e)}")
            return

        self.status_label.config(text="Combining images...")
        pattern = self.pattern_var.get()

        try:
            for i in range(self.num_images):
                self.images[i] = self.images[i].resize((output_width, output_height), Image.NEAREST)

            self.combined_image = Image.new("RGBA", (output_width, output_height))

            if self.num_images == 2:
                if pattern == "Horizontal Split":
                    half_width = output_width // 2
                    left_half = self.images[0].crop((0, 0, half_width, output_height))
                    right_half = self.images[1].crop((half_width, 0, output_width, output_height))
                    self.combined_image.paste(left_half, (0, 0))
                    self.combined_image.paste(right_half, (half_width, 0))
                elif pattern == "Horizontal Split (Reverse)":
                    half_width = output_width // 2
                    left_half = self.images[1].crop((0, 0, half_width, output_height))
                    right_half = self.images[0].crop((half_width, 0, output_width, output_height))
                    self.combined_image.paste(left_half, (0, 0))
                    self.combined_image.paste(right_half, (half_width, 0))
                elif pattern == "Vertical Split":
                    half_height = output_height // 2
                    top_half = self.images[0].crop((0, 0, output_width, half_height))
                    bottom_half = self.images[1].crop((0, half_height, output_width, output_height))
                    self.combined_image.paste(top_half, (0, 0))
                    self.combined_image.paste(bottom_half, (0, half_height))
                elif pattern == "Vertical Split (Reverse)":
                    half_height = output_height // 2
                    top_half = self.images[1].crop((0, 0, output_width, half_height))
                    bottom_half = self.images[0].crop((0, half_height, output_width, output_height))
                    self.combined_image.paste(top_half, (0, 0))
                    self.combined_image.paste(bottom_half, (0, half_height))
                elif pattern == "Checkerboard":
                    half_width = output_width // 2
                    half_height = output_height // 2
                    self.combined_image.paste(self.images[0].crop((0, 0, half_width, half_height)), (0, 0))
                    self.combined_image.paste(self.images[1].crop((half_width, 0, output_width, half_height)), (half_width, 0))
                    self.combined_image.paste(self.images[1].crop((0, half_height, half_width, output_height)), (0, half_height))
                    self.combined_image.paste(self.images[0].crop((half_width, half_height, output_width, output_height)), (half_width, half_height))
                elif pattern == "Checkerboard (Reverse)":
                    half_width = output_width // 2
                    half_height = output_height // 2
                    self.combined_image.paste(self.images[1].crop((0, 0, half_width, half_height)), (0, 0))
                    self.combined_image.paste(self.images[0].crop((half_width, 0, output_width, half_height)), (half_width, 0))
                    self.combined_image.paste(self.images[0].crop((0, half_height, half_width, output_height)), (0, half_height))
                    self.combined_image.paste(self.images[1].crop((half_width, half_height, output_width, output_height)), (half_width, half_height))
                elif pattern == "Per Bend":
                    for x in range(output_width):
                        for y in range(output_height):
                            if y < (output_height * x) // output_width:
                                self.combined_image.putpixel((x, y), self.images[1].getpixel((x, y)))
                            else:
                                self.combined_image.putpixel((x, y), self.images[0].getpixel((x, y)))
                elif pattern == "Per Bend (Reverse)":
                    for x in range(output_width):
                        for y in range(output_height):
                            if y < (output_height * (output_width - 1 - x)) // output_width:
                                self.combined_image.putpixel((x, y), self.images[1].getpixel((x, y)))
                            else:
                                self.combined_image.putpixel((x, y), self.images[0].getpixel((x, y)))
                elif pattern == "Cross":
                    cross_thickness = max(1, output_width // 5)
                    center_x = (output_width - 1) / 2
                    center_y = (output_height - 1) / 2
                    half_thickness = cross_thickness / 2
                    for x in range(output_width):
                        for y in range(output_height):
                            in_cross = (
                                (center_x - half_thickness <= x <= center_x + half_thickness) or
                                (center_y - half_thickness <= y <= center_y + half_thickness)
                            )
                            if in_cross:
                                self.combined_image.putpixel((x, y), self.images[0].getpixel((x, y)))
                            else:
                                self.combined_image.putpixel((x, y), self.images[1].getpixel((x, y)))
                elif pattern == "Cross (Reverse)":
                    cross_thickness = max(1, output_width // 5)
                    center_x = (output_width - 1) / 2
                    center_y = (output_height - 1) / 2
                    half_thickness = cross_thickness / 2
                    for x in range(output_width):
                        for y in range(output_height):
                            in_cross = (
                                (center_x - half_thickness <= x <= center_x + half_thickness) or
                                (center_y - half_thickness <= y <= center_y + half_thickness)
                            )
                            if in_cross:
                                self.combined_image.putpixel((x, y), self.images[1].getpixel((x, y)))
                            else:
                                self.combined_image.putpixel((x, y), self.images[0].getpixel((x, y)))
                elif pattern == "Chevron":
                    for x in range(output_width):
                        for y in range(output_height):
                            if y < (output_height * x) // output_width:
                                self.combined_image.putpixel((x, y), self.images[0].getpixel((x, y)))
                            else:
                                self.combined_image.putpixel((x, y), self.images[1].getpixel((x, y)))
                elif pattern == "Chevron (Reverse)":
                    for x in range(output_width):
                        for y in range(output_height):
                            if y < (output_height * (output_width - 1 - x)) // output_width:
                                self.combined_image.putpixel((x, y), self.images[0].getpixel((x, y)))
                            else:
                                self.combined_image.putpixel((x, y), self.images[1].getpixel((x, y)))
                elif pattern == "Inverted Chevron":
                    for x in range(output_width):
                        for y in range(output_height):
                            if y > (output_height * x) // output_width:
                                self.combined_image.putpixel((x, y), self.images[0].getpixel((x, y)))
                            else:
                                self.combined_image.putpixel((x, y), self.images[1].getpixel((x, y)))
                elif pattern == "Inverted Chevron (Reverse)":
                    for x in range(output_width):
                        for y in range(output_height):
                            if y > (output_height * (output_width - 1 - x)) // output_width:
                                self.combined_image.putpixel((x, y), self.images[0].getpixel((x, y)))
                            else:
                                self.combined_image.putpixel((x, y), self.images[1].getpixel((x, y)))
                elif pattern == "Stripes Horizontal":
                    stripe_height = max(1, output_height // 4)
                    for x in range(output_width):
                        for y in range(output_height):
                            if (y // stripe_height) % 2 == 0:
                                self.combined_image.putpixel((x, y), self.images[0].getpixel((x, y)))
                            else:
                                self.combined_image.putpixel((x, y), self.images[1].getpixel((x, y)))
                elif pattern == "Stripes Vertical":
                    stripe_width = max(1, output_width // 4)
                    for x in range(output_width):
                        for y in range(output_height):
                            if (x // stripe_width) % 2 == 0:
                                self.combined_image.putpixel((x, y), self.images[0].getpixel((x, y)))
                            else:
                                self.combined_image.putpixel((x, y), self.images[1].getpixel((x, y)))
                elif pattern == "Border":
                    border_width = max(1, output_width // 8)
                    for x in range(output_width):
                        for y in range(output_height):
                            is_border = (
                                x < border_width or
                                x >= output_width - border_width or
                                y < border_width or
                                y >= output_height - border_width
                            )
                            if is_border:
                                self.combined_image.putpixel((x, y), self.images[0].getpixel((x, y)))
                            else:
                                self.combined_image.putpixel((x, y), self.images[1].getpixel((x, y)))
                elif pattern == "Border (Reverse)":
                    border_width = max(1, output_width // 8)
                    for x in range(output_width):
                        for y in range(output_height):
                            is_border = (
                                x < border_width or
                                x >= output_width - border_width or
                                y < border_width or
                                y >= output_height - border_width
                            )
                            if is_border:
                                self.combined_image.putpixel((x, y), self.images[1].getpixel((x, y)))
                            else:
                                self.combined_image.putpixel((x, y), self.images[0].getpixel((x, y)))
                elif pattern == "Diamond":
                    center_x = (output_width - 1) / 2
                    center_y = (output_height - 1) / 2
                    diamond_size = min(output_width, output_height) / 2
                    for x in range(output_width):
                        for y in range(output_height):
                            dist = abs(x - center_x) + abs(y - center_y)
                            if dist < diamond_size:
                                self.combined_image.putpixel((x, y), self.images[0].getpixel((x, y)))
                            else:
                                self.combined_image.putpixel((x, y), self.images[1].getpixel((x, y)))
                elif pattern == "Diamond (Reverse)":
                    center_x = (output_width - 1) / 2
                    center_y = (output_height - 1) / 2
                    diamond_size = min(output_width, output_height) / 2
                    for x in range(output_width):
                        for y in range(output_height):
                            dist = abs(x - center_x) + abs(y - center_y)
                            if dist < diamond_size:
                                self.combined_image.putpixel((x, y), self.images[1].getpixel((x, y)))
                            else:
                                self.combined_image.putpixel((x, y), self.images[0].getpixel((x, y)))

            else:
                if f"Split {self.num_images} Horizontal" in pattern:
                    section_width = output_width // self.num_images
                    remaining_width = output_width % self.num_images
                    for i in range(self.num_images):
                        start_x = i * section_width + min(i, remaining_width)
                        current_section_width = section_width + (1 if i < remaining_width else 0)
                        end_x = start_x + current_section_width
                        if end_x > output_width:
                            end_x = output_width
                            current_section_width = end_x - start_x
                        self.combined_image.paste(
                            self.images[i].crop((start_x, 0, end_x, output_height)),
                            (start_x, 0)
                        )
                elif f"Split {self.num_images} Vertical" in pattern:
                    section_height = output_height // self.num_images
                    remaining_height = output_height % self.num_images
                    for i in range(self.num_images):
                        start_y = i * section_height + min(i, remaining_height)
                        current_section_height = section_height + (1 if i < remaining_height else 0)
                        end_y = start_y + current_section_height
                        if end_y > output_height:
                            end_y = output_height
                            current_section_height = end_y - start_y
                        self.combined_image.paste(
                            self.images[i].crop((0, start_y, output_width, end_y)),
                            (0, start_y)
                        )
                elif f"Checkerboard {self.num_images}" in pattern:
                    rows = int(self.num_images ** 0.5)
                    cols = (self.num_images + rows - 1) // rows
                    cell_width = output_width // cols
                    cell_height = output_height // rows
                    remaining_width = output_width % cols
                    remaining_height = output_height % rows
                    for row in range(rows):
                        for col in range(cols):
                            idx = row * cols + col
                            if idx >= self.num_images:
                                idx = idx % self.num_images
                            start_x = col * cell_width + min(col, remaining_width)
                            start_y = row * cell_height + min(row, remaining_height)
                            current_cell_width = cell_width + (1 if col < remaining_width else 0)
                            current_cell_height = cell_height + (1 if row < remaining_height else 0)
                            end_x = start_x + current_cell_width
                            end_y = start_y + current_cell_height
                            if end_x > output_width:
                                end_x = output_width
                                current_cell_width = end_x - start_x
                            if end_y > output_height:
                                end_y = output_height
                                current_cell_height = end_y - start_y
                            self.combined_image.paste(
                                self.images[idx].crop((0, 0, current_cell_width, current_cell_height)),
                                (start_x, start_y)
                            )
                elif f"Stripes Horizontal {self.num_images}" in pattern:
                    stripe_height = max(1, output_height // self.num_images)
                    for y in range(output_height):
                        img_idx = (y // stripe_height) % self.num_images
                        for x in range(output_width):
                            self.combined_image.putpixel((x, y), self.images[img_idx].getpixel((x, y)))
                elif f"Stripes Vertical {self.num_images}" in pattern:
                    stripe_width = max(1, output_width // self.num_images)
                    for x in range(output_width):
                        img_idx = (x // stripe_width) % self.num_images
                        for y in range(output_height):
                            self.combined_image.putpixel((x, y), self.images[img_idx].getpixel((x, y)))
                elif f"Gradient {self.num_images}" in pattern:
                    for y in range(output_height):
                        t = (y * self.num_images) // output_height
                        if t >= self.num_images:
                            t = self.num_images - 1
                        for x in range(output_width):
                            self.combined_image.putpixel((x, y), self.images[t].getpixel((x, y)))
                elif f"Border Cycle {self.num_images}" in pattern:
                    border_width = max(1, output_width // 8)
                    for x in range(output_width):
                        for y in range(output_height):
                            dist = min(x, y, output_width - 1 - x, output_height - 1 - y)
                            idx = (dist // border_width) % self.num_images
                            self.combined_image.putpixel((x, y), self.images[idx].getpixel((x, y)))
                elif f"Diamond Cycle {self.num_images}" in pattern:
                    center_x = (output_width - 1) / 2
                    center_y = (output_height - 1) / 2
                    max_dist = min(output_width, output_height) / 2
                    for x in range(output_width):
                        for y in range(output_height):
                            dist = abs(x - center_x) + abs(y - center_y)
                            idx = int((dist * self.num_images) / max_dist) % self.num_images
                            self.combined_image.putpixel((x, y), self.images[idx].getpixel((x, y)))

            self.display_combined_image()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to combine images: {str(e)}")
            self.status_label.config(text="Error: Failed to combine images")
            print(f"Error combining images: {str(e)}")

    def overlay_images(self):
        if self.num_images != 2:
            messagebox.showerror("Error", "Overlay mode is only supported for 2 images.")
            self.status_label.config(text="Error: Overlay mode only for 2 images")
            return

        self.overlay_mode = True
        first_path = self.image_paths[0].get()
        second_path = self.image_paths[1].get()
        if not first_path or not second_path:
            messagebox.showerror("Error", "Please upload both images.")
            self.status_label.config(text="Error: Please upload both images")
            return

        self.images[0] = Image.open(first_path).convert("RGBA")
        self.images[1] = Image.open(second_path).convert("RGBA")

        self.first_image_pos = [self.combined_canvas.winfo_width()//2, self.combined_canvas.winfo_height()//2]
        self.first_image_size = [self.combined_canvas.winfo_width(), self.combined_canvas.winfo_height()]
        self.second_image_pos = [self.combined_canvas.winfo_width()//2, self.combined_canvas.winfo_height()//2]
        self.second_image_size = [self.combined_canvas.winfo_width()//2, self.combined_canvas.winfo_height()//2]
        self.focused_image = "second"

        self.display_overlay()

        self.combined_canvas.bind("<Button-1>", self.start_drag_or_resize)
        self.combined_canvas.bind("<B1-Motion>", self.on_drag_or_resize)
        self.combined_canvas.bind("<ButtonRelease-1>", self.stop_drag_or_resize)

    def display_combined_image(self):
        canvas_width = self.combined_canvas.winfo_width()
        canvas_height = self.combined_canvas.winfo_height()
        img_width, img_height = self.combined_image.size
        scale = min(canvas_width / img_width, canvas_height / img_height)
        new_width = int(img_width * scale)
        new_height = int(img_height * scale)
        combined_image_resized = self.combined_image.resize((new_width, new_height), Image.NEAREST)
        tk_combined = ImageTk.PhotoImage(combined_image_resized)
        self.combined_canvas.delete("all")
        self.combined_canvas.create_image(canvas_width//2, canvas_height//2, anchor="center", image=tk_combined)
        self.combined_canvas.image = tk_combined
        self.status_label.config(text="Images combined successfully")

    def display_overlay(self):
        canvas_width = self.combined_canvas.winfo_width()
        canvas_height = self.combined_canvas.winfo_height()

        first_image = self.images[0].copy()
        first_image = first_image.resize((self.first_image_size[0], self.first_image_size[1]), Image.NEAREST)
        self.tk_first_image = ImageTk.PhotoImage(first_image)

        second_image = self.images[1].copy()
        second_image = second_image.resize((self.second_image_size[0], self.second_image_size[1]), Image.NEAREST)
        self.tk_second_image = ImageTk.PhotoImage(second_image)

        self.combined_canvas.delete("all")
        self.combined_canvas.create_image(self.first_image_pos[0], self.first_image_pos[1], anchor="center", image=self.tk_first_image, tags="first_image")
        self.combined_canvas.create_image(self.second_image_pos[0], self.second_image_pos[1], anchor="center", image=self.tk_second_image, tags="second_image")

        self.draw_bounding_box()

        self.status_label.config(text=f"Overlay mode: Focused on {self.focused_image} image. Click to focus, drag to move/resize")

    def draw_bounding_box(self):
        self.combined_canvas.delete("bounding_box")
        self.resize_handles = []

        if self.focused_image == "first":
            pos = self.first_image_pos
            size = self.first_image_size
        else:
            pos = self.second_image_pos
            size = self.second_image_size

        x, y = pos
        w, h = size
        half_w, half_h = w // 2, h // 2
        left = x - half_w
        top = y - half_h
        right = x + half_w
        bottom = y + half_h

        self.combined_canvas.create_rectangle(left, top, right, bottom, outline="white", dash=(2, 2), tags="bounding_box")

        handle_size = 8
        tl_handle = self.combined_canvas.create_rectangle(left - handle_size//2, top - handle_size//2, left + handle_size//2, top + handle_size//2, fill="white", tags="bounding_box")
        tr_handle = self.combined_canvas.create_rectangle(right - handle_size//2, top - handle_size//2, right + handle_size//2, top + handle_size//2, fill="white", tags="bounding_box")
        bl_handle = self.combined_canvas.create_rectangle(left - handle_size//2, bottom - handle_size//2, left + handle_size//2, bottom + handle_size//2, fill="white", tags="bounding_box")
        br_handle = self.combined_canvas.create_rectangle(right - handle_size//2, bottom - handle_size//2, right + handle_size//2, bottom + handle_size//2, fill="white", tags="bounding_box")

        self.resize_handles = [tl_handle, tr_handle, bl_handle, br_handle]

        for handle in self.resize_handles:
            self.combined_canvas.tag_bind(handle, "<Enter>", lambda e: self.combined_canvas.config(cursor="size_nw_se"))
            self.combined_canvas.tag_bind(handle, "<Leave>", lambda e: self.combined_canvas.config(cursor=""))

    def start_drag_or_resize(self, event):
        if not self.overlay_mode:
            return

        x, y = event.x, event.y

        pos = self.first_image_pos
        size = self.first_image_size
        half_w, half_h = size[0] // 2, size[1] // 2
        left = pos[0] - half_w
        top = pos[1] - half_h
        right = pos[0] + half_w
        bottom = pos[1] + half_h
        if left <= x <= right and top <= y <= bottom:
            self.focused_image = "first"

        pos = self.second_image_pos
        size = self.second_image_size
        half_w, half_h = size[0] // 2, size[1] // 2
        left = pos[0] - half_w
        top = pos[1] - half_h
        right = pos[0] + half_w
        bottom = pos[1] + half_h
        if left <= x <= right and top <= y <= bottom:
            self.focused_image = "second"

        if self.focused_image == "first":
            pos = self.first_image_pos
            size = self.first_image_size
        else:
            pos = self.second_image_pos
            size = self.second_image_size

        x_img, y_img = pos
        w, h = size
        half_w, half_h = w // 2, h // 2
        left = x_img - half_w
        top = y_img - half_h
        right = x_img + half_w
        bottom = y_img + half_h

        handle_size = 8
        if abs(x - left) < handle_size and abs(y - top) < handle_size:
            self.resizing = True
            self.resize_corner = "top-left"
        elif abs(x - right) < handle_size and abs(y - top) < handle_size:
            self.resizing = True
            self.resize_corner = "top-right"
        elif abs(x - left) < handle_size and abs(y - bottom) < handle_size:
            self.resizing = True
            self.resize_corner = "bottom-left"
        elif abs(x - right) < handle_size and abs(y - bottom) < handle_size:
            self.resizing = True
            self.resize_corner = "bottom-right"
        elif left <= x <= right and top <= y <= bottom:
            self.dragging = True

        self.drag_start = [x, y]
        self.display_overlay()

    def on_drag_or_resize(self, event):
        if not self.overlay_mode:
            return

        x, y = event.x, event.y
        dx = x - self.drag_start[0]
        dy = y - self.drag_start[1]

        if self.focused_image == "first":
            pos = self.first_image_pos
            size = self.first_image_size
        else:
            pos = self.second_image_pos
            size = self.second_image_size

        canvas_width = self.combined_canvas.winfo_width()
        canvas_height = self.combined_canvas.winfo_height()

        if self.dragging:
            new_x = pos[0] + dx
            new_y = pos[1] + dy
            w, h = size
            half_w, half_h = w // 2, h // 2
            new_x = max(half_w, min(canvas_width - half_w, new_x))
            new_y = max(half_h, min(canvas_height - half_h, new_y))
            pos[0] = new_x
            pos[1] = new_y

        elif self.resizing:
            w, h = size
            half_w, half_h = w // 2, h // 2
            img_x, img_y = pos
            left = img_x - half_w
            top = img_y - half_h
            right = img_x + half_w
            bottom = img_y + half_h
            original_x, original_y = pos[0], pos[1]

            if self.resize_corner == "top-left":
                new_left = left + dx
                new_top = top + dy
                new_w = right - new_left
                new_h = bottom - new_top
                if new_w > 50 and new_h > 50:
                    size[0] = new_w
                    size[1] = new_h
                    pos[0] = new_left + new_w // 2
                    pos[1] = new_top + new_h // 2
            elif self.resize_corner == "top-right":
                new_right = right + dx
                new_top = top + dy
                new_w = new_right - left
                new_h = bottom - new_top
                if new_w > 50 and new_h > 50:
                    size[0] = new_w
                    size[1] = new_h
                    pos[0] = left + new_w // 2
                    pos[1] = new_top + new_h // 2
            elif self.resize_corner == "bottom-left":
                new_left = left + dx
                new_bottom = bottom + dy
                new_w = right - new_left
                new_h = new_bottom - top
                if new_w > 50 and new_h > 50:
                    size[0] = new_w
                    size[1] = new_h
                    pos[0] = new_left + new_w // 2
                    pos[1] = top + new_h // 2
            elif self.resize_corner == "bottom-right":
                new_right = right + dx
                new_bottom = bottom + dy
                new_w = new_right - left
                new_h = new_bottom - top
                if new_w > 50 and new_h > 50:
                    size[0] = new_w
                    size[1] = new_h
                    pos[0] = left + new_w // 2
                    pos[1] = top + new_h // 2

        self.drag_start = [x, y]
        self.display_overlay()

    def stop_drag_or_resize(self, event):
        self.dragging = False
        self.resizing = False
        self.resize_corner = None

    def export_combined_image(self):
        if not hasattr(self, 'combined_image') or self.combined_image is None:
            messagebox.showerror("Error", "No combined image to export.")
            self.status_label.config(text="Error: No combined image")
            return

        file_path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG files", "*.png")])
        if file_path:
            try:
                if self.overlay_mode:
                    first_image = self.images[0].copy()
                    second_image = self.images[1].copy()
                    output_width = self.combined_canvas.winfo_width()
                    output_height = self.combined_canvas.winfo_height()
                    first_image = first_image.resize((self.first_image_size[0], self.first_image_size[1]), Image.NEAREST)
                    second_image = second_image.resize((self.second_image_size[0], self.second_image_size[1]), Image.NEAREST)
                    combined = Image.new("RGBA", (output_width, output_height))
                    first_pos_x = self.first_image_pos[0] - self.first_image_size[0] // 2
                    first_pos_y = self.first_image_pos[1] - self.first_image_size[1] // 2
                    second_pos_x = self.second_image_pos[0] - self.second_image_size[0] // 2
                    second_pos_y = self.second_image_pos[1] - self.second_image_size[1] // 2
                    combined.paste(first_image, (int(first_pos_x), int(first_pos_y)), first_image)
                    combined.paste(second_image, (int(second_pos_x), int(second_pos_y)), second_image)
                    combined.save(file_path)
                else:
                    self.combined_image.save(file_path)
                self.status_label.config(text="Combined image exported successfully")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export image: {str(e)}")
                self.status_label.config(text="Error: Failed to export image")

    def load_combined_into_editor(self):
        if not hasattr(self, 'combined_image') or self.combined_image is None:
            messagebox.showerror("Error", "No combined image to load.")
            self.status_label.config(text="Error: No combined image")
            return

        if self.overlay_mode:
            first_image = self.images[0].copy()
            second_image = self.images[1].copy()
            output_width = self.combined_canvas.winfo_width()
            output_height = self.combined_canvas.winfo_height()
            first_image = first_image.resize((self.first_image_size[0], self.first_image_size[1]), Image.NEAREST)
            second_image = second_image.resize((self.second_image_size[0], self.second_image_size[1]), Image.NEAREST)
            self.combined_image = Image.new("RGBA", (output_width, output_height))
            first_pos_x = self.first_image_pos[0] - self.first_image_size[0] // 2
            first_pos_y = self.first_image_pos[1] - self.first_image_size[1] // 2
            second_pos_x = self.second_image_pos[0] - self.second_image_size[0] // 2
            second_pos_y = self.second_image_pos[1] - self.second_image_size[1] // 2
            self.combined_image.paste(first_image, (int(first_pos_x), int(first_pos_y)), first_image)
            self.combined_image.paste(second_image, (int(second_pos_x), int(second_pos_y)), second_image)

        self.image = self.combined_image.copy()
        self.undo_stack = [self.image.copy()]
        self.redo_stack = []
        self.update_undo_redo_buttons()
        self.update_canvas()
        self.notebook.select(self.editor_frame)
        self.status_label.config(text="Combined image loaded into editor")

    def on_drop(self, event):
        file_path = event.data
        if file_path.startswith("{") and file_path.endswith("}"):
            file_path = file_path[1:-1]
        if not os.path.exists(file_path):
            messagebox.showerror("Error", f"File not found: {file_path}")
            return
        if not file_path.lower().endswith(('.png', '.jpg', '.jpeg')):
            messagebox.showerror("Error", "Only PNG/JPG files are supported")
            return
        try:
            self.image = Image.open(file_path).convert("RGBA")
            self.undo_stack = [self.image.copy()]
            self.redo_stack = []
            self.update_undo_redo_buttons()
            self.update_canvas()
            self.notebook.select(self.editor_frame)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load image: {str(e)}")

    def load_projects(self):
        projects_file = os.path.join(INSTALL_DIR, "projects.pkl")
        if os.path.exists(projects_file):
            try:
                with open(projects_file, "rb") as f:
                    self.projects = pickle.load(f)
            except:
                self.projects = {}

    def save_projects(self):
        if not os.path.exists(INSTALL_DIR):
            os.makedirs(INSTALL_DIR)
        projects_file = os.path.join(INSTALL_DIR, "projects.pkl")
        with open(projects_file, "wb") as f:
            pickle.dump(self.projects, f)

    def new_project(self):
        size_dialog = tk.Toplevel(self.root)
        size_dialog.title("New Project")
        size_dialog.configure(bg="#1a1a1a")

        tk.Label(size_dialog, text="Width:", bg="#1a1a1a", fg="white").grid(row=0, column=0, padx=5, pady=5)
        width_entry = tk.Entry(size_dialog, bg="#3a3a3a", fg="white", insertbackground="white")
        width_entry.grid(row=0, column=1, padx=5, pady=5)
        width_entry.insert(0, "16")

        tk.Label(size_dialog, text="Height:", bg="#1a1a1a", fg="white").grid(row=1, column=0, padx=5, pady=5)
        height_entry = tk.Entry(size_dialog, bg="#3a3a3a", fg="white", insertbackground="white")
        height_entry.grid(row=1, column=1, padx=5, pady=5)
        height_entry.insert(0, "16")

        def create():
            try:
                width = int(width_entry.get())
                height = int(height_entry.get())
                if width <= 0 or height <= 0:
                    raise ValueError("Dimensions must be positive integers.")
                self.image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
                self.undo_stack = [self.image.copy()]
                self.redo_stack = []
                self.update_undo_redo_buttons()
                self.update_canvas()
                size_dialog.destroy()
            except ValueError as e:
                messagebox.showerror("Error", str(e))

        tk.Button(size_dialog, text="Create", command=create, bg="#4CAF50", fg="white").grid(row=2, column=0, columnspan=2, pady=10)

    def import_image(self):
        file_path = filedialog.askopenfilename(filetypes=[("Image files", "*.png *.jpg *.jpeg")])
        if file_path:
            self.image = Image.open(file_path).convert("RGBA")
            self.undo_stack = [self.image], self.redo_stack = []
            self.update_undo_redo_buttons()
            self.update_canvas_id = self.root.after(100, self.update_canvas)
            self.notebook.select(self.editor_frame)

    def export_image(self):
        if not self.image:
            messagebox.showerror("Error", "No image to export.")
            return
        file_path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG files", "*.png")])
        if file_path:
            self.image.save(file_path)
            messagebox.showinfo("Success", "Image exported successfully.")

    def save_project(self):
        if not self.image:
            messagebox.showerror("Error", "No image to save.")
            return

        project_name = tk.simpledialog.askstring("Save Project", "Enter project name:", parent=self.root)
        if project_name:
            project_data = {
                "image": self.image.copy(),
                "undo_stack": self.undo_stack.copy(),
                "redo_stack": self.redo_stack.copy()
            }
            self.projects[project_name] = project_data
            self.save_projects()
            messagebox.showinfo("Success", f"Project '{project_name}' saved successfully.")

    def show_projects(self):
        projects_window = tk.Toplevel(self.root)
        projects_window.title("Projects")
        projects_window.configure(bg="#1a1a1a")

        listbox = tk.Listbox(projects_window, bg="#3a3a3a", fg="white", selectbackground="#4CAF50")
        listbox.pack(padx=10, pady=10, fill="both", expand=True)

        for project_name in self.projects.keys():
            listbox.insert(tk.END, project_name)

        def load_project():
            selected = listbox.curselection()
            if not selected:
                messagebox.showerror("Error", "No project selected.")
                return
            project_name = listbox.get(selected[0])
            project_data = self.projects.get(project_name)
            if project_data:
                self.image = project_data["image"].copy()
                self.undo_stack = project_data["undo_stack"].copy()
                self.redo_stack = project_data["redo_stack"].copy()
                self.update_undo_redo_buttons()
                self.update_canvas()
                self.notebook.select(self.editor_frame)
                projects_window.destroy()

        def delete_project():
            selected = listbox.curselection()
            if not selected:
                messagebox.showerror("Error", "No project selected.")
                return
            project_name = listbox.get(selected[0])
            if project_name in self.projects:
                del self.projects[project_name]
                self.save_projects()
                listbox.delete(selected[0])
                messagebox.showinfo("Success", f"Project '{project_name}' deleted.")

        tk.Button(projects_window, text="Load", command=load_project, bg="#4CAF50", fg="white").pack(side="left", padx=5, pady=5)
        tk.Button(projects_window, text="Delete", command=delete_project, bg="#f44336", fg="white").pack(side="left", padx=5, pady=5)
        tk.Button(projects_window, text="Close", command=projects_window.destroy, bg="#3a3a3a", fg="white").pack(side="right", padx=5, pady=5)

    def undo(self):
        if len(self.undo_stack) > 1:
            self.redo_stack.append(self.undo_stack.pop())
            self.image = self.undo_stack[-1].copy()
            self.update_undo_redo_buttons()
            self.update_canvas()

    def redo(self):
        if self.redo_stack:
            self.undo_stack.append(self.redo_stack.pop())
            self.image = self.undo_stack[-1].copy()
            self.update_undo_redo_buttons()
            self.update_canvas()

    def update_undo_redo_buttons(self):
        self.undo_btn.config(state="normal" if len(self.undo_stack) > 1 else "disabled")
        self.redo_btn.config(state="normal" if self.redo_stack else "disabled")

    def set_tool(self, tool):
        self.current_tool = tool
        for btn in self.tools_frame.winfo_children():
            btn.config(bg="#3a3a3a")
        if tool == "paint":
            self.tools_frame.winfo_children()[0].config(bg="#5a5a5a")
        elif tool == "erase":
            self.tools_frame.winfo_children()[1].config(bg="#5a5a5a")
        elif tool == "eyedropper":
            self.tools_frame.winfo_children()[2].config(bg="#5a5a5a")
        elif tool == "bucket":
            self.tools_frame.winfo_children()[3].config(bg="#5a5a5a")

    def toggle_grid(self):
        self.show_grid = not self.show_grid
        self.update_canvas()

    def update_grid_size(self, event=None):
        try:
            new_grid_size_x = int(self.grid_size_x_entry.get())
            new_grid_size_y = int(self.grid_size_y_entry.get())
            if new_grid_size_x > 0 and new_grid_size_y > 0:
                self.grid_size_x = new_grid_size_x
                self.grid_size_y = new_grid_size_y
                self.update_canvas()
            else:
                messagebox.showerror("Error", "Grid size must be positive integers.")
                self.grid_size_x_entry.delete(0, tk.END)
                self.grid_size_x_entry.insert(0, str(self.grid_size_x))
                self.grid_size_y_entry.delete(0, tk.END)
                self.grid_size_y_entry.insert(0, str(self.grid_size_y))
        except ValueError:
            messagebox.showerror("Error", "Grid size must be integers.")
            self.grid_size_x_entry.delete(0, tk.END)
            self.grid_size_x_entry.insert(0, str(self.grid_size_x))
            self.grid_size_y_entry.delete(0, tk.END)
            self.grid_size_y_entry.insert(0, str(self.grid_size_y))

    def pick_color(self):
        color = colorchooser.askcolor(title="Choose Color", initialcolor="#000000")[1]
        if color:
            self.hex_entry.delete(0, tk.END)
            self.hex_entry.insert(0, color)
            r = int(color[1:3], 16)
            g = int(color[3:5], 16)
            b = int(color[5:7], 16)
            a = int(self.alpha_slider.get())
            self.current_color = (r, g, b, a)
            self.color_swatch.config(bg=color)

    def update_color_from_hex(self, event=None):
        hex_color = self.hex_entry.get()
        try:
            if hex_color.startswith("#") and len(hex_color) == 7:
                r = int(hex_color[1:3], 16)
                g = int(hex_color[3:5], 16)
                b = int(hex_color[5:7], 16)
                a = int(self.alpha_slider.get())
                self.current_color = (r, g, b, a)
                self.color_swatch.config(bg=hex_color)
            else:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Invalid hex color code. Use format #RRGGBB.")
            r, g, b, a = self.current_color
            self.hex_entry.delete(0, tk.END)
            self.hex_entry.insert(0, f"#{r:02x}{g:02x}{b:02x}")

    def update_alpha(self, value):
        r, g, b, _ = self.current_color
        a = int(float(value))
        self.current_color = (r, g, b, a)

    def zoom_in(self):
        if self.zoom_factor < 32:
            self.zoom_factor *= 2
            self.zoom_label.config(text=f"{int(self.zoom_factor * 100)}%")
            self.update_canvas()

    def zoom_out(self):
        if self.zoom_factor > 1:
            self.zoom_factor //= 2
            self.zoom_label.config(text=f"{int(self.zoom_factor * 100)}%")
            self.update_canvas()

    def update_canvas(self):
        if not hasattr(self, 'canvas') or not self.canvas.winfo_exists():
            return

        if self.update_canvas_id is not None:
            self.root.after_cancel(self.update_canvas_id)
            self.update_canvas_id = None

        self.canvas.delete("all")
        if self.image:
            width, height = self.image.size
            scaled_width = int(width * self.zoom_factor)
            scaled_height = int(height * self.zoom_factor)
            resized_image = self.image.resize((scaled_width, scaled_height), Image.NEAREST)
            self.tk_image = ImageTk.PhotoImage(resized_image)
            self.canvas.config(width=scaled_width, height=scaled_height)
            self.canvas.create_image(0, 0, anchor="nw", image=self.tk_image)

            if self.show_grid:
                for x in range(0, scaled_width, self.grid_size_x * self.zoom_factor):
                    self.canvas.create_line(x, 0, x, scaled_height, fill="#FFFFFF", stipple="gray50")
                for y in range(0, scaled_height, self.grid_size_y * self.zoom_factor):
                    self.canvas.create_line(0, y, scaled_width, y, fill="#FFFFFF", stipple="gray50")

    def on_mouse_down(self, event):
        if not self.image:
            return
        self.is_drawing = True
        self.last_action = self.image.copy()
        self.edit_pixel(event)

    def on_mouse_drag(self, event):
        if not self.image or not self.is_drawing:
            return
        self.edit_pixel(event)

    def on_mouse_up(self, event):
        if not self.image:
            return
        self.is_drawing = False
        if self.last_action:
            self.undo_stack.append(self.image.copy())
self.redo_stack = []
self.update_undo_redo_buttons()
self.last_action = None

def edit_pixel(self, event):
        if not self.image:
            return
        x = int(event.x // self.zoom_factor)
        y = int(event.y // self.zoom_factor)
        if not (0 <= x < self.image.width and 0 <= y < self.image.height):
            return

        pixels = self.image.load()
        if self.current_tool == "paint":
            pixels[x, y] = self.current_color
        elif self.current_tool == "erase":
            pixels[x, y] = (0, 0, 0, 0)
        elif self.current_tool == "eyedropper":
            r, g, b, a = pixels[x, y]
            self.current_color = (r, g, b, a)
            self.hex_entry.delete(0, tk.END)
            self.hex_entry.insert(0, f"#{r:02x}{g:02x}{b:02x}")
            self.color_swatch.config(bg=f"#{r:02x}{g:02x}{b:02x}")
            self.alpha_slider.set(a)
            self.set_tool("paint")  # Switch back to paint tool after picking color

        self.update_canvas()

def paint_bucket(self, event):
        if not self.image:
            print("Paint Bucket: No image loaded.")
            return
        x = int(event.x // self.zoom_factor)
        y = int(event.y // self.zoom_factor)
        if not (0 <= x < self.image.width and 0 <= y < self.image.height):
            print(f"Paint Bucket: Click outside image bounds (x={x}, y={y}, width={self.image.width}, height={self.image.height}).")
            return

        print(f"Paint Bucket: Starting at position (x={x}, y={y}) with color {self.current_color}")
        try:
            self.paint_bucket_animation(x, y)
        except Exception as e:
            print(f"Paint Bucket: Error in paint_bucket: {str(e)}")
            # Fallback: Fill the image immediately if animation fails
            pixels = self.image.load()
            width, height = self.image.size
            for px in range(width):
                for py in range(height):
                    pixels[px, py] = self.current_color
            self.undo_stack.append(self.image.copy())
            self.redo_stack = []
            self.update_undo_redo_buttons()
            self.update_canvas()
            print("Paint Bucket: Fallback fill completed.")

def paint_bucket_animation(self, x, y):
        """Simulate a 'ball of paint' spreading effect and fill the entire image."""
        try:
            pixels = self.image.load()
            width, height = self.image.size
            filled_pixels = [(px, py) for px in range(width) for py in range(height)]  # All pixels in the image
            print(f"Paint Bucket Animation: Total pixels to fill: {len(filled_pixels)}")

            # Animation parameters
            max_radius = max(width, height)  # Base radius on image dimensions (not scaled)
            steps = 20  # Number of animation frames
            pixels_per_step = max(1, len(filled_pixels) // steps)
            print(f"Paint Bucket Animation: Steps={steps}, Pixels per step={pixels_per_step}")

            def animate_fill(step=0):
                try:
                    if step >= steps:
                        # Final fill of all pixels
                        for px, py in filled_pixels:
                            pixels[px, py] = self.current_color
                        self.undo_stack.append(self.image.copy())
                        self.redo_stack = []
                        self.update_undo_redo_buttons()
                        self.canvas.delete("animation")
                        self.update_canvas()
                        print("Paint Bucket Animation: Completed successfully.")
                        return

                    # Calculate radius for the animation (scaled by zoom_factor for canvas display)
                    radius = (step / steps) * max_radius * self.zoom_factor
                    r, g, b, a = self.current_color
                    hex_color = f"#{r:02x}{g:02x}{b:02x}"
                    print(f"Paint Bucket Animation: Step {step}, Radius={radius}, Color={hex_color}")

                    # Draw the animation circle
                    self.canvas.delete("animation")
                    canvas_x = x * self.zoom_factor + self.zoom_factor // 2  # Center in the pixel
                    canvas_y = y * self.zoom_factor + self.zoom_factor // 2
                    self.canvas.create_oval(
                        canvas_x - radius, canvas_y - radius,
                        canvas_x + radius, canvas_y + radius,
                        fill=hex_color, outline=hex_color, tags="animation"
                    )
                    print(f"Paint Bucket Animation: Drew circle at ({canvas_x}, {canvas_y}) with radius {radius}")

                    # Fill a portion of the pixels
                    start_idx = step * pixels_per_step
                    end_idx = min((step + 1) * pixels_per_step, len(filled_pixels))
                    for idx in range(start_idx, end_idx):
                        px, py = filled_pixels[idx]
                        pixels[px, py] = self.current_color
                    print(f"Paint Bucket Animation: Filled pixels {start_idx} to {end_idx}")

                    # Force canvas update
                    self.canvas.update_idletasks()
                    self.update_canvas()

                    # Schedule the next animation step
                    self.root.after(50, animate_fill, step + 1)
                except Exception as e:
                    print(f"Paint Bucket Animation: Error at step {step}: {str(e)}")
                    # Fallback: Complete the fill immediately
                    for px, py in filled_pixels:
                        pixels[px, py] = self.current_color
                    self.undo_stack.append(self.image.copy())
                    self.redo_stack = []
                    self.update_undo_redo_buttons()
                    self.canvas.delete("animation")
                    self.update_canvas()
                    print("Paint Bucket Animation: Fallback fill completed due to error.")

            animate_fill()
        except Exception as e:
            print(f"Paint Bucket Animation: Initialization error: {str(e)}")
            # Fallback: Fill the image immediately
            for px in range(width):
                for py in range(height):
                    pixels[px, py] = self.current_color
            self.undo_stack.append(self.image.copy())
            self.redo_stack = []
            self.update_undo_redo_buttons()
            self.update_canvas()
            print("Paint Bucket Animation: Fallback fill completed during initialization.")

if __name__ == "__main__":
    root = TkinterDnD.Tk()
    app = MinecraftTextureEditor(root)
    root.mainloop()