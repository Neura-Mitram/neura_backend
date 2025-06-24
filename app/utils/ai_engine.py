from app.utils.mistral_engine import get_mistral_reply

def generate_ai_reply(prompt: str):
    """
    Wrapper function to generate an AI reply from a given prompt using Mistral.
       This keeps your app logic clean and abstracted from model implementation.
    """
    return get_mistral_reply(prompt)
