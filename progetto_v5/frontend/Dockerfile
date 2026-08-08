FROM python:3.12-slim

WORKDIR /app

RUN pip install --upgrade pip

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ .
COPY templates/ ./templates/

EXPOSE 8004

CMD ["python", "-m", "uvicorn", "frontend:app", "--host", "0.0.0.0", "--port", "8004"]