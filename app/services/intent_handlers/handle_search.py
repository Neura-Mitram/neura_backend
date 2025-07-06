# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


from sqlalchemy.orm import Session
from app.models.user import User, TierLevel
from fastapi import HTTPException, Request
from app.services.mistral_ai_service import get_mistral_reply
from app.utils.auth_utils import ensure_token_user_match
from app.services.search_service import search_wikipedia, search_duckduckgo, format_results_for_summary

import logging
logger = logging.getLogger(__name__)

async def handle_search(request: Request, user: User, message: str, db: Session):
    # Ensure token-user match
    # await ensure_token_user_match(request, user.id)

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
            summary = get_mistral_reply(prompt)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"AI summarization failed: {str(e)}")

        return {
            "query": query,
            "summary": summary.strip(),
            "results": results
        }

    else:
        raise HTTPException(status_code=403, detail="Invalid user tier")
