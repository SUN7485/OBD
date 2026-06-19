# syntax=docker/dockerfile:1

FROM python:3.11-slim as base

WORKDIR /app

# System utilities for postgres and build tools
RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql-client build-essential gcc libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY . .

ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
