from datetime import UTC, datetime

import bcrypt
from fastapi import APIRouter, Depends, HTTPException

from src.dependencies import get_db, jwt_auth
from src.models.schemas import LoginRequest, RegisterRequest
from src.services.jwt import issue_jwt

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register")
async def register(body: RegisterRequest, db=Depends(get_db)):
    """Create account, return JWT. No auth required."""
    email = body.email.strip().lower()
    password_hash = bcrypt.hashpw(body.password.encode(), bcrypt.gensalt()).decode()
    user = {
        "email": email,
        "name": body.name,
        "passwordHash": password_hash,
        "tenantId": None,
        "role": None,
        "createdAt": datetime.now(UTC),
        "updatedAt": datetime.now(UTC),
    }
    try:
        result = await db.users.insert_one(user)
    except Exception as e:
        if "duplicate key" in str(e).lower():
            raise HTTPException(status_code=409, detail="Email already registered") from e
        raise
    token = issue_jwt(str(result.inserted_id), email, body.name, None, None)
    return {"token": token, "user": {"email": email, "name": body.name, "tenantId": None}}


@router.post("/login")
async def login(body: LoginRequest, db=Depends(get_db)):
    """Validate credentials, return JWT."""
    user = await db.users.find_one({"email": body.email.strip().lower()})
    if not user or not bcrypt.checkpw(
        body.password.encode(), user["passwordHash"].encode()
    ):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = issue_jwt(
        str(user["_id"]),
        user["email"],
        user["name"],
        str(user["tenantId"]) if user.get("tenantId") else None,
        user.get("role"),
    )
    return {
        "token": token,
        "user": {
            "email": user["email"],
            "name": user["name"],
            "tenantId": str(user["tenantId"]) if user.get("tenantId") else None,
            "role": user.get("role"),
        },
    }


@router.get("/me")
async def me(user: dict = Depends(jwt_auth)):
    """Current user from JWT."""
    return {
        "userId": user["sub"],
        "email": user["email"],
        "name": user["name"],
        "tenantId": user.get("tenantId"),
        "role": user.get("role"),
    }
