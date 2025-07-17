# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


from fastapi import Request
from sqlalchemy.orm import Session
from app.models.user import User
from app.services.emotion_tone_updater import update_emotion_status
from app.utils.red_flag_utils import detect_red_flag
from app.utils.ai_engine import generate_ai_reply
from app.utils.prompt_templates import red_flag_response, creator_info_response, self_query_response
from app.utils.persona_prompt_wrapper import inject_persona_into_prompt
from app.utils.usage_tracker import track_usage_event
from app.services.smart_snapshot_generator import generate_memory_snapshot
from app.services.translation_service import translate

async def handle_fallback_ai(request: Request, db: Session, user: User, intent_payload: dict):
    try:
        user_query = intent_payload.get("query", "").strip()
        if not user_query:
            user_query = "Just say something helpful and intelligent."

        user_lang = user.preferred_lang or "en"
        ai_name = user.ai_name or "Neura"

        # 🚩 Red flag detection
        red_flag = detect_red_flag(user_query)

        if red_flag == "code":
            return {
                "status": "success",
                "intent": "fallback",
                "reply": red_flag_response("code or internal details", lang=user_lang)
            }

        if red_flag == "creator":
            return {
                "status": "success",
                "intent": "fallback",
                "reply": creator_info_response(lang=user_lang)
            }

        if red_flag == "self_query":
            return {
                "status": "success",
                "intent": "fallback",
                "reply": self_query_response(ai_name=ai_name, lang=user_lang)
            }

        if red_flag == "sos":
            reply_text = "🚨 Emergency keyword detected. Please say 'Neura, help me' aloud to trigger SOS."
            if user_lang != "en":
                reply_text = translate(reply_text, source_lang="en", target_lang=user_lang)
            return {
                "status": "success",
                "intent": "fallback",
                "reply": reply_text
            }

        # ✅ Emotion tag
        emotion_label = await update_emotion_status(user, user_query, db, source="voice_fallback")

        # ✨ Prompt with fallback-safe persona injection
        raw_prompt = f"User: {user_query}\nNeura:"

        # 🧠 NEW: Inject memory snapshot context
        snapshot = generate_memory_snapshot(user.id)
        memory_context = snapshot.get("summary", "")
        if memory_context:
            raw_prompt = f"(Context: {memory_context})\n" + raw_prompt

        try:
            full_prompt = inject_persona_into_prompt(user, raw_prompt, db)
        except Exception as e:
            full_prompt = raw_prompt  # fallback to basic prompt

        ai_reply = generate_ai_reply(full_prompt)

        track_usage_event(db, user, category="voice_fallback")

        return {
            "status": "success",
            "intent": "fallback",
            "reply": ai_reply.strip(),
            "emotion": emotion_label
        }

    except Exception as e:
        return {
            "status": "error",
            "message": "Fallback AI handler failed",
            "detail": str(e)
        }
