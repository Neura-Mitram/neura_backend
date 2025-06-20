from fastapi import APIRouter, Query, HTTPException, Header, Depends
from app.utils.web_search import search_wikipedia
from app.utils.ai_engine import generate_ai_reply
from app.utils.jwt_utils import verify_access_token
router = APIRouter()

def require_token(authorization: str = Header(...)):
    token = authorization.replace("Bearer ", "")
    return verify_access_token(token)

@router.get("/neura/web-search")
def web_search(
    q: str = Query(..., description="Search query"),
    user_id: int = Query(..., description="User ID"),
    user_data: dict = Depends(require_token)
):
    if str(user_data["sub"]) != str(user_id):
        raise HTTPException(status_code=401, detail="Token/user mismatch")

    results = search_wikipedia(q)
    if not results:
        return {"message": "No results found."}

    formatted = "\n\n".join(
        [f"Title: {r['title']}\nSnippet: {r['snippet']}\nLink: {r['link']}" for r in results]
    )

    prompt = f"Summarize the following web results for the query '{q}':\n\n{formatted}\n\nGive a useful and concise answer."
    summary = generate_ai_reply(prompt)

    return {
        "query": q,
        "summary": summary,
        "results": results
    }

