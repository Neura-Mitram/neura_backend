# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


from sqlalchemy.orm import Session
from app.models.user import User
from app.models.message_model import Message
from app.services.emotion_tone_updater import update_emotion_status
from app.utils.auth_utils import build_chat_history
from app.utils.ai_engine import generate_ai_reply
from app.utils.red_flag_utils import detect_red_flag
from app.utils.prompt_templates import red_flag_response, creator_info_response, self_query_response
from app.utils.persona_prompt_wrapper import inject_persona_into_prompt
from app.utils.usage_tracker import track_usage_event
from app.services.smart_snapshot_generator import generate_memory_snapshot
from app.services.translation_service import translate

ASSISTANT_NAME = "Neura"

async def handle_chat_fallback(
    db: Session,
    user: User,
    user_message: str,
    is_important: bool,
    conversation_id: int,

):
    user_lang = user.preferred_lang or "en"
    ai_name = user.ai_name or "Neura"

    # 🚩 Red flag detection
    red_flag = detect_red_flag(user_message)
    if red_flag == "code":
        reply_text = red_flag_response(reason="code or internal details", lang=user_lang)
        return {
            "reply": reply_text,
            "memory_enabled": user.memory_enabled,
            "important": is_important,
            "messages_used_this_month": user.monthly_gpt_count
        }

    if red_flag == "creator":
        reply_text = creator_info_response(lang=user_lang)
        return {
            "reply": reply_text,
            "memory_enabled": user.memory_enabled,
            "important": is_important,
            "messages_used_this_month": user.monthly_gpt_count
        }

    if red_flag == "self_query":
        reply_text = self_query_response(ai_name=ai_name, lang=user_lang)
        return {
            "reply": reply_text,
            "memory_enabled": user.memory_enabled,
            "important": is_important,
            "messages_used_this_month": user.monthly_gpt_count
        }

    if red_flag == "sos":
        reply_text = "🚨 Emergency keyword detected. Please say 'Neura, help me' aloud to trigger SOS."
        if user_lang != "en":
            reply_text = translate(reply_text, source_lang="en", target_lang=user_lang)
        return {
            "reply": reply_text,
            "memory_enabled": user.memory_enabled,
            "important": is_important,
            "messages_used_this_month": user.monthly_gpt_count
        }

    # ✅ Emotion update
    emotion_label = await update_emotion_status(user, user_message, db, source="chat_fallback")

    # 🧠 Build chat memory context
    if user.memory_enabled:
        history = build_chat_history(db, user.id, conversation_id)
        raw_prompt = f"{history}\nUser: {user_message}\n{ASSISTANT_NAME}:"
    else:
        raw_prompt = f"User: {user_message}\n{ASSISTANT_NAME}:"

    # 🧠 🧠 NEW: Inject memory snapshot context
    snapshot = generate_memory_snapshot(user.id)
    memory_context = snapshot.get("summary", "")
    if memory_context:
        raw_prompt = f"(Context: {memory_context})\n" + raw_prompt

    # 🤖 Mistral reply with fallback-safe injection
    try:
        full_prompt = inject_persona_into_prompt(user, raw_prompt, db)
    except Exception as e:
        full_prompt = raw_prompt  # fallback to simple prompt

    ai_reply = generate_ai_reply(full_prompt)

    # 💾 Save to memory if enabled
    if user.memory_enabled:
        db.add_all([
            Message(user_id=user.id, conversation_id=conversation_id, sender="user", message=user_message, important=is_important),
            Message(user_id=user.id, conversation_id=conversation_id, sender="assistant", message=ai_reply, important=False),
        ])

    # 🔢 Increment usage
    user.monthly_gpt_count += 1
    db.commit()

    track_usage_event(db, user, category="chat_fallback")

    return {
        "reply": ai_reply.strip(),
        "memory_enabled": user.memory_enabled,
        "important": is_important,
        "messages_used_this_month": user.monthly_gpt_count,
        "emotion": emotion_label
    }
