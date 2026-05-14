FROM python:3.11-slim

WORKDIR /app

COPY . /app

RUN pip install fastapi redis rq chromadb sentence-transformers

CMD ["python", "workers/worker.py"]