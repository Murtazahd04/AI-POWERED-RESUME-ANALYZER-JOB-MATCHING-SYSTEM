from fastapi import APIRouter, UploadFile, File, HTTPException
from app.services.cloudinary_service import upload_image_to_cloud

router = APIRouter(prefix="/media", tags=["Media Storage"])

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    # Guard clause to check if an actual file filename was delivered
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file payload detected.")
        
    # Execute our cloud service helper
    url = await upload_image_to_cloud(file)
    return {"message": "Upload successful!", "file_url": url}
