import wikipedia
import logging

# Optional: Set language if your users are primarily non-English
# wikipedia.set_lang("en")

logging.basicConfig(level=logging.INFO)

def search_wikipedia(query: str, max_results: int = 1) -> list[dict]:
    """
    Searches Wikipedia and returns a list of summaries and links.
    Current-ly returns only 1 result per query for simplicity.
    """
    try:
        summary = wikipedia.summary(query, sentences=5)
        return [{
            "title": query.title(),
            "link": f"https://en.wikipedia.org/wiki/{query.replace(' ', '_')}",
            "snippet": summary
        }]

    except wikipedia.exceptions.DisambiguationError as e:
        logging.warning(f"DisambiguationError for query '{query}': {e.options[:3]}")
        return [{
            "title": "Disambiguation Error",
            "link": "",
            "snippet": f"'{query}' may refer to multiple topics. Try being more specific: {', '.join(e.options[:3])}"
        }]

    except wikipedia.exceptions.PageError:
        logging.info(f"No page found for query '{query}'")
        return [{
            "title": "No Page Found",
            "link": "",
            "snippet": f"No Wikipedia page found for '{query}'. Try another term."
        }]

    except Exception as e:
        logging.error(f"Error searching Wikipedia for '{query}': {str(e)}")
        return [{
            "title": "Error",
            "link": "",
            "snippet": f"An unexpected error occurred: {str(e)}"
        }]
