# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.

from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
import json

from app.models.database import SessionLocal
from app.models.user import User
from app.schemas.intent_schemas import IntentRequest
from app.utils.auth_utils import require_token, ensure_token_user_match
from app.utils.ai_engine import generate_ai_reply
from app.utils.intent_tracker import track_intent_usage
from app.services.update_device_state import handle_update_device_state
from app.services.save_message import save_user_message
from app.utils.schedulers.cron.morning_news_cron import is_trivia_question

# Red flags / emotion / fallback
from app.services.intent_handlers.handle_fallback_ai import handle_fallback_ai
from app.services.emotion_tone_updater import update_emotion_status

# Intent handlers
from app.services.intent_handlers.journal.handle_journal_add import handle_journal_add
from app.services.intent_handlers.journal.handle_journal_list import handle_journal_list
from app.services.intent_handlers.journal.handle_journal_delete import handle_journal_delete
from app.services.intent_handlers.journal.handle_journal_modify import handle_journal_modify
from app.services.intent_handlers.journal.handle_journal_weekly_summary import handle_journal_weekly_summary

from app.services.intent_handlers.checkin.handle_daily_checkin_add import handle_checkin_add
from app.services.intent_handlers.checkin.handle_daily_checkin_list import handle_checkin_list
from app.services.intent_handlers.checkin.handle_daily_checkin_delete import handle_checkin_delete
from app.services.intent_handlers.checkin.handle_daily_checkin_modify import handle_checkin_modify
from app.services.intent_handlers.checkin.handle_weekly_checkin_summary import handle_weekly_checkin_summary

from app.services.intent_handlers.habit.handle_habit_add import handle_add_habit
from app.services.intent_handlers.habit.handle_habits_list import handle_list_habits
from app.services.intent_handlers.habit.handle_habit_modify import handle_modify_habit
from app.services.intent_handlers.habit.handle_habit_delete import handle_delete_habit
from app.services.intent_handlers.habit.habit_handlers import handle_habit_modify
from app.services.intent_handlers.habit.handle_habit_weekly_summary import handle_habit_weekly_summary

from app.services.intent_handlers.goal.handle_goal_add import handle_goal_add
from app.services.intent_handlers.goal.handle_goals_list import handle_list_goals
from app.services.intent_handlers.goal.handle_goal_modify import handle_modify_goal
from app.services.intent_handlers.goal.handle_goal_delete import handle_delete_goal
from app.services.intent_handlers.goal.goal_handlers import handle_goal_modify
from app.services.intent_handlers.goal.handle_goal_weekly_summary import handle_goal_weekly_summary

from app.services.intent_handlers.mood.handle_mood_checkin_add import handle_mood_checkin_add
from app.services.intent_handlers.mood.handle_mood_checkin_list import handle_mood_checkin_list

from app.services.intent_handlers.creator.handle_creator_mode import handle_creator_mode
from app.services.intent_handlers.creator.content.handle_caption import handle_creator_caption
from app.services.intent_handlers.creator.growth.handle_content_ideas import handle_creator_content_ideas
from app.services.intent_handlers.creator.growth.handle_weekly_plan import handle_creator_weekly_plan
from app.services.intent_handlers.creator.growth.handle_audience_helper import handle_creator_audience_helper
from app.services.intent_handlers.creator.growth.handle_viral_reels import handle_creator_viral_reels
from app.services.intent_handlers.creator.utility.handle_seo import handle_creator_seo
from app.services.intent_handlers.creator.utility.handle_email import handle_creator_email
from app.services.intent_handlers.creator.utility.handle_time_planner import handle_creator_time_planner
from app.services.intent_handlers.creator.content.handle_youtube_script import handle_creator_youtube_script
from app.services.intent_handlers.creator.content.handle_blog import handle_creator_blog

from app.services.intent_handlers.handle_search import handle_search
from app.services.intent_handlers.handle_smart_reply import handle_smart_reply
from app.services.intent_handlers.handle_notification import handle_notification_add
from app.services.intent_handlers.handle_important_summary import handle_important_summary
from app.services.intent_handlers.intent_qna_handler import handle_qna_semantic_summary


