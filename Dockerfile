FROM python:3.10.9-slim

WORKDIR /code

# Install system dependencies
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# ✅ Fix Hugging Face cache permissions
ENV TRANSFORMERS_CACHE=/tmp/hf_cache
RUN mkdir -p /tmp/hf_cache

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the app
COPY app/ /code/app

# Run the app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
