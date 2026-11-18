FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY workers/retrieval/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY workers /app/workers

EXPOSE 8081

CMD ["python", "-m", "uvicorn", "workers.retrieval.app:app", "--host", "0.0.0.0", "--port", "8081"]