from app.services.intent_handlers.privatemode.handle_private_mode_toggle import handle_private_mode_toggle
from app.services.intent_handlers.privatemode.handle_private_mode_status import handle_private_mode_status


from app.services.intent_handlers.handle_summary import handle_daily_summary, handle_weekly_emotion_summary
from app.services.intent_handlers.handle_weekly_trait_summary import handle_weekly_trait_summary


from app.services.handle_nudge_trigger import handle_nudge_trigger
from app.utils.persona_prompt_wrapper import inject_persona_into_prompt
from app.utils.intent_mappings_utils import INTENT_ALIAS_MAP, INTENT_EXAMPLES, ALL_VALID_INTENTS

router = APIRouter(prefix="/intent-core", tags=["Intent Router"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def detect_and_route_intent(
    request: Request,
    payload: IntentRequest,
    db: Session = Depends(get_db),
    user_data: dict = Depends(require_token)
):
    ensure_token_user_match(user_data["sub"], payload.user_id)

    user = db.query(User).filter(User.id == payload.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Use inject_persona_into_prompt to enrich the intent prompt
    user_input_escaped = json.dumps(payload.message)
    intent_prompt = f"""
    You are Neura, a smart assistant. Map the user's request to the most relevant **intent** from this list:

    {', '.join(ALL_VALID_INTENTS)}

    Also use these **aliases** and **examples** to understand real-life phrasing:

    ALIASES:
    {json.dumps(INTENT_ALIAS_MAP, indent=2)}

    EXAMPLES:
    {json.dumps(INTENT_EXAMPLES, indent=2)}

    Now classify this user message:
    {user_input_escaped}

    Respond ONLY in this format:
    {{
      "intent": "<one of the intents above>",
      "entities": {{
        "goal_id": <int|null>,
        "habit_id": <int|null>
      }}
    }}
    """.strip()

    raw_response = generate_ai_reply(inject_persona_into_prompt(user, intent_prompt, db))

    try:
        parsed = json.loads(raw_response)
        intent = parsed["intent"].strip().lower()
        entities = parsed["entities"]
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid AI response: {e}")

    track_intent_usage(db, user, intent, payload.message)

    # Routing
    if intent == "habit":
        result = await handle_add_habit(request, user, payload.message, db)
    elif intent == "habit_list":
        result = await handle_list_habits(request, user, payload.message, db)
    elif intent == "habit_modify":
        result = await handle_modify_habit(request, user, payload.message, db)
    elif intent == "habit_delete":
        result = await handle_delete_habit(request, user, payload.message, db)
    elif intent == "habit_weekly_summary":
        result = await handle_habit_weekly_summary(request, user, payload.message, db)
    elif intent == "mark_habit_completed":
        habit_id = entities.get("habit_id")
        if not habit_id:
            raise HTTPException(status_code=400, detail="Missing habit_id.")
        result = handle_habit_modify(user, habit_id, {"status": "completed"})

    elif intent == "checkin":
        result = await handle_checkin_add(request, user, payload.message, db)
    elif intent == "checkin_list":
        result = await handle_checkin_list(request, user, payload.message, db)
    elif intent == "checkin_delete":
        result = await handle_checkin_delete(request, user, payload.message, db)
    elif intent == "checkin_modify":
        result = await handle_checkin_modify(request, user, payload.message, db)
    elif intent == "checkin_weekly_summary":
        result = await handle_weekly_checkin_summary(request, user, payload.message, db)

    elif intent == "journal":
        result = await handle_journal_add(request, user, payload.message, db)
    elif intent == "journal_list":
        result = await handle_journal_list(request, user, payload.message, db)
    elif intent == "journal_delete":
        result = await handle_journal_delete(request, user, payload.message, db)
    elif intent == "journal_modify":
        result = await handle_journal_modify(request, user, payload.message, db)
    elif intent == "journal_weekly_summary":
        result = await handle_journal_weekly_summary(request, user, payload.message, db)

    elif intent == "goal":
        result = await handle_goal_add(request, user, payload.message, db)
    elif intent == "goal_list":
        result = await handle_list_goals(request, user, payload.message, db)
    elif intent == "goal_modify":
        result = await handle_modify_goal(request, user, payload.message, db)
    elif intent == "goal_delete":
        result = await handle_delete_goal(request, user, payload.message, db)
    elif intent == "goal_weekly_summary":
        result = await handle_goal_weekly_summary(request, user, payload.message, db)
    elif intent == "mark_goal_completed":
        goal_id = entities.get("goal_id")
        if not goal_id:
            raise HTTPException(status_code=400, detail="Missing goal_id.")
        result = handle_goal_modify(user, goal_id, {"status": "completed"})

    elif intent == "mood":
        result = await handle_mood_checkin_add(request, user, payload.message, db)
    elif intent == "mood_history":
        result = await handle_mood_checkin_list(request, user, payload.message, db)
    elif intent == "summary":
        result = await handle_daily_summary(request, user, payload.message, db)
    elif intent == "nudge":
        result = await handle_nudge_trigger(request, user, payload.message, db)

    elif intent == "creator_mode":
        result = await handle_creator_mode(request, user, payload.message, db)
    elif intent == "creator_caption":
        result = await handle_creator_caption(request, user, payload.message, db)
    elif intent == "creator_content_ideas":
        result = await handle_creator_content_ideas(request, user, payload.message, db)
    elif intent == "creator_weekly_plan":
        result = await handle_creator_weekly_plan(request, user, payload.message, db)
    elif intent == "creator_audience_helper":
        result = await handle_creator_audience_helper(request, user, payload.message, db)
    elif intent == "creator_viral_reels":
        result = await handle_creator_viral_reels(request, user, payload.message, db)
    elif intent == "creator_seo":
        result = await handle_creator_seo(request, user, payload.message, db)
    elif intent == "creator_email":
        result = await handle_creator_email(request, user, payload.message, db)
    elif intent == "creator_time_planner":
        result = await handle_creator_time_planner(request, user, payload.message, db)
    elif intent == "creator_youtube_script":
        result = await handle_creator_youtube_script(request, user, payload.message, db)
    elif intent == "creator_blog":
        result = await handle_creator_blog(request, user, payload.message, db)

    elif intent == "search":
        result = await handle_search(request, user, payload.message, db)
    elif intent == "smart_reply":
        result = await handle_smart_reply(request, user, payload.message, db)
    elif intent == "notification":
        result = await handle_notification_add(request, user, payload.message, db)
    elif intent == "update_device":
        result = await handle_update_device_state(request, user, payload.message, db)
    elif intent == "important_summary":
        result = await handle_important_summary(request, user, payload.message, db)
    elif intent == "weekly_emotion_summary":
        result = await handle_weekly_emotion_summary(request, user, payload.message, db)
    elif intent == "qna_summary":
        result = await handle_qna_semantic_summary(request, user, payload.message, db)
    elif intent == "weekly_trait_summary":
        result = await handle_weekly_trait_summary(request, user, payload.message, db)
    elif intent == "private_mode_toggle":
        result = handle_private_mode_toggle(request, user, payload.message, db)
    elif intent == "private_mode_status":
        result = handle_private_mode_status(request, user)
    else:
        if is_trivia_question(payload.message):
            result = await handle_qna_semantic_summary(request, user, payload.message, db)
        else:
            result = await handle_fallback_ai(request, db, user, {"query": payload.message})

    save_user_message(db, user, payload.message, conversation_id=payload.conversation_id, sender="user")
    if isinstance(result, dict):
        assistant_reply = result.get("reply") or result.get("message") or result.get("nudge")
        if assistant_reply:
            save_user_message(db, user, assistant_reply, conversation_id=payload.conversation_id, sender="assistant")

    return result
