FROM python:3.10.9

# Set working directory
WORKDIR /code

# Install essential system packages (for librosa, torch, etc.)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    build-essential \
    curl \
    git \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Optional: Clean and setup huggingface cache dirs
RUN rm -rf /tmp/hf_cache && mkdir -p /tmp/hf_cache && chmod -R 777 /tmp/hf_cache
ENV TRANSFORMERS_CACHE=/tmp/hf_cache
ENV HF_HOME=/tmp/hf_cache

# Upgrade pip explicitly (recommended for modern builds)
RUN curl -sS https://bootstrap.pypa.io/get-pip.py | python3

# Copy and install requirements
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the code
COPY . /code/

# Default CMD for Hugging Face or local
CMD ["python", "reset_db.py", "&&", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]

# Run app
#CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
#------------------------------------------------------------------------------------------


