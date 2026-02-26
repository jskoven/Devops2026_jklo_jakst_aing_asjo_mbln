FROM python:3.10-slim

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

CMD python3 -c "import os; from db_handler import init_db; \
    if not os.path.exists('/data/minitwit.db'): \
    print('No DB found. Initializing...'); init_db()" && \
    uvicorn minitwit:app --host 0.0.0.0 --port 5001