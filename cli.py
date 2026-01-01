"""
Command Line Interface for Image Processor
=========================================

A powerful CLI for batch processing images with watermarks and web optimization.

Optimized for Michael J Wright Estate web image processing:
- Resize to 1200px long edge
- sRGB color space, 72 DPI
- JPEG at 75-80% quality (< 300KB)
- Text watermark: "© Michael J Wright Estate - Property of"
- Output: filename_web.jpg in web_optimized subfolder
"""

import argparse
import os
import sys
from pathlib import Path
import yaml
from typing import Optional

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from image_processor import ImageProcessor, ProcessingConfig
from loguru import logger


def create_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser."""
    
    parser = argparse.ArgumentParser(
        description="MJW Estate Web Image Optimizer - Automated watermarking and web optimization",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Quick web optimization (uses defaults optimized for MJW Estate)
  python cli.py -i "paintings_folder"
  
  # Custom watermark text
  python cli.py -i "photos" --watermark-text "© My Custom Text"
  
  # Advanced options
  python cli.py -i "photos" --long-edge 1500 --quality 85 --opacity 30
  
  # Use configuration file
  python cli.py --config "my_settings.yaml"
  
  # Generate default config
  python cli.py --generate-config "default.yaml"
        """
    )
    
    # Input/Output
    parser.add_argument('-i', '--input', type=str, required=False,
                       help='Input folder containing images')
    parser.add_argument('-o', '--output', type=str, default=None,
                       help='Output folder (default: creates subfolder in input)')
    parser.add_argument('-w', '--watermark', type=str, help='Path to watermark PNG file (optional, uses text by default)')
    
    # Web optimization settings (new defaults for MJW Estate)
    parser.add_argument('--long-edge', type=int, default=1200,
                       help='Long edge size in pixels for paintings (default: 1200)')
    parser.add_argument('--target-size', type=int, default=300,
                       help='Target max file size in KB (default: 300)')
    parser.add_argument('--subfolder', type=str, default='web_optimized',
                       help='Name of output subfolder (default: web_optimized)')
    parser.add_argument('--suffix', type=str, default='_web',
                       help='Filename suffix for processed files (default: _web)')
    
    # Text watermark settings (new)
    parser.add_argument('--watermark-text', type=str, 
                       default='© Michael J Wright Estate - Property of',
                       help='Text watermark to apply across images')
    parser.add_argument('--text-opacity', type=int, default=25, metavar='0-255',
                       help='Text watermark opacity (0=invisible, 255=solid, default: 25)')
    parser.add_argument('--text-rotation', type=int, default=-30,
                       help='Text rotation angle in degrees (default: -30)')
    parser.add_argument('--text-spacing', type=float, default=1.8,
                       help='Text spacing ratio (default: 1.8)')
    parser.add_argument('--font-size', type=float, default=0.025,
                       help='Font size as ratio of image width (default: 0.025)')
    parser.add_argument('--no-text-watermark', action='store_true',
                       help='Disable text watermark (use image watermark instead)')
    
    # Output settings
    parser.add_argument('--format', choices=['JPEG', 'PNG', 'WEBP'], default='JPEG',
                       help='Output image format (default: JPEG)')
    parser.add_argument('--quality', type=int, default=77, metavar='1-100',
                       help='Output quality for JPEG/WEBP (default: 77)')
    
    # Image watermark settings (legacy/optional)
    parser.add_argument('--opacity', type=float, default=0.3, metavar='0.1-1.0',
                       help='Image watermark opacity (default: 0.3)')
    parser.add_argument('--position', choices=['center', 'top-left', 'top-right', 'bottom-left', 'bottom-right'],
                       default='bottom-right', help='Image watermark position (default: bottom-right)')
    parser.add_argument('--scale', type=float, default=0.2, metavar='0.05-0.5',
                       help='Image watermark scale relative to image size (default: 0.2)')
    
    # Tiled watermark settings
    parser.add_argument('--no-tiling', action='store_true',
                       help='Use single watermark instead of tiled pattern')
    parser.add_argument('--tile-size', type=float, default=0.18, metavar='0.1-0.3',
                       help='Size of each tile in tiled pattern (default: 0.18)')
    parser.add_argument('--tile-spacing', type=float, default=1.6, metavar='1.0-3.0',
                       help='Spacing between tiles as multiplier (default: 1.6)')
    parser.add_argument('--tile-opacity-reduction', type=float, default=0.7, metavar='0.3-1.0',
                       help='Opacity reduction for tiled watermarks (default: 0.7)')
    
    # Image size settings (legacy)
    parser.add_argument('--max-width', type=int, default=1920,
                       help='Maximum output width - legacy (default: 1920)')
    parser.add_argument('--max-height', type=int, default=1080,
                       help='Maximum output height - legacy (default: 1080)')
    parser.add_argument('--no-preserve-aspect', action='store_true',
                       help='Do not preserve aspect ratio when resizing')
    
    # PDF settings
    parser.add_argument('--pdf-dpi', type=int, default=200,
                       help='DPI for PDF to image conversion (default: 200)')
    
    # Performance settings
    parser.add_argument('--no-multiprocessing', action='store_true',
                       help='Disable multiprocessing (use single thread)')
    parser.add_argument('--max-workers', type=int, default=None,
                       help='Maximum number of worker processes (default: auto)')
    
    # Configuration
    parser.add_argument('--config', type=str,
                       help='Load settings from YAML configuration file')
    parser.add_argument('--save-config', type=str,
                       help='Save current settings to YAML file and exit')
    parser.add_argument('--generate-config', type=str,
                       help='Generate a default configuration file and exit')
    
    # Other options
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be processed without actually processing')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    parser.add_argument('--quiet', '-q', action='store_true',
                       help='Suppress all output except errors')
    
    return parser


