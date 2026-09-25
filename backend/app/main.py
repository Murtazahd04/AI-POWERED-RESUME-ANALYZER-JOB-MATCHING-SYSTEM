from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import connect_to_mongo, close_mongo_connection
from app.routes.media import router as media_router
from app.services.ai_service import verify_gemini_connection
# 1. Define Server Lifespan Events (Manages MongoDB Connection)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Runs automatically when your Uvicorn server Boots Up
    await connect_to_mongo()
    yield
    # Runs automatically when your Uvicorn server Shuts Down
    await close_mongo_connection()

# 2. Instantiate the FastAPI Engine
app = FastAPI(title="My React-FastAPI App", lifespan=lifespan)

# 3. Configure Cross-Origin Resource Sharing (CORS)
# This allows the local Vite frontend and the deployed production frontend to access the API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 4. Mount Sub-Routers (Enables your Cloudinary /media/upload endpoint layout)
app.include_router(media_router)

# 5. Core Operational Endpoints
@app.get("/")
def read_root():
    """Baseline application health check path."""
    return {"message": "FastAPI backend is running successfully!"}

@app.get("/test-config")
def test_config():
    """
    Security check path. 
    Verifies that your .env properties are loading into memory without leaking credentials.
    """
    return {
        "database_connected": bool(settings.MONGODB_URL),
        "ai_model": settings.AI_MODEL_NAME,
        "cloudinary_active": bool(settings.CLOUDINARY_CLOUD_NAME)
    }
@app.get("/test-gemini")
async def test_gemini():
    """Endpoint that utilizes the AI service layer to verify Gemini connectivity."""
    try:
        response_text = await verify_gemini_connection()
        return {
            "status": "success",
            "model_used": settings.AI_MODEL_NAME,
            "gemini_response": response_text
        }
    except Exception as e:
        return {
            "status": "failed",
            "error_details": str(e)
        }