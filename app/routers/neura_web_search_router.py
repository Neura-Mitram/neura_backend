from fastapi import APIRouter, Query
from utils.web_search import search_wikipedia
from utils.ai_engine import generate_ai_reply

router = APIRouter()


@router.get("/neura/web-search")
def web_search(q: str = Query(..., description="Search query")):
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
