import logging
from pymongo import AsyncMongoClient

from .config import get_settings
from .security import hash_password
from .utils import now

log = logging.getLogger("db")
_client = None
_db = None


async def _provision_initial_admin(db, settings) -> None:
    password = settings.initial_admin_password
    if not password:
        log.warning("Initial admin was not provisioned: set INITIAL_ADMIN_PASSWORD in the private environment.")
        return
    if len(password) < 8 or len(password) > 72 or not any(c.isalpha() for c in password) or not any(c.isdigit() for c in password):
        raise ValueError("INITIAL_ADMIN_PASSWORD must be 8-72 characters and contain a letter and a number.")

    email = settings.initial_admin_email.strip().lower()
    if not email:
        raise ValueError("INITIAL_ADMIN_EMAIL must not be empty.")

    await db.users.update_one(
        {"email": email},
        {
            "$set": {"role": "admin"},
            "$setOnInsert": {
                "name": "Admin",
                "email": email,
                "password_hash": hash_password(password),
                "created_at": now(),
            },
        },
        upsert=True,
    )


async def connect() -> None:
    global _client, _db
    if _db is None:
        s = get_settings()
        _client = AsyncMongoClient(s.mongodb_url, serverSelectionTimeoutMS=5000)
        _db = _client[s.mongodb_db]
    try:
        await _db.users.create_index("email", unique=True)
        await _db.ai_usage_events.create_index([("timestamp", -1)])
        await _db.ai_usage_events.create_index([("user_id", 1), ("timestamp", -1)])
        await _provision_initial_admin(_db, s)
    except Exception as exc:
        log.warning("Could not initialize user records: %s", exc)


async def close() -> None:
    if _client is not None:
        await _client.close()


def get_db():
    if _db is None:
        raise RuntimeError("Database not initialised")
    return _db
