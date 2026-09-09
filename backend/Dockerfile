FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUTF8=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/app/.hf

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Pre-cache the embedding model into the image so the first request is fast and
# the container works even with no outbound network at runtime.
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')" || true

COPY . .

EXPOSE 8000

# $PORT is provided by most PaaS (Railway/Render); default 8000 locally.
CMD ["sh", "-c", "alembic upgrade head && \
     if [ \"$SEED_ON_START\" = \"1\" ]; then python -m app.scripts.seed || true; fi && \
     uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
