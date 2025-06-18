import wikipedia

def search_wikipedia(query: str, max_results: int = 1):
    try:
        summary = wikipedia.summary(query, sentences=5)
        return [{
            "title": query.title(),
            "link": f"https://en.wikipedia.org/wiki/{query.replace(' ', '_')}",
            "snippet": summary
        }]
    except wikipedia.exceptions.DisambiguationError as e:
        return [{
            "title": "Disambiguation Error",
            "link": "",
            "snippet": f"Your query '{query}' is ambiguous. Try something more specific like: {e.options[:3]}"
        }]
    except wikipedia.exceptions.PageError:
        return [{
            "title": "No Page Found",
            "link": "",
            "snippet": f"No Wikipedia page found for '{query}'. Try a different term."
        }]
    except Exception as e:
        return [{
            "title": "Error",
            "link": "",
            "snippet": f"An error occurred: {str(e)}"
        }]
