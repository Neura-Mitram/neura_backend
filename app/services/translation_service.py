# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.



from transformers import pipeline
from langdetect import detect
import logging

logger = logging.getLogger(__name__)

# Load model (make sure you're using a multilingual NLLB model)
translator = pipeline("translation", model="facebook/nllb-200-distilled-600M")

# Mapping user-friendly codes to model lang codes
LANG_MAP = {

    "ar": "ara_Arab",  # Arabic
    "bg": "bul_Cyrl",  # Bulgarian
    "zh": "cmn_Hans",  # Mandarin Chinese
    "hr": "hrv_Latn",  # Croatian
    "cs": "ces_Latn",  # Czech
    "da": "dan_Latn",  # Danish
    "nl": "nld_Latn",  # Dutch
    "en": "eng_Latn",  # English
    "fil": "fil_Latn", # Filipino
    "fi": "fin_Latn",  # Finnish
    "fr": "fra_Latn",  # French
    "de": "deu_Latn",  # German
    "el": "ell_Grek",  # Greek
    "hi": "hin_Deva",  # Hindi
    "id": "ind_Latn",  # Indonesian
    "it": "ita_Latn",  # Italian
    "ja": "jpn_Jpan",  # Japanese
    "ko": "kor_Kore",  # Korean
    "ms": "msa_Latn",  # Malay
    "pl": "pol_Latn",  # Polish
    "pt": "por_Latn",  # Portuguese
    "ro": "ron_Latn",  # Romanian
    "ru": "rus_Cyrl",  # Russian
    "sk": "slk_Latn",  # Slovak
    "es": "spa_Latn",  # Spanish
    "sv": "swe_Latn",  # Swedish
    "ta": "tam_Taml",  # Tamil
    "tr": "tur_Latn",  # Turkish
    "uk": "ukr_Cyrl",  # Ukrainian
    "hu": "hun_Latn",  # Hungarian
    "no": "nor_Latn",  # Norwegian
    "vi": "vie_Latn",  # Vietnamese
    
    # ➕ Add more as needed later
}

def translate(text: str, source_lang: str = "en", target_lang: str = "hi") -> str:
    try:
        src = LANG_MAP.get(source_lang, "eng_Latn")
        tgt = LANG_MAP.get(target_lang, "hin_Deva")

        result = translator(text, src_lang=src, tgt_lang=tgt)
        return result[0]["translation_text"]
    except Exception as e:
        logger.warning(f"[TranslationService] Failed to translate: {e}")
        return text  # fallback to original


def detect_language(text: str) -> str:
    try:
        return detect(text)
    except Exception as e:
        logger.warning(f"[LanguageDetector] Failed to detect language: {e}")
        return "en"
