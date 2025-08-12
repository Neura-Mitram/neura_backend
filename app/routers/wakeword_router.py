# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, Request
from sqlalchemy.orm import Session
import os
from pathlib import Path
from app.services.wakeword_trainer import train_wakeword_model, MASTER_WAKE_AUDIO, RAW_AUDIO_BASE, MODEL_BASE
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

    audio_dir = RAW_AUDIO_BASE / device_id
    os.makedirs(audio_dir, exist_ok=True)

    filepaths = []
    for idx, file in enumerate([file1, file2, file3], start=1):
        filename = f"{wakeword_label}_{idx}.wav"
        path = audio_dir / filename
        with open(path, "wb") as f:
            f.write(await file.read())
        filepaths.append(str(path))

    tflite_path = train_wakeword_model(device_id, filepaths, wakeword_label)

    return {
        "message": "Wakeword model trained successfully",
        "model_path": f"/wake_audio/models/{device_id}_{wakeword_label}.tflite"
    }



@router.get("/download-model")
def download_wakeword_model(
    device_id: str,
    user_data: dict = Depends(require_token)
):
    ensure_token_user_match(user_data["sub"], device_id)

    tflite_path = MODEL_BASE / f"{device_id}_neura.tflite"
    if not tflite_path.exists():
        raise HTTPException(status_code=404, detail="Model not found.")

    return FileResponse(
        path=str(tflite_path),
        media_type="application/octet-stream",
        filename="wakeword_model.tflite"
    )
