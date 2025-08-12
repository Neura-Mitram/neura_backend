# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, Request
from sqlalchemy.orm import Session
from pathlib import Path
import os
import re
from fastapi.responses import FileResponse, JSONResponse

from app.services.wakeword_trainer import train_wakeword_model, MASTER_WAKE_AUDIO, RAW_AUDIO_BASE, MODEL_BASE
from app.models.database import SessionLocal
from app.models.user import User
from app.utils.auth_utils import require_token, ensure_token_user_match

router = APIRouter(prefix="/wakeword", tags=["Wake Word Trainer"])

_safe_re = re.compile(r'[^A-Za-z0-9_.-]')

def _sanitize(name: str) -> str:
    return _safe_re.sub('_', str(name))

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
    # security check: ensure device belongs to user
    ensure_token_user_match(user_data["sub"], device_id)

    user = db.query(User).filter(User.temp_uid == device_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # sanitize inputs to prevent path injection
    device_id_safe = _sanitize(device_id)
    wakeword_label_safe = _sanitize(wakeword_label)

    audio_dir = RAW_AUDIO_BASE / device_id_safe
    audio_dir.mkdir(parents=True, exist_ok=True)

    filepaths = []
    try:
        for idx, upload_file in enumerate([file1, file2, file3], start=1):
            # optional: validate content type loosely
            # allowed types often: "audio/wav", "audio/x-wav", "audio/mpeg", ...
            # but we'll still try to load in trainer which will raise on invalid files.

            filename = f"{wakeword_label_safe}_{idx}.wav"
            path = audio_dir / filename
            content = await upload_file.read()
            if not content:
                raise HTTPException(status_code=400, detail=f"Empty file uploaded: {filename}")
            # write bytes
            with open(path, "wb") as f:
                f.write(content)
            filepaths.append(str(path))

        # call training
        try:
            tflite_path = train_wakeword_model(device_id_safe, filepaths, wakeword_label_safe)
        except Exception as e:
            # training error bubble up as 500 with message
            raise HTTPException(status_code=500, detail=f"Training failed: {e}")

        # return download URL (client should call this to get file)
        download_url = f"/wakeword/download-model?device_id={device_id_safe}"
        return JSONResponse(status_code=200, content={
            "message": "Wakeword model trained successfully",
            "download_url": download_url,
            "model_path": str(tflite_path)
        })

    finally:
        # do not delete tflite here; raw files are deleted in trainer; still attempt cleanup defensively
        for p in filepaths:
            try:
                Path(p).unlink(missing_ok=True)
            except Exception:
                pass


@router.get("/download-model")
def download_wakeword_model(
    device_id: str,
    user_data: dict = Depends(require_token)
):
    ensure_token_user_match(user_data["sub"], device_id)

    # find latest model matching device_id_*.tflite
    models = list(MODEL_BASE.glob(f"{_sanitize(device_id)}_*.tflite"))
    if not models:
        raise HTTPException(status_code=404, detail="No trained model found for this device")

    models.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    latest_model = models[0]

    return FileResponse(
        path=str(latest_model),
        media_type="application/octet-stream",
        filename="wakeword_model.tflite"
    )
