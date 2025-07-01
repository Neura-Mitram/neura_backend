from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.utils.auth_utils import require_token, ensure_token_user_match
from app.utils.ai_engine import generate_ai_reply
from app.models.database import SessionLocal
from app.models.user import User
import json

# Journal
from app.services.intent_handlers.journal.handle_journal_add import handle_journal_add
from app.services.intent_handlers.journal.handle_journal_list import handle_journal_list
from app.services.intent_handlers.journal.handle_journal_delete import handle_journal_delete
from app.services.intent_handlers.journal.handle_journal_modify import handle_journal_modify

# Checkin
from app.services.intent_handlers.checkin.handle_daily_checkin_add import handle_checkin_add
from app.services.intent_handlers.checkin.handle_daily_checkin_list import handle_checkin_list
from app.services.intent_handlers.checkin.handle_daily_checkin_delete import handle_checkin_delete
from app.services.intent_handlers.checkin.handle_daily_checkin_modify import handle_checkin_modify

# Habit
from app.services.intent_handlers.habit.handle_habit_add import handle_add_habit
from app.services.intent_handlers.habit.handle_habits_list import handle_list_habits
from app.services.intent_handlers.habit.handle_habit_modify import handle_modify_habit
from app.services.intent_handlers.habit.handle_habit_delete import handle_delete_habit
from app.services.intent_handlers.habit.habit_handlers import handle_habit_modify

# Goal
from app.services.intent_handlers.goal.handle_goal_add import handle_goal_add
from app.services.intent_handlers.goal.handle_goals_list import handle_list_goals
from app.services.intent_handlers.goal.handle_goal_modify import handle_modify_goal
from app.services.intent_handlers.goal.handle_goal_delete import handle_delete_goal
from app.services.intent_handlers.goal.goal_handlers import handle_goal_modify

# Creator
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


# Misc
from app.services.intent_handlers.handle_search import handle_search
from app.services.intent_handlers.handle_smart_reply import handle_smart_reply
from app.services.intent_handlers.handle_notification import handle_notification_add
from app.services.intent_handlers.handle_fallback_ai import handle_fallback_ai

from app.services.update_device_state import handle_update_device_state
from app.services.save_message import save_user_message

from app.utils.intent_tracker import track_intent_usage


router = APIRouter(prefix="/intent-core", tags=["Intent Router"])

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


ALL_VALID_INTENTS = [
        "journal", "journal_list", "journal_delete", "journal_modify",
        "checkin", "checkin_list", "checkin_delete", "checkin_modify",
        "habit", "habit_list", "habit_modify", "habit_delete",
        "goal", "goal_list", "goal_modify", "goal_delete",
        "mark_goal_completed", "mark_habit_completed",
        "search", "notification", "smart_reply",
        "update_device",
        "fallback",
        "creator_mode", "creator_caption", "creator_content_ideas",
        "creator_weekly_plan", "creator_audience_helper", "creator_viral_reels",
        "creator_seo", "creator_email", "creator_time_planner",
        "creator_youtube_script", "creator_blog"
    ]

class IntentRequest(BaseModel):
    user_id: int
    message: str
    conversation_id: int = 1

@router.post("/detect-intent")
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

    # 🔍 Prompt for intent detection
    intent_prompt = f"""
    You are Neura, an assistant that detects user intent and extracts relevant IDs.

    You must always respond in this JSON format:

    {{
      "intent": "<one of: {', '.join(ALL_VALID_INTENTS)}>",
      "entities": {{
        "goal_id": <integer or null>,
        "habit_id": <integer or null>
      }}
    }}

    Examples:

    User: "I finished my goal to read 5 books."
    Response:
    {{
      "intent": "mark_goal_completed",
      "entities": {{
        "goal_id": 3,
        "habit_id": null
      }}
    }}

    User: "Mark my habit meditate as completed."
    Response:
    {{
      "intent": "mark_habit_completed",
      "entities": {{
        "goal_id": null,
        "habit_id": 5
      }}
    }}

    User input: "{payload.message}"

    JSON:
    """

    intent_raw = generate_ai_reply(intent_prompt)

    try:
        parsed = json.loads(intent_raw)
        intent = parsed["intent"].strip().lower()
        entities = parsed["entities"]
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid AI response: {e}")

    track_intent_usage(db, user, intent, payload.message)

    # 🧠 Route to correct intent handler

    # Habit
    if intent == "habit":
        result = await handle_add_habit(request, user, payload.message, db)
    elif intent == "habit_list":
        result = await handle_list_habits(request, user, payload.message, db)
    elif intent == "habit_modify":
        result = await handle_modify_habit(request, user, payload.message, db)
    elif intent == "habit_delete":
        result = await handle_delete_habit(request, user, payload.message, db)

    # Mark Habit Completed
    elif intent == "mark_habit_completed":
        habit_id = entities.get("habit_id")
        if not habit_id:
            raise HTTPException(status_code=400, detail="No habit_id provided by AI.")
        result = handle_habit_modify(user, habit_id, {"status": "completed"})

    # Checkin
    elif intent == "checkin":
        result = await handle_checkin_add(request, user, payload.message, db)
    elif intent == "checkin_list":
        result = await handle_checkin_list(request, user, payload.message, db)
    elif intent == "checkin_delete":
        result = await handle_checkin_delete(request, user, payload.message, db)
    elif intent == "checkin_modify":
        result = await handle_checkin_modify(request, user, payload.message, db)

    # Journal
    elif intent == "journal":
        result = await handle_journal_add(request, user, payload.message, db)
    elif intent == "journal_list":
        result = await handle_journal_list(request, user, payload.message, db)
    elif intent == "journal_delete":
        result = await handle_journal_delete(request, user, payload.message, db)
    elif intent == "journal_modify":
        result = await handle_journal_modify(request, user, payload.message, db)

    # Goal
    elif intent == "goal":
        result = await handle_add_goal(request, user, payload.message, db)
    elif intent == "goal_list":
        result = await handle_list_goals(request, user, payload.message, db)
    elif intent == "goal_modify":
        result = await handle_modify_goal(request, user, payload.message, db)
    elif intent == "goal_delete":
        result = await handle_delete_goal(request, user, payload.message, db)

    # Mark Goal Completed
    elif intent == "mark_goal_completed":
        goal_id = entities.get("goal_id")
        if not goal_id:
            raise HTTPException(status_code=400, detail="No goal_id provided by AI.")
        result = handle_goal_modify(user, goal_id, {"status": "completed"})

    # Creator
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

    # Misc
    elif intent == "search":
        result = await handle_search(request, user, payload.message, db)
    elif intent == "smart_reply":
        result = await handle_smart_reply(request, user, payload.message, db)
    elif intent == "notification":
        result = await handle_notification_add(request, user, payload.message, db)
    elif intent == "update_device":
        result = await handle_update_device_state(request, user, payload.message, db)

    # Fallback
    else:
        result = await handle_fallback_ai(request, db, user, {"query": payload.message})

    # ✅ Save user message to memory with conversation ID
    save_user_message(db, user, payload.message, conversation_id=payload.conversation_id)

    return result

