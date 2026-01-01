"""
Advanced Image Processor with Watermarking and Web Optimization
=============================================================

A comprehensive solution for automated image processing with the following features:
- Batch processing of PDF, JPG, TIFF, and BMP files
- Transparent watermark application
- Web-optimized output with configurable compression
- Azure cloud integration
- Power Platform Automate workflows
- Modern GUI and command-line interfaces

Author: GitHub Copilot
Date: July 2025
"""

import os
import sys
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
import logging
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import multiprocessing as mp

# Core image processing
from PIL import Image, ImageEnhance, ImageOps, ImageDraw, ImageFont, ImageCms
import cv2
import numpy as np
import io

# PDF processing
import fitz  # PyMuPDF
from pdf2image import convert_from_path

# Progress tracking
from tqdm import tqdm

# Configuration
import yaml
from dataclasses import dataclass, asdict
import json

# Logging setup
from loguru import logger

# Setup logging
logger.add("logs/image_processor_{time}.log", rotation="1 day", retention="30 days")


@dataclass
class ProcessingConfig:
    """Configuration class for image processing settings."""
    
    # Input/Output settings
    input_folder: str = ""
    output_folder: str = ""
    watermark_path: str = ""
    
    # Image quality settings
    jpeg_quality: int = 100  # Maximum quality - crisp watermark is priority
    png_compression: int = 6
    webp_quality: int = 100
    target_max_size_kb: int = 5000  # No real limit - quality is priority
    preserve_metadata: bool = True  # Preserve EXIF and other metadata from original
    
    # Watermark settings
    watermark_opacity: float = 0.3
    watermark_position: str = "bottom-right"  # Options: center, top-left, top-right, bottom-left, bottom-right
    watermark_scale: float = 0.2  # Scale relative to image size
    
    # Tiled watermark settings
    use_tiled_watermark: bool = True  # Use tiled pattern instead of single watermark
    tile_size_ratio: float = 0.2  # Size of each tile relative to image width
    tile_spacing_ratio: float = 1.5  # Spacing between tiles (multiplier of tile size)
    tile_opacity_reduction: float = 0.7  # Reduce opacity for tiled watermarks
    
    # Text watermark settings (for Michael J Wright Estate)
    use_text_watermark: bool = True  # Use text-based watermark instead of image
    watermark_text: str = "Michael J Wright Estate | All Rights Reserved"
    text_font_size_ratio: float = 0.015  # Small font (~36px on 2400px)
    text_watermark_opacity: int = 63  # Grey at ~25% opacity
    text_watermark_color: tuple = (128, 128, 128)  # Medium grey - visible on light and dark
    text_rotation_angle: int = -30  # Diagonal rotation angle
    text_spacing_ratio: float = -0.3  # Overlap tiles for denser coverage (negative = overlap)
    use_text_outline: bool = False  # No outline - clean single color
    text_outline_width: int = 0  # No outline
    text_outline_color: tuple = (0, 0, 0, 0)  # Disabled
    
    # Web optimization settings
    long_edge_pixels: int = 2400  # Resize to this on long edge (larger for legible watermark)
    output_dpi: int = 300  # High DPI for crisp text
    convert_to_srgb: bool = True  # Convert to sRGB color space
    web_output_suffix: str = "_web"  # Suffix for output files
    create_subfolder: bool = True  # Create output subfolder in source folder
    subfolder_name: str = "web_optimized"  # Name of output subfolder
    
    # Processing settings
    max_width: int = 1920
    max_height: int = 1080
    output_format: str = "JPEG"  # Options: JPEG, PNG, WEBP
    preserve_aspect_ratio: bool = True
    
    # Performance settings
    use_multiprocessing: bool = False  # Disabled - causes issues with PyInstaller GUI
    max_workers: Optional[int] = None
    
    # PDF settings
    pdf_dpi: int = 200
    
    def save_to_file(self, filepath: str) -> None:
        """Save configuration to YAML file."""
        with open(filepath, 'w') as f:
            yaml.dump(asdict(self), f, default_flow_style=False)
    
    @classmethod
    def load_from_file(cls, filepath: str) -> 'ProcessingConfig':
        """Load configuration from YAML file."""
        with open(filepath, 'r') as f:
            data = yaml.safe_load(f)
        return cls(**data)


