# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.



from fastapi import APIRouter
from sqlalchemy.orm import Session
from app.models.database import SessionLocal
from app.models.user import User
import os

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/healthz")
async def health_check():
    db: Session = SessionLocal()
    result = {
        "db_connection": False,
        "fcm_test": False,
        "wakeword_model_check": False
    }

    try:
        # ✅ Check DB read
        any_user = db.query(User).first()
        if any_user:
            result["db_connection"] = True

        # ✅ FCM check (test token presence)
        if any_user and any_user.device_token:
            result["fcm_test"] = True

        # ✅ Wakeword model file exists
        if any_user:
            model_path = f"trained_models/{any_user.temp_uid}_neura.tflite"
            result["wakeword_model_check"] = os.path.exists(model_path)

        return {
            "status": "ok" if all(result.values()) else "partial",
            "details": result
        }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "details": result
        }

    finally:
        db.close()
