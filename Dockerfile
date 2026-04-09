FROM python:3.11-slim

# 1. Install system dependencies for Postgres
# hadolint ignore=DL3008
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*
COPY . .

CMD ["uvicorn", "minitwit:app", "--host", "0.0.0.0", "--port", "5001"]