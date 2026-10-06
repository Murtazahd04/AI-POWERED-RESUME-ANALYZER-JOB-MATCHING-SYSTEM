from fastapi import APIRouter, Depends, HTTPException
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from ..database import get_db
from ..deps import get_current_user
from ..schemas import (
    LoginRequest,
    PasswordChangeRequest,
    ProfileUpdate,
    RegisterRequest,
    TokenResponse,
    UserOut,
)
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


@router.patch("/me", response_model=UserOut)
async def update_me(body: ProfileUpdate, user: dict = Depends(get_current_user)):
    updates = body.model_dump(exclude_unset=True, exclude_none=True)
    if "email" in updates:
        updates["email"] = updates["email"].lower()
        if updates["email"] != user["email"]:
            existing = await get_db().users.find_one(
                {"email": updates["email"], "_id": {"$ne": user["_id"]}}
            )
            if existing:
                raise HTTPException(
                    status_code=409,
                    detail="An account with this email already exists.",
                )

    try:
        updated_user = await get_db().users.find_one_and_update(
            {"_id": user["_id"]},
            {"$set": updates},
            return_document=ReturnDocument.AFTER,
        )
    except DuplicateKeyError as exc:
        raise HTTPException(
            status_code=409,
            detail="An account with this email already exists.",
        ) from exc

    if updated_user is None:
        raise HTTPException(status_code=404, detail="Account not found.")
    return _user_out(updated_user)


@router.post("/me/password")
async def change_password(
    body: PasswordChangeRequest,
    user: dict = Depends(get_current_user),
):
    if not verify_password(body.current_password, user["password_hash"]):
        raise HTTPException(status_code=400, detail="Current password is incorrect.")

    result = await get_db().users.update_one(
        {"_id": user["_id"]},
        {"$set": {"password_hash": hash_password(body.new_password)}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Account not found.")
    return {"message": "Password updated."}