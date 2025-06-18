from app.utils.mistral_engine import get_mistral_reply

def generate_ai_reply(prompt: str):
    return get_mistral_reply(prompt)
