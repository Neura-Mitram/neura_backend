# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.

import os
import logging
import requests
from langdetect import detect

logger = logging.getLogger(__name__)

# ✅ Load environment
if os.getenv("ENV") != "production":
    from dotenv import load_dotenv
    load_dotenv()

HF_TOKEN = os.getenv("HUGGINGFACE_TOKEN")
TRANSLATION_MODEL = "facebook/nllb-200-distilled-600M"

API_URL = f"https://api-inference.huggingface.co/models/{TRANSLATION_MODEL}"
HEADERS = {
    "Authorization": f"Bearer {HF_TOKEN}",
    "Content-Type": "application/json"
}

# ✅ Language code mapping
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


def translate(text: str, source_lang: str = "en", target_lang: str = "hi") -> str:
    """Translate text from source to target using Hugging Face Inference API."""
    try:
        src = LANG_MAP.get(source_lang, "eng_Latn")
        tgt = LANG_MAP.get(target_lang, "hin_Deva")

        payload = {
            "inputs": text,
            "parameters": {
                "src_lang": src,
                "tgt_lang": tgt
            }
        }

        response = requests.post(API_URL, headers=HEADERS, json=payload)
        response.raise_for_status()
        result = response.json()

        if isinstance(result, list) and "translation_text" in result[0]:
            return result[0]["translation_text"]
        else:
            logger.warning("[TranslationService] Unexpected response format.")
            return text

    except Exception as e:
        logger.warning(f"[TranslationService] Failed to translate: {e}")
        return text  # fallback


def detect_language(text: str) -> str:
    """Detect the ISO 639-1 language code of a string."""
    try:
        return detect(text)
    except Exception as e:
        logger.warning(f"[LanguageDetector] Failed to detect language: {e}")
        return "en"
