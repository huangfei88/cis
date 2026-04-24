FROM python:3.11-slim AS base

# SECURITY: run as non-root
RUN groupadd -g 1000 appuser && useradd -u 1000 -g appuser -s /sbin/nologin -M appuser

# Install curl for the Docker healthcheck (docker-compose uses `curl -f /health`)
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chown -R appuser:appuser /app
USER 1000:1000

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
