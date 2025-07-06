# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


from fastapi import Request, HTTPException
from sqlalchemy.orm import Session
from app.models.user import User
from app.utils.auth_utils import ensure_token_user_match
from app.utils.tier_logic import is_pro_user
from app.services.emotion_tone_updater import update_emotion_status

async def handle_creator_mode(request: Request, user: User, message: str, db: Session):
    # ✅ Validate token
    # await ensure_token_user_match(request, user.id)

    # ✅ Pro-only
    if not is_pro_user(user):
        raise HTTPException(status_code=403, detail="🔒 Creator Mode is only available to Pro users.")

    # 🔍 Detect emotion
    emotion_label = await update_emotion_status(user, message, db)

    return {
        "message": f"🎬 Creator Mode Activated. (Detected emotion: {emotion_label})",
        "options": [
            "✍️ Generate Instagram Captions",
            "✨ Content Ideas for your niche",
            "📅 Weekly Content Planner",
            "🎯 Audience Targeting Suggestions",
            "🎥 Viral Reels Concepts",
            "📈 SEO Suggestions",
            "📧 Email Draft Helper",
            "🕓 Time Block Planner",
            "📽️ YouTube Video Script",
            "📝 Blog/LinkedIn Draft"
        ],
        "note": "Just tell me what you'd like help with, and I'll guide you step by step."
    }
