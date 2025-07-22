"""
Command Line Interface for Image Processor
=========================================

A powerful CLI for batch processing images with watermarks and web optimization.
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
        description="Image Processor CLI - Automated watermarking and web optimization",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage
  python cli.py -i "input_folder" -o "output_folder" -w "watermark.png"
  
  # Advanced options
  python cli.py -i "photos" -o "web_photos" -w "logo.png" --quality 90 --opacity 0.5 --format WEBP
  
  # Use configuration file
  python cli.py --config "my_settings.yaml"
  
  # Generate default config
  python cli.py --generate-config "default.yaml"
        """
    )
    
    # Input/Output
    parser.add_argument('-i', '--input', type=str, help='Input folder containing images')
    parser.add_argument('-o', '--output', type=str, help='Output folder for processed images')
    parser.add_argument('-w', '--watermark', type=str, help='Path to watermark PNG file')
    
    # Output settings
    parser.add_argument('--format', choices=['JPEG', 'PNG', 'WEBP'], default='JPEG',
                       help='Output image format (default: JPEG)')
    parser.add_argument('--quality', type=int, default=85, metavar='1-100',
                       help='Output quality for JPEG/WEBP (default: 85)')
    
    # Watermark settings
    parser.add_argument('--opacity', type=float, default=0.3, metavar='0.1-1.0',
                       help='Watermark opacity (default: 0.3)')
    parser.add_argument('--position', choices=['center', 'top-left', 'top-right', 'bottom-left', 'bottom-right'],
                       default='bottom-right', help='Watermark position (default: bottom-right)')
    parser.add_argument('--scale', type=float, default=0.2, metavar='0.05-0.5',
                       help='Watermark scale relative to image size (default: 0.2)')
    
    # Tiled watermark settings (NEW)
    parser.add_argument('--no-tiling', action='store_true',
                       help='Use single watermark instead of tiled pattern')
    parser.add_argument('--tile-size', type=float, default=0.18, metavar='0.1-0.3',
                       help='Size of each tile in tiled pattern (default: 0.18)')
    parser.add_argument('--tile-spacing', type=float, default=1.6, metavar='1.0-3.0',
                       help='Spacing between tiles as multiplier (default: 1.6)')
    parser.add_argument('--tile-opacity-reduction', type=float, default=0.7, metavar='0.3-1.0',
                       help='Opacity reduction for tiled watermarks (default: 0.7)')
    
    # Image size settings
    parser.add_argument('--max-width', type=int, default=1920,
                       help='Maximum output width (default: 1920)')
    parser.add_argument('--max-height', type=int, default=1080,
                       help='Maximum output height (default: 1080)')
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
    
    if not args.output:
        logger.error("Output folder is required (use -o or --output)")
        return False
    
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
        output_folder=args.output or "",
        watermark_path=args.watermark or "",
        jpeg_quality=args.quality,
        png_compression=6,
        webp_quality=args.quality,
        watermark_opacity=args.opacity,
        watermark_position=args.position,
        watermark_scale=args.scale,
        use_tiled_watermark=not args.no_tiling,
        tile_size_ratio=args.tile_size,
        tile_spacing_ratio=args.tile_spacing,
        tile_opacity_reduction=args.tile_opacity_reduction,
        max_width=args.max_width,
        max_height=args.max_height,
        output_format=args.format,
        preserve_aspect_ratio=not args.no_preserve_aspect,
        use_multiprocessing=not args.no_multiprocessing,
        max_workers=args.max_workers,
        pdf_dpi=args.pdf_dpi
    )


def generate_default_config(output_path: str) -> None:
    """Generate a default configuration file."""
    
    config = ProcessingConfig()
    
    # Add some example values
    config.input_folder = "input"
    config.output_folder = "output"
    config.watermark_path = "watermarks/watermark.png"
    
    config.save_to_file(output_path)
    logger.info(f"Default configuration saved to: {output_path}")
    
    # Also create example folder structure
    os.makedirs("input", exist_ok=True)
    os.makedirs("output", exist_ok=True)
    os.makedirs("watermarks", exist_ok=True)
    
    logger.info("Created example folder structure: input/, output/, watermarks/")


def run_dry_run(processor: ImageProcessor) -> None:
    """Run a dry run to show what would be processed."""
    
    input_files = processor.get_image_files(processor.config.input_folder)
    
    if not input_files:
        logger.warning(f"No supported files found in {processor.config.input_folder}")
        return
    
    logger.info(f"Dry run - Would process {len(input_files)} files:")
    logger.info(f"Input folder: {processor.config.input_folder}")
    logger.info(f"Output folder: {processor.config.output_folder}")
    logger.info(f"Output format: {processor.config.output_format}")
    logger.info(f"Quality: {processor.config.jpeg_quality}")
    
    if processor.config.watermark_path:
        logger.info(f"Watermark: {processor.config.watermark_path}")
        logger.info(f"  Opacity: {processor.config.watermark_opacity}")
        logger.info(f"  Position: {processor.config.watermark_position}")
        logger.info(f"  Scale: {processor.config.watermark_scale}")
    else:
        logger.info("Watermark: None")
    
    logger.info(f"Max dimensions: {processor.config.max_width}x{processor.config.max_height}")
    logger.info(f"Preserve aspect ratio: {processor.config.preserve_aspect_ratio}")
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
    
    if not config.output_folder:
        logger.error("Output folder is required")
        return 1
    
    try:
        # Create processor
        processor = ImageProcessor(config)
        
        # Run dry run if requested
        if args.dry_run:
            run_dry_run(processor)
            return 0
        
        # Run actual processing
        logger.info("Starting image processing...")
        logger.info(f"Input: {config.input_folder}")
        logger.info(f"Output: {config.output_folder}")
        
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
