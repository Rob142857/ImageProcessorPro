"""
Azure Cloud Integration for Image Processor
==========================================

Provides cloud processing capabilities using Azure services.
"""

import os
import sys
from typing import Optional, List, Dict, Any, Callable
import tempfile
import time
import warnings
from pathlib import Path
import json

# Azure Blob is the only supported production integration in this module.
try:
    from azure.storage.blob import BlobServiceClient, ContentSettings
    from azure.core.exceptions import ResourceExistsError
    BLOB_STORAGE_AVAILABLE = True
except ImportError:
    BLOB_STORAGE_AVAILABLE = False

try:
    from azure.identity import DefaultAzureCredential
    AZURE_IDENTITY_AVAILABLE = True
except ImportError:
    AZURE_IDENTITY_AVAILABLE = False

# Kept only for compatibility with existing installations. Azure Image Analysis
# is on a published retirement path and must not be selected for new workflows.
try:
    from azure.cognitiveservices.vision.computervision import ComputerVisionClient
    from azure.cognitiveservices.vision.computervision.models import OperationStatusCodes
    from msrest.authentication import CognitiveServicesCredentials
    LEGACY_VISION_AVAILABLE = True
except ImportError:
    LEGACY_VISION_AVAILABLE = False

# Core dependencies
from loguru import logger
from concurrent.futures import ThreadPoolExecutor

# Local imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from image_processor import ImageProcessor, ProcessingConfig


class AzureBlobStorage:
    """Azure Blob Storage integration for image processing."""
    
    def __init__(self, connection_string: Optional[str] = None,
                 container_name: str = "images", *,
                 account_url: Optional[str] = None,
                 credential: Any = None):
        if not BLOB_STORAGE_AVAILABLE:
            raise ImportError("Azure SDK not available. Install with: pip install azure-storage-blob")

        if connection_string:
            self.blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        elif account_url:
            if credential is None:
                if not AZURE_IDENTITY_AVAILABLE:
                    raise ImportError("Managed identity requires the azure-identity package")
                credential = DefaultAzureCredential()
            self.blob_service_client = BlobServiceClient(account_url=account_url, credential=credential)
        else:
            raise ValueError("Provide account_url for managed identity or a legacy connection string")

        self.container_name = container_name
        
        # Create container if it doesn't exist
        try:
            self.blob_service_client.create_container(container_name)
        except ResourceExistsError:
            pass
    
    def upload_image(self, image_data: bytes, blob_name: str,
                    content_type: str = "image/jpeg", *, overwrite: bool = False) -> str:
        """Upload image to Azure Blob Storage."""
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name, 
                blob=blob_name
            )
            
            blob_client.upload_blob(
                image_data,
                overwrite=overwrite,
                content_settings=ContentSettings(content_type=content_type)
            )
            
            return blob_client.url
        except Exception as e:
            logger.error(f"Failed to upload {blob_name} to Azure: {e}")
            raise
    
    def download_image(self, blob_name: str) -> bytes:
        """Download image from Azure Blob Storage."""
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            
            return blob_client.download_blob().readall()
        except Exception as e:
            logger.error(f"Failed to download {blob_name} from Azure: {e}")
            raise
    
    def list_blobs(self, prefix: str = "") -> List[str]:
        """List blobs in the container."""
        try:
            container_client = self.blob_service_client.get_container_client(self.container_name)
            blobs = container_client.list_blobs(name_starts_with=prefix)
            return [blob.name for blob in blobs]
        except Exception as e:
            logger.error(f"Failed to list blobs: {e}")
            raise
    
    def delete_blob(self, blob_name: str) -> None:
        """Delete a blob from storage."""
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            blob_client.delete_blob()
        except Exception as e:
            logger.error(f"Failed to delete {blob_name}: {e}")
            raise


