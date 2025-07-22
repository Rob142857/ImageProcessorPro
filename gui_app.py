"""
Modern GUI for Image Processor
============================

A user-friendly interface for the automated image processing system.
Built with CustomTkinter for a modern appearance.
"""

import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from pathlib import Path
import threading
from typing import Optional, Callable
import json

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from image_processor import ImageProcessor, ProcessingConfig

# Set appearance mode and color theme
ctk.set_appearance_mode("dark")  # Modes: "System", "Dark", "Light"
ctk.set_default_color_theme("blue")  # Themes: "blue", "green", "dark-blue"


class ImageProcessorGUI:
    """Modern GUI for the Image Processor application."""
    
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("Image Processor Pro - Watermark & Web Optimizer")
        self.root.geometry("900x700")
        self.root.minsize(800, 600)
        
        # Initialize variables
        self.config = ProcessingConfig()
        self.processor: Optional[ImageProcessor] = None
        self.processing_thread: Optional[threading.Thread] = None
        self.is_processing = False
        
        # Create GUI elements
        self.create_widgets()
        self.load_settings()
        
        # Configure window closing
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def create_widgets(self):
        """Create and layout all GUI widgets."""
        
        # Main container with padding
        main_frame = ctk.CTkFrame(self.root)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Title
        title_label = ctk.CTkLabel(
            main_frame, 
            text="Image Processor Pro", 
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title_label.pack(pady=(0, 20))
        
        # Create tabview
        self.tabview = ctk.CTkTabview(main_frame)
        self.tabview.pack(fill="both", expand=True)
        
        # Add tabs
        self.tab_basic = self.tabview.add("Basic Settings")
        self.tab_advanced = self.tabview.add("Advanced Settings")
        self.tab_processing = self.tabview.add("Processing")
        
        self.create_basic_tab()
        self.create_advanced_tab()
        self.create_processing_tab()
    
    def create_basic_tab(self):
        """Create basic settings tab."""
        
        # Input folder selection
        input_frame = ctk.CTkFrame(self.tab_basic)
        input_frame.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(input_frame, text="Input Folder:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(10, 5))
        
        input_path_frame = ctk.CTkFrame(input_frame)
        input_path_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        self.input_folder_var = ctk.StringVar()
        self.input_entry = ctk.CTkEntry(input_path_frame, textvariable=self.input_folder_var, placeholder_text="Select input folder...")
        self.input_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self.input_browse_btn = ctk.CTkButton(input_path_frame, text="Browse", command=self.browse_input_folder, width=100)
        self.input_browse_btn.pack(side="right")
        
        # Output folder selection
        output_frame = ctk.CTkFrame(self.tab_basic)
        output_frame.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(output_frame, text="Output Folder:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(10, 5))
        
        output_path_frame = ctk.CTkFrame(output_frame)
        output_path_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        self.output_folder_var = ctk.StringVar()
        self.output_entry = ctk.CTkEntry(output_path_frame, textvariable=self.output_folder_var, placeholder_text="Select output folder...")
        self.output_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self.output_browse_btn = ctk.CTkButton(output_path_frame, text="Browse", command=self.browse_output_folder, width=100)
        self.output_browse_btn.pack(side="right")
        
        # Watermark selection
        watermark_frame = ctk.CTkFrame(self.tab_basic)
        watermark_frame.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(watermark_frame, text="Watermark Image (PNG):", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(10, 5))
        
        watermark_path_frame = ctk.CTkFrame(watermark_frame)
        watermark_path_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        self.watermark_path_var = ctk.StringVar()
        self.watermark_entry = ctk.CTkEntry(watermark_path_frame, textvariable=self.watermark_path_var, placeholder_text="Select watermark image...")
        self.watermark_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self.watermark_browse_btn = ctk.CTkButton(watermark_path_frame, text="Browse", command=self.browse_watermark, width=100)
        self.watermark_browse_btn.pack(side="right")
        
        # Output format and quality
        settings_frame = ctk.CTkFrame(self.tab_basic)
        settings_frame.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(settings_frame, text="Output Settings:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(10, 5))
        
        format_quality_frame = ctk.CTkFrame(settings_frame)
        format_quality_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        # Output format
        ctk.CTkLabel(format_quality_frame, text="Format:").pack(side="left", padx=(0, 10))
        self.format_var = ctk.StringVar(value="JPEG")
        format_menu = ctk.CTkOptionMenu(format_quality_frame, variable=self.format_var, values=["JPEG", "PNG", "WEBP"])
        format_menu.pack(side="left", padx=(0, 20))
        
        # Quality
        ctk.CTkLabel(format_quality_frame, text="Quality:").pack(side="left", padx=(0, 10))
        self.quality_var = ctk.IntVar(value=85)
        quality_slider = ctk.CTkSlider(format_quality_frame, from_=10, to=100, variable=self.quality_var, number_of_steps=90)
        quality_slider.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self.quality_label = ctk.CTkLabel(format_quality_frame, text="85")
        self.quality_label.pack(side="left")
        quality_slider.configure(command=self.update_quality_label)
    
    def create_advanced_tab(self):
        """Create advanced settings tab."""
        
        # Watermark settings
        watermark_frame = ctk.CTkFrame(self.tab_advanced)
        watermark_frame.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(watermark_frame, text="Watermark Settings:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(10, 5))
        
        # Opacity
        opacity_frame = ctk.CTkFrame(watermark_frame)
        opacity_frame.pack(fill="x", padx=10, pady=(0, 5))
        
        ctk.CTkLabel(opacity_frame, text="Opacity:").pack(side="left", padx=(10, 10))
        self.opacity_var = ctk.DoubleVar(value=0.3)
        opacity_slider = ctk.CTkSlider(opacity_frame, from_=0.1, to=1.0, variable=self.opacity_var, number_of_steps=18)
        opacity_slider.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self.opacity_label = ctk.CTkLabel(opacity_frame, text="0.3")
        self.opacity_label.pack(side="left", padx=(0, 10))
        opacity_slider.configure(command=self.update_opacity_label)
        
        # Position
        position_frame = ctk.CTkFrame(watermark_frame)
        position_frame.pack(fill="x", padx=10, pady=(0, 5))
        
        ctk.CTkLabel(position_frame, text="Position:").pack(side="left", padx=(10, 10))
        self.position_var = ctk.StringVar(value="bottom-right")
        position_menu = ctk.CTkOptionMenu(
            position_frame, 
            variable=self.position_var, 
            values=["center", "top-left", "top-right", "bottom-left", "bottom-right"]
        )
        position_menu.pack(side="left", padx=(0, 10))
        
        # Scale
        scale_frame = ctk.CTkFrame(watermark_frame)
        scale_frame.pack(fill="x", padx=10, pady=(0, 5))
        
        ctk.CTkLabel(scale_frame, text="Scale:").pack(side="left", padx=(10, 10))
        self.scale_var = ctk.DoubleVar(value=0.2)
        scale_slider = ctk.CTkSlider(scale_frame, from_=0.05, to=0.5, variable=self.scale_var, number_of_steps=45)
        scale_slider.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self.scale_label = ctk.CTkLabel(scale_frame, text="0.2")
        self.scale_label.pack(side="left", padx=(0, 10))
        scale_slider.configure(command=self.update_scale_label)
        
        # Tiling mode (NEW)
        tiling_frame = ctk.CTkFrame(watermark_frame)
        tiling_frame.pack(fill="x", padx=10, pady=(0, 5))
        
        ctk.CTkLabel(tiling_frame, text="Watermark Mode:").pack(side="left", padx=(10, 10))
        self.tiling_var = ctk.BooleanVar(value=True)
        tiling_checkbox = ctk.CTkCheckBox(
            tiling_frame, 
            text="Tiled Pattern (better protection)", 
            variable=self.tiling_var,
            command=self.toggle_tiling_mode
        )
        tiling_checkbox.pack(side="left", padx=(0, 10))
        
        # Tile size (only visible when tiling is enabled)
        self.tile_size_frame = ctk.CTkFrame(watermark_frame)
        self.tile_size_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        ctk.CTkLabel(self.tile_size_frame, text="Tile Size:").pack(side="left", padx=(10, 10))
        self.tile_size_var = ctk.DoubleVar(value=0.18)
        tile_size_slider = ctk.CTkSlider(self.tile_size_frame, from_=0.1, to=0.3, variable=self.tile_size_var, number_of_steps=20)
        tile_size_slider.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self.tile_size_label = ctk.CTkLabel(self.tile_size_frame, text="0.18")
        self.tile_size_label.pack(side="left", padx=(0, 10))
        tile_size_slider.configure(command=self.update_tile_size_label)
        
        # Image size settings
        size_frame = ctk.CTkFrame(self.tab_advanced)
        size_frame.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(size_frame, text="Image Size Settings:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(10, 5))
        
        dimensions_frame = ctk.CTkFrame(size_frame)
        dimensions_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        # Max width
        ctk.CTkLabel(dimensions_frame, text="Max Width:").pack(side="left", padx=(10, 10))
        self.max_width_var = ctk.IntVar(value=1920)
        width_entry = ctk.CTkEntry(dimensions_frame, textvariable=self.max_width_var, width=100)
        width_entry.pack(side="left", padx=(0, 20))
        
        # Max height
        ctk.CTkLabel(dimensions_frame, text="Max Height:").pack(side="left", padx=(0, 10))
        self.max_height_var = ctk.IntVar(value=1080)
        height_entry = ctk.CTkEntry(dimensions_frame, textvariable=self.max_height_var, width=100)
        height_entry.pack(side="left", padx=(0, 20))
        
        # Preserve aspect ratio
        self.preserve_aspect_var = ctk.BooleanVar(value=True)
        preserve_check = ctk.CTkCheckBox(dimensions_frame, text="Preserve Aspect Ratio", variable=self.preserve_aspect_var)
        preserve_check.pack(side="left")
        
        # Performance settings
        perf_frame = ctk.CTkFrame(self.tab_advanced)
        perf_frame.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(perf_frame, text="Performance Settings:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(10, 5))
        
        perf_options_frame = ctk.CTkFrame(perf_frame)
        perf_options_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        # Multiprocessing
        self.multiprocessing_var = ctk.BooleanVar(value=True)
        mp_check = ctk.CTkCheckBox(perf_options_frame, text="Use Multiprocessing", variable=self.multiprocessing_var)
        mp_check.pack(side="left", padx=(10, 20))
        
        # Max workers
        ctk.CTkLabel(perf_options_frame, text="Max Workers:").pack(side="left", padx=(0, 10))
        self.max_workers_var = ctk.IntVar(value=4)
        workers_entry = ctk.CTkEntry(perf_options_frame, textvariable=self.max_workers_var, width=80)
        workers_entry.pack(side="left")
    
    def create_processing_tab(self):
        """Create processing tab."""
        
        # File count display
        self.file_info_frame = ctk.CTkFrame(self.tab_processing)
        self.file_info_frame.pack(fill="x", pady=(0, 20))
        
        self.file_count_label = ctk.CTkLabel(
            self.file_info_frame, 
            text="No input folder selected", 
            font=ctk.CTkFont(size=14)
        )
        self.file_count_label.pack(pady=20)
        
        # Progress section
        progress_frame = ctk.CTkFrame(self.tab_processing)
        progress_frame.pack(fill="x", pady=(0, 20))
        
        ctk.CTkLabel(progress_frame, text="Processing Progress:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(10, 5))
        
        self.progress_bar = ctk.CTkProgressBar(progress_frame)
        self.progress_bar.pack(fill="x", padx=10, pady=(0, 10))
        self.progress_bar.set(0)
        
        self.progress_label = ctk.CTkLabel(progress_frame, text="Ready to process")
        self.progress_label.pack(pady=(0, 10))
        
        # Control buttons
        button_frame = ctk.CTkFrame(self.tab_processing)
        button_frame.pack(fill="x", pady=(0, 20))
        
        buttons_container = ctk.CTkFrame(button_frame)
        buttons_container.pack(pady=20)
        
        self.scan_btn = ctk.CTkButton(
            buttons_container, 
            text="Scan Files", 
            command=self.scan_files,
            width=120,
            height=40
        )
        self.scan_btn.pack(side="left", padx=(0, 10))
        
        self.process_btn = ctk.CTkButton(
            buttons_container, 
            text="Start Processing", 
            command=self.start_processing,
            width=140,
            height=40,
            fg_color="#28a745",
            hover_color="#218838"
        )
        self.process_btn.pack(side="left", padx=(0, 10))
        
        self.stop_btn = ctk.CTkButton(
            buttons_container, 
            text="Stop", 
            command=self.stop_processing,
            width=100,
            height=40,
            fg_color="#dc3545",
            hover_color="#c82333",
            state="disabled"
        )
        self.stop_btn.pack(side="left", padx=(0, 10))
        
        # Settings management
        settings_frame = ctk.CTkFrame(self.tab_processing)
        settings_frame.pack(fill="x")
        
        settings_container = ctk.CTkFrame(settings_frame)
        settings_container.pack(pady=20)
        
        save_settings_btn = ctk.CTkButton(
            settings_container, 
            text="Save Settings", 
            command=self.save_settings,
            width=120
        )
        save_settings_btn.pack(side="left", padx=(0, 10))
        
        load_settings_btn = ctk.CTkButton(
            settings_container, 
            text="Load Settings", 
            command=self.load_settings_dialog,
            width=120
        )
        load_settings_btn.pack(side="left")
    
    def update_quality_label(self, value):
        """Update quality label when slider changes."""
        self.quality_label.configure(text=f"{int(value)}")
    
    def update_opacity_label(self, value):
        """Update opacity label when slider changes."""
        self.opacity_label.configure(text=f"{value:.1f}")
    
    def update_scale_label(self, value):
        """Update scale label when slider changes."""
        self.scale_label.configure(text=f"{value:.2f}")
    
    def update_tile_size_label(self, value):
        """Update tile size label when slider changes."""
        self.tile_size_label.configure(text=f"{value:.2f}")
    
    def toggle_tiling_mode(self):
        """Toggle visibility of tiling-specific controls."""
        if self.tiling_var.get():
            self.tile_size_frame.pack(fill="x", padx=10, pady=(0, 10))
        else:
            self.tile_size_frame.pack_forget()
    
    def browse_input_folder(self):
        """Browse for input folder."""
        folder = filedialog.askdirectory(title="Select Input Folder")
        if folder:
            self.input_folder_var.set(folder)
            self.scan_files()
    
    def browse_output_folder(self):
        """Browse for output folder."""
        folder = filedialog.askdirectory(title="Select Output Folder")
        if folder:
            self.output_folder_var.set(folder)
    
    def browse_watermark(self):
        """Browse for watermark image."""
        file_path = filedialog.askopenfilename(
            title="Select Watermark Image",
            filetypes=[("PNG files", "*.png"), ("All files", "*.*")]
        )
        if file_path:
            self.watermark_path_var.set(file_path)
    
    def scan_files(self):
        """Scan input folder for supported files."""
        input_folder = self.input_folder_var.get()
        if not input_folder or not os.path.exists(input_folder):
            self.file_count_label.configure(text="Please select a valid input folder")
            return
        
        # Create temporary processor to scan files
        temp_config = self.get_current_config()
        temp_processor = ImageProcessor(temp_config)
        files = temp_processor.get_image_files(input_folder)
        
        if files:
            self.file_count_label.configure(text=f"Found {len(files)} supported files")
        else:
            self.file_count_label.configure(text="No supported files found (PDF, JPG, PNG, BMP, TIFF)")
    
    def get_current_config(self) -> ProcessingConfig:
        """Get current configuration from GUI."""
        return ProcessingConfig(
            input_folder=self.input_folder_var.get(),
            output_folder=self.output_folder_var.get(),
            watermark_path=self.watermark_path_var.get(),
            jpeg_quality=self.quality_var.get(),
            png_compression=6,
            webp_quality=self.quality_var.get(),
            watermark_opacity=self.opacity_var.get(),
            watermark_position=self.position_var.get(),
            watermark_scale=self.scale_var.get(),
            use_tiled_watermark=self.tiling_var.get(),
            tile_size_ratio=self.tile_size_var.get(),
            tile_spacing_ratio=1.6,  # Default spacing
            tile_opacity_reduction=0.7,  # Default reduction
            max_width=self.max_width_var.get(),
            max_height=self.max_height_var.get(),
            output_format=self.format_var.get(),
            preserve_aspect_ratio=self.preserve_aspect_var.get(),
            use_multiprocessing=self.multiprocessing_var.get(),
            max_workers=self.max_workers_var.get() if self.multiprocessing_var.get() else None,
            pdf_dpi=200
        )
    
    def start_processing(self):
        """Start the image processing in a separate thread."""
        if self.is_processing:
            return
        
        # Validate inputs
        config = self.get_current_config()
        if not config.input_folder or not os.path.exists(config.input_folder):
            messagebox.showerror("Error", "Please select a valid input folder")
            return
        
        if not config.output_folder:
            messagebox.showerror("Error", "Please select an output folder")
            return
        
        # Create output folder if it doesn't exist
        os.makedirs(config.output_folder, exist_ok=True)
        
        # Update UI
        self.is_processing = True
        self.process_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.progress_bar.set(0)
        self.progress_label.configure(text="Initializing...")
        
        # Start processing thread
        self.processor = ImageProcessor(config)
        self.processing_thread = threading.Thread(target=self.run_processing)
        self.processing_thread.daemon = True
        self.processing_thread.start()
    
    def run_processing(self):
        """Run the image processing with progress updates."""
        try:
            def progress_callback(current, total):
                progress = current / total
                self.root.after(0, lambda: self.update_progress(progress, current, total))
            
            self.root.after(0, lambda: self.progress_label.configure(text="Processing images..."))
            
            results = self.processor.process_folder(progress_callback)
            
            # Update UI on completion
            self.root.after(0, lambda: self.processing_complete(results))
            
        except Exception as e:
            self.root.after(0, lambda: self.processing_error(str(e)))
    
    def update_progress(self, progress: float, current: int, total: int):
        """Update progress bar and label."""
        self.progress_bar.set(progress)
        self.progress_label.configure(text=f"Processing: {current}/{total} files")
    
    def processing_complete(self, results: dict):
        """Handle processing completion."""
        self.is_processing = False
        self.process_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.progress_bar.set(1.0)
        
        success_count = results.get('processed', 0)
        failed_count = results.get('failed', 0)
        total_count = results.get('total', 0)
        
        self.progress_label.configure(
            text=f"Complete: {success_count} processed, {failed_count} failed"
        )
        
        messagebox.showinfo(
            "Processing Complete",
            f"Processing finished!\n\n"
            f"Successfully processed: {success_count} files\n"
            f"Failed: {failed_count} files\n"
            f"Total: {total_count} files"
        )
    
    def processing_error(self, error_message: str):
        """Handle processing error."""
        self.is_processing = False
        self.process_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.progress_label.configure(text="Error occurred during processing")
        
        messagebox.showerror("Processing Error", f"An error occurred:\n{error_message}")
    
    def stop_processing(self):
        """Stop the current processing (note: this is a graceful request)."""
        if self.is_processing:
            self.is_processing = False
            self.progress_label.configure(text="Stopping...")
            # Note: Actual stopping depends on the processing implementation
    
    def save_settings(self):
        """Save current settings to file."""
        try:
            config = self.get_current_config()
            file_path = filedialog.asksaveasfilename(
                defaultextension=".yaml",
                filetypes=[("YAML files", "*.yaml"), ("All files", "*.*")],
                title="Save Settings"
            )
            if file_path:
                config.save_to_file(file_path)
                messagebox.showinfo("Success", "Settings saved successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings:\n{e}")
    
    def load_settings_dialog(self):
        """Load settings from file."""
        try:
            file_path = filedialog.askopenfilename(
                filetypes=[("YAML files", "*.yaml"), ("All files", "*.*")],
                title="Load Settings"
            )
            if file_path:
                config = ProcessingConfig.load_from_file(file_path)
                self.apply_config(config)
                messagebox.showinfo("Success", "Settings loaded successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load settings:\n{e}")
    
    def apply_config(self, config: ProcessingConfig):
        """Apply configuration to GUI."""
        self.input_folder_var.set(config.input_folder)
        self.output_folder_var.set(config.output_folder)
        self.watermark_path_var.set(config.watermark_path)
        self.format_var.set(config.output_format)
        self.quality_var.set(config.jpeg_quality)
        self.opacity_var.set(config.watermark_opacity)
        self.position_var.set(config.watermark_position)
        self.scale_var.set(config.watermark_scale)
        
        # Tiling settings
        if hasattr(config, 'use_tiled_watermark'):
            self.tiling_var.set(config.use_tiled_watermark)
            self.toggle_tiling_mode()  # Update UI visibility
        if hasattr(config, 'tile_size_ratio'):
            self.tile_size_var.set(config.tile_size_ratio)
        
        self.max_width_var.set(config.max_width)
        self.max_height_var.set(config.max_height)
        self.preserve_aspect_var.set(config.preserve_aspect_ratio)
        self.multiprocessing_var.set(config.use_multiprocessing)
        if config.max_workers:
            self.max_workers_var.set(config.max_workers)
        
        # Update labels
        self.update_quality_label(config.jpeg_quality)
        self.update_opacity_label(config.watermark_opacity)
        self.update_scale_label(config.watermark_scale)
        if hasattr(config, 'tile_size_ratio'):
            self.update_tile_size_label(config.tile_size_ratio)
        
        # Scan files if input folder is set
        if config.input_folder:
            self.scan_files()
    
    def load_settings(self):
        """Load default settings from config file if it exists."""
        config_path = "config/default_settings.yaml"
        if os.path.exists(config_path):
            try:
                config = ProcessingConfig.load_from_file(config_path)
                self.apply_config(config)
            except Exception as e:
                print(f"Failed to load default settings: {e}")
    
    def save_default_settings(self):
        """Save current settings as default."""
        try:
            os.makedirs("config", exist_ok=True)
            config = self.get_current_config()
            config.save_to_file("config/default_settings.yaml")
        except Exception as e:
            print(f"Failed to save default settings: {e}")
    
    def on_closing(self):
        """Handle window closing."""
        self.save_default_settings()
        if self.is_processing:
            if messagebox.askokcancel("Quit", "Processing is in progress. Do you want to quit?"):
                self.is_processing = False
                self.root.destroy()
        else:
            self.root.destroy()
    
    def run(self):
        """Start the GUI application."""
        self.root.mainloop()


if __name__ == "__main__":
    app = ImageProcessorGUI()
    app.run()
