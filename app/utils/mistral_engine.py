from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
import os

hf_token = os.getenv("HUGGINGFACE_TOKEN")

if not hf_token:
    raise EnvironmentError("HUGGINGFACE_TOKEN not found in environment variables")

tokenizer = AutoTokenizer.from_pretrained(
    "mistralai/Mistral-7B-Instruct-v0.2",
    token=hf_token
)
model = AutoModelForCausalLM.from_pretrained(
    "mistralai/Mistral-7B-Instruct-v0.2",
    device_map="auto",
    torch_dtype="auto",
    token=hf_token
)

generator = pipeline("text-generation", model=model, tokenizer=tokenizer)

def get_mistral_reply(prompt: str) -> str:
    response = generator(prompt, max_new_tokens=512, do_sample=True, temperature=0.7)
    return response[0]["generated_text"]
