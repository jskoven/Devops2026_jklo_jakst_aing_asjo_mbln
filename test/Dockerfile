# hadolint ignore=DL3008,DL3015
FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "minitwit:app", "--host", "0.0.0.0", "--port", "5001"]