from fastapi import APIRouter, Depends, HTTPException

from ..database import get_db
from ..deps import get_current_user
from ..schemas import LoginRequest, RegisterRequest, TokenResponse, UserOut
from ..security import create_access_token, hash_password, verify_password
from ..utils import now, serialize
from ..config import get_settings

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _user_out(doc: dict) -> UserOut:
    return UserOut(**serialize(doc, drop=("password_hash",)))


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(body: RegisterRequest):
    db = get_db()
    if await db.users.find_one({"email": body.email.lower()}):
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    role = "admin" if body.email.lower() in get_settings().admin_email_set else "user"
    doc = {
        "name": body.name, "email": body.email.lower(),
        "password_hash": hash_password(body.password),
        "role": role, "created_at": now(),
    }
    result = await db.users.insert_one(doc)
    doc["_id"] = result.inserted_id
    token = create_access_token(str(result.inserted_id))
    return TokenResponse(access_token=token, user=_user_out(doc))


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest):
    db = get_db()
    user = await db.users.find_one({"email": body.email.lower()})
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")
    token = create_access_token(str(user["_id"]))
    return TokenResponse(access_token=token, user=_user_out(user))


@router.post("/logout")
async def logout(_user: dict = Depends(get_current_user)):
    return {"message": "Logged out."}


@router.get("/me", response_model=UserOut)
async def me(user: dict = Depends(get_current_user)):
    return _user_out(user)