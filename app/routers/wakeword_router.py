# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, Request
from sqlalchemy.orm import Session
import os
from app.services.wakeword_trainer import train_wakeword_model
from app.models.database import SessionLocal
from app.models.user import User
from app.utils.auth_utils import require_token, ensure_token_user_match
from fastapi.responses import FileResponse


router = APIRouter(prefix="/wakeword", tags=["Wake Word Trainer"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/train")
async def train_custom_wakeword(
    request: Request,
    device_id: str = Form(...),
    wakeword_label: str = Form("neura"),
    file1: UploadFile = File(...),
    file2: UploadFile = File(...),
    file3: UploadFile = File(...),
    db: Session = Depends(get_db),
    user_data: dict = Depends(require_token)
):
    ensure_token_user_match(user_data["sub"], device_id)

    user = db.query(User).filter(User.temp_uid == device_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    audio_dir = f"wake_audio/{device_id}"
    os.makedirs(audio_dir, exist_ok=True)

    filepaths = []
    for idx, file in enumerate([file1, file2, file3], start=1):
        filename = f"{wakeword_label}_{idx}.wav"
        path = os.path.join(audio_dir, filename)
        with open(path, "wb") as f:
            f.write(await file.read())
        filepaths.append(path)

    tflite_path = train_wakeword_model(device_id, filepaths, wakeword_label)

    return {
        "message": "Wakeword model trained successfully",
        "model_path": f"/{tflite_path}"
    }



@router.get("/download-model")
def download_wakeword_model(
    device_id: str,
    user_data: dict = Depends(require_token)
):
    ensure_token_user_match(user_data["sub"], device_id)

    tflite_path = f"trained_models/{device_id}_neura.tflite"
    if not os.path.exists(tflite_path):
        raise HTTPException(status_code=404, detail="Model not found.")

    return FileResponse(
        path=tflite_path,
        media_type="application/octet-stream",
        filename="wakeword_model.tflite"
    )
