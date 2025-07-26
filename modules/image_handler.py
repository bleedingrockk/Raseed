import base64
import os
from werkzeug.utils import secure_filename
from flask import current_app
import uuid

class ImageHandler:
    """Handle image upload and processing"""
    
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}
    UPLOAD_FOLDER = 'uploads'
    
    @staticmethod
    def allowed_file(filename):
        """Check if the file extension is allowed"""
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in ImageHandler.ALLOWED_EXTENSIONS
    
    @staticmethod
    def ensure_upload_folder():
        """Ensure upload folder exists"""
        if not os.path.exists(ImageHandler.UPLOAD_FOLDER):
            os.makedirs(ImageHandler.UPLOAD_FOLDER)
    
    @staticmethod
    def save_image(file):
        """Save uploaded image and return file path"""
        if file and ImageHandler.allowed_file(file.filename):
            # Ensure upload folder exists
            ImageHandler.ensure_upload_folder()
            
            # Generate unique filename
            filename = secure_filename(file.filename)
            unique_filename = f"{uuid.uuid4().hex}_{filename}"
            file_path = os.path.join(ImageHandler.UPLOAD_FOLDER, unique_filename)
            
            # Save file
            file.save(file_path)
            return file_path
        return None
    
    @staticmethod
    def image_to_base64(file_path):
        """Convert image file to base64 string"""
        try:
            with open(file_path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
                return encoded_string
        except Exception as e:
            print(f"Error converting image to base64: {e}")
            return None
    
    @staticmethod
    def get_image_info(file_path):
        """Get image information including base64 data"""
        if not os.path.exists(file_path):
            return None
        
        try:
            # Get file size
            file_size = os.path.getsize(file_path)
            
            # Convert to base64
            base64_data = ImageHandler.image_to_base64(file_path)
            
            # Get file extension
            file_extension = os.path.splitext(file_path)[1].lower()
            
            return {
                'file_path': file_path,
                'file_size': file_size,
                'file_extension': file_extension,
                'base64_data': base64_data,
                'filename': os.path.basename(file_path)
            }
        except Exception as e:
            print(f"Error getting image info: {e}")
            return None
    
    @staticmethod
    def cleanup_old_files(max_age_hours=24):
        """Clean up old uploaded files"""
        import time
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        
        if not os.path.exists(ImageHandler.UPLOAD_FOLDER):
            return
        
        for filename in os.listdir(ImageHandler.UPLOAD_FOLDER):
            file_path = os.path.join(ImageHandler.UPLOAD_FOLDER, filename)
            if os.path.isfile(file_path):
                file_age = current_time - os.path.getmtime(file_path)
                if file_age > max_age_seconds:
                    try:
                        os.remove(file_path)
                        print(f"Cleaned up old file: {filename}")
                    except Exception as e:
                        print(f"Error cleaning up file {filename}: {e}") 