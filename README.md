# Image Processor Pro - Automated Watermarking & Web Optimization

A comprehensive, user-friendly solution for automated image processing with watermarking and web optimization. Built for Windows 11 with powerful hardware and Azure integration capabilities.

## 🚀 Features

### Core Functionality
- **Multi-format Support**: PDF, JPG, JPEG, PNG, BMP, TIFF files
- **Intelligent Watermarking**: Transparent PNG watermarks with customizable opacity, position, and scaling
- **Web Optimization**: Automatic resizing and compression for web-compatible formats
- **Batch Processing**: Process entire folders with progress tracking
- **High Performance**: Multi-processing support optimized for powerful hardware

### User Interfaces
- **Modern GUI**: Clean, intuitive interface built with CustomTkinter
- **Command Line**: Powerful CLI for automation and scripting
- **HTTP API**: RESTful API for Power Platform and cloud integration

### Cloud Integration
- **Azure Blob Storage**: Cloud-based image processing and storage
- **Azure Computer Vision**: AI-powered image analysis and text detection
- **Power Platform**: Ready-to-use Power Automate workflows and Power Apps integration

### Enterprise Features
- **Configuration Management**: YAML-based settings with presets
- **Comprehensive Logging**: Detailed logs with rotation and retention
- **Error Handling**: Robust error recovery and reporting
- **Performance Monitoring**: Progress tracking and statistics

## 📋 Requirements

### System Requirements
- **OS**: Windows 11 Pro/Business (recommended)
- **Hardware**: Multi-core processor, 8GB+ RAM
- **Python**: 3.8 or higher

### Python Dependencies
```bash
pip install -r requirements.txt
```

Key packages:
- **Pillow**: Image processing
- **OpenCV**: Advanced image operations
- **PyMuPDF**: PDF handling
- **CustomTkinter**: Modern GUI
- **Azure SDK**: Cloud integration (optional)
- **Flask**: HTTP API (optional)

## 🎯 Quick Start

### 1. Setup
```bash
# Clone or download the project
cd ImageProcessorMJWProject

# Install dependencies
pip install -r requirements.txt

# Create input/output folders
mkdir input output watermarks
```

### 2. Add Your Watermark
Place a transparent PNG watermark in the `watermarks/` folder and update the configuration.

### 3. Choose Your Interface

#### GUI Application (Recommended for most users)
```bash
python gui_app.py
```

#### Command Line (For automation)
```bash
# Basic usage
python cli.py -i "input_folder" -o "output_folder" -w "watermarks/logo.png"

# Advanced options
python cli.py -i "photos" -o "web_photos" -w "logo.png" --quality 90 --opacity 0.5 --format WEBP
```

#### HTTP API (For Power Platform integration)
```bash
# Start the API server
python power_platform/power_platform_integration.py
```

## 🔧 Configuration

### Using Configuration Files
The system supports YAML configuration files for easy preset management:

```bash
# Use a specific config file
python cli.py --config config/web_optimized_config.yaml

# Generate a new config template
python cli.py --generate-config my_settings.yaml
```

### Available Presets
- **`default_config.yaml`**: Balanced quality and performance
- **`high_quality_config.yaml`**: Maximum quality for important images
- **`web_optimized_config.yaml`**: Fast processing for web use

### Key Settings
```yaml
# Image Quality
jpeg_quality: 85          # 1-100 (higher = better quality, larger files)
output_format: "JPEG"     # JPEG, PNG, WEBP

# Watermark
watermark_opacity: 0.3    # 0.1-1.0 (transparency level)
watermark_position: "bottom-right"  # Placement on image
watermark_scale: 0.2      # Size relative to image (0.05-0.5)

# Dimensions
max_width: 1920           # Maximum output width
max_height: 1080          # Maximum output height
```

## 🌐 Power Platform Integration

### Power Automate Workflows
Pre-built templates for:
- **Email Processing**: Process attachments from emails
- **SharePoint Integration**: Automatic folder monitoring
- **OneDrive Batch**: Scheduled bulk processing

Templates available in `power_platform/templates/`

### Power Apps Integration
- Custom connector setup
- Mobile-friendly image capture
- Batch processing interface
- Integration formulas provided

### API Endpoints
- `POST /api/process-image`: Upload and process files
- `POST /api/process-base64`: Process base64 images (Power Apps)
- `POST /api/process-batch`: Batch processing
- `GET /api/health`: Health check

## ☁️ Azure Integration

### Setup Azure Services
1. **Blob Storage**: For cloud image storage
2. **Computer Vision**: For AI analysis (optional)

### Configuration
```bash
# Copy template and add your credentials
cp azure/azure_config_template.json azure/azure_config.json
```

### Features
- Cloud-based batch processing
- Automatic image analysis and tagging
- OCR text detection
- Scalable storage solutions

## 🖥️ GUI Usage

### Basic Workflow
1. **Launch**: Run `python gui_app.py`
2. **Configure**: Set input/output folders and watermark
3. **Adjust Settings**: Quality, opacity, dimensions
4. **Scan**: Check how many files will be processed
5. **Process**: Start the batch operation
6. **Monitor**: Watch progress and results

### Advanced Features
- **Presets**: Save and load common configurations
- **Preview**: Scan folders before processing
- **Progress Tracking**: Real-time processing updates
- **Error Reporting**: Detailed failure information

