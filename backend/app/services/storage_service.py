import cloudinary
import cloudinary.uploader

from ..config import get_settings

_configured = False


def _ensure_configured() -> None:
    global _configured
    if _configured:
        return
    s = get_settings()
    if not (s.cloudinary_cloud_name and s.cloudinary_api_key and s.cloudinary_api_secret):
        raise RuntimeError("Cloudinary is not configured. Check the CLOUDINARY_* values in backend/.env")
    cloudinary.config(
        cloud_name=s.cloudinary_cloud_name,
        api_key=s.cloudinary_api_key,
        api_secret=s.cloudinary_api_secret,
        secure=True,
    )
    _configured = True


def upload_resume(data: bytes, filename: str, user_id: str) -> dict:
    """Send the file to Cloudinary. 'raw' means 'not an image' (PDFs/DOCX)."""
    _ensure_configured()
    result = cloudinary.uploader.upload(
        data,
        resource_type="raw",
        folder=f"resumes/{user_id}",
        use_filename=True,
        unique_filename=True,
        filename_override=filename,
    )
    return {"public_id": result["public_id"], "url": result["secure_url"]}


def delete_resume(public_id: str) -> None:
    _ensure_configured()
    cloudinary.uploader.destroy(public_id, resource_type="raw")