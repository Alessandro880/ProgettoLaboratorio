FROM python:3.12-slim

WORKDIR /app

# Aggiorna pip
RUN pip install --upgrade pip

# Sfrutta la cache copiando prima solo i requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia il codice sorgente
COPY src/ /app/src/

# Esponi la porta del tuo server
EXPOSE 11434

# Avvia FastAPI (assicurati che il percorso del file server.py sia corretto)
CMD ["python", "-m", "uvicorn", "src.server:app", "--host", "0.0.0.0", "--port", "11434"]