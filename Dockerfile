FROM python:3.10.9-slim

WORKDIR /code

RUN apt-get update && \
    apt-get install -y ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# ✅ Use writable directory in HF Spaces
ENV TRANSFORMERS_CACHE=/tmp/hf_cache
ENV HF_HOME=/tmp/hf_cache

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Optional preload (use /tmp as cache)
RUN python3 -c "from transformers import pipeline; pipeline('translation', model='facebook/nllb-200-distilled-600M')"
RUN python3 -c "from transformers import pipeline; pipeline('text-classification', model='j-hartmann/emotion-english-distilroberta-base')"

COPY . /code/

CMD python reset_db.py && uvicorn app.main:app --host 0.0.0.0 --port 7860


# Run app
#CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
#------------------------------------------------------------------------------------------


