# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.

from fastapi import Request
from sqlalchemy.orm import Session
from app.models.user import User
from app.utils.tier_logic import get_user_tier, is_voice_ping_allowed
from app.utils.ai_engine import generate_ai_reply
from app.utils.voice_sender import store_voice_weekly_summary
from app.services.search_service import search_wikipedia, search_duckduckgo, format_results_for_summary
import re
import datetime
from app.utils.persona_prompt_wrapper import inject_persona_into_prompt
from app.utils.usage_tracker import track_usage_event


def try_math_solver(query: str):
    try:
        expression = query.lower().replace("x", "*").replace("×", "*").replace("÷", "/")
        match = re.search(r"(?:what(?:'s| is)?|calculate|solve)\s+(.+)", expression)
        if match:
            expr = re.sub(r"[^\d.+\-*/()\s]", "", match.group(1))
            result = eval(expr, {"__builtins__": {}})
            return f"The answer is {round(result, 2)}."
    except Exception:
        pass
    return None



def try_date_question(query: str):
    try:
        if "day was" in query.lower():
            parts = query.lower().split("day was")
            date_str = parts[1].strip().replace("?", "")
            full_date_str = f"{date_str} {datetime.datetime.now().year}"
            parsed = datetime.datetime.strptime(full_date_str, "%B %d %Y")
            weekday = parsed.strftime("%A")
            return f"{date_str} falls on a {weekday}."
    except Exception:
        pass
    return None



async def handle_qna_semantic_summary(request: Request, user: User, message: str, db: Session):
    """
    Handles Q&A using math, date, Wikipedia or DuckDuckGo + Mistral summarization.
    """
    tier = get_user_tier(user)
    query = message.strip()

    # Step 0: Math or date shortcut
    math_result = try_math_solver(query)
    if math_result:
        return {"reply": math_result, "source": "math"}

    date_result = try_date_question(query)
    if date_result:
        return {"reply": date_result, "source": "date"}

    # Step 1: Wikipedia
    wiki_results = search_wikipedia(query)
    results_used = []
    source_used = ""

    if wiki_results:
        results_used = wiki_results[:3]
        source_used = "Wikipedia"
    else:
        # Step 2: DuckDuckGo fallback
        ddg_results = search_duckduckgo(query)
        if ddg_results:
            results_used = ddg_results[:5]
            source_used = "Web (DuckDuckGo)"
        else:
            return {
                "reply": f"Sorry, I couldn’t find info for: '{query}'. Try rephrasing?",
                "source": "none"
            }

    # Step 3: Mistral Summarize
    summary_prompt = format_results_for_summary(results_used, query)
    ai_summary = f"I found results from {source_used}, but couldn’t summarize them right now."
    try:
        final_prompt = inject_persona_into_prompt(user, summary_prompt, db)
        ai_summary = generate_ai_reply(final_prompt).strip()
    except Exception:
        pass  # fallback summary already defined

    # Step 4: Voice summary (Proactive)
    if is_voice_ping_allowed(user) and user.voice_nudges_enabled and user.preferred_delivery_mode == "voice":
        store_voice_weekly_summary(user, ai_summary, db)

    # Step 5: Track usage
    track_usage_event(db, user, category="qna_summary")

    # Final return (guaranteed path)
    return {
        "reply": ai_summary,
        "source": source_used,
        "tier": tier
    }
