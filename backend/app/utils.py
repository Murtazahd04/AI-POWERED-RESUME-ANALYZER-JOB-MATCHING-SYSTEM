from datetime import datetime, timezone
from bson import ObjectId
from fastapi import HTTPException


def now() -> datetime:
    return datetime.now(timezone.utc)


def to_object_id(value: str) -> ObjectId:
    if not ObjectId.is_valid(value):
        raise HTTPException(status_code=404, detail="Not found")
    return ObjectId(value)


def serialize(doc: dict | None, drop: tuple[str, ...] = ()) -> dict | None:
    if doc is None:
        return None
    out = {}
    for key, value in doc.items():
        if key in drop:
            continue
        if key == "_id":
            out["id"] = str(value)
        elif isinstance(value, ObjectId):
            out[key] = str(value)
        else:
            out[key] = value
    return out