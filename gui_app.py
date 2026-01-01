"""
Modern GUI for Image Processor
============================

A user-friendly interface for the automated image processing system.
Built with CustomTkinter for a modern appearance.

Optimized for Michael J Wright Estate web image processing:
- Resize to 2400px long edge
- sRGB color space, 300 DPI, 100% quality
- Text watermark: "(C) Michael J Wright Estate | All Rights Reserved"
- Output: filename_web.jpg in web_optimized subfolder
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


def get_resource_path(relative_path: str) -> str:
    """Get absolute path to resource, works for dev and for PyInstaller."""
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


# Add src to path for imports
src_path = get_resource_path('src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from image_processor import ImageProcessor, ProcessingConfig

# Set appearance mode and color theme
ctk.set_appearance_mode("dark")  # Modes: "System", "Dark", "Light"
ctk.set_default_color_theme("blue")  # Themes: "blue", "green", "dark-blue"


class ImageProcessorGUI:
    """Modern GUI for the Image Processor application."""
    
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("MJW Estate Web Image Optimizer")
        self.root.geometry("900x750")
        self.root.minsize(800, 650)
        
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
            text="MJW Estate Web Image Optimizer", 
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title_label.pack(pady=(0, 10))
        
        # Subtitle with specs
        subtitle_label = ctk.CTkLabel(
            main_frame, 
            text="2400px long edge • sRGB • 300 DPI • JPEG 100% • © Outlined Watermark", 
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        subtitle_label.pack(pady=(0, 15))
        
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
        """Create basic settings tab - simplified for web optimization."""
        
        # Input folder selection
        input_frame = ctk.CTkFrame(self.tab_basic)
        input_frame.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(input_frame, text="Select Folder with Images:", font=ctk.CTkFont(weight="bold", size=14)).pack(anchor="w", padx=10, pady=(10, 5))
        
        ctk.CTkLabel(input_frame, text="Select a folder containing paintings/images to process for web.", 
                    text_color="gray").pack(anchor="w", padx=10, pady=(0, 5))
        
        input_path_frame = ctk.CTkFrame(input_frame)
        input_path_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        self.input_folder_var = ctk.StringVar()
        self.input_entry = ctk.CTkEntry(input_path_frame, textvariable=self.input_folder_var, placeholder_text="Select input folder...")
        self.input_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self.input_browse_btn = ctk.CTkButton(input_path_frame, text="Browse", command=self.browse_input_folder, width=100)
        self.input_browse_btn.pack(side="right")
        
        # Output info (read-only, shows where files will be saved)
        output_frame = ctk.CTkFrame(self.tab_basic)
        output_frame.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(output_frame, text="Output Location:", font=ctk.CTkFont(weight="bold", size=14)).pack(anchor="w", padx=10, pady=(10, 5))
        
        self.output_info_label = ctk.CTkLabel(
            output_frame, 
            text="Files will be saved to: [input folder]/web_optimized/filename_web.jpg",
            text_color="gray"
        )
        self.output_info_label.pack(anchor="w", padx=10, pady=(0, 10))
        
        # Hidden variables for compatibility (output folder not used in subfolder mode)
        self.output_folder_var = ctk.StringVar()
        self.watermark_path_var = ctk.StringVar()
        
        # Watermark text preview
        watermark_frame = ctk.CTkFrame(self.tab_basic)
        watermark_frame.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(watermark_frame, text="Watermark Text:", font=ctk.CTkFont(weight="bold", size=14)).pack(anchor="w", padx=10, pady=(10, 5))
        
        self.watermark_text_var = ctk.StringVar(value="Michael J Wright Estate | All Rights Reserved")
        self.watermark_text_entry = ctk.CTkEntry(
            watermark_frame, 
            textvariable=self.watermark_text_var, 
            placeholder_text="Enter watermark text..."
        )
        self.watermark_text_entry.pack(fill="x", padx=10, pady=(0, 5))
        
        ctk.CTkLabel(
            watermark_frame, 
            text="This text will be repeated diagonally across each image with light transparency.",
            text_color="gray",
            font=ctk.CTkFont(size=11)
        ).pack(anchor="w", padx=10, pady=(0, 10))
        
        # Quick settings summary
        summary_frame = ctk.CTkFrame(self.tab_basic)
        summary_frame.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(summary_frame, text="Processing Settings:", font=ctk.CTkFont(weight="bold", size=14)).pack(anchor="w", padx=10, pady=(10, 5))
        
        settings_text = """• Resize: 2400px on long edge (paintings optimized)
