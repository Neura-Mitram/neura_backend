# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.

import os
import logging
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline

# Set cache paths (Hugging Face Spaces safe)
os.environ["HF_HOME"] = "/tmp/hf_cache"
os.environ["TRANSFORMERS_CACHE"] = "/tmp/hf_cache"

# Setup logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

hf_token = os.getenv("HUGGINGFACE_TOKEN")

if not hf_token:
    raise EnvironmentError("HUGGINGFACE_TOKEN not found in environment variables")

try:
    tokenizer = AutoTokenizer.from_pretrained(
        "mistralai/Mistral-7B-Instruct-v0.2",
        use_fast=False,
        token=hf_token
    )

    model = AutoModelForCausalLM.from_pretrained(
        "mistralai/Mistral-7B-Instruct-v0.2",
        device_map="auto",
        torch_dtype="auto",
        token=hf_token
    )

    generator = pipeline("text-generation", model=model, tokenizer=tokenizer)

except Exception as e:
    logger.exception("❌ Failed to load Mistral model/tokenizer")
    generator = None


def get_mistral_reply(prompt: str) -> str:
    """Generate a clean Mistral response from a raw prompt."""
    if generator is None:
        return "⚠️ AI is temporarily unavailable."

    try:
        result = generator(prompt, max_new_tokens=512, do_sample=True, temperature=0.7)[0]["generated_text"]
        return result[len(prompt):].strip() if result.startswith(prompt) else result.strip()
    except Exception as e:
        logger.exception("Mistral generation failed")
        return "⚠️ AI couldn't process the request right now. Please try again later."
