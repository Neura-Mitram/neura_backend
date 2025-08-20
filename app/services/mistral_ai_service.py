# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.

import os
import logging
import requests
from time import sleep

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
SPACE_URL = os.getenv(
    "LLM_SPACE_URL",
    "https://hf.space/embed/deepseek-ai/deepseek-vl2-small/api/predict"
)

# ---------------------------
# ✅ Headers
# ---------------------------

HEADERS = {"Content-Type": "application/json"}
if HF_TOKEN:
    HEADERS["Authorization"] = f"Bearer {HF_TOKEN}"

# ---------------------------
# ✅ Hugging Face Space Function
# ---------------------------

def get_mistral_reply(prompt: str) -> str:
    """
    Send a prompt to the DeepSeek Hugging Face Space and return the generated text.
    Function name kept unchanged for backward compatibility.
    Retries once in case of temporary failures.
    """

    if not SPACE_URL:
        logger.error("❌ Missing Hugging Face Space URL.")
        return "⚠️ AI Space URL not configured."

    try_count = 0
    max_retries = 2

    while try_count < max_retries:
        try:
            logger.info(f"🔁 Sending prompt to Hugging Face Space: {SPACE_URL}")
            response = requests.post(
                SPACE_URL,
                headers=HEADERS,
                json={"data": [prompt]},
                timeout=30
            )

            response.raise_for_status()
            result = response.json()

            # Parse the Space response
            if "data" in result and isinstance(result["data"], list):
                return result["data"][0]
            else:
                logger.warning("⚠️ Unexpected Space response format: %s", result)
                return "⚠️ Unexpected AI response format."

        except requests.exceptions.RequestException as e:
            try_count += 1
            logger.warning("⚠️ API request failed (attempt %d/%d). Retrying...", try_count, max_retries)
            sleep(1)  # brief pause before retry

            if try_count == max_retries:
                logger.exception("❌ Space API request failed after retries.")
                return "⚠️ AI is currently unreachable. Please try again later."

        except Exception as e:
            logger.exception("❌ Unexpected error in AI response.")
            return "⚠️ AI couldn't process your request."
