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

# Full image: sentence-transformers + torch + the pre-cached embedding model.
# Needs ~1GB RAM at runtime. For small hosts use Dockerfile.slim instead.
COPY requirements.txt requirements-embeddings.txt ./
RUN pip install --upgrade pip && pip install -r requirements-embeddings.txt && \
    python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')" || true

COPY . .

EXPOSE 8000

CMD ["sh", "-c", "python -m alembic upgrade head && \
     if [ \"$SEED_ON_START\" = \"1\" ]; then python -m app.scripts.seed || true; fi && \
     python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
