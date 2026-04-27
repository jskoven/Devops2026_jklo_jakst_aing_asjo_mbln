FROM python:3.11-slim

# 1. Install system dependencies for Postgres
# hadolint ignore=DL3008
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 2. Create non-root user and group
# See article on running as non-root:
# https://oneuptime.com/blog/post/2026-02-20-docker-rootless-containers/view
RUN addgroup -S appgroup && adduser -S appuser -G appgroup

WORKDIR /app

# hadolint ignore=DL3013
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# 3. Give appuser ownership of the app directory
RUN chown -R appuser:appgroup /app

# 4. Switch to non-root user — everything below runs as appuser
USER appuser

CMD ["uvicorn", "minitwit:app", "--host", "0.0.0.0", "--port", "5001"]