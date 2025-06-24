from fastapi import APIRouter, Query, HTTPException, Header, Depends
from app.utils.web_search import search_wikipedia
from app.utils.ai_engine import generate_ai_reply
from app.utils.auth_utils import ensure_token_user_match, require_token
from pydantic import BaseModel
from typing import List
from app.models.user_model import TierLevel
from app.utils.tier_check import ensure_minimum_tier

from app.utils.rate_limit_utils import get_tier_limit, limiter

router = APIRouter()


# ----- Request and Response Models -----
class WebSearchRequest(BaseModel):
    user_id: int
    query: str
    count: int = 5  # Optional, defaults to 5

class WebSearchResult(BaseModel):
    title: str
    snippet: str
    link: str

class WebSearchResponse(BaseModel):
    query: str
    summary: str
    results: List[WebSearchResult]

@limiter.limit(get_tier_limit)
@router.post("/neura/wiki-search", response_model=WebSearchResponse)
def web_search(
        payload: WebSearchRequest,
        user_data: dict = Depends(require_token)
):
    # ✅ Validate token-user match
    ensure_token_user_match(user_data["sub"], payload.user_id)

    # ⛔ Limit access to Basic+ tiers
    ensure_minimum_tier(payload.user_id, TierLevel.basic)

    # 🔒 Safety cap on result count (optional, set max limit)
    payload.count = min(payload.count, 10)

    # 🌐 Perform web search
    results = search_wikipedia(payload.query, payload.count)

    if not results:
        raise HTTPException(status_code=404, detail="No results found.")

    # ✍️ Build prompt for AI summary
    formatted = "\n\n".join(
        [f"Title: {r['title']}\nSnippet: {r['snippet']}\nLink: {r['link']}" for r in results]
    )
    prompt = f"Summarize the following web results for the query '{payload.query}':\n\n{formatted}\n\nGive a useful and concise answer."

    try:
        summary = generate_ai_reply(prompt)

        return WebSearchResponse(
            query=payload.query,
            summary=summary,
            results=results  # must be list of dicts with title, snippet, link
        )
    except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to generate summary: {str(e)}")



