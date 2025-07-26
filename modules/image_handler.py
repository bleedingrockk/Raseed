import base64
import os
import logging
import uuid
from datetime import datetime, timedelta
import traceback
from werkzeug.utils import secure_filename
from google.cloud import storage
from google.cloud.exceptions import GoogleCloudError

# --- IMPORTANT: Set your service account key path here ---
# This path should point to the JSON file you downloaded from Google Cloud for your service account.
# For example, if your file is in the 'modules' directory relative to your script:
# os.environ.setdefault('GOOGLE_APPLICATION_CREDENTIALS', 'modules/graphite-record-467002-g2-6004dd9c6b4e.json')
# Ensure this path is correct for your environment.
os.environ.setdefault('GOOGLE_APPLICATION_CREDENTIALS', 'modules/graphite-record-467002-g2-6004dd9c6b4e.json')

# Set GCS bucket name (FIXED: Removed leading space)
os.environ.setdefault('GCS_BUCKET_NAME', 'hackathon_26072025')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ImageHandler:
    """Handle image upload and processing with GCS"""
    
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}
    # Retrieve bucket name from environment variable, ensuring no leading/trailing spaces
    BUCKET_NAME = os.environ.get('GCS_BUCKET_NAME', 'hackathon2024neocoders').strip()
    
    @staticmethod
    def allowed_file(filename):
        """Check if the file extension is allowed"""
        try:
            if not filename or '.' not in filename:
                return False
            extension = filename.rsplit('.', 1)[1].lower()
            return extension in ImageHandler.ALLOWED_EXTENSIONS
        except Exception as e:
            logger.error(f"Error checking file extension for {filename}: {str(e)}")
            return False
    
    @staticmethod
    def upload_to_gcs(file, filename):
        """Upload file to Google Cloud Storage with comprehensive error handling"""
        try:
            logger.info(f"Starting upload for file: {filename} to bucket: {ImageHandler.BUCKET_NAME}")
            
            if not file:
                logger.error("No file provided for upload")
                return None, "No file provided"
            
            if not filename:
                logger.error("No filename provided for upload")
                return None, "No filename provided"
            
            if not ImageHandler.BUCKET_NAME or ImageHandler.BUCKET_NAME == 'your-bucket-name':
                logger.error("Bucket name not configured properly or is default placeholder.")
                return None, "Storage configuration error: Bucket name is invalid."
            
            # Initialize GCS client
            # The storage.Client() constructor will automatically pick up credentials
            # from GOOGLE_APPLICATION_CREDENTIALS environment variable.
            try:
                client = storage.Client()
                logger.info("Google Cloud Storage client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize GCS client. Check GOOGLE_APPLICATION_CREDENTIALS: {str(e)}")
                return None, "Storage service unavailable or authentication failed."
            
            # Access bucket
            try:
                bucket = client.bucket(ImageHandler.BUCKET_NAME)
                # It's good practice to check if the bucket exists or if you have permission to access it.
                # Note: bucket.exists() might incur a small cost/latency. For production,
                # rely on proper IAM setup rather than runtime checks if performance is critical.
                # You might comment out the exists() check after initial development if you're sure
                # the bucket exists and permissions are set.
                if not bucket.exists():
                    logger.error(f"Bucket '{ImageHandler.BUCKET_NAME}' does not exist or client lacks permission to view it. Please create the bucket manually.")
                    return None, "Storage bucket not found or access denied."
            except GoogleCloudError as e:
                logger.error(f"Error accessing bucket '{ImageHandler.BUCKET_NAME}': {str(e)}")
                return None, "Storage access error"
            except Exception as e:
                logger.error(f"Unexpected error accessing bucket: {str(e)}")
                return None, "Storage configuration error"
            
            # Generate blob name
            try:
                # Use current date to simulate folder structure (YYYY/MM/DD)
                timestamp_path = datetime.now().strftime('%Y/%m/%d')
                unique_id = str(uuid.uuid4())
                secured_filename = secure_filename(filename)
                # Construct path: images/YYYY/MM/DD/unique_id_filename.ext
                blob_name = f"images/{timestamp_path}/{unique_id}_{secured_filename}"
                logger.info(f"Generated blob name: {blob_name}")
            except Exception as e:
                logger.error(f"Error generating blob name: {str(e)}")
                return None, "File naming error"
            
            # Upload file
            try:
                blob = bucket.blob(blob_name)
                file.seek(0) # Ensure the file pointer is at the beginning
                content_type = getattr(file, 'content_type', 'application/octet-stream')
                blob.upload_from_file(file, content_type=content_type)
                logger.info(f"File uploaded successfully to {blob_name}")
                
                # Generate signed URL (more secure than public)
                url = blob.generate_signed_url(
                    version="v4",
                    expiration=timedelta(hours=24), # URL is valid for 24 hours
                    method="GET"
                )
                logger.info("Generated signed URL for file")
                
                return url, None
                
            except GoogleCloudError as e:
                logger.error(f"Google Cloud Storage error during upload: {str(e)}")
                return None, "Upload failed due to storage error"
            except Exception as e:
                logger.error(f"Unexpected error during upload: {str(e)}")
                logger.error(f"Traceback: {traceback.format_exc()}") # More detailed error
                return None, "Upload failed due to unexpected error"
                
        except Exception as e:
            logger.error(f"Critical error in upload_to_gcs: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None, "Critical upload error"
    
    @staticmethod
    def save_image(file):
        """Save uploaded image to GCS and return URL"""
        if file and ImageHandler.allowed_file(file.filename):
            url, error = ImageHandler.upload_to_gcs(file, file.filename)
            if url:
                return url  # Return URL instead of file path
            else:
                logger.error(f"Failed to upload to GCS: {error}")
                return None
        logger.warning(f"File not allowed or no file provided: {getattr(file, 'filename', 'No file object')}")
        return None
    
    @staticmethod
    def image_to_base64(file_path_or_url):
        """Convert image file to base64 string - works with local files only"""
        if file_path_or_url.startswith('http'):
            logger.warning("Cannot convert URL to base64 directly. Download file first if local base64 is required.")
            return None
            
        try:
            with open(file_path_or_url, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
                return encoded_string
        except FileNotFoundError:
            logger.error(f"File not found at: {file_path_or_url}")
            return None
        except Exception as e:
            logger.error(f"Error converting image to base64: {e}")
            return None
    
    @staticmethod
    def get_image_info(file_path_or_url):
        """Get image information - limited for URLs"""
        if file_path_or_url.startswith('http'):
            # For URLs, return limited info
            return {
                'url': file_path_or_url,
                'storage_type': 'gcs',
                'filename': file_path_or_url.split('/')[-1].split('?')[0] # Get filename before query params
            }
            
        # For local files
        if not os.path.exists(file_path_or_url):
            logger.warning(f"Local file not found: {file_path_or_url}")
            return None
        
        try:
            file_size = os.path.getsize(file_path_or_url)
            base64_data = ImageHandler.image_to_base64(file_path_or_url)
            file_extension = os.path.splitext(file_path_or_url)[1].lower()
            
            return {
                'file_path': file_path_or_url,
                'file_size': file_size,
                'file_extension': file_extension,
                'base64_data': base64_data,
                'filename': os.path.basename(file_path_or_url),
                'storage_type': 'local'
            }
        except Exception as e:
            logger.error(f"Error getting image info for local file {file_path_or_url}: {e}")
            return None
    
    @staticmethod
    def cleanup_old_files(max_age_hours=24):
        """
        Clean up old uploaded files from GCS. This requires listing and deleting
        objects, which can be time-consuming for large buckets.
        
        This is a basic implementation and could be optimized (e.g., using object lifecycle policies
        in GCS directly for automatic deletion).
        """
        logger.info(f"Attempting to clean up GCS files older than {max_age_hours} hours...")
        
        try:
            client = storage.Client()
            bucket = client.bucket(ImageHandler.BUCKET_NAME)
            
            if not bucket.exists():
                logger.warning(f"Bucket {ImageHandler.BUCKET_NAME} does not exist for cleanup. Skipping cleanup.")
                return
            
            # Define the cutoff time
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
            
            deleted_count = 0
            # List blobs in the 'images/' prefix (assuming all images are under this prefix)
            # Use 'versions=False' to only get current versions of objects, if versioning is enabled.
            # Otherwise, you might delete old versions as well.
            for blob in bucket.list_blobs(prefix="images/"):
                # Blobs that are directories (like 'images/2024/07/27/') don't have update_time.
                # Only process actual files.
                if blob.update_time and blob.update_time.replace(tzinfo=None) < cutoff_time:
                    try:
                        blob.delete()
                        logger.info(f"Deleted old file: {blob.name}")
                        deleted_count += 1
                    except GoogleCloudError as e:
                        logger.error(f"Error deleting blob {blob.name}: {str(e)}")
                    except Exception as e:
                        logger.error(f"Unexpected error deleting blob {blob.name}: {str(e)}")
            
            logger.info(f"Cleanup complete. Deleted {deleted_count} old files from GCS.")
            
        except GoogleCloudError as e:
            logger.error(f"Google Cloud Storage error during cleanup: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during cleanup: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")


# if __name__ block
if __name__ == '__main__':
    """
    This block demonstrates how to use the ImageHandler class locally.
    In a real application (e.g., Flask, Django), the 'file' object
    would typically come from a web request (e.g., request.files['image_field']).
    """
    
    print("--- Starting ImageHandler Demonstration ---")

    # 1. Create a dummy file for simulating an upload
    dummy_file_path = "demo_test_image.png"
    # A tiny transparent PNG image encoded in base64
    base64_png_data = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
    try:
        with open(dummy_file_path, "wb") as f:
            f.write(base64.b64decode(base64_png_data))
        print(f"Created a dummy file: {dummy_file_path}")
    except Exception as e:
        print(f"Error creating dummy file: {e}")
        exit() # Exit if we can't create the dummy file

    # 2. Simulate a file object similar to what you'd get from a web framework
    class DummyFile:
        def __init__(self, path, filename, content_type):
            self.path = path
            self.filename = filename
            # Open the file in binary read mode
            self._file = open(path, "rb")
            self.content_type = content_type

        def __getattr__(self, name):
            # Delegate common file methods (read, seek, tell, close) to the actual file object
            return getattr(self._file, name)
        
        def close(self):
            # Ensure the underlying file object is closed
            self._file.close()
            
    # Instantiate the dummy file
    dummy_upload_file = DummyFile(dummy_file_path, "my_uploaded_photo.png", "image/png")

    print(f"\nAttempting to upload file '{dummy_upload_file.filename}' to GCS...")
    
    # 3. Call the save_image method to upload
    uploaded_url = ImageHandler.save_image(dummy_upload_file)
    
    # IMPORTANT: Always close the dummy file object after use
    dummy_upload_file.close() 

    if uploaded_url:
        print(f"\nSUCCESS: Image uploaded to GCS!")
        print(f"  Generated URL: {uploaded_url}")
        
        # 4. Get information about the uploaded image using its URL
        print("\nRetrieving image information from the URL:")
        image_info = ImageHandler.get_image_info(uploaded_url)
        if image_info:
            for key, value in image_info.items():
                print(f"    {key}: {value}")
        else:
            print("  FAILED to retrieve image info from URL.")

    else:
        print("\nFAILURE: Image upload to GCS failed. Check logs above for details.")

    # 5. Clean up the locally created dummy file
    if os.path.exists(dummy_file_path):
        try:
            os.remove(dummy_file_path)
            print(f"\nCleaned up local dummy file: {dummy_file_path}")
        except Exception as e:
            print(f"Error cleaning up dummy file {dummy_file_path}: {e}")

    # 6. Optional: Demonstrate cleanup of old files in GCS (USE WITH CAUTION IN PRODUCTION!)
    # To test cleanup, you might upload a file, wait a very short period (e.g., 10 seconds),
    # then set max_age_hours to a very small number like 0.001 (approx 3.6 seconds).
    # Be extremely careful with this in a production bucket.
    # print("\n--- Attempting GCS Cleanup (Testing purposes) ---")
    # ImageHandler.cleanup_old_files(max_age_hours=0.001) # Cleans up files older than approx 3.6 seconds
    # print("--- GCS Cleanup Attempt Finished ---")

    print("\n--- ImageHandler Demonstration Complete ---")