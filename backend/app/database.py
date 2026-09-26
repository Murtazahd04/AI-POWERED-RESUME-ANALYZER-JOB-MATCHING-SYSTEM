import logging
from pymongo import AsyncMongoClient

from .config import get_settings

log = logging.getLogger("db")
_client = None
_db = None


async def connect() -> None:
    global _client, _db
    if _db is None:
        s = get_settings()
        _client = AsyncMongoClient(s.mongodb_url, serverSelectionTimeoutMS=5000)
        _db = _client[s.mongodb_db]
    try:
        await _db.users.create_index("email", unique=True)
    except Exception as exc:
        log.warning("Could not create indexes: %s", exc)


async def close() -> None:
    if _client is not None:
        await _client.close()


def get_db():
    if _db is None:
        raise RuntimeError("Database not initialised")
    return _db