def setup_logging(verbose: bool = False, quiet: bool = False) -> None:
    """Setup logging configuration."""
    
    # Remove default logger
    logger.remove()
    
    if quiet:
        # Only show errors
        logger.add(sys.stderr, level="ERROR", format="<red>ERROR</red>: {message}")
    elif verbose:
        # Show debug and above
        logger.add(sys.stderr, level="DEBUG", 
                  format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | {message}")
    else:
        # Show info and above
        logger.add(sys.stderr, level="INFO", format="<level>{level}</level>: {message}")


def validate_args(args: argparse.Namespace) -> bool:
    """Validate command line arguments."""
    
    if args.config:
        # Config file will be validated when loaded
        return True
    
    if args.generate_config or args.save_config:
        # No validation needed for config generation
        return True
    
    # Check required arguments
    if not args.input:
        logger.error("Input folder is required (use -i or --input)")
        return False
    
    # Output folder is optional in subfolder mode
    # if not args.output:
    #     logger.info("No output folder specified - will create subfolder in input directory")
    
    # Check input folder exists
    if not os.path.exists(args.input):
        logger.error(f"Input folder does not exist: {args.input}")
        return False
    
    # Check watermark file if specified
    if args.watermark and not os.path.exists(args.watermark):
        logger.error(f"Watermark file does not exist: {args.watermark}")
        return False
    
    # Validate ranges
    if not (1 <= args.quality <= 100):
        logger.error("Quality must be between 1 and 100")
        return False
    
    if not (0.1 <= args.opacity <= 1.0):
        logger.error("Opacity must be between 0.1 and 1.0")
        return False
    
    if not (0.05 <= args.scale <= 0.5):
        logger.error("Scale must be between 0.05 and 0.5")
        return False
    
    return True


def args_to_config(args: argparse.Namespace) -> ProcessingConfig:
    """Convert command line arguments to ProcessingConfig."""
    
    return ProcessingConfig(
        input_folder=args.input or "",
        output_folder=args.output or args.input or "",  # Default to input folder for subfolder mode
        watermark_path=args.watermark or "",
        
        # JPEG quality settings
        jpeg_quality=args.quality,
        png_compression=6,
        webp_quality=args.quality,
        target_max_size_kb=args.target_size,
        
        # Text watermark settings (new primary mode)
        use_text_watermark=not args.no_text_watermark,
        watermark_text=args.watermark_text,
        text_font_size_ratio=args.font_size,
        text_watermark_opacity=args.text_opacity,
        text_rotation_angle=args.text_rotation,
        text_spacing_ratio=args.text_spacing,
        
        # Image watermark settings (legacy/optional)
        watermark_opacity=args.opacity,
        watermark_position=args.position,
        watermark_scale=args.scale,
        use_tiled_watermark=not args.no_tiling,
        tile_size_ratio=args.tile_size,
        tile_spacing_ratio=args.tile_spacing,
        tile_opacity_reduction=args.tile_opacity_reduction,
        
        # Web optimization settings
        long_edge_pixels=args.long_edge,
        output_dpi=72,
        convert_to_srgb=True,
        web_output_suffix=args.suffix,
        create_subfolder=True,
        subfolder_name=args.subfolder,
        
        # Size and format settings
        max_width=args.max_width,
        max_height=args.max_height,
        output_format=args.format,
        preserve_aspect_ratio=not args.no_preserve_aspect,
        use_multiprocessing=not args.no_multiprocessing,
        max_workers=args.max_workers,
        pdf_dpi=args.pdf_dpi
    )


def generate_default_config(output_path: str) -> None:
    """Generate a default configuration file for MJW Estate web optimization."""
    
    config = ProcessingConfig(
        input_folder="input",
        output_folder="input",  # Subfolder mode
        # Text watermark
        use_text_watermark=True,
        watermark_text="© Michael J Wright Estate - Property of",
        text_watermark_opacity=25,
        text_rotation_angle=-30,
        text_spacing_ratio=1.8,
        text_font_size_ratio=0.025,
        # Web optimization
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
    
    config.save_to_file(output_path)
    logger.info(f"Default configuration saved to: {output_path}")
    
    # Also create example folder structure
    os.makedirs("input", exist_ok=True)
    os.makedirs("watermarks", exist_ok=True)
    
    logger.info("Created example folder structure: input/, watermarks/")


def run_dry_run(processor: ImageProcessor) -> None:
    """Run a dry run to show what would be processed."""
    
    input_files = processor.get_image_files(processor.config.input_folder)
    
    if not input_files:
        logger.warning(f"No supported files found in {processor.config.input_folder}")
        return
    
    logger.info(f"Dry run - Would process {len(input_files)} files:")
    logger.info(f"Input folder: {processor.config.input_folder}")
    
    # Show output location
    if processor.config.create_subfolder:
        output_loc = os.path.join(processor.config.input_folder, processor.config.subfolder_name)
        logger.info(f"Output folder: {output_loc} (subfolder)")
    else:
        logger.info(f"Output folder: {processor.config.output_folder}")
    
    logger.info(f"Output format: {processor.config.output_format}")
    logger.info(f"Quality: {processor.config.jpeg_quality}")
    logger.info(f"Target size: < {processor.config.target_max_size_kb} KB")
    
    # Web optimization settings
    logger.info(f"Long edge: {processor.config.long_edge_pixels}px")
    logger.info(f"DPI: {processor.config.output_dpi}")
    logger.info(f"sRGB conversion: {processor.config.convert_to_srgb}")
    logger.info(f"File suffix: {processor.config.web_output_suffix}")
    
    # Watermark info
    if processor.config.use_text_watermark:
        logger.info(f"Text watermark: '{processor.config.watermark_text}'")
        logger.info(f"  Opacity: {processor.config.text_watermark_opacity}/255")
        logger.info(f"  Rotation: {processor.config.text_rotation_angle}°")
    elif processor.config.watermark_path:
        logger.info(f"Image watermark: {processor.config.watermark_path}")
        logger.info(f"  Opacity: {processor.config.watermark_opacity}")
        logger.info(f"  Position: {processor.config.watermark_position}")
    else:
        logger.info("Watermark: None")
    
    logger.info(f"Multiprocessing: {processor.config.use_multiprocessing}")
    
    if processor.config.max_workers:
        logger.info(f"Max workers: {processor.config.max_workers}")
    
    logger.info("\nFiles to process:")
    for i, file_path in enumerate(input_files[:10], 1):  # Show first 10 files
        rel_path = os.path.relpath(file_path, processor.config.input_folder)
        logger.info(f"  {i}. {rel_path}")
    
    if len(input_files) > 10:
        logger.info(f"  ... and {len(input_files) - 10} more files")


def main():
    """Main CLI function."""
    
    parser = create_parser()
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose, args.quiet)
    
    # Handle config generation
    if args.generate_config:
        generate_default_config(args.generate_config)
        return 0
    
    # Load configuration
    if args.config:
        try:
            config = ProcessingConfig.load_from_file(args.config)
            logger.info(f"Loaded configuration from: {args.config}")
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            return 1
    else:
        # Validate arguments first
        if not validate_args(args):
            return 1
        
        config = args_to_config(args)
    
    # Handle config saving
    if args.save_config:
        try:
            config.save_to_file(args.save_config)
            logger.info(f"Configuration saved to: {args.save_config}")
            return 0
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            return 1
    
    # Final validation
    if not config.input_folder or not os.path.exists(config.input_folder):
        logger.error("Valid input folder is required")
        return 1
    
    # Output folder not required in subfolder mode
    # if not config.output_folder:
    #     logger.error("Output folder is required")
    #     return 1
    
    try:
        # Create processor
        processor = ImageProcessor(config)
        
        # Run dry run if requested
        if args.dry_run:
            run_dry_run(processor)
            return 0
        
        # Run actual processing
        logger.info("Starting MJW Estate web image processing...")
        logger.info(f"Input: {config.input_folder}")
        
        if config.create_subfolder:
            output_loc = os.path.join(config.input_folder, config.subfolder_name)
            logger.info(f"Output: {output_loc}")
        else:
            logger.info(f"Output: {config.output_folder}")
        
        logger.info(f"Settings: {config.long_edge_pixels}px, {config.output_dpi} DPI, JPEG {config.jpeg_quality}%, < {config.target_max_size_kb}KB")
        
        def progress_callback(current: int, total: int):
            if not args.quiet:
                percentage = (current / total) * 100
                logger.info(f"Progress: {current}/{total} ({percentage:.1f}%)")
        
        results = processor.process_folder(progress_callback)
        
        # Report results
        success_count = results.get('processed', 0)
        failed_count = results.get('failed', 0)
        total_count = results.get('total', 0)
        
        logger.info(f"Processing complete!")
        logger.info(f"  Successfully processed: {success_count} files")
        logger.info(f"  Failed: {failed_count} files")
        logger.info(f"  Total: {total_count} files")
        
        if config.create_subfolder:
            logger.info(f"  Output saved to: {os.path.join(config.input_folder, config.subfolder_name)}")
        
        if failed_count > 0:
            logger.warning(f"{failed_count} files failed to process. Check logs for details.")
            return 1
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("Processing interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
