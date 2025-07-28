# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.

import os
import logging
import requests

# ---------------------------
# ✅ Logger Setup
# ---------------------------

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# ---------------------------
# ✅ Environment Variables
# ---------------------------

if os.getenv("ENV") != "production":
    from dotenv import load_dotenv
    load_dotenv()

HF_TOKEN = os.getenv("HUGGINGFACE_TOKEN")
MODEL_ID = os.getenv("LLM_MODEL", "sshleifer/tiny-gpt2")

# ---------------------------
# ✅ Hugging Face Inference API
# ---------------------------

API_URL = f"https://api-inference.huggingface.co/models/{MODEL_ID}"
HEADERS = {
    "Authorization": f"Bearer {HF_TOKEN}",
    "Content-Type": "application/json"
}


def get_mistral_reply(prompt: str) -> str:
    """Send a prompt to Hugging Face Inference API and return the generated text."""

    if not HF_TOKEN:
        logger.error("❌ Missing Hugging Face token.")
        return "⚠️ AI token not found."

    try:
        logger.info(f"🔁 Sending prompt to Hugging Face: {MODEL_ID}")
        response = requests.post(
            API_URL,
            headers=HEADERS,
            json={"inputs": prompt}
        )

        response.raise_for_status()
        result = response.json()

        if isinstance(result, list) and "generated_text" in result[0]:
            generated = result[0]["generated_text"]
            return generated[len(prompt):].strip() if generated.startswith(prompt) else generated.strip()
        else:
            logger.warning("⚠️ Unexpected response format.")
            return "⚠️ Unexpected AI response format."

    except requests.exceptions.RequestException as e:
        logger.exception("❌ API request failed.")
        return "⚠️ AI is currently unreachable. Please try again later."

    except Exception as e:
        logger.exception("❌ Unexpected error in AI response.")
        return "⚠️ AI couldn't process your request."
