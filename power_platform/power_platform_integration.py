"""
Power Platform Integration Examples
==================================

Examples and templates for integrating the Image Processor with Microsoft Power Platform.
Includes Power Automate workflows, Power Apps integration, and HTTP API endpoints.
"""

import os
import sys
import json
from typing import Dict, Any, Optional, List
from pathlib import Path
import tempfile
import base64
import binascii
import hmac
import io
from datetime import datetime, timezone
from PIL import Image, UnidentifiedImageError

# Flask for creating HTTP API endpoints
try:
    from flask import Flask, request, jsonify, send_file
    from werkzeug.utils import secure_filename
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False

# Local imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from image_processor import ImageProcessor, ProcessingConfig
from loguru import logger


class PowerPlatformAPI:
    """HTTP API for Power Platform integration."""
    
    def __init__(self, config: ProcessingConfig):
        if not FLASK_AVAILABLE:
            raise ImportError("Flask not available. Install with: pip install flask")
        
        self.app = Flask(__name__)
        self.config = config
        self.processor = ImageProcessor(config)
        self.api_token = os.environ.get('IMAGE_PROCESSOR_API_TOKEN', '')
        self.allow_config_mutation = os.environ.get('IMAGE_PROCESSOR_ALLOW_CONFIG_MUTATION', '').lower() == 'true'
        self.max_upload_bytes = int(os.environ.get('IMAGE_PROCESSOR_MAX_UPLOAD_BYTES', 50 * 1024 * 1024))
        
        # Configure upload settings
        self.app.config['MAX_CONTENT_LENGTH'] = self.max_upload_bytes
        self.ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp'}
        
        self.setup_routes()
    
    def setup_routes(self):
        """Setup API routes for Power Platform integration."""

        @self.app.before_request
        def require_api_token():
            if request.path == '/api/health':
                return None
            supplied = request.headers.get('Authorization', '')
            expected = f'Bearer {self.api_token}' if self.api_token else ''
            if not expected or not hmac.compare_digest(supplied, expected):
                return jsonify({'error': {'code': 'unauthorized', 'message': 'Authentication is required.'}}), 401
            return None
        
        @self.app.route('/api/health', methods=['GET'])
        def health_check():
            """Health check endpoint."""
            return jsonify({
                'status': 'healthy',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'version': '2.0.0'
            })
        
        @self.app.route('/api/process-image', methods=['POST'])
        def process_single_image():
            """Process a single uploaded image."""
            try:
                # Check if file is in request
                if 'file' not in request.files:
                    return jsonify({'error': 'No file provided'}), 400
                
                file = request.files['file']
                if file.filename == '':
                    return jsonify({'error': 'No file selected'}), 400
                
                # Validate file extension
                if not self.allowed_file(file.filename):
                    return jsonify({'error': 'File type not supported'}), 400
                data = file.read()
                if len(data) > self.max_upload_bytes:
                    return jsonify({'error': {'code': 'payload_too_large', 'message': 'File exceeds the configured limit.'}}), 413
                if not self.verify_uploaded_content(data, file.filename):
                    return jsonify({'error': {'code': 'invalid_file', 'message': 'File content is not a valid supported still image.'}}), 400
                file.stream.seek(0)
                
                # Get processing options from request
                options = self.get_processing_options(request)
                
                # Process the image
                result = self.process_uploaded_file(file, options)
                
                if result['success']:
                    return jsonify(result), 200
                else:
                    return jsonify(result), 500
                    
            except ValueError as error:
                return jsonify({'error': {'code': 'invalid_options', 'message': str(error)}}), 400
            except Exception:
                logger.exception("API error processing image")
                return jsonify({'error': {'code': 'processing_failed', 'message': 'Image processing failed.'}}), 500
        
        @self.app.route('/api/process-batch', methods=['POST'])
        def process_batch_images():
            """Process multiple uploaded images."""
            try:
                files = request.files.getlist('files')
                if not files:
                    return jsonify({'error': 'No files provided'}), 400
                
                # Get processing options
                options = self.get_processing_options(request)
                
                results = []
                for file in files:
                    if file.filename and self.allowed_file(file.filename):
                        data = file.read()
                        if len(data) > self.max_upload_bytes or not self.verify_uploaded_content(data, file.filename):
                            results.append({'success': False, 'filename': file.filename, 'error': {'code': 'invalid_file', 'message': 'Invalid or oversized file.'}})
                            continue
                        file.stream.seek(0)
                        result = self.process_uploaded_file(file, options)
                        results.append(result)
                
                # Summary statistics
                success_count = sum(1 for r in results if r['success'])
                total_count = len(results)
                
                return jsonify({
                    'success': True,
                    'processed': success_count,
                    'total': total_count,
                    'results': results
                }), 200
                
            except ValueError as error:
                return jsonify({'error': {'code': 'invalid_options', 'message': str(error)}}), 400
            except Exception:
                logger.exception("API error processing batch")
                return jsonify({'error': {'code': 'processing_failed', 'message': 'Batch processing failed.'}}), 500
        
        @self.app.route('/api/process-base64', methods=['POST'])
        def process_base64_image():
            """Process a base64 encoded image (useful for Power Apps)."""
            try:
                data = request.get_json()
                if not data or 'image' not in data:
                    return jsonify({'error': 'No image data provided'}), 400
                
                # Decode base64 image
                encoded = data['image']
                if not isinstance(encoded, str) or len(encoded) > ((self.max_upload_bytes * 4) // 3) + 8:
                    return jsonify({'error': {'code': 'payload_too_large', 'message': 'Image payload exceeds the configured limit.'}}), 413
                try:
                    image_data = base64.b64decode(encoded, validate=True)
                except (binascii.Error, ValueError):
                    return jsonify({'error': 'Invalid base64 image data'}), 400
                if len(image_data) > self.max_upload_bytes:
                    return jsonify({'error': {'code': 'payload_too_large', 'message': 'Image payload exceeds the configured limit.'}}), 413
                if not self.verify_uploaded_content(image_data, 'upload.jpg'):
                    return jsonify({'error': {'code': 'invalid_file', 'message': 'Image content is invalid.'}}), 400
                
                # Get processing options
                options = self.normalise_options(data.get('options', {}))
                
                # Process the image
                result = self.process_base64_data(image_data, options)
                
                if result['success']:
                    return jsonify(result), 200
                else:
                    return jsonify(result), 500
                    
            except ValueError as error:
                return jsonify({'error': {'code': 'invalid_options', 'message': str(error)}}), 400
            except Exception:
                logger.exception("API error processing base64 image")
                return jsonify({'error': {'code': 'processing_failed', 'message': 'Image processing failed.'}}), 500
        
        @self.app.route('/api/config', methods=['GET', 'POST'])
        def handle_config():
            """Get or update processing configuration."""
            if request.method == 'GET':
                return jsonify(self.config.__dict__)
            
            elif request.method == 'POST':
                if not self.allow_config_mutation:
                    return jsonify({'error': {'code': 'config_mutation_disabled', 'message': 'Configuration updates are disabled.'}}), 403
                try:
                    data = request.get_json()
                    # Update configuration
                    for key, value in data.items():
                        if hasattr(self.config, key):
                            setattr(self.config, key, value)
                    
                    # Recreate processor with new config
                    self.processor = ImageProcessor(self.config)
                    
                    return jsonify({'success': True, 'message': 'Configuration updated'})
                except Exception:
                    logger.exception("Configuration update failed")
                    return jsonify({'error': {'code': 'config_update_failed', 'message': 'Configuration update failed.'}}), 500
    
    def allowed_file(self, filename: str) -> bool:
        """Check if file extension is allowed."""
        return Path(filename).suffix.lower() in self.ALLOWED_EXTENSIONS

    def verify_uploaded_content(self, data: bytes, filename: str) -> bool:
        """Reject disguised/corrupt image payloads before handing them to processors."""
        suffix = Path(filename).suffix.lower()
        try:
            with Image.open(io.BytesIO(data)) as image:
                image.verify()
            return True
        except (UnidentifiedImageError, OSError, ValueError):
            return False
    
    def get_processing_options(self, request) -> Dict[str, Any]:
        """Extract processing options from request."""
        return self.normalise_options(request.form.to_dict())

    def normalise_options(self, raw: Any) -> Dict[str, Any]:
        """Apply one strict option contract to multipart and JSON clients."""
        if not isinstance(raw, dict):
            raise ValueError("options must be an object")
        allowed = {"quality", "opacity", "format", "max_width", "max_height"}
        unknown = set(raw) - allowed
        if unknown:
            raise ValueError(f"unsupported option(s): {', '.join(sorted(unknown))}")

        options: Dict[str, Any] = {}
        try:
            if "quality" in raw:
                if isinstance(raw["quality"], bool): raise ValueError
                options["quality"] = int(raw["quality"])
                if not 1 <= options["quality"] <= 100: raise ValueError
            if "opacity" in raw:
                if isinstance(raw["opacity"], bool): raise ValueError
                options["opacity"] = float(raw["opacity"])
                if not 0 <= options["opacity"] <= 1: raise ValueError
            if "format" in raw:
                if not isinstance(raw["format"], str): raise ValueError
                options["format"] = raw["format"].upper()
                if options["format"] not in {"JPEG", "PNG", "WEBP"}: raise ValueError
            for field in ("max_width", "max_height"):
                if field in raw:
                    if isinstance(raw[field], bool): raise ValueError
                    options[field] = int(raw[field])
                    if not 1 <= options[field] <= 10000: raise ValueError
        except (TypeError, ValueError) as error:
            raise ValueError("options contain an invalid value") from error
        return options
    
    def process_uploaded_file(self, file, options: Dict[str, Any]) -> Dict[str, Any]:
        """Process an uploaded file."""
        input_path = output_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=Path(file.filename).suffix, delete=False) as temp_input:
                input_path = temp_input.name
                file.save(temp_input.name)
            temp_config = self.apply_options_to_config(options)
            temp_processor = ImageProcessor(temp_config)
            with tempfile.NamedTemporaryFile(suffix=f".{temp_config.output_format.lower()}", delete=False) as temp_output:
                output_path = temp_output.name
            if not temp_processor.process_single_image(input_path, output_path):
                return {'success': False, 'filename': file.filename, 'error': {'code': 'processing_failed', 'message': 'Processing failed.'}}
            with open(output_path, 'rb') as output_file:
                processed_data = output_file.read()
            return {'success': True, 'filename': file.filename, 'processed_image': base64.b64encode(processed_data).decode('utf-8'), 'format': temp_config.output_format, 'size': len(processed_data)}
        except Exception:
            logger.exception("Uploaded file processing failed")
            return {'success': False, 'filename': file.filename, 'error': {'code': 'processing_failed', 'message': 'Processing failed.'}}
        finally:
            sidecar_path = f"{output_path}.json" if output_path else None
            for path in (input_path, output_path, sidecar_path):
                if path:
                    try: os.unlink(path)
                    except FileNotFoundError: pass
    
    def process_base64_data(self, image_data: bytes, options: Dict[str, Any]) -> Dict[str, Any]:
        """Process base64 image data."""
        input_path = output_path = None
        try:
            temp_config = self.apply_options_to_config(options)
            temp_processor = ImageProcessor(temp_config)
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temp_input:
                input_path = temp_input.name
                temp_input.write(image_data)
                temp_input.flush()
            with tempfile.NamedTemporaryFile(suffix=f".{temp_config.output_format.lower()}", delete=False) as temp_output:
                output_path = temp_output.name
            if not temp_processor.process_single_image(input_path, output_path):
                return {'success': False, 'error': {'code': 'processing_failed', 'message': 'Processing failed.'}}
            with open(output_path, 'rb') as output_file:
                processed_data = output_file.read()
            return {'success': True, 'processed_image': base64.b64encode(processed_data).decode('utf-8'), 'format': temp_config.output_format, 'size': len(processed_data)}
        except Exception:
            logger.exception("Base64 image processing failed")
            return {'success': False, 'error': {'code': 'processing_failed', 'message': 'Processing failed.'}}
        finally:
            sidecar_path = f"{output_path}.json" if output_path else None
            for path in (input_path, output_path, sidecar_path):
                if path:
                    try: os.unlink(path)
                    except FileNotFoundError: pass
    
    def apply_options_to_config(self, options: Dict[str, Any]) -> ProcessingConfig:
        """Apply processing options to create a temporary config."""
        temp_config = ProcessingConfig(
            input_folder=self.config.input_folder,
            output_folder=self.config.output_folder,
            watermark_path=self.config.watermark_path,
            jpeg_quality=options.get('quality', self.config.jpeg_quality),
            watermark_opacity=options.get('opacity', self.config.watermark_opacity),
            max_width=options.get('max_width', self.config.max_width),
            max_height=options.get('max_height', self.config.max_height),
            output_format=options.get('format', self.config.output_format),
            preserve_aspect_ratio=self.config.preserve_aspect_ratio,
            watermark_position=self.config.watermark_position,
            watermark_scale=self.config.watermark_scale,
            use_multiprocessing=False,  # Disable for API calls
            pdf_dpi=self.config.pdf_dpi
        )
        return temp_config
    
    def run(self, host='127.0.0.1', port=5000, debug=False):
        """Run the Flask API server."""
        logger.info(f"Starting Power Platform API server on {host}:{port}")
        self.app.run(host=host, port=port, debug=debug)


