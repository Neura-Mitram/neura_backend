from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline

# Load once globally
tokenizer = AutoTokenizer.from_pretrained("mistralai/Mistral-7B-Instruct-v0.2")
model = AutoModelForCausalLM.from_pretrained("mistralai/Mistral-7B-Instruct-v0.2")

mistral_pipeline = pipeline("text-generation", model=model, tokenizer=tokenizer)

def get_mistral_reply(prompt: str) -> str:
    result = mistral_pipeline(prompt, max_new_tokens=256, do_sample=True, temperature=0.7)
    return result[0]["generated_text"]