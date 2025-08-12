# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.

from fastapi import Request, HTTPException
from app.utils.auth_utils import decode_token  # this should decode JWT
from app.models.database import SessionLocal
from app.models.user import User, TierLevel
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

TIER_RATES = {
    TierLevel.free.value: "5/minute",
    TierLevel.basic.value: "20/minute",
    TierLevel.pro.value: "60/minute",
}

async def get_tier_limit(request: Request) -> str:
    # 1️⃣ Get token from header
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    
    token = auth_header.split(" ")[1]

    # 2️⃣ Decode token
    try:
        payload = decode_token(token)  # must return dict with "sub"
        user_id = payload.get("sub")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    # 3️⃣ Look up tier in DB
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        tier = user.tier.value if user.tier else TierLevel.free.value
    finally:
        db.close()

    # 4️⃣ Return matching tier limit
    return TIER_RATES.get(tier, "5/minute")
