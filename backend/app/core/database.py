from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
import logging

logger = logging.getLogger("uvicorn.error")

class MongoDB:
    client: AsyncIOMotorClient = None
    db = None

db_instance = MongoDB()

async def connect_to_mongo():
    """Establish database connection pool when FastAPI starts."""
    try:
        logger.info("Connecting to MongoDB Atlas...")
        db_instance.client = AsyncIOMotorClient(settings.MONGODB_URL)
        
        # Safe fallback logic to prevent ConfigurationError
        try:
            db_name = db_instance.client.get_default_database().name
        except Exception:
            # Fallback if no database name is specified at the end of the URL string
            db_name = "data_science_lab_project"
            
        db_instance.db = db_instance.client[db_name]
        
        # Trigger a quick command to verify connection works
        await db_instance.client.admin.command('ping')
        logger.info(f"Successfully connected to MongoDB database: '{db_name}'! 🎉")
    except Exception as e:
        logger.error(f"Could not connect to MongoDB: {e}")
        raise e


async def close_mongo_connection():
    """Cleanly close database pool when FastAPI shuts down."""
    if db_instance.client:
        db_instance.client.close()
        logger.info("MongoDB connection pool closed.")

def get_database():
    """Dependency helper to inject the database instance into API routes."""
    return db_instance.db