class ImageProcessor:
    """Advanced image processor with watermarking and optimization capabilities."""
    
    def __init__(self, config: ProcessingConfig):
        self.config = config
        self.supported_formats = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.pdf'}
        self.watermark_image = None
        
        # Load watermark if specified
        if config.watermark_path and os.path.exists(config.watermark_path):
            self.load_watermark(config.watermark_path)
        
        # Setup output directory
        os.makedirs(config.output_folder, exist_ok=True)
        os.makedirs("logs", exist_ok=True)
    
    def load_watermark(self, watermark_path: str) -> None:
        """Load and prepare watermark image."""
        try:
            self.watermark_image = Image.open(watermark_path).convert("RGBA")
            logger.info(f"Loaded watermark: {watermark_path}")
        except Exception as e:
            logger.error(f"Failed to load watermark: {e}")
            self.watermark_image = None
    
    def apply_text_watermark(self, image: Image.Image) -> Image.Image:
        """Apply repeating text watermark across the entire image with transparency.
        
        The watermark uses '© Michael J Wright Estate - Property of' text
        repeated diagonally across the image at low opacity so it's visible
        at high magnification but doesn't interrupt the image at normal view.
        """
        try:
            # Ensure image is in RGBA mode for transparency
            if image.mode != 'RGBA':
                image = image.convert('RGBA')
            
            img_width, img_height = image.size
            
            # Calculate font size based on image dimensions
            font_size = max(int(img_width * self.config.text_font_size_ratio), 12)
            
            # Try to load a font, fall back to default
            try:
                # Try modern crisp fonts first (Segoe UI is clean and modern)
                font_paths = [
                    "C:/Windows/Fonts/segoeui.ttf",  # Modern Windows font - crisp and clean
                    "C:/Windows/Fonts/calibri.ttf",  # Clean sans-serif
                    "C:/Windows/Fonts/arial.ttf",    # Fallback
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                    "/System/Library/Fonts/Helvetica.ttc",
                ]
                font = None
                for font_path in font_paths:
                    if os.path.exists(font_path):
                        font = ImageFont.truetype(font_path, font_size)
                        logger.debug(f"Using font: {font_path}")
                        break
                if font is None:
                    font = ImageFont.load_default()
            except Exception:
                font = ImageFont.load_default()
            
            # Create a temporary image to measure text size
            temp_img = Image.new('RGBA', (1, 1), (0, 0, 0, 0))
            temp_draw = ImageDraw.Draw(temp_img)
            
            # Get text bounding box - prepend hardcoded copyright symbol
            text = "\u00A9 " + self.config.watermark_text
            bbox = temp_draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            # Create watermark overlay for single text block (will be rotated)
            # Make it bigger to account for rotation and outline
            padding = 80
            single_text_img = Image.new('RGBA', (text_width + padding * 2, text_height + padding * 2), (0, 0, 0, 0))
            draw = ImageDraw.Draw(single_text_img)
            
            # Get opacity and color settings
            opacity = self.config.text_watermark_opacity
            
            # Get watermark color (default to grey if not set)
            text_color = getattr(self.config, 'text_watermark_color', (128, 128, 128))
            if isinstance(text_color, list):
                text_color = tuple(text_color)
            # Add opacity as alpha channel
            fill_color = (*text_color[:3], opacity)
            
            # Draw text with outline for visibility on any background (if enabled)
            if self.config.use_text_outline and self.config.text_outline_width > 0:
                outline_width = self.config.text_outline_width
                outline_color = self.config.text_outline_color
                # Convert list to tuple if needed (for YAML compatibility)
                if isinstance(outline_color, list):
                    outline_color = tuple(outline_color)
                
                # Draw outline by rendering text multiple times offset in all directions
                for dx in range(-outline_width, outline_width + 1):
                    for dy in range(-outline_width, outline_width + 1):
                        if dx != 0 or dy != 0:  # Skip center position
                            draw.text((padding + dx, padding + dy), text, font=font, fill=outline_color)
            
            # Draw main text (grey or configured color)
            draw.text((padding, padding), text, font=font, fill=fill_color)
            
            # Rotate the text block
            rotated_text = single_text_img.rotate(
                self.config.text_rotation_angle, 
                expand=True, 
                resample=Image.Resampling.BICUBIC
            )
            
            # Get rotated dimensions
            rotated_width, rotated_height = rotated_text.size
            
            # Calculate spacing between watermarks
            # spacing_ratio is the GAP between tiles as a fraction of tile size
            # Total step = tile size + gap
            gap_x = int(rotated_width * self.config.text_spacing_ratio)
            gap_y = int(rotated_height * self.config.text_spacing_ratio)
            spacing_x = rotated_width + gap_x
            spacing_y = rotated_height + gap_y
            
            # Create the full overlay
            overlay = Image.new('RGBA', image.size, (0, 0, 0, 0))
            
            # Tile the rotated text across the entire image
            # Start from negative positions to ensure full coverage
            start_x = -rotated_width
            start_y = -rotated_height
            
            tiles_placed = 0
            y = start_y
            row = 0
            while y < img_height + rotated_height:
                x = start_x
                # Offset every other row for diagonal pattern
                if row % 2 == 1:
                    x += spacing_x // 2
                
                while x < img_width + rotated_width:
                    overlay.paste(rotated_text, (x, y), rotated_text)
                    tiles_placed += 1
                    x += spacing_x
                
                y += spacing_y
                row += 1
            
            # Composite the watermark onto the image
            result = Image.alpha_composite(image, overlay)
            
            logger.info(f"Applied text watermark: '{text}' - {tiles_placed} tiles at {opacity}/255 opacity")
            return result
            
        except Exception as e:
            logger.error(f"Failed to apply text watermark: {e}")
            import traceback
            traceback.print_exc()
            return image
    
    def apply_watermark(self, image: Image.Image) -> Image.Image:
        """Apply watermark to image - text watermark, tiled pattern, or single positioned watermark."""
        # Use text watermark if configured (primary mode for Michael J Wright Estate)
        if self.config.use_text_watermark:
            return self.apply_text_watermark(image)
        
        # Otherwise use image-based watermark if available
        if not self.watermark_image:
            return image
        
        if self.config.use_tiled_watermark:
            return self.apply_tiled_watermark(image)
        else:
            return self.apply_single_watermark(image)
    
    def apply_tiled_watermark(self, image: Image.Image) -> Image.Image:
        """Apply tiled watermark pattern across the entire image."""
        try:
            # Ensure image is in RGBA mode for transparency
            if image.mode != 'RGBA':
                image = image.convert('RGBA')
            
            # Calculate watermark size for tiling
            img_width, img_height = image.size
            
            # Use configurable tile size
            tile_width = int(img_width * self.config.tile_size_ratio)
            tile_height = int(tile_width * self.watermark_image.height / self.watermark_image.width)
            
            # Resize watermark for tiling
            watermark_tile = self.watermark_image.resize((tile_width, tile_height), Image.Resampling.LANCZOS)
            
            # Adjust opacity for tiled watermark
            opacity = self.config.watermark_opacity * self.config.tile_opacity_reduction
            if opacity < 1.0:
                # Create a new image with adjusted alpha
                watermark_with_opacity = Image.new('RGBA', watermark_tile.size, (0, 0, 0, 0))
                for x in range(watermark_tile.width):
                    for y in range(watermark_tile.height):
                        r, g, b, a = watermark_tile.getpixel((x, y))
                        a = int(a * opacity)
                        watermark_with_opacity.putpixel((x, y), (r, g, b, a))
                watermark_tile = watermark_with_opacity
            
            # Create a transparent overlay for the entire image
            overlay = Image.new('RGBA', image.size, (0, 0, 0, 0))
            
            # Calculate spacing between tiles
            spacing_x = int(tile_width * self.config.tile_spacing_ratio)
            spacing_y = int(tile_height * self.config.tile_spacing_ratio)
            
            # Tile the watermark across the entire image
            tiles_placed = 0
            for x in range(0, img_width + spacing_x, spacing_x):
                for y in range(0, img_height + spacing_y, spacing_y):
                    # Add some offset to alternate rows for better coverage
                    offset_x = (spacing_x // 2) if (y // spacing_y) % 2 == 1 else 0
                    pos_x = x + offset_x
                    pos_y = y
                    
                    # Only paste if the watermark will be at least partially visible
                    if pos_x < img_width and pos_y < img_height:
                        overlay.paste(watermark_tile, (pos_x, pos_y), watermark_tile)
                        tiles_placed += 1
            
            # Composite the images
            result = Image.alpha_composite(image, overlay)
            
            logger.info(f"Applied tiled watermark pattern: {tiles_placed} tiles with {opacity:.2f} opacity")
            return result
            
        except Exception as e:
            logger.error(f"Failed to apply tiled watermark: {e}")
            return image
    
    def apply_single_watermark(self, image: Image.Image) -> Image.Image:
        """Apply single watermark at specified position."""
        try:
            # Ensure image is in RGBA mode for transparency
            if image.mode != 'RGBA':
                image = image.convert('RGBA')
            
            # Calculate watermark size
            img_width, img_height = image.size
            watermark_width = int(img_width * self.config.watermark_scale)
            watermark_height = int(watermark_width * self.watermark_image.height / self.watermark_image.width)
            
            # Resize watermark
            watermark = self.watermark_image.resize((watermark_width, watermark_height), Image.Resampling.LANCZOS)
            
            # Adjust opacity
            if self.config.watermark_opacity < 1.0:
                # Create a new image with adjusted alpha
                watermark_with_opacity = Image.new('RGBA', watermark.size, (0, 0, 0, 0))
                for x in range(watermark.width):
                    for y in range(watermark.height):
                        r, g, b, a = watermark.getpixel((x, y))
                        a = int(a * self.config.watermark_opacity)
                        watermark_with_opacity.putpixel((x, y), (r, g, b, a))
                watermark = watermark_with_opacity
            
            # Calculate position
            position = self.calculate_watermark_position(img_width, img_height, watermark_width, watermark_height)
            
            # Create a transparent overlay
            overlay = Image.new('RGBA', image.size, (0, 0, 0, 0))
            overlay.paste(watermark, position, watermark)
            
            # Composite the images
            result = Image.alpha_composite(image, overlay)
            
            logger.info(f"Applied single watermark at {self.config.watermark_position} with {self.config.watermark_opacity:.2f} opacity")
            return result
            
        except Exception as e:
            logger.error(f"Failed to apply single watermark: {e}")
            return image
    
    def calculate_watermark_position(self, img_width: int, img_height: int, 
                                   watermark_width: int, watermark_height: int) -> Tuple[int, int]:
        """Calculate watermark position based on configuration."""
        positions = {
            'center': ((img_width - watermark_width) // 2, (img_height - watermark_height) // 2),
            'top-left': (20, 20),
            'top-right': (img_width - watermark_width - 20, 20),
            'bottom-left': (20, img_height - watermark_height - 20),
            'bottom-right': (img_width - watermark_width - 20, img_height - watermark_height - 20)
        }
        return positions.get(self.config.watermark_position, positions['bottom-right'])
    
    def resize_for_web(self, image: Image.Image) -> Image.Image:
        """Resize image for web optimization.
        
        Resizes to configured long edge (default 1200px) while preserving aspect ratio.
        This is optimized for paintings/artwork display on the web.
        """
        width, height = image.size
        long_edge = self.config.long_edge_pixels
        
        # Determine which dimension is the long edge
        if width >= height:
            # Landscape or square - width is long edge
            if width <= long_edge:
                return image  # No resize needed
            
            scale = long_edge / width
            new_width = long_edge
            new_height = int(height * scale)
        else:
            # Portrait - height is long edge
            if height <= long_edge:
                return image  # No resize needed
            
            scale = long_edge / height
            new_height = long_edge
            new_width = int(width * scale)
        
        resized = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        logger.info(f"Resized image: {width}x{height} -> {new_width}x{new_height} (long edge: {long_edge}px)")
        return resized
    
    def process_pdf(self, pdf_path: str) -> List[Image.Image]:
        """Convert PDF pages to images."""
        try:
            images = convert_from_path(pdf_path, dpi=self.config.pdf_dpi)
            logger.info(f"Converted PDF to {len(images)} images: {pdf_path}")
            return images
        except Exception as e:
            logger.error(f"Failed to process PDF {pdf_path}: {e}")
            return []
    
    def process_single_image(self, input_path: str, output_path: str) -> bool:
        """Process a single image file with watermarking and optimization."""
        try:
            file_ext = Path(input_path).suffix.lower()
            
            if file_ext == '.pdf':
                # Process PDF pages
                images = self.process_pdf(input_path)
                if not images:
                    return False
                
                # Process each page
                base_name = Path(output_path).stem
                output_dir = Path(output_path).parent
                
                for i, image in enumerate(images):
                    page_output_path = output_dir / f"{base_name}_page_{i+1:03d}.{self.config.output_format.lower()}"
                    
                    # Apply processing - resize FIRST, then watermark
                    # This ensures watermark text is correctly sized for the final output
                    processed_image = self.resize_for_web(image)
                    processed_image = self.apply_watermark(processed_image)
                    
                    # Convert to RGB if saving as JPEG
                    if self.config.output_format.upper() == 'JPEG' and processed_image.mode == 'RGBA':
                        processed_image = processed_image.convert('RGB')
                    
                    # Save with appropriate settings
                    self.save_optimized_image(processed_image, str(page_output_path))
                
                return True
            
            else:
                # Process regular image
                with Image.open(input_path) as image:
                    # Extract comprehensive metadata from original
                    orig_format = image.format or Path(input_path).suffix.upper().replace('.', '')
                    orig_mode = image.mode
                    orig_size = image.size
                    
                    # Extract EXIF data if available
                    orig_exif = None
                    try:
                        orig_exif = image.getexif()
                        if orig_exif:
                            logger.info(f"Original EXIF tags: {len(orig_exif)} entries")
                    except Exception:
                        pass
                    
                    # Extract ICC color profile
                    orig_icc_profile = image.info.get('icc_profile')
                    if orig_icc_profile:
                        logger.info(f"Original ICC profile: {len(orig_icc_profile)} bytes")
                    
                    # Extract other metadata
                    orig_dpi = image.info.get('dpi', (72, 72))
                    orig_info = {k: v for k, v in image.info.items() if k not in ('exif', 'icc_profile')}
                    
                    logger.info(f"Original: {orig_size[0]}x{orig_size[1]} {orig_format} ({orig_mode})")
                    logger.info(f"Original DPI: {orig_dpi}, Info keys: {list(orig_info.keys())}")
                    
                    # Store metadata for later use in save
                    self._current_orig_exif = orig_exif
                    self._current_orig_icc = orig_icc_profile
                    
                    # Keep as much original quality as possible during processing
                    # Work in RGB/RGBA to avoid multiple conversions
                    if image.mode not in ('RGB', 'RGBA'):
                        image = image.convert('RGB')
                    
                    # Resize for web FIRST (uses LANCZOS for best quality)
                    processed_image = self.resize_for_web(image)
                    
                    # Apply watermark AFTER resize (so text is correctly sized)
                    processed_image = self.apply_watermark(processed_image)
                    
                    # Convert to RGB if saving as JPEG
                    if self.config.output_format.upper() == 'JPEG' and processed_image.mode == 'RGBA':
                        processed_image = processed_image.convert('RGB')
                    
                    # Save optimized image (with preserved metadata)
                    self.save_optimized_image(processed_image, output_path)
                    
                    # Clear stored metadata
                    self._current_orig_exif = None
                    self._current_orig_icc = None
                    
                    return True
                    
        except Exception as e:
            logger.error(f"Failed to process {input_path}: {e}")
            return False
    
    def save_optimized_image(self, image: Image.Image, output_path: str) -> None:
        """Save image with optimized settings for web.
        
        Includes:
        - sRGB color space conversion
        - 72 DPI for web
        - JPEG at 75-80% quality targeting < 300KB
        """
        format_upper = self.config.output_format.upper()
        
        # Convert to sRGB color space if configured
        if self.config.convert_to_srgb:
            image = self._convert_to_srgb(image)
        
        # Convert to RGB if saving as JPEG (remove alpha channel)
        if format_upper == 'JPEG' and image.mode in ('RGBA', 'P', 'LA'):
            # Create white background for transparency
            background = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'P':
                image = image.convert('RGBA')
            if image.mode in ('RGBA', 'LA'):
                background.paste(image, mask=image.split()[-1])
                image = background
            else:
                image = image.convert('RGB')
        
        # Set DPI metadata
        dpi = (self.config.output_dpi, self.config.output_dpi)
        
        if format_upper == 'JPEG':
            # Try to hit target file size < 300KB with quality adjustment
            image = self._save_jpeg_optimized(image, output_path, dpi)
        elif format_upper == 'PNG':
            image.save(output_path, 'PNG', 
                      compress_level=self.config.png_compression, 
                      optimize=True,
                      dpi=dpi)
        elif format_upper == 'WEBP':
            image.save(output_path, 'WEBP', 
                      quality=self.config.webp_quality, 
                      optimize=True)
        else:
            image.save(output_path, optimize=True, dpi=dpi)
    
    def _convert_to_srgb(self, image: Image.Image) -> Image.Image:
        """Convert image to sRGB color space."""
        try:
            # Check if image has an ICC profile
            if 'icc_profile' in image.info:
                # Get the embedded profile
                icc_profile = image.info.get('icc_profile')
                if icc_profile:
                    # Create sRGB profile
                    srgb_profile = ImageCms.createProfile('sRGB')
                    
                    # Convert from embedded profile to sRGB
                    try:
                        input_profile = ImageCms.ImageCmsProfile(io.BytesIO(icc_profile))
                        # Ensure we're in the right mode for the transform
                        if image.mode == 'RGBA':
                            image_rgb = image.convert('RGB')
                            image_rgb = ImageCms.profileToProfile(
                                image_rgb, input_profile, srgb_profile,
                                outputMode='RGB'
                            )
                            # Preserve alpha
                            r, g, b = image_rgb.split()
                            a = image.split()[3]
                            image = Image.merge('RGBA', (r, g, b, a))
                        elif image.mode in ('RGB', 'L'):
                            image = ImageCms.profileToProfile(
                                image, input_profile, srgb_profile,
                                outputMode='RGB' if image.mode == 'RGB' else 'L'
                            )
                        logger.debug("Converted image to sRGB color space")
                    except Exception as e:
                        logger.debug(f"Could not convert color profile: {e}")
            
            return image
        except Exception as e:
            logger.debug(f"sRGB conversion skipped: {e}")
            return image
    
    def _save_jpeg_optimized(self, image: Image.Image, output_path: str, dpi: tuple) -> Image.Image:
        """Save JPEG with maximum quality for crisp watermark text.
        
        Uses 4:4:4 subsampling to preserve watermark text sharpness.
        Preserves EXIF metadata from original if available.
        """
        target_size_kb = self.config.target_max_size_kb
        quality = self.config.jpeg_quality
        min_quality = 85  # Higher minimum - quality is priority
        
        # Use 4:4:4 subsampling (no chroma subsampling) to keep text sharp
        # This preserves fine detail like watermark text better than default 4:2:0
        subsampling = 0  # 0 = 4:4:4, 1 = 4:2:2, 2 = 4:2:0
        
        # Build save parameters
        save_params = {
            'quality': quality,
            'optimize': True,
            'dpi': dpi,
            'subsampling': subsampling
        }
        
        # Preserve EXIF metadata if configured and available
        if self.config.preserve_metadata:
            orig_exif = getattr(self, '_current_orig_exif', None)
            if orig_exif:
                save_params['exif'] = orig_exif
                logger.info("Preserving original EXIF metadata")
        
        # First attempt at configured quality
        buffer = io.BytesIO()
        image.save(buffer, 'JPEG', **save_params)
        size_kb = buffer.tell() / 1024
        
        # If already under target, save directly (likely with 100% quality)
        if size_kb <= target_size_kb:
            image.save(output_path, 'JPEG', **save_params)
            logger.info(f"Saved {output_path}: {size_kb:.1f}KB at quality {quality}")
            return image
        
        # Otherwise, reduce quality until we hit target (rarely needed at 5MB limit)
        while size_kb > target_size_kb and quality > min_quality:
            quality -= 3
            save_params['quality'] = quality
            buffer = io.BytesIO()
            image.save(buffer, 'JPEG', **save_params)
            size_kb = buffer.tell() / 1024
        
        # Save with final quality
        image.save(output_path, 'JPEG', **save_params)
        logger.info(f"Saved {output_path}: {size_kb:.1f}KB at quality {quality}")
        
        return image
    
    def get_image_files(self, folder_path: str) -> List[str]:
        """Get all supported image files from folder.
        
        Excludes:
        - Files in the output subfolder (web_optimized) to prevent reprocessing
        - Files with the web output suffix (e.g., _web.jpg) 
        """
        image_files = []
        
        # Get the output subfolder name to exclude
        output_subfolder = self.config.subfolder_name.lower() if self.config.subfolder_name else "web_optimized"
        web_suffix = self.config.web_output_suffix.lower() if self.config.web_output_suffix else "_web"
        
        for root, dirs, files in os.walk(folder_path):
            # Skip output subfolders to prevent reprocessing
            # Modify dirs in-place to prevent os.walk from descending into them
            dirs[:] = [d for d in dirs if d.lower() != output_subfolder]
            
            for file in files:
                file_lower = file.lower()
                file_stem = Path(file).stem.lower()
                
                # Skip files that have already been processed (have web suffix)
                if web_suffix and file_stem.endswith(web_suffix):
                    continue
                    
                if Path(file).suffix.lower() in self.supported_formats:
                    image_files.append(os.path.join(root, file))
        
        logger.info(f"Found {len(image_files)} original images (excluded output folder '{output_subfolder}')")
        return sorted(image_files)
    
    def process_folder(self, progress_callback=None) -> Dict[str, Any]:
        """Process all images in the configured input folder."""
        input_files = self.get_image_files(self.config.input_folder)
        
        if not input_files:
            logger.warning(f"No supported image files found in {self.config.input_folder}")
            return {"processed": 0, "failed": 0, "total": 0}
        
        logger.info(f"Found {len(input_files)} files to process")
        
        results = {"processed": 0, "failed": 0, "total": len(input_files)}
        
        if self.config.use_multiprocessing and len(input_files) > 1:
            results = self._process_with_multiprocessing(input_files, progress_callback)
        else:
            results = self._process_sequentially(input_files, progress_callback)
        
        logger.info(f"Processing complete: {results['processed']} succeeded, {results['failed']} failed")
        return results
    
    def _process_sequentially(self, input_files: List[str], progress_callback=None) -> Dict[str, Any]:
        """Process files sequentially with progress tracking."""
        results = {"processed": 0, "failed": 0, "total": len(input_files)}
        
        for i, input_path in enumerate(tqdm(input_files, desc="Processing images")):
            output_path = self._get_output_path(input_path)
            
            if self.process_single_image(input_path, output_path):
                results["processed"] += 1
            else:
                results["failed"] += 1
            
            if progress_callback:
                # progress_callback returns False to signal stop
                should_continue = progress_callback(i + 1, len(input_files))
                if should_continue is False:
                    logger.info("Processing stopped by user")
                    results["stopped"] = True
                    break
        
        return results
    
    def _process_with_multiprocessing(self, input_files: List[str], progress_callback=None) -> Dict[str, Any]:
        """Process files using multiprocessing for better performance."""
        max_workers = self.config.max_workers or min(mp.cpu_count(), len(input_files))
        results = {"processed": 0, "failed": 0, "total": len(input_files)}
        
        # Prepare tasks
        tasks = [(input_path, self._get_output_path(input_path)) for input_path in input_files]
        
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            futures = [executor.submit(self._process_task, task) for task in tasks]
            
            # Process results with progress tracking
            for i, future in enumerate(tqdm(futures, desc="Processing images")):
                try:
                    if future.result():
                        results["processed"] += 1
                    else:
                        results["failed"] += 1
                except Exception as e:
                    logger.error(f"Task failed: {e}")
                    results["failed"] += 1
                
                if progress_callback:
                    progress_callback(i + 1, len(futures))
        
        return results
    
    def _process_task(self, task: Tuple[str, str]) -> bool:
        """Process a single task (used for multiprocessing)."""
        input_path, output_path = task
        return self.process_single_image(input_path, output_path)
    
    def _get_output_path(self, input_path: str) -> str:
        """Generate output path for processed image.
        
        For web optimization mode:
        - Adds '_web' suffix to filename
        - Creates 'web_optimized' subfolder in the source folder
        
        Example: /photos/painting.jpg -> /photos/web_optimized/painting_web.jpg
        """
        input_file = Path(input_path)
        
        # Determine output directory
        if self.config.create_subfolder:
            # Create subfolder in the source folder (not output folder)
            source_folder = input_file.parent
            output_dir = source_folder / self.config.subfolder_name
        elif self.config.output_folder:
            # Use configured output folder
            relative_path = input_file.relative_to(self.config.input_folder)
            output_dir = Path(self.config.output_folder) / relative_path.parent
        else:
            # Fall back to source folder
            output_dir = input_file.parent
        
        # Create output directory if it doesn't exist
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate output filename with _web suffix
        output_name = f"{input_file.stem}{self.config.web_output_suffix}.{self.config.output_format.lower()}"
        output_path = output_dir / output_name
        
        return str(output_path)


if __name__ == "__main__":
    # Example usage - Web optimization for Michael J Wright Estate
    config = ProcessingConfig(
        input_folder="input",
        output_folder="output",
        # Text watermark settings
        use_text_watermark=True,
        watermark_text="Michael J Wright Estate | All Rights Reserved",
        text_watermark_opacity=25,  # Very light - visible at zoom, not at full view
        text_rotation_angle=-30,
        text_spacing_ratio=1.8,
        # Web optimization settings
        long_edge_pixels=1200,
        output_dpi=72,
        convert_to_srgb=True,
        jpeg_quality=77,
        target_max_size_kb=300,
        web_output_suffix="_web",
        create_subfolder=True,
        subfolder_name="web_optimized",
        output_format="JPEG"
    )
    
    processor = ImageProcessor(config)
    results = processor.process_folder()
    
    print(f"Processing complete:")
    print(f"  Processed: {results['processed']}")
    print(f"  Failed: {results['failed']}")
    print(f"  Total: {results['total']}")
