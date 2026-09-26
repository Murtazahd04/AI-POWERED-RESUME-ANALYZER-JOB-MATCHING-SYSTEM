from bson import ObjectId
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .database import get_db
from .security import decode_token

bearer = HTTPBearer(auto_error=False)


async def get_current_user(creds: HTTPAuthorizationCredentials | None = Depends(bearer)) -> dict:
    unauthorized = HTTPException(status_code=401, detail="Not authenticated",
                                  headers={"WWW-Authenticate": "Bearer"})
    if creds is None:
        raise unauthorized
    user_id = decode_token(creds.credentials)
    if not user_id or not ObjectId.is_valid(user_id):
        raise unauthorized
    user = await get_db().users.find_one({"_id": ObjectId(user_id)})
    if user is None:
        raise unauthorized
    return user