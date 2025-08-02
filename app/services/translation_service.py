
# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.

import os
import logging
import httpx
from langdetect import detect
import asyncio

logger = logging.getLogger(__name__)

# ✅ Load environment
if os.getenv("ENV") != "production":
    from dotenv import load_dotenv
    load_dotenv()

# ✅ Language code mapping for NLLB
LANG_MAP = {
    "ar": "ara_Arab", "bg": "bul_Cyrl", "zh": "cmn_Hans", "hr": "hrv_Latn",
    "cs": "ces_Latn", "da": "dan_Latn", "nl": "nld_Latn", "en": "eng_Latn",
    "fil": "fil_Latn", "fi": "fin_Latn", "fr": "fra_Latn", "de": "deu_Latn",
    "el": "ell_Grek", "hi": "hin_Deva", "id": "ind_Latn", "it": "ita_Latn",
    "ja": "jpn_Jpan", "ko": "kor_Kore", "ms": "msa_Latn", "pl": "pol_Latn",
    "pt": "por_Latn", "ro": "ron_Latn", "ru": "rus_Cyrl", "sk": "slk_Latn",
    "es": "spa_Latn", "sv": "swe_Latn", "ta": "tam_Taml", "tr": "tur_Latn",
    "uk": "ukr_Cyrl", "hu": "hun_Latn", "no": "nor_Latn", "vi": "vie_Latn",
}

# ✅ Your private clone of the NLLB API Space
API_URL = "https://byshiladityamallick-neura-translation-api.hf.space/api/v4/translator"
SECRET_TOKEN = os.getenv("HUGGINGFACE_TOKEN")  # fallback if .env not loaded


async def translate(text: str, source_lang: str = "en", target_lang: str = "hi") -> str:
    """Translate text using Hugging Face NLLB API with retries, no signature changes."""

    src = LANG_MAP.get(source_lang, "eng_Latn")
    tgt = LANG_MAP.get(target_lang, "hin_Deva")

    headers = {
        "Authorization": f"Bearer {SECRET_TOKEN}"
    }

    max_retries = 3
    backoff_base = 2.0

    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(
                    API_URL,
                    params={"text": text, "source": src, "target": tgt},
                    headers=headers,
                )
                response.raise_for_status()
                result = response.json()
                return result.get("translation_text", text)

        except (httpx.HTTPError, httpx.RequestError) as e:
            logger.warning(f"[Translate Retry {attempt+1}/{max_retries}] Error: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(backoff_base ** attempt)  # 1s → 2s → 4s
            else:
                logger.error("[Translate] All retries failed. Returning original text.")
                return text



def detect_language(text: str) -> str:
    """Detect the ISO 639-1 language code of a string."""
    try:
        return detect(text)
    except Exception as e:
        logger.warning(f"[LanguageDetector] Failed to detect language: {e}")
        return "en"
