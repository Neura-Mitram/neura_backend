# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
import os
import logging

# Setup logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

hf_token = os.getenv("HUGGINGFACE_TOKEN")

if not hf_token:
    raise EnvironmentError("HUGGINGFACE_TOKEN not found in environment variables")

# Load model and tokenizer
tokenizer = AutoTokenizer.from_pretrained(
    "mistralai/Mistral-7B-Instruct-v0.2",
    use_fast=False,  # ✅ Prevent tokenizer crash
    token=hf_token
)
model = AutoModelForCausalLM.from_pretrained(
    "mistralai/Mistral-7B-Instruct-v0.2",
    device_map="auto",
    torch_dtype="auto",
    token=hf_token
)

# Create text generation pipeline
generator = pipeline("text-generation", model=model, tokenizer=tokenizer)


def get_mistral_reply(prompt: str) -> str:
    """
    Generate a clean Mistral response from a raw prompt.
    Strips the prompt from the response if echoed.
    """
    try:
        result = generator(prompt, max_new_tokens=512, do_sample=True, temperature=0.7)[0]["generated_text"]
        # ✂️ Strip echoed prompt if present
        if result.startswith(prompt):
            result = result[len(prompt):]
        return result.strip()
    except Exception as e:
        logger.exception("Mistral generation failed")
        return "⚠️ AI couldn't process the request right now. Please try again later."
