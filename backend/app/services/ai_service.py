from google import genai
from app.core.config import settings
import logging

logger = logging.getLogger("uvicorn.error")

# Initialize the official Google GenAI Client using your .env key
try:
    client = genai.Client(api_key=settings.AI_API_KEY)
    logger.info("Gemini AI Client successfully initialized.")
except Exception as e:
    logger.error(f"Failed to initialize Gemini AI Client: {e}")

async def verify_gemini_connection() -> str:
    """
    Sends a simple text request to Gemini to verify that the API key 
    and network connection are working correctly.
    """
    try:
        response = client.models.generate_content(
            model=settings.AI_MODEL_NAME,
            contents="Say 'Gemini is fully functional!'"
        )
        return response.text.strip()
    except Exception as e:
        logger.error(f"Gemini API call failed: {e}")
        raise RuntimeError(f"Gemini API connection error: {e}")
