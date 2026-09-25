import cloudinary
import cloudinary.uploader
from fastapi import UploadFile
from app.core.config import settings
import logging

logger = logging.getLogger("uvicorn.error")

# Configure Cloudinary globally using your environment settings
cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET,
    secure=True
)

async def upload_image_to_cloud(file: UploadFile, folder_name: str = "data_science_project") -> str:
    """
    Uploads an incoming file directly to Cloudinary and returns its secure HTTPS URL string.
    """
    try:
        # Read file contents into memory asynchronously
        file_bytes = await file.read()
        
        # Upload the file stream natively to Cloudinary
        upload_result = cloudinary.uploader.upload(
            file_bytes,
            folder=folder_name,
            resource_type="auto"  # Automatically detects if asset is an image, video, or document
        )
        
        # Extract and return the secure HTTPS link pointer
        secure_url = upload_result.get("secure_url")
        logger.info(f"Asset successfully uploaded to Cloudinary: {secure_url}")
        return secure_url

    except Exception as e:
        logger.error(f"Cloudinary upload failed: {e}")
        raise RuntimeError(f"Could not upload file to cloud storage: {e}")
    finally:
        # Reset file pointer read index just in case it is processed elsewhere
        await file.seek(0)