class AzureComputerVision:
    """Deprecated compatibility wrapper; do not use for new workflows."""
    
    def __init__(self, subscription_key: str, endpoint: str):
        if not LEGACY_VISION_AVAILABLE:
            raise ImportError("Azure SDK not available. Install with: pip install azure-cognitiveservices-vision-computervision")

        warnings.warn(
            "Azure Image Analysis is retiring on 2028-09-25. "
            "This legacy integration is compatibility-only.",
            DeprecationWarning,
            stacklevel=2,
        )
        
        self.client = ComputerVisionClient(
            endpoint=endpoint,
            credentials=CognitiveServicesCredentials(subscription_key)
        )
    
    def analyze_image(self, image_url: str) -> Dict[str, Any]:
        """Analyze image using Azure Computer Vision."""
        try:
            features = ['categories', 'description', 'faces', 'image_type', 'tags']
            analysis = self.client.analyze_image(image_url, visual_features=features)
            
            return {
                'description': analysis.description.captions[0].text if analysis.description.captions else "",
                'tags': [tag.name for tag in analysis.tags],
                'categories': [cat.name for cat in analysis.categories],
                'faces': len(analysis.faces) if analysis.faces else 0,
                'image_type': {
                    'clip_art_type': analysis.image_type.clip_art_type,
                    'line_drawing_type': analysis.image_type.line_drawing_type
                }
            }
        except Exception as e:
            logger.error(f"Failed to analyze image: {e}")
            raise
    
    def detect_text(self, image_url: str) -> List[str]:
        """Detect text in image using OCR."""
        try:
            read_response = self.client.read(image_url, raw=True)
            operation_id = read_response.headers["Operation-Location"].split("/")[-1]
            
            # Wait for the operation to complete
            while True:
                read_result = self.client.get_read_result(operation_id)
                if read_result.status not in ['notStarted', 'running']:
                    break
                time.sleep(1)
            
            # Extract text
            text_lines = []
            if read_result.status == OperationStatusCodes.succeeded:
                for text_result in read_result.analyze_result.read_results:
                    for line in text_result.lines:
                        text_lines.append(line.text)
            
            return text_lines
        except Exception as e:
            logger.error(f"Failed to detect text: {e}")
            raise


