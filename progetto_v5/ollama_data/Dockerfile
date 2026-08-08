FROM python:3.12-slim

WORKDIR /app

RUN pip install --upgrade pip

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ /app/src/

EXPOSE 11434

CMD ["python", "-m", "uvicorn", "src.server:app", "--host", "0.0.0.0", "--port", "11434"]