def create_power_automate_templates():
    """Create Power Automate flow templates."""
    
    templates_dir = Path("power_platform/templates")
    templates_dir.mkdir(parents=True, exist_ok=True)
    
    # Template 1: Email attachment processing
    email_flow_template = {
        "displayName": "Process Email Attachments - Image Watermarking",
        "description": "Automatically process image attachments from emails, apply watermarks, and save to SharePoint",
        "secureParameters": {"ImageProcessorApiToken": {"type": "SecureString"}},
        "triggers": [
            {
                "type": "When a new email arrives (V3)",
                "connector": "Office 365 Outlook",
                "conditions": {
                    "hasAttachments": True,
                    "subject": "Contains 'process images'"
                }
            }
        ],
        "actions": [
            {
                "step": 1,
                "name": "Get email attachments",
                "type": "Get attachments (V2)",
                "connector": "Office 365 Outlook"
            },
            {
                "step": 2,
                "name": "Apply to each attachment",
                "type": "Apply to each",
                "forEach": "@outputs('Get_attachments_(V2)')?['body/value']",
                "actions": [
                    {
                        "name": "Condition - Check if image",
                        "type": "Condition",
                        "expression": "@contains(item()?['contentType'], 'image')"
                    },
                    {
                        "name": "HTTP - Process image",
                        "type": "HTTP",
                        "method": "POST",
                        "uri": "https://your-api-server.com/api/process-base64",
                        "headers": {
                            "Content-Type": "application/json",
                            "Authorization": "Bearer @{parameters('ImageProcessorApiToken')}"
                        },
                        "body": {
                            "image": "@item()?['contentBytes']",
                            "options": {
                                "quality": 85,
                                "opacity": 0.3,
                                "format": "JPEG"
                            }
                        }
                    },
                    {
                        "name": "Create file in SharePoint",
                        "type": "Create file",
                        "connector": "SharePoint",
                        "siteAddress": "https://yourtenant.sharepoint.com/sites/yoursite",
                        "folderPath": "/Shared Documents/Processed Images",
                        "fileName": "@{item()?['name']}_processed.jpg",
                        "fileContent": "@base64ToBinary(body('HTTP_-_Process_image')?['processed_image'])"
                    }
                ]
            },
            {
                "step": 3,
                "name": "Send confirmation email",
                "type": "Send an email (V2)",
                "connector": "Office 365 Outlook",
                "to": "@triggerBody()?['from']",
                "subject": "Images processed successfully",
                "body": "Your images have been processed and saved to SharePoint."
            }
        ]
    }
    
    # Template 2: SharePoint document library processing
    sharepoint_flow_template = {
        "displayName": "SharePoint Image Processing Workflow",
        "description": "Process images uploaded to SharePoint library with watermarks",
        "secureParameters": {"ImageProcessorApiToken": {"type": "SecureString"}},
        "triggers": [
            {
                "type": "When a file is created (properties only)",
                "connector": "SharePoint",
                "siteAddress": "https://yourtenant.sharepoint.com/sites/yoursite",
                "listName": "Documents",
                "folderPath": "/Input Images"
            }
        ],
        "actions": [
            {
                "step": 1,
                "name": "Get file properties",
                "type": "Get file properties",
                "connector": "SharePoint"
            },
            {
                "step": 2,
                "name": "Get file content",
                "type": "Get file content",
                "connector": "SharePoint"
            },
            {
                "step": 3,
                "name": "Condition - Check file type",
                "type": "Condition",
                "expression": "@or(endsWith(triggerBody()?['Name'], '.jpg'), endsWith(triggerBody()?['Name'], '.png'), endsWith(triggerBody()?['Name'], '.bmp'))"
            },
            {
                "step": 4,
                "name": "HTTP - Process image",
                "type": "HTTP",
                "method": "POST",
                "uri": "https://your-api-server.com/api/process-base64",
                "headers": {
                    "Content-Type": "application/json",
                    "Authorization": "Bearer @{parameters('ImageProcessorApiToken')}"
                },
                "body": {
                    "image": "@base64(body('Get_file_content'))",
                    "options": {
                        "quality": 85,
                        "opacity": 0.3,
                        "format": "JPEG",
                        "max_width": 1920,
                        "max_height": 1080
                    }
                }
            },
            {
                "step": 5,
                "name": "Create processed file",
                "type": "Create file",
                "connector": "SharePoint",
                "siteAddress": "https://yourtenant.sharepoint.com/sites/yoursite",
                "folderPath": "/Processed Images",
                "fileName": "@{replace(triggerBody()?['Name'], '.', '_processed.')}",
                "fileContent": "@base64ToBinary(body('HTTP_-_Process_image')?['processed_image'])"
            }
        ]
    }
    
    # Template 3: OneDrive batch processing
    onedrive_flow_template = {
        "displayName": "OneDrive Batch Image Processing",
        "description": "Process all images in a OneDrive folder on schedule",
        "secureParameters": {"ImageProcessorApiToken": {"type": "SecureString"}},
        "triggers": [
            {
                "type": "Recurrence",
                "frequency": "Day",
                "interval": 1,
                "startTime": "2024-01-01T09:00:00Z"
            }
        ],
        "actions": [
            {
                "step": 1,
                "name": "List files in folder",
                "type": "List files in folder",
                "connector": "OneDrive for Business",
                "folderPath": "/Images/To Process"
            },
            {
                "step": 2,
                "name": "Apply to each file",
                "type": "Apply to each",
                "forEach": "@outputs('List_files_in_folder')?['body/value']",
                "actions": [
                    {
                        "name": "Get file content",
                        "type": "Get file content",
                        "connector": "OneDrive for Business",
                        "file": "@item()?['Id']"
                    },
                    {
                        "name": "HTTP - Process image",
                        "type": "HTTP",
                        "method": "POST",
                        "uri": "https://your-api-server.com/api/process-base64",
                        "headers": {
                            "Content-Type": "application/json",
                            "Authorization": "Bearer @{parameters('ImageProcessorApiToken')}"
                        },
                        "body": {
                            "image": "@base64(body('Get_file_content'))",
                            "options": {
                                "quality": 80,
                                "format": "WEBP"
                            }
                        }
                    },
                    {
                        "name": "Create processed file",
                        "type": "Create file",
                        "connector": "OneDrive for Business",
                        "folderPath": "/Images/Processed",
                        "fileName": "@{replace(item()?['DisplayName'], '.', '_web.')}",
                        "fileContent": "@base64ToBinary(body('HTTP_-_Process_image')?['processed_image'])"
                    },
                    {
                        "name": "Move original file",
                        "type": "Move file",
                        "connector": "OneDrive for Business",
                        "source": "@item()?['Id']",
                        "destination": "/Images/Archive/@{item()?['DisplayName']}"
                    }
                ]
            }
        ]
    }
    
    # Save templates
    templates = {
        "email_processing": email_flow_template,
        "sharepoint_processing": sharepoint_flow_template,
        "onedrive_batch": onedrive_flow_template
    }
    
    for name, template in templates.items():
        template_file = templates_dir / f"{name}_flow.json"
        with open(template_file, 'w') as f:
            json.dump(template, f, indent=2)
        
        logger.info(f"Created Power Automate template: {template_file}")
    
    # Create README for templates
    readme_content = """# Power Automate Templates for Image Processing

This folder contains Power Automate flow templates for automated image processing.

## Templates Included

### 1. Email Processing Flow (`email_processing_flow.json`)
- **Trigger**: New email with attachments containing "process images" in subject
- **Action**: Process image attachments and save to SharePoint
- **Use Case**: Email-based image processing requests

### 2. SharePoint Processing Flow (`sharepoint_processing_flow.json`)
- **Trigger**: New file uploaded to SharePoint "Input Images" folder
- **Action**: Automatically process and save to "Processed Images" folder
- **Use Case**: Drop folder for automatic processing

### 3. OneDrive Batch Processing (`onedrive_batch.json`)
- **Trigger**: Daily scheduled run
- **Action**: Process all images in OneDrive folder and archive originals
- **Use Case**: Scheduled bulk processing

## Setup Instructions

1. **Deploy the API Server**
   - Host the Python API server (see `api_server.py`)
   - Update the URI in the templates to point to your server
   - Ensure the server is accessible from Power Automate

2. **Import Templates**
   - Open Power Automate (https://flow.microsoft.com)
   - Go to "My flows" > "Import"
   - Upload the JSON template file
   - Configure connections (SharePoint, OneDrive, Outlook)

3. **Customize Settings**
   - Update SharePoint site URLs
   - Modify folder paths
   - Adjust processing options (quality, format, etc.)
   - Set up proper error handling

## API Endpoints Used

- `POST /api/process-base64`: Process base64 encoded images
- `POST /api/process-image`: Process uploaded files
- `GET /api/health`: Health check

## Security Considerations

- Keep the API on localhost unless it is behind an authenticated HTTPS gateway
- Store ImageProcessorApiToken as a Power Platform secure parameter
- Validate file types and sizes
- Set up proper logging and monitoring

## Troubleshooting

- Check API server logs for processing errors
- Verify SharePoint/OneDrive permissions
- Test with small images first
- Monitor flow run history in Power Automate
"""
    
    readme_file = templates_dir / "README.md"
    with open(readme_file, 'w') as f:
        f.write(readme_content)
    
    logger.info(f"Created Power Automate documentation: {readme_file}")


