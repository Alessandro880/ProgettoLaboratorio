# Usa una versione di Python compatibile con il tuo progetto
FROM python:3.10-slim

# Imposta la directory di lavoro
WORKDIR /app

# Copia i requisiti e installa le dipendenze
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install chromium
RUN playwright install-deps
# Copia il codice sorgente (la cartella src) nella directory di lavoro
COPY src/ .

# Espone la porta del backend
EXPOSE 8003

# Comando per avviare il backend (assumendo l'uso di uvicorn per FastAPI)
# Se usi un altro comando per avviare server.py, modificalo qui
# Cambia l'ultima riga in questo modo:
    CMD ["python", "-m", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8003"] 