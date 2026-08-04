FROM python:3.12-slim

WORKDIR /app

# 1. Aggiorna pip per evitare warning di deprecazione
RUN pip install --upgrade pip

# 2. Copia SOLO i requirements prima, per sfruttare la cache di Docker
COPY requirements.txt .

# 3. Installa le librerie Python
RUN pip install --no-cache-dir -r requirements.txt
RUN crawl4ai-setup
# 4. Installa le dipendenze di sistema di Playwright e Chromium
# Eseguito dopo i requirements così se cambi solo il tuo codice Python, 
# Docker salta questo passaggio lentissimo usando la cache.
# RUN playwright install-deps && playwright install chromium

# 5. Solo alla fine copia il codice sorgente
COPY src/ .

EXPOSE 8003

CMD ["python", "-m", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8003"]