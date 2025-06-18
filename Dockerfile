FROM python:3.10.9-slim

WORKDIR /code

# Install system dependencies
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# ✅ Set safe writable cache for Hugging Face
ENV TRANSFORMERS_CACHE=/code/cache
RUN mkdir -p /code/cache

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the app
COPY app/ /code/app

# Start the app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
