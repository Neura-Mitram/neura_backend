# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


from app.services.mistral_ai_service import get_mistral_reply

def generate_ai_reply(prompt: str):
    """
    Wrapper function to generate an AI reply from a given prompt using Mistral.
       This keeps your app logic clean and abstracted from model implementation.
    """
    return get_mistral_reply(prompt)
