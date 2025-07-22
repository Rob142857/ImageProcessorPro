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
from PIL import Image, ImageEnhance, ImageOps
import cv2
import numpy as np

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
    jpeg_quality: int = 85
    png_compression: int = 6
    webp_quality: int = 85
    
    # Watermark settings
    watermark_opacity: float = 0.3
    watermark_position: str = "bottom-right"  # Options: center, top-left, top-right, bottom-left, bottom-right
    watermark_scale: float = 0.2  # Scale relative to image size
    
    # Tiled watermark settings
    use_tiled_watermark: bool = True  # Use tiled pattern instead of single watermark
    tile_size_ratio: float = 0.2  # Size of each tile relative to image width
    tile_spacing_ratio: float = 1.5  # Spacing between tiles (multiplier of tile size)
    tile_opacity_reduction: float = 0.7  # Reduce opacity for tiled watermarks
    
    # Processing settings
    max_width: int = 1920
    max_height: int = 1080
    output_format: str = "JPEG"  # Options: JPEG, PNG, WEBP
    preserve_aspect_ratio: bool = True
    
    # Performance settings
    use_multiprocessing: bool = True
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
    
    def apply_watermark(self, image: Image.Image) -> Image.Image:
        """Apply watermark to image - either tiled pattern or single positioned watermark."""
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
        """Resize image for web optimization while preserving aspect ratio."""
        width, height = image.size
        
        if width <= self.config.max_width and height <= self.config.max_height:
            return image
        
        if self.config.preserve_aspect_ratio:
            # Calculate scaling factor
            scale_w = self.config.max_width / width
            scale_h = self.config.max_height / height
            scale = min(scale_w, scale_h)
            
            new_width = int(width * scale)
            new_height = int(height * scale)
        else:
            new_width = min(width, self.config.max_width)
            new_height = min(height, self.config.max_height)
        
        return image.resize((new_width, new_height), Image.Resampling.LANCZOS)
    
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
                    
                    # Apply processing
                    processed_image = self.apply_watermark(image)
                    processed_image = self.resize_for_web(processed_image)
                    
                    # Convert to RGB if saving as JPEG
                    if self.config.output_format.upper() == 'JPEG' and processed_image.mode == 'RGBA':
                        processed_image = processed_image.convert('RGB')
                    
                    # Save with appropriate settings
                    self.save_optimized_image(processed_image, str(page_output_path))
                
                return True
            
            else:
                # Process regular image
                with Image.open(input_path) as image:
                    # Apply watermark
                    processed_image = self.apply_watermark(image)
                    
                    # Resize for web
                    processed_image = self.resize_for_web(processed_image)
                    
                    # Convert to RGB if saving as JPEG
                    if self.config.output_format.upper() == 'JPEG' and processed_image.mode == 'RGBA':
                        processed_image = processed_image.convert('RGB')
                    
                    # Save optimized image
                    self.save_optimized_image(processed_image, output_path)
                    
                    return True
                    
        except Exception as e:
            logger.error(f"Failed to process {input_path}: {e}")
            return False
    
    def save_optimized_image(self, image: Image.Image, output_path: str) -> None:
        """Save image with optimized settings for web."""
        format_upper = self.config.output_format.upper()
        
        if format_upper == 'JPEG':
            image.save(output_path, 'JPEG', 
                      quality=self.config.jpeg_quality, 
                      optimize=True)
        elif format_upper == 'PNG':
            image.save(output_path, 'PNG', 
                      compress_level=self.config.png_compression, 
                      optimize=True)
        elif format_upper == 'WEBP':
            image.save(output_path, 'WEBP', 
                      quality=self.config.webp_quality, 
                      optimize=True)
        else:
            image.save(output_path, optimize=True)
    
    def get_image_files(self, folder_path: str) -> List[str]:
        """Get all supported image files from folder."""
        image_files = []
        
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                if Path(file).suffix.lower() in self.supported_formats:
                    image_files.append(os.path.join(root, file))
        
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
                progress_callback(i + 1, len(input_files))
        
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
        """Generate output path for processed image."""
        input_file = Path(input_path)
        relative_path = input_file.relative_to(self.config.input_folder)
        
        # Change extension based on output format
        output_name = relative_path.stem + f".{self.config.output_format.lower()}"
        output_path = Path(self.config.output_folder) / relative_path.parent / output_name
        
        # Create output directory if it doesn't exist
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        return str(output_path)


if __name__ == "__main__":
    # Example usage
    config = ProcessingConfig(
        input_folder="input",
        output_folder="output",
        watermark_path="watermarks/watermark.png",
        jpeg_quality=85,
        watermark_opacity=0.3,
        max_width=1920,
        max_height=1080
    )
    
    processor = ImageProcessor(config)
    results = processor.process_folder()
    
    print(f"Processing complete:")
    print(f"  Processed: {results['processed']}")
    print(f"  Failed: {results['failed']}")
    print(f"  Total: {results['total']}")
