# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


from fastapi import APIRouter, Depends, HTTPException, Header
from typing import Dict
import os, json
from pathlib import Path
import asyncio
from sqlalchemy.orm import Session
from app.models.database import SessionLocal
from app.models.user import User, TierLevel
from more_itertools import chunked
from app.utils.auth_utils import ensure_token_user_match, require_token

from app.utils.jwt_utils import create_access_token  #✅ JWT added
from app.schemas.user_schemas import (
    OnboardingUpdateRequest,
    LoginRequest,
    ProfileRequest,
    TierUpgradeRequest,
    TierDowngradeRequest,
    TranslationRequest,
    TranslationResponse,
    UserLangRequest
)

from app.utils.audio_processor import synthesize_voice
from app.services.translation_service import translate


router = APIRouter(prefix="/auth", tags=["Anonymous Auth"])

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()



@router.post("/anonymous-login")
def anonymous_login(payload: LoginRequest, db: Session = Depends(get_db)):
    device_id = payload.device_id
    user = db.query(User).filter(User.temp_uid == device_id).first()

    if user:
        token = create_access_token({"sub": user.temp_uid})
        return {
            "message": "🔁 Returning user",
            "token": token,
            "user": {
                "id": user.id,
                "device_id": user.temp_uid,
                "ai_name": user.ai_name,
                "voice": user.voice,
                "tier": user.tier.value,
            }
        }

    new_user = User(
        temp_uid=device_id,
        is_verified=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    token = create_access_token({"sub": new_user.temp_uid})
    return {
        "message": "🆕 New anonymous user created",
        "token": token,
        "user": {
            "id": new_user.id,
            "device_id": new_user.temp_uid,
            "ai_name": new_user.ai_name,
            "voice": new_user.voice,
            "tier": new_user.tier.value,
        }
    }



@router.post("/update-onboarding")
def update_onboarding(payload: OnboardingUpdateRequest, db: Session = Depends(get_db), user_data: dict = Depends(require_token)):


    if not payload.device_id:
        raise HTTPException(status_code=400, detail="Missing device_id")

    ensure_token_user_match(user_data["sub"], payload.device_id)

    user = db.query(User).filter(User.temp_uid == payload.device_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    if payload.voice and payload.voice not in ["male", "female"]:
        raise HTTPException(status_code=400, detail="Invalid voice option")

    # ✅ Update onboarding fields
    if payload.ai_name:
        user.ai_name = payload.ai_name
    if payload.voice:
        user.voice = payload.voice
    if payload.preferred_lang:  # ✅ Add this block
        user.preferred_lang = payload.preferred_lang

    db.commit()

    # ✅ Wakeword instruction text
    base_instruction = "Please record your wake word 3 times so Neura can activate by voice. Example : 'Hey Neura or Neura Baby' "
    user_lang = user.preferred_lang or "en"

    if user_lang != "en":
        translated_text = translate(base_instruction, source_lang="en", target_lang=user_lang)
    else:
        translated_text = base_instruction

    # ✅ Generate streaming voice
    stream_url = synthesize_voice(
        text=translated_text,
        gender=user.voice if user.voice in ["male", "female"] else "female",
        emotion="joy",
        lang=user_lang
    )

    return {
        "message": "✅ Onboarding updated successfully",
        "device_id": user.temp_uid,
        "ai_name": user.ai_name,
        "voice": user.voice,
        "preferred_lang": user.preferred_lang,
        "next_step": "WakeWord Setup",
        "wakeword_instruction": translated_text,
        "audio_stream_url": stream_url  # 🔊 for Flutter autoplay
    }


#---------------------------------------------------
#---------------------------------------------------


# ✅ Use a writable and persistent location
CACHE_ROOT = Path(os.getenv("HF_HOME", "/data"))
CACHE_DIR = CACHE_ROOT / "translation_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)



def _get_lang_cache_path(lang: str) -> Path:
    return CACHE_DIR / f"{lang}.json"

def _load_lang_cache(lang: str) -> Dict[str, str]:
    path = _get_lang_cache_path(lang)
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def _save_lang_cache(lang: str, cache: Dict[str, str]):
    path = _get_lang_cache_path(lang)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


@router.post("/translate-ui", response_model=TranslationResponse)
async def translate_ui_texts(
    payload: TranslationRequest,
    db: Session = Depends(get_db),
    user_data: dict = Depends(require_token)
) -> Dict[str, str]:

    ensure_token_user_match(user_data["sub"], payload.device_id)

    user = db.query(User).filter(User.temp_uid == payload.device_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    # ✅ Save preferred language
    user.preferred_lang = payload.target_lang
    db.commit()

    # ✅ Load existing cache
    lang_cache = _load_lang_cache(payload.target_lang)
    translations: Dict[str, str] = {}

    # ✅ Translate only missing strings (batched in 50s)
    if missing_texts:
        for batch in chunked(missing_texts, 50):
            batch_results = await asyncio.gather(*[
                translate(text=txt, source_lang="en", target_lang=payload.target_lang)
                for txt in batch
            ])
            for txt, translated in zip(batch, batch_results):
                lang_cache[txt] = translated
                translations[txt] = translated
    
        _save_lang_cache(payload.target_lang, lang_cache)

    # ✅ Combine cache and new ones
    for txt in payload.strings:
        translations[txt] = lang_cache.get(txt, txt)

    return {
        "message": "✅ UI translations returned",
        "preferred_lang": user.preferred_lang,
        "translations": translations
    }

#---------------------------------------------------
#---------------------------------------------------

@router.post("/profile")
def get_profile(payload: ProfileRequest, db: Session = Depends(get_db), user_data: dict = Depends(require_token)):
    ensure_token_user_match(user_data["sub"], payload.device_id)

    user = db.query(User).filter(User.temp_uid == payload.device_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    is_upgraded = user.tier in [TierLevel.basic, TierLevel.pro]

    return {
        "device_id": user.temp_uid,
        "ai_name": user.ai_name,
        "voice": user.voice,
        "tier": user.tier.value,
        "is_upgraded": is_upgraded
    }



@router.post("/change-user-language")
def change_user_lang(payload: UserLangRequest, db: Session = Depends(get_db), user_data: dict = Depends(require_token)):
    ensure_token_user_match(user_data["sub"], payload.device_id)

    user = db.query(User).filter(User.temp_uid == payload.device_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    # Update language
    user.preferred_lang = payload.preferred_lang
    db.commit()

    # Return response
    return {
            "message": "Language updated successfully.",
            "preferred_lang": user.preferred_lang,
        }


@router.post("/upgrade-tier")
def upgrade_anonymous_tier(payload: TierUpgradeRequest, db: Session = Depends(get_db), user_data: dict = Depends(require_token)):
    ensure_token_user_match(user_data["sub"], payload.device_id)
    valid_tiers = [TierLevel.basic.value, TierLevel.pro.value]
    if payload.new_tier not in valid_tiers:
        raise HTTPException(status_code=400, detail="Invalid tier. Choose 'basic' or 'pro'.")

    if not payload.payment_key:
        raise HTTPException(status_code=400, detail="❌ Payment key is required.")

    user = db.query(User).filter(User.temp_uid == payload.device_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    user.tier = TierLevel(payload.new_tier)
    user.payment_key = payload.payment_key
    db.commit()

    return {
        "message": f"✅ Tier upgraded to {user.tier.value}",
        "device_id": user.temp_uid,
        "new_tier": user.tier.value,
        "payment_key": user.payment_key,
    }



@router.post("/downgrade-tier")
def downgrade_tier(payload: TierDowngradeRequest, db: Session = Depends(get_db), user_data: dict = Depends(require_token)):
    ensure_token_user_match(user_data["sub"], payload.device_id)

    if payload.new_tier != TierLevel.basic.value:
        raise HTTPException(status_code=400, detail="❌ Downgrade only allowed to 'basic' (from 'pro').")

    user = db.query(User).filter(User.temp_uid == payload.device_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="❌ User not found.")

    if user.tier != TierLevel.pro:
        raise HTTPException(status_code=403, detail="❌ Downgrade only allowed from 'pro' tier.")

    user.tier = TierLevel.basic
    db.commit()

    return {
        "message": f"✅ Tier downgraded to {user.tier.value}",
        "device_id": user.temp_uid,
        "new_tier": user.tier.value
    }
