import base64
import os
import logging
import uuid
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from google.cloud import storage
from google.cloud.exceptions import GoogleCloudError

# --- IMPORTANT: Set your service account key path here ---
os.environ.setdefault('GOOGLE_APPLICATION_CREDENTIALS', 'modules/graphite-record-467002-g2-6004dd9c6b4e.json')
os.environ.setdefault('GCS_BUCKET_NAME', 'hackathon2024neocoders1')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SimpleImageHandler:
    """Simplified image handler for GCS upload and base64 conversion"""
    
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}
    BUCKET_NAME = os.environ.get('GCS_BUCKET_NAME', 'hackathon2024neocoders1').strip()
    
    @staticmethod
    def allowed_file(filename):
        """Check if the file extension is allowed"""
        if not filename or '.' not in filename:
            return False
        extension = filename.rsplit('.', 1)[1].lower()
        return extension in SimpleImageHandler.ALLOWED_EXTENSIONS
    
    @staticmethod
    def upload_image(file, filename=None):
        """
        Upload image to Google Cloud Storage and return URL with confirmation
        
        Args:
            file: File object to upload
            filename: Optional custom filename (will use file.filename if not provided)
            
        Returns:
            dict: {'success': bool, 'url': str, 'message': str}
        """
        try:
            # Use provided filename or get from file object
            if not filename:
                filename = getattr(file, 'filename', 'uploaded_image.jpg')
            
            # Validate file
            if not file:
                return {'success': False, 'url': None, 'message': 'No file provided'}
            
            if not SimpleImageHandler.allowed_file(filename):
                return {'success': False, 'url': None, 'message': 'File type not allowed'}
            
            # Initialize GCS client
            client = storage.Client()
            bucket = client.bucket(SimpleImageHandler.BUCKET_NAME)
            
            # Generate unique blob name with timestamp folder structure
            timestamp_path = datetime.now().strftime('%Y/%m/%d')
            unique_id = str(uuid.uuid4())[:8]  # Shorter UUID for cleaner names
            secured_filename = secure_filename(filename)
            blob_name = f"images/{timestamp_path}/{unique_id}_{secured_filename}"
            
            # Upload file
            blob = bucket.blob(blob_name)
            file.seek(0)  # Reset file pointer
            content_type = getattr(file, 'content_type', 'image/jpeg')
            blob.upload_from_file(file, content_type=content_type)
            
            # Generate signed URL (valid for 24 hours)
            url = blob.generate_signed_url(
                version="v4",
                expiration=timedelta(hours=24),
                method="GET"
            )
            
            logger.info(f"Successfully uploaded {filename} to {blob_name}")
            
            return {
                'success': True,
                'url': url,
                'message': f'Image uploaded successfully as {blob_name}'
            }
            
        except GoogleCloudError as e:
            error_msg = f"Google Cloud Storage error: {str(e)}"
            logger.error(error_msg)
            return {'success': False, 'url': None, 'message': error_msg}
        
        except Exception as e:
            error_msg = f"Upload failed: {str(e)}"
            logger.error(error_msg)
            return {'success': False, 'url': None, 'message': error_msg}
    
    @staticmethod
    def image_to_base64(file_path):
        """
        Convert image file to base64 string
        
        Args:
            file_path: Path to the image file
            
        Returns:
            dict: {'success': bool, 'base64': str, 'message': str}
        """
        try:
            if not os.path.exists(file_path):
                return {'success': False, 'base64': None, 'message': 'File not found'}
            
            with open(file_path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
                
            return {
                'success': True,
                'base64': encoded_string,
                'message': 'Image converted to base64 successfully'
            }
            
        except Exception as e:
            error_msg = f"Base64 conversion failed: {str(e)}"
            logger.error(error_msg)
            return {'success': False, 'base64': None, 'message': error_msg}


# Example usage
if __name__ == '__main__':
    """
    Example of how to use the SimpleImageHandler
    """
    print("=== Simple Image Handler Demo ===")
    
    # Create a test image file
    test_image_path = "test_image.png"
    # Minimal PNG image data
    png_data = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
    
    try:
        with open(test_image_path, "wb") as f:
            f.write(base64.b64decode(png_data))
        print(f"✓ Created test image: {test_image_path}")
    except Exception as e:
        print(f"✗ Failed to create test image: {e}")
        exit()
    
    # Simulate file upload object
    class MockFile:
        def __init__(self, path, filename):
            self.path = path
            self.filename = filename
            self.content_type = "image/png"
            self._file = open(path, "rb")
        
        def read(self, size=-1):
            return self._file.read(size)
        
        def seek(self, offset, whence=0):
            return self._file.seek(offset, whence)
        
        def close(self):
            self._file.close()
    
    # Test upload
    mock_file = MockFile(test_image_path, "my_test_image.png")
    
    print("\n--- Testing Image Upload ---")
    result = SimpleImageHandler.upload_image(mock_file)
    
    if result['success']:
        print(f"✓ Upload successful!")
        print(f"  URL: {result['url']}")
        print(f"  Message: {result['message']}")
    else:
        print(f"✗ Upload failed: {result['message']}")
    
    mock_file.close()
    
    # Test base64 conversion
    print("\n--- Testing Base64 Conversion ---")
    base64_result = SimpleImageHandler.image_to_base64(test_image_path)
    
    if base64_result['success']:
        print(f"✓ Base64 conversion successful!")
        print(f"  Base64 length: {len(base64_result['base64'])} characters")
        print(f"  Base64 preview: {base64_result['base64'][:50]}...")
        print(f"  Message: {base64_result['message']}")
    else:
        print(f"✗ Base64 conversion failed: {base64_result['message']}")
    
    # Cleanup
    try:
        os.remove(test_image_path)
        print(f"\n✓ Cleaned up test file: {test_image_path}")
    except Exception as e:
        print(f"✗ Failed to cleanup: {e}")
    
    print("\n=== Demo Complete ===")