## 💻 Command Line Usage

### Basic Examples
```bash
# Simple processing
python cli.py -i "C:\Photos" -o "C:\WebPhotos" -w "logo.png"

# Custom quality and format
python cli.py -i input -o output -w watermark.png --quality 90 --format WEBP

# Use configuration file
python cli.py --config config/high_quality_config.yaml

# Dry run (see what would be processed)
python cli.py -i input -o output --dry-run
```

### Advanced Options
```bash
# Custom dimensions
python cli.py -i input -o output --max-width 2560 --max-height 1440

# Watermark customization
python cli.py -i input -o output --opacity 0.5 --position center --scale 0.3

# Performance tuning
python cli.py -i input -o output --max-workers 8 --no-multiprocessing
```

## 🔍 Troubleshooting

### Common Issues

#### "No files found"
- Check input folder path
- Verify supported formats: PDF, JPG, PNG, BMP, TIFF
- Ensure files aren't corrupted

#### "Watermark not applied"
- Verify watermark file exists and is PNG format
- Check watermark path in configuration
- Ensure watermark has transparency

#### "Processing failed"
- Check available disk space
- Verify write permissions to output folder
- Review logs in `logs/` folder

#### Performance Issues
- Reduce `max_workers` if system becomes unresponsive
- Use SSD storage for better I/O performance
- Increase available RAM

### Log Files
Detailed logs are stored in `logs/image_processor_{timestamp}.log`

## 🚀 Deployment Options

### Local Development
- Run directly with Python
- Use virtual environments for isolation

### Windows Service
Convert to a Windows service for background processing:
```bash
# Install service dependencies
pip install pywin32

# Create service wrapper (example in deployment/)
```

### Docker Container
```dockerfile
# See deployment/Dockerfile for complete setup
FROM python:3.11-slim
COPY requirements.txt .
RUN pip install -r requirements.txt
```

### Azure Functions
Deploy API endpoints as serverless functions for scalable cloud processing.

## 🔐 Security Considerations

### File Handling
- Input validation for all file types
- Size limits to prevent memory issues
- Sandboxed processing environment

### API Security
- Authentication headers
- Rate limiting
- Input sanitization
- HTTPS enforcement

### Azure Integration
- Managed identities for authentication
- Private endpoints for storage
- Key Vault for secret management

## 📈 Performance Optimization

### Hardware Optimization
- **CPU**: Utilizes all available cores with multiprocessing
- **Memory**: Efficient image handling with streaming
- **Storage**: SSD recommended for faster I/O

### Processing Tips
- Use WEBP format for best compression
- Batch similar-sized images together
- Consider GPU acceleration for large volumes

### Scaling
- Azure cloud processing for unlimited scale
- Load balancing for API endpoints
- Distributed storage for large datasets

## 🛠️ Development

### Project Structure
```
ImageProcessorMJWProject/
├── src/                    # Core processing logic
├── gui_app.py             # GUI application
├── cli.py                 # Command line interface
├── config/                # Configuration presets
├── azure/                 # Azure integration
├── power_platform/        # Power Platform templates
├── watermarks/           # Watermark images
├── logs/                 # Application logs
└── requirements.txt      # Dependencies
```

### Adding Features
- Extend `ImageProcessor` class for new functionality
- Add new configuration options to `ProcessingConfig`
- Create custom GUI tabs for advanced features

### Testing
```bash
# Run with test images
python cli.py -i test_images -o test_output --dry-run

# Check processing quality
python -c "from src.image_processor import ImageProcessor; ..."
```

## 🎮 Use Cases

### Photography Studios
- Batch watermarking for client galleries
- Web optimization for online portfolios
- Automated copyright protection

### E-commerce
- Product image standardization
- Watermarking for brand protection
- Multi-format output for different platforms

### Marketing Agencies
- Social media image preparation
- Client asset management
- Brand compliance automation

### Enterprise Content
- Document processing workflows
- SharePoint integration
- Automated archival systems

## 📚 API Reference

### ProcessingConfig Class
```python
config = ProcessingConfig(
    input_folder="input",
    output_folder="output", 
    watermark_path="logo.png",
    jpeg_quality=85,
    watermark_opacity=0.3,
    max_width=1920,
    max_height=1080,
    output_format="JPEG"
)
```

### ImageProcessor Class
```python
processor = ImageProcessor(config)
results = processor.process_folder()
```

### HTTP API Endpoints
- `POST /api/process-image`: Multipart file upload
- `POST /api/process-base64`: JSON with base64 image
- `GET /api/config`: Get current configuration
- `POST /api/config`: Update configuration

## 🤝 Contributing

### Development Setup
1. Fork the repository
2. Create feature branch
3. Install development dependencies
4. Run tests before submitting

### Code Style
- Follow PEP 8 conventions
- Add type hints for all functions
- Include comprehensive docstrings
- Write unit tests for new features

## 📄 License

This project is provided as-is for educational and commercial use. Please ensure you have proper rights to any watermark images used.

## 📞 Support

### Documentation
- Check this README for common solutions
- Review configuration examples
- Examine log files for error details

### Community
- Report issues with detailed error information
- Include system specifications and log excerpts
- Provide sample images (without sensitive content)

---

**Built with ❤️ for automated image processing workflows**