• Color: sRGB color space
• Resolution: 300 DPI, 100% JPEG quality
• Watermark: White text with dark outline (visible on any background)
• Format: JPEG at 75-80% quality
• Target: < 300 KB per image
• Output: filename_web.jpg in web_optimized subfolder"""
        
        ctk.CTkLabel(
            summary_frame, 
            text=settings_text,
            justify="left",
            font=ctk.CTkFont(size=12)
        ).pack(anchor="w", padx=10, pady=(0, 10))
        
        # Format and quality (keep for compatibility but set defaults)
        self.format_var = ctk.StringVar(value="JPEG")
        self.quality_var = ctk.IntVar(value=100)
        self.quality_label = ctk.CTkLabel(summary_frame, text="77")
    
    def create_advanced_tab(self):
        """Create advanced settings tab - text watermark options."""
        
        # Text watermark settings
        watermark_frame = ctk.CTkFrame(self.tab_advanced)
        watermark_frame.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(watermark_frame, text="Text Watermark Settings:", font=ctk.CTkFont(weight="bold", size=14)).pack(anchor="w", padx=10, pady=(10, 5))
        
        # Opacity (transparency)
        opacity_frame = ctk.CTkFrame(watermark_frame)
        opacity_frame.pack(fill="x", padx=10, pady=(0, 5))
        
        ctk.CTkLabel(opacity_frame, text="Opacity (lower = more subtle):").pack(side="left", padx=(10, 10))
        self.text_opacity_var = ctk.IntVar(value=63)  # 0-255, 63 is ~25%
        opacity_slider = ctk.CTkSlider(opacity_frame, from_=30, to=150, variable=self.text_opacity_var, number_of_steps=120)
        opacity_slider.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self.text_opacity_label = ctk.CTkLabel(opacity_frame, text="63")
        self.text_opacity_label.pack(side="left", padx=(0, 10))
        opacity_slider.configure(command=self.update_text_opacity_label)
        
        # Rotation angle
        rotation_frame = ctk.CTkFrame(watermark_frame)
        rotation_frame.pack(fill="x", padx=10, pady=(0, 5))
        
        ctk.CTkLabel(rotation_frame, text="Rotation Angle:").pack(side="left", padx=(10, 10))
        self.rotation_var = ctk.IntVar(value=-30)
        rotation_slider = ctk.CTkSlider(rotation_frame, from_=-45, to=45, variable=self.rotation_var, number_of_steps=90)
        rotation_slider.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self.rotation_label = ctk.CTkLabel(rotation_frame, text="-30°")
        self.rotation_label.pack(side="left", padx=(0, 10))
        rotation_slider.configure(command=self.update_rotation_label)
        
        # Text spacing
        spacing_frame = ctk.CTkFrame(watermark_frame)
        spacing_frame.pack(fill="x", padx=10, pady=(0, 5))
        
        ctk.CTkLabel(spacing_frame, text="Text Spacing:").pack(side="left", padx=(10, 10))
        self.text_spacing_var = ctk.DoubleVar(value=-0.3)
        spacing_slider = ctk.CTkSlider(spacing_frame, from_=-0.5, to=0.5, variable=self.text_spacing_var, number_of_steps=20)
        spacing_slider.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self.text_spacing_label = ctk.CTkLabel(spacing_frame, text="-0.3")
        self.text_spacing_label.pack(side="left", padx=(0, 10))
        spacing_slider.configure(command=self.update_text_spacing_label)
        
        # Font size
        font_frame = ctk.CTkFrame(watermark_frame)
        font_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        ctk.CTkLabel(font_frame, text="Font Size Ratio:").pack(side="left", padx=(10, 10))
        self.font_size_var = ctk.DoubleVar(value=0.015)
        font_slider = ctk.CTkSlider(font_frame, from_=0.010, to=0.05, variable=self.font_size_var, number_of_steps=40)
        font_slider.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self.font_size_label = ctk.CTkLabel(font_frame, text="0.015")
        self.font_size_label.pack(side="left", padx=(0, 10))
        font_slider.configure(command=self.update_font_size_label)
        
        # Image size settings
        size_frame = ctk.CTkFrame(self.tab_advanced)
        size_frame.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(size_frame, text="Image Size Settings:", font=ctk.CTkFont(weight="bold", size=14)).pack(anchor="w", padx=10, pady=(10, 5))
        
        dimensions_frame = ctk.CTkFrame(size_frame)
        dimensions_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        # Long edge pixels
        ctk.CTkLabel(dimensions_frame, text="Long Edge (px):").pack(side="left", padx=(10, 10))
        self.long_edge_var = ctk.IntVar(value=2400)
        long_edge_entry = ctk.CTkEntry(dimensions_frame, textvariable=self.long_edge_var, width=100)
        long_edge_entry.pack(side="left", padx=(0, 20))
        
        # Target file size
        ctk.CTkLabel(dimensions_frame, text="Target Max KB:").pack(side="left", padx=(0, 10))
        self.target_size_var = ctk.IntVar(value=5000)
        target_size_entry = ctk.CTkEntry(dimensions_frame, textvariable=self.target_size_var, width=100)
        target_size_entry.pack(side="left", padx=(0, 10))
        
        # Output subfolder name
        subfolder_frame = ctk.CTkFrame(size_frame)
        subfolder_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        ctk.CTkLabel(subfolder_frame, text="Output Subfolder:").pack(side="left", padx=(10, 10))
        self.subfolder_var = ctk.StringVar(value="web_optimized")
        subfolder_entry = ctk.CTkEntry(subfolder_frame, textvariable=self.subfolder_var, width=200)
        subfolder_entry.pack(side="left", padx=(0, 10))
        
        ctk.CTkLabel(subfolder_frame, text="File Suffix:").pack(side="left", padx=(10, 10))
        self.suffix_var = ctk.StringVar(value="_web")
        suffix_entry = ctk.CTkEntry(subfolder_frame, textvariable=self.suffix_var, width=100)
        suffix_entry.pack(side="left", padx=(0, 10))
        
        # Hidden variables for compatibility
        self.opacity_var = ctk.DoubleVar(value=0.1)
        self.position_var = ctk.StringVar(value="center")
        self.scale_var = ctk.DoubleVar(value=0.2)
        self.tiling_var = ctk.BooleanVar(value=True)
        self.tile_size_var = ctk.DoubleVar(value=0.18)
        self.max_width_var = ctk.IntVar(value=1920)
        self.max_height_var = ctk.IntVar(value=1080)
        self.preserve_aspect_var = ctk.BooleanVar(value=True)
        self.multiprocessing_var = ctk.BooleanVar(value=True)
        self.max_workers_var = ctk.IntVar(value=4)
        self.opacity_label = ctk.CTkLabel(size_frame, text="0.1")
        self.scale_label = ctk.CTkLabel(size_frame, text="0.2")
        self.tile_size_label = ctk.CTkLabel(size_frame, text="0.18")
    
    def update_text_opacity_label(self, value):
        """Update text opacity label when slider changes."""
        self.text_opacity_label.configure(text=f"{int(value)}")
    
    def update_rotation_label(self, value):
        """Update rotation label when slider changes."""
        self.rotation_label.configure(text=f"{int(value)}°")
    
    def update_text_spacing_label(self, value):
        """Update text spacing label when slider changes."""
        self.text_spacing_label.configure(text=f"{value:.1f}")
    
    def update_font_size_label(self, value):
        """Update font size label when slider changes."""
        self.font_size_label.configure(text=f"{value:.3f}")
    
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
        """Update opacity label when slider changes (compatibility)."""
        pass  # Not used in simplified UI
    
    def update_scale_label(self, value):
        """Update scale label when slider changes (compatibility)."""
        pass  # Not used in simplified UI
    
    def update_tile_size_label(self, value):
        """Update tile size label when slider changes (compatibility)."""
        pass  # Not used in simplified UI
    
    def toggle_tiling_mode(self):
        """Toggle visibility of tiling-specific controls (compatibility)."""
        pass  # Not used in simplified UI
    
    def browse_input_folder(self):
        """Browse for input folder."""
        folder = filedialog.askdirectory(title="Select Folder with Images")
        if folder:
            self.input_folder_var.set(folder)
            # Update output info label
            subfolder = self.subfolder_var.get() if hasattr(self, 'subfolder_var') else "web_optimized"
            suffix = self.suffix_var.get() if hasattr(self, 'suffix_var') else "_web"
            self.output_info_label.configure(
                text=f"Files will be saved to: {folder}/{subfolder}/filename{suffix}.jpg"
            )
            self.scan_files()
    
    def browse_output_folder(self):
        """Browse for output folder (not used in simplified mode)."""
        folder = filedialog.askdirectory(title="Select Output Folder")
        if folder:
            self.output_folder_var.set(folder)
    
    def browse_watermark(self):
        """Browse for watermark image (not used in text watermark mode)."""
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
        """Get current configuration from GUI - optimized for web processing."""
        return ProcessingConfig(
            input_folder=self.input_folder_var.get(),
            output_folder=self.output_folder_var.get() if self.output_folder_var.get() else self.input_folder_var.get(),
            watermark_path=self.watermark_path_var.get(),
            
            # JPEG quality settings
            jpeg_quality=self.quality_var.get(),
            png_compression=6,
            webp_quality=self.quality_var.get(),
            target_max_size_kb=self.target_size_var.get(),
            
            # Text watermark settings (primary mode)
            use_text_watermark=True,
            watermark_text=self.watermark_text_var.get(),
            text_font_size_ratio=self.font_size_var.get(),
            text_watermark_opacity=self.text_opacity_var.get(),
            text_rotation_angle=self.rotation_var.get(),
            text_spacing_ratio=self.text_spacing_var.get(),
            
            # Image watermark settings (for compatibility)
            watermark_opacity=self.opacity_var.get(),
            watermark_position=self.position_var.get(),
            watermark_scale=self.scale_var.get(),
            use_tiled_watermark=self.tiling_var.get(),
            tile_size_ratio=self.tile_size_var.get(),
            tile_spacing_ratio=1.6,
            tile_opacity_reduction=0.7,
            
            # Web optimization settings
            long_edge_pixels=self.long_edge_var.get(),
            output_dpi=300,
            convert_to_srgb=True,
            web_output_suffix=self.suffix_var.get(),
            create_subfolder=True,
            subfolder_name=self.subfolder_var.get(),
            
            # Size and format settings
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
        
        # In subfolder mode, output folder is not required
        # (files will be saved to input_folder/web_optimized/)
        
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
                if not self.is_processing:
                    return False  # Signal to stop
                progress = current / total
                # Use default args to capture current values, not references
                self.root.after(0, lambda p=progress, c=current, t=total: self.update_progress(p, c, t))
                return True  # Continue processing
            
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
        
        success_count = results.get('processed', 0)
        failed_count = results.get('failed', 0)
        total_count = results.get('total', 0)
        was_stopped = results.get('stopped', False)
        
        if was_stopped:
            self.progress_label.configure(
                text=f"Stopped: {success_count} processed before stopping"
            )
            messagebox.showinfo(
                "Processing Stopped",
                f"Processing was stopped by user.\n\n"
                f"Processed before stopping: {success_count} files\n"
                f"Failed: {failed_count} files"
            )
        else:
            self.progress_bar.set(1.0)
            self.progress_label.configure(
                text=f"Complete: {success_count} processed, {failed_count} failed"
            )
        
        # Get output location for message
        input_folder = self.input_folder_var.get()
        subfolder = self.subfolder_var.get() if hasattr(self, 'subfolder_var') else "web_optimized"
        output_location = os.path.join(input_folder, subfolder)
        
        messagebox.showinfo(
            "Processing Complete",
            f"Web optimization finished!\n\n"
            f"Successfully processed: {success_count} files\n"
            f"Failed: {failed_count} files\n"
            f"Total: {total_count} files\n\n"
            f"Output saved to:\n{output_location}"
        )
    
    def processing_error(self, error_message: str):
        """Handle processing error."""
        self.is_processing = False
        self.process_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.progress_label.configure(text="Error occurred during processing")
        
        messagebox.showerror("Processing Error", f"An error occurred:\n{error_message}")
    
    def stop_processing(self):
        """Stop the current processing."""
        if self.is_processing:
            self.is_processing = False
            self.progress_label.configure(text="Stopping after current file...")
            self.stop_btn.configure(state="disabled")
    
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
        
        # Text watermark settings
        if hasattr(config, 'watermark_text') and hasattr(self, 'watermark_text_var'):
            self.watermark_text_var.set(config.watermark_text)
        if hasattr(config, 'text_watermark_opacity') and hasattr(self, 'text_opacity_var'):
            self.text_opacity_var.set(config.text_watermark_opacity)
        if hasattr(config, 'text_rotation_angle') and hasattr(self, 'rotation_var'):
            self.rotation_var.set(config.text_rotation_angle)
        if hasattr(config, 'text_spacing_ratio') and hasattr(self, 'text_spacing_var'):
            self.text_spacing_var.set(config.text_spacing_ratio)
        if hasattr(config, 'text_font_size_ratio') and hasattr(self, 'font_size_var'):
            self.font_size_var.set(config.text_font_size_ratio)
        
        # Web optimization settings
        if hasattr(config, 'long_edge_pixels') and hasattr(self, 'long_edge_var'):
            self.long_edge_var.set(config.long_edge_pixels)
        if hasattr(config, 'target_max_size_kb') and hasattr(self, 'target_size_var'):
            self.target_size_var.set(config.target_max_size_kb)
        if hasattr(config, 'subfolder_name') and hasattr(self, 'subfolder_var'):
            self.subfolder_var.set(config.subfolder_name)
        if hasattr(config, 'web_output_suffix') and hasattr(self, 'suffix_var'):
            self.suffix_var.set(config.web_output_suffix)
        
        # Legacy settings (for compatibility)
        self.opacity_var.set(config.watermark_opacity)
        self.position_var.set(config.watermark_position)
        self.scale_var.set(config.watermark_scale)
        
        if hasattr(config, 'use_tiled_watermark'):
            self.tiling_var.set(config.use_tiled_watermark)
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
        if hasattr(self, 'text_opacity_label') and hasattr(config, 'text_watermark_opacity'):
            self.update_text_opacity_label(config.text_watermark_opacity)
        if hasattr(self, 'rotation_label') and hasattr(config, 'text_rotation_angle'):
            self.update_rotation_label(config.text_rotation_angle)
        if hasattr(self, 'text_spacing_label') and hasattr(config, 'text_spacing_ratio'):
            self.update_text_spacing_label(config.text_spacing_ratio)
        if hasattr(self, 'font_size_label') and hasattr(config, 'text_font_size_ratio'):
            self.update_font_size_label(config.text_font_size_ratio)
        
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
    # Required for PyInstaller + multiprocessing on Windows
    import multiprocessing
    multiprocessing.freeze_support()
    
    app = ImageProcessorGUI()
    app.run()
