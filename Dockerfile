FROM python:3.10.9-slim

WORKDIR /code

# System dependencies
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# ✅ Create writable cache + database directories
RUN mkdir -p /data/hf_cache && chmod -R 777 /data/hf_cache
RUN mkdir -p /data && chmod -R 777 /data

ENV TRANSFORMERS_CACHE=/data/hf_cache
ENV HF_HOME=/data/hf_cache

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy FastAPI app
COPY . /code/

# Run app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