class AzureImageProcessor:
    """Cloud-based image processor using Azure services."""
    
    def __init__(self, config: ProcessingConfig, 
                 blob_connection_string: Optional[str] = None,
                 blob_account_url: Optional[str] = None,
                 blob_credential: Any = None,
                 cv_subscription_key: Optional[str] = None,
                 cv_endpoint: Optional[str] = None):
        
        self.config = config
        self.local_processor = ImageProcessor(config)
        
        # Initialize Azure services if credentials provided
        self.blob_storage = None
        self.computer_vision = None
        
        if blob_account_url or blob_connection_string:
            self.blob_storage = AzureBlobStorage(
                blob_connection_string,
                account_url=blob_account_url,
                credential=blob_credential,
            )
        
        if cv_subscription_key and cv_endpoint:
            self.computer_vision = AzureComputerVision(cv_subscription_key, cv_endpoint)
    
    def process_images_cloud(self, 
                           input_container: str = "input",
                           output_container: str = "output",
                           progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """Process images stored in Azure Blob Storage."""
        
        if not self.blob_storage:
            raise ValueError("Azure Blob Storage not configured")
        
        try:
            # List input images
            input_blobs = self.blob_storage.list_blobs()
            if not input_blobs:
                logger.warning("No images found in input container")
                return {"processed": 0, "failed": 0, "total": 0}
            
            logger.info(f"Found {len(input_blobs)} images to process")
            
            results = {"processed": 0, "failed": 0, "total": len(input_blobs)}
            
            # Process each image
            with ThreadPoolExecutor(max_workers=self.config.max_workers or 4) as executor:
                futures = []
                
                for blob_name in input_blobs:
                    future = executor.submit(self._process_cloud_image, blob_name, output_container)
                    futures.append((future, blob_name))
                
                # Process results
                for i, (future, blob_name) in enumerate(futures):
                    try:
                        if future.result():
                            results["processed"] += 1
                            logger.info(f"Successfully processed: {blob_name}")
                        else:
                            results["failed"] += 1
                            logger.error(f"Failed to process: {blob_name}")
                    except Exception as e:
                        results["failed"] += 1
                        logger.error(f"Error processing {blob_name}: {e}")
                    
                    if progress_callback:
                        progress_callback(i + 1, len(futures))
            
            return results
            
        except Exception as e:
            logger.error(f"Cloud processing failed: {e}")
            raise
    
    def _process_cloud_image(self, input_blob_name: str, output_container: str) -> bool:
        """Process a single image in the cloud."""
        try:
            # Download image
            image_data = self.blob_storage.download_image(input_blob_name)
            
            # A private temporary directory avoids Windows NamedTemporaryFile
            # locking and guarantees cleanup on every exit path.
            with tempfile.TemporaryDirectory(prefix="mjw-image-") as temp_dir:
                temp_input = Path(temp_dir) / (Path(input_blob_name).name or "input.jpg")
                temp_output = Path(temp_dir) / f"output.{self.config.output_format.lower()}"
                temp_input.write_bytes(image_data)

                success = self.local_processor.process_single_image(str(temp_input), str(temp_output))
                if not success:
                    return False

                processed_data = temp_output.read_bytes()
                output_blob_name = self._get_output_blob_name(input_blob_name)
                content_type = self._get_content_type(self.config.output_format)
                url = self.blob_storage.upload_image(
                    processed_data,
                    output_blob_name,
                    content_type,
                    overwrite=False,
                )

                logger.debug(f"Uploaded processed image: {url}")
                return True
                    
        except Exception as e:
            logger.error(f"Failed to process cloud image {input_blob_name}: {e}")
            return False
    
    def _get_output_blob_name(self, input_blob_name: str) -> str:
        """Generate output blob name."""
        path = Path(input_blob_name)
        return f"processed/{path.stem}.{self.config.output_format.lower()}"
    
    def _get_content_type(self, format_name: str) -> str:
        """Get MIME content type for format."""
        types = {
            'JPEG': 'image/jpeg',
            'PNG': 'image/png',
            'WEBP': 'image/webp'
        }
        return types.get(format_name.upper(), 'image/jpeg')
    
    def analyze_images(self, blob_names: List[str]) -> Dict[str, Dict[str, Any]]:
        """Analyze images using Azure Computer Vision."""
        if not self.computer_vision:
            raise ValueError("Azure Computer Vision not configured")
        
        results = {}
        
        for blob_name in blob_names:
            try:
                # Get blob URL (assuming public access or generate SAS token)
                blob_client = self.blob_storage.blob_service_client.get_blob_client(
                    container=self.blob_storage.container_name,
                    blob=blob_name
                )
                
                analysis = self.computer_vision.analyze_image(blob_client.url)
                results[blob_name] = analysis
                
            except Exception as e:
                logger.error(f"Failed to analyze {blob_name}: {e}")
                results[blob_name] = {"error": str(e)}
        
        return results
    
    def batch_upload_from_local(self, local_folder: str, 
                               blob_prefix: str = "",
                               progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """Upload local images to Azure Blob Storage."""
        if not self.blob_storage:
            raise ValueError("Azure Blob Storage not configured")
        
        # Get local image files
        image_files = self.local_processor.get_image_files(local_folder)
        
        if not image_files:
            logger.warning(f"No images found in {local_folder}")
            return {"uploaded": 0, "failed": 0, "total": 0}
        
        results = {"uploaded": 0, "failed": 0, "total": len(image_files)}
        
        with ThreadPoolExecutor(max_workers=self.config.max_workers or 4) as executor:
            futures = []
            
            for file_path in image_files:
                future = executor.submit(self._upload_single_file, file_path, local_folder, blob_prefix)
                futures.append((future, file_path))
            
            for i, (future, file_path) in enumerate(futures):
                try:
                    if future.result():
                        results["uploaded"] += 1
                    else:
                        results["failed"] += 1
                except Exception as e:
                    results["failed"] += 1
                    logger.error(f"Error uploading {file_path}: {e}")
                
                if progress_callback:
                    progress_callback(i + 1, len(futures))
        
        return results
    
    def _upload_single_file(self, file_path: str, base_folder: str, blob_prefix: str) -> bool:
        """Upload a single file to blob storage."""
        try:
            # Generate blob name
            rel_path = os.path.relpath(file_path, base_folder)
            blob_name = f"{blob_prefix}{rel_path}".replace("\\", "/")
            
            # Read file
            with open(file_path, 'rb') as f:
                file_data = f.read()
            
            # Determine content type
            ext = Path(file_path).suffix.lower()
            content_type_map = {
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.bmp': 'image/bmp',
                '.tiff': 'image/tiff',
                '.tif': 'image/tiff'
            }
            content_type = content_type_map.get(ext, 'application/octet-stream')
            
            # Upload
            url = self.blob_storage.upload_image(file_data, blob_name, content_type, overwrite=False)
            logger.debug(f"Uploaded {file_path} to {url}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to upload {file_path}: {e}")
            return False


# Configuration helper functions
def load_azure_config() -> Dict[str, str]:
    """Load Azure configuration from environment variables or config file."""
    config = {}
    
    # Try environment variables first
    env_vars = {
        'blob_connection_string': 'AZURE_STORAGE_CONNECTION_STRING',
        'blob_account_url': 'AZURE_STORAGE_ACCOUNT_URL',
        'cv_subscription_key': 'AZURE_CV_SUBSCRIPTION_KEY',
        'cv_endpoint': 'AZURE_CV_ENDPOINT'
    }
    
    for key, env_var in env_vars.items():
        value = os.getenv(env_var)
        if value:
            config[key] = value
    
    # Try config file
    config_file = Path("config/azure_config.json")
    if config_file.exists():
        try:
            with open(config_file, 'r') as f:
                file_config = json.load(f)
                for key, value in file_config.items():
                    if key not in config and value:
                        config[key] = value
        except Exception as e:
            logger.warning(f"Failed to load Azure config file: {e}")
    
    return config


def create_azure_config_template() -> None:
    """Create a template Azure configuration file."""
    config_template = {
        "blob_account_url": "https://your-account.blob.core.windows.net",
        "authentication": "Use DefaultAzureCredential / managed identity; do not store account keys here",
        "legacy_vision": "Deprecated; evaluate a supported replacement before enabling AI analysis"
    }
    
    os.makedirs("config", exist_ok=True)
    
    with open("config/azure_config_template.json", 'w') as f:
        json.dump(config_template, f, indent=2)
    
    logger.info("Created Azure config template at config/azure_config_template.json")
    logger.info("Use AZURE_STORAGE_ACCOUNT_URL with DefaultAzureCredential; do not store secrets in this file")


if __name__ == "__main__":
    # Example usage
    create_azure_config_template()
    
    # Example of using Azure services
    azure_config = load_azure_config()
    
    if azure_config.get('blob_account_url') or azure_config.get('blob_connection_string'):
        config = ProcessingConfig(
            watermark_path="watermarks/watermark.png",
            jpeg_quality=85,
            output_format="JPEG"
        )
        
        azure_processor = AzureImageProcessor(
            config,
            blob_connection_string=azure_config.get('blob_connection_string'),
            blob_account_url=azure_config.get('blob_account_url'),
            cv_subscription_key=azure_config.get('cv_subscription_key'),
            cv_endpoint=azure_config.get('cv_endpoint')
        )
        
        print("Azure Image Processor initialized successfully")
    else:
        print("Azure configuration not found. Set AZURE_STORAGE_ACCOUNT_URL for managed identity.")
