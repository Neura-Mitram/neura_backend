# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


from sqlalchemy.orm import Session
from app.models.user import User, TierLevel
from fastapi import HTTPException, Request
from app.utils.ai_engine import generate_ai_reply
from app.utils.auth_utils import ensure_token_user_match
from app.services.search_service import search_wikipedia, search_duckduckgo, format_results_for_summary
from app.utils.persona_prompt_wrapper import inject_persona_into_prompt
from app.utils.usage_tracker import track_usage_event

import logging
logger = logging.getLogger(__name__)

async def handle_search(request: Request, user: User, message: str, db: Session):

    query = message.strip()
    count = 5

    logger.info(f"🔍 User {user.id} searched: '{query}' | Tier: {user.tier.value}")

    # 🔍 Determine data source based on tier
    if user.tier == TierLevel.free:
        results = search_wikipedia(query, count)
        if not results:
            raise HTTPException(status_code=404, detail="No Wikipedia results found.")
        return {
            "query": query,
            "summary": results[0]["snippet"],  # just show wiki summary
            "results": results
        }

    elif user.tier in [TierLevel.basic, TierLevel.pro]:
        results = search_duckduckgo(query, count)
        if not results:
            raise HTTPException(status_code=404, detail="No DuckDuckGo results found.")
        prompt = format_results_for_summary(results, query)
        try:
            summary = generate_ai_reply(inject_persona_into_prompt(user, prompt, db))

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"AI summarization failed: {str(e)}")

        track_usage_event(db, user, category="handle_search")

        return {
            "query": query,
            "summary": summary.strip(),
            "results": results
        }

    else:
        raise HTTPException(status_code=403, detail="Invalid user tier")
