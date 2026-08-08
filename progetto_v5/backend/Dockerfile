FROM python:3.12-slim

WORKDIR /app

# 1. Aggiorna pip per evitare warning di deprecazione
RUN pip install --upgrade pip

# 2. Copia SOLO i requirements prima, per sfruttare la cache di Docker
COPY requirements.txt .

RUN apt-get update && apt-get install -y \
    gcc \
    libmariadb-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# 3. Installa le librerie Python
RUN pip install --no-cache-dir -r requirements.txt
RUN crawl4ai-setup

COPY src/ .

EXPOSE 8003

CMD ["python", "-m", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8003"]