def create_power_apps_integration():
    """Create Power Apps integration examples."""
    
    integration_dir = Path("power_platform/power_apps")
    integration_dir.mkdir(parents=True, exist_ok=True)
    
    # Power Apps formula examples
    formulas = {
        "camera_capture_and_process": """
// Formula for capturing and processing image from camera
Set(
    ProcessedImage,
    PowerPlatformAPI.ProcessImage(
        Camera1.Photo,
        {
            quality: Slider_Quality.Value,
            opacity: Slider_Opacity.Value,
            format: Dropdown_Format.Selected.Value,
            max_width: 1920,
            max_height: 1080
        }
    )
);

// Display success message
Notify("Image processed successfully!", NotificationType.Success)
        """,
        
        "gallery_batch_process": """
// Formula for processing multiple selected images
ForAll(
    Gallery_Images.AllItems,
    Set(
        ProcessResult,
        PowerPlatformAPI.ProcessImage(
            ThisItem.Image,
            {
                quality: 85,
                format: "JPEG"
            }
        )
    );
    
    // Save to SharePoint
    Patch(
        'Processed Images',
        Defaults('Processed Images'),
        {
            Title: ThisItem.Title & "_processed",
            Image: ProcessResult.processed_image
        }
    )
)
        """,
        
        "upload_to_api": """
// Formula for uploading to custom API
Set(
    APIResponse,
    PowerPlatformAPI.UploadAndProcess(
        {
            file: FileUpload1.File,
            options: {
                quality: Slider_Quality.Value,
                watermark_opacity: Slider_Opacity.Value,
                output_format: Dropdown_Format.Selected.Value
            }
        }
    )
);

If(
    APIResponse.success,
    Set(ResultImage, APIResponse.processed_image);
    Notify("Processing complete!", NotificationType.Success),
    Notify("Processing failed: " & APIResponse.error, NotificationType.Error)
)
        """
    }
    
    # Save formulas
    for name, formula in formulas.items():
        formula_file = integration_dir / f"{name}.txt"
        with open(formula_file, 'w') as f:
            f.write(formula)
    
    # Create Power Apps integration guide
    guide_content = """# Power Apps Integration Guide

## Custom Connector Setup

To integrate the Image Processor API with Power Apps, you'll need to create a custom connector.

### 1. Create Custom Connector

1. Go to Power Apps (https://make.powerapps.com)
2. Navigate to "Data" > "Custom connectors"
3. Click "New custom connector" > "Create from blank"
4. Configure the connector:

```json
{
  "swagger": "2.0",
  "info": {
    "title": "Image Processor API",
    "description": "Custom connector for image processing with watermarks",
    "version": "1.0"
  },
  "host": "your-api-server.com",
  "basePath": "/api",
  "schemes": ["https"],
  "consumes": ["application/json"],
  "produces": ["application/json"],
  "paths": {
    "/process-base64": {
      "post": {
        "summary": "Process Base64 Image",
        "operationId": "ProcessImage",
        "parameters": [
          {
            "name": "body",
            "in": "body",
            "required": true,
            "schema": {
              "type": "object",
              "properties": {
                "image": {"type": "string"},
                "options": {
                  "type": "object",
                  "properties": {
                    "quality": {"type": "integer"},
                    "opacity": {"type": "number"},
                    "format": {"type": "string"}
                  }
                }
              }
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Success",
            "schema": {
              "type": "object",
              "properties": {
                "success": {"type": "boolean"},
                "processed_image": {"type": "string"},
                "format": {"type": "string"}
              }
            }
          }
        }
      }
    }
  }
}
```

### 2. App Components

#### Image Upload Screen
- **AddMediaButton**: For selecting images
- **Camera**: For capturing photos
- **Gallery**: For displaying selected images
- **Sliders**: For quality and opacity settings
- **Dropdown**: For format selection

#### Processing Screen
- **Loading spinner**: Show during processing
- **Progress indicator**: For batch operations
- **Result display**: Show processed images
- **Download button**: Save processed images

#### Settings Screen
- **Input fields**: API endpoint configuration
- **Toggle switches**: Enable/disable features
- **Presets**: Save common processing settings

### 3. Example Screens

#### Main Processing Screen
```
Screen1:
  - Header: "Image Processor Pro"
  - ImageUpload: AddMediaButton
  - CameraCapture: Camera control
  - Settings Panel:
    - Quality: Slider (1-100)
    - Opacity: Slider (0.1-1.0)
    - Format: Dropdown (JPEG, PNG, WEBP)
  - ProcessButton: "Process Images"
  - ResultGallery: Display processed images
```

#### Batch Processing Screen
```
Screen2:
  - FileUpload: Multiple file selection
  - ProgressBar: Show batch progress
  - ResultsList: List of processed files
  - ExportButton: "Save All to SharePoint"
```

### 4. Key Formulas

See the `.txt` files in this folder for specific Power Apps formulas.

### 5. Error Handling

```powerapps
If(
    IsError(APIResponse),
    Notify("Network error: " & FirstError.Message, NotificationType.Error),
    If(
        APIResponse.success,
        Notify("Success!", NotificationType.Success),
        Notify("Processing error: " & APIResponse.error, NotificationType.Error)
    )
)
```

### 6. Performance Tips

- Use thumbnails for image previews
- Implement pagination for large image sets
- Cache processed images locally
- Use background processing for large files

### 7. Security Considerations

- Validate file sizes before upload
- Supply the required Bearer token from a secure Power Platform parameter
- Expose the API only through an authenticated HTTPS gateway
- Sanitize user inputs
"""
    
    guide_file = integration_dir / "integration_guide.md"
    with open(guide_file, 'w') as f:
        f.write(guide_content)
    
    logger.info(f"Created Power Apps integration guide: {guide_file}")


if __name__ == "__main__":
    # Create example configuration
    config = ProcessingConfig(
        watermark_path="watermarks/watermark.png",
        jpeg_quality=85,
        output_format="JPEG"
    )
    
    # Create templates and documentation
    create_power_automate_templates()
    create_power_apps_integration()
    
    # Example of starting the API server
    if FLASK_AVAILABLE:
        print("Power Platform API ready to start")
        print("To run the API server:")
        print("python power_platform/power_platform_integration.py")
        
        # Uncomment to start the server
        # api = PowerPlatformAPI(config)
        # api.run(debug=True)
    else:
        print("Flask not installed. Install with: pip install flask")
