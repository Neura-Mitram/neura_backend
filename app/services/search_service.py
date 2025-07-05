# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


from duckduckgo_search import DDGS
import wikipedia

def search_wikipedia(query: str, count: int = 5):
    try:
        search_results = wikipedia.search(query, results=count)
        result_data = []
        for title in search_results:
            try:
                summary = wikipedia.summary(title, sentences=2)
                result_data.append({
                    "title": title,
                    "snippet": summary,
                    "link": f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}"
                })
            except Exception:
                continue
        return result_data
    except Exception:
        return []

def search_duckduckgo(query: str, count: int = 5):
    results = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=count):
            results.append({
                "title": r.get("title", ""),
                "snippet": r.get("body", ""),
                "link": r.get("href", "")
            })
    return results

def format_results_for_summary(results: list, query: str) -> str:
    formatted = "\n\n".join(
        [f"Title: {r['title']}\nSnippet: {r['snippet']}\nLink: {r['link']}" for r in results]
    )
    return f"Summarize the following web results for the query '{query}':\n\n{formatted}\n\nGive a useful and concise answer."
