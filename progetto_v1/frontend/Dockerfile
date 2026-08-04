FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia tutto il contenuto di src (inclusi i template)
COPY src/ .

EXPOSE 8004

# Comando per avviare il frontend
# Assicurati che frontend.py sia configurato per ascoltare sulla porta 8004
CMD ["python", "-m", "uvicorn", "frontend:app", "--host", "0.0.0.0", "--port", "